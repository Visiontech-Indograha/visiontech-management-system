import 'dart:io';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_ui.dart';
import '../records/my_records_screens.dart'
    show DocumentPickSource, PickedDocument, documentPickOverride, validateDocumentFile;

/// Batas lampiran per pengajuan (sama dengan API: 5 berkas).
const maxLampiran = 5;

/// Jenis pengajuan yang boleh punya lampiran; [path] sama dengan awalan rute API.
enum LampiranJenis {
  lembur('overtime', 'lembur'),
  mess('mess', 'mess');

  const LampiranJenis(this.path, this.label);
  final String path;
  final String label;

  /// Lampiran hanya bisa diubah selagi pengajuan menunggu keputusan.
  bool terkunci(String? status) => switch (this) {
    lembur => status != 'PENDING_PM' && status != 'PENDING',
    mess => status != 'REQUESTED',
  };
}

bool bisaTambahLampiran(int jumlah, {required bool terkunci}) => !terkunci && jumlah < maxLampiran;

bool bisaHapusLampiran(Map<String, dynamic> item, {required bool terkunci}) => !terkunci && item['mine'] == true;

/// Pesan awam untuk galat lampiran (409 dipetakan menurut kode API).
String pesanLampiran(Object e) {
  if (e is DioException && e.response?.statusCode == 409) {
    return switch (apiErrorCode(e)) {
      'LAMPIRAN_PENUH' => 'Lampiran sudah $maxLampiran berkas. Hapus satu dulu bila ingin menambah.',
      'LAMPIRAN_TERKUNCI' => 'Pengajuan ini sudah diputuskan atau dibatalkan, jadi lampirannya tidak bisa diubah lagi.',
      _ => apiErrorMessage(e),
    };
  }
  return apiErrorMessage(e, fallback: 'Lampiran gagal diproses. Coba lagi.');
}

String ukuranLampiran(num bytes) =>
    bytes < 1024 * 1024 ? '${(bytes / 1024).ceil()} KB' : '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';

/// Buka lembar lampiran untuk satu pengajuan.
Future<void> bukaLampiran(
  BuildContext context, {
  required LampiranJenis jenis,
  required String id,
  required String? status,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  builder: (_) => LampiranSheet(jenis: jenis, id: id, status: status),
);

class LampiranSheet extends ConsumerStatefulWidget {
  const LampiranSheet({super.key, required this.jenis, required this.id, required this.status});
  final LampiranJenis jenis;
  final String id;
  final String? status;

  @override
  ConsumerState<LampiranSheet> createState() => _LampiranSheetState();
}

class _LampiranSheetState extends ConsumerState<LampiranSheet> {
  List<Map<String, dynamic>>? _items;
  DateTime? _cachedAt;
  String? _error;
  bool _loading = true;
  bool _busy = false;
  late bool _locked = widget.jenis.terkunci(widget.status);

  String get _key => 'lampiran_${widget.jenis.path}_${widget.id}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final engine = ref.read(syncEngineProvider);
    try {
      final r = await engine.fetchList(_key, () => engine.api.attachments(widget.jenis.path, widget.id));
      if (!mounted) return;
      final kosongOffline = SyncEngine.neverCached(r.cachedAt);
      setState(() {
        _loading = false;
        _items = kosongOffline ? null : r.items;
        _cachedAt = kosongOffline ? null : r.cachedAt;
        _error = kosongOffline ? SyncEngine.offlineNoDataMessage : null;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = pesanLampiran(e);
        });
      }
    }
  }

  void _apply(List<Map<String, dynamic>> items) {
    ref.read(syncEngineProvider).cachePut(_key, items);
    setState(() {
      _items = items;
      _cachedAt = null;
    });
  }

  /// Galat 409 terkunci: sembunyikan tombol tambah/hapus.
  void _fail(Object e) {
    if (!mounted) return;
    if (e is DioException && apiErrorCode(e) == 'LAMPIRAN_TERKUNCI') setState(() => _locked = true);
    showVmsToast(context, pesanLampiran(e), error: true);
  }

  Future<PickedDocument?> _pick(DocumentPickSource source) async {
    final override = documentPickOverride;
    if (override != null) return override(source);
    if (source == DocumentPickSource.file) {
      final files = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'webp', 'heic'],
      );
      if (files.isEmpty || files.first.path == null) return null;
      return (path: files.first.path!, name: files.first.name);
    }
    final shot = await ImagePicker().pickImage(
      source: source == DocumentPickSource.camera ? ImageSource.camera : ImageSource.gallery,
    );
    return shot == null ? null : (path: shot.path, name: shot.name);
  }

  Future<void> _add(DocumentPickSource source) async {
    if (_busy) return;
    final PickedDocument? picked;
    try {
      picked = await _pick(source);
    } catch (_) {
      if (mounted) showVmsToast(context, 'Berkas tidak bisa dipilih. Coba lagi.', error: true);
      return;
    }
    if (picked == null || !mounted) return;
    final file = File(picked.path);
    final problem = validateDocumentFile(name: picked.name, bytes: await file.length());
    if (problem != null) {
      if (mounted) showVmsToast(context, problem, error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      final fileId = await api.uploadFile(file);
      _apply(await api.addAttachment(widget.jenis.path, widget.id, fileId));
    } catch (e) {
      _fail(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _remove(Map<String, dynamic> item) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus lampiran?'),
        content: Text('"${item['file_name']}" akan dihapus dari pengajuan ini.'),
        actions: [
          TextButton(
            style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(48, 48)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      _apply(await api.removeAttachment(widget.jenis.path, widget.id, '${item['file_id']}'));
    } catch (e) {
      _fail(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _open(Map<String, dynamic> item) async {
    final fileId = '${item['file_id']}';
    final mime = item['mime_type'] as String? ?? '';
    try {
      if (mime.startsWith('image/')) {
        await showVmsImageViewer(context, fileId);
        return;
      }
      final bytes = await ref.read(syncEngineProvider).api.fileBytes(fileId, variant: 'view');
      final name = '${item['file_name']}';
      final dot = name.lastIndexOf('.');
      final ext = dot < 0 ? 'bin' : name.substring(dot + 1);
      final f = File('${(await getTemporaryDirectory()).path}/$fileId.$ext');
      await f.writeAsBytes(bytes, flush: true);
      final res = await OpenFilex.open(f.path);
      if (res.type != ResultType.done && mounted) {
        showVmsToast(context, 'Tidak ada aplikasi untuk membuka berkas ini.', error: true);
      }
    } catch (e) {
      if (mounted) showVmsToast(context, pesanLampiran(e), error: true);
    }
  }

  Widget _tombol(Key key, IconData icon, String label, DocumentPickSource s) => SizedBox(
    height: 48,
    child: OutlinedButton.icon(
      key: key,
      onPressed: _busy ? null : () => _add(s),
      icon: Icon(icon),
      label: Text(label),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.85),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Lampiran ${widget.jenis.label}',
                style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700, fontSize: 18),
              ),
              const SizedBox(height: 4),
              Text('Bukti pendukung, misalnya foto atau PDF. Maksimal $maxLampiran berkas.', style: VmsTextStyles.bodySm),
              const SizedBox(height: 12),
              if (_loading)
                const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))
              else if (items == null)
                Column(
                  key: const Key('lampiran-galat'),
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_error ?? 'Lampiran belum bisa dimuat.', style: VmsTextStyles.bodySm),
                    const SizedBox(height: 8),
                    SizedBox(height: 48, child: FilledButton(onPressed: _load, child: const Text('Coba lagi'))),
                  ],
                )
              else ...[
                if (_cachedAt != null)
                  const Padding(
                    padding: EdgeInsets.only(bottom: 8),
                    child: Text('Data terakhir yang tersimpan di HP. Sambungkan internet untuk memperbarui.'),
                  ),
                if (items.isEmpty)
                  const Padding(
                    key: Key('lampiran-kosong'),
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Row(
                      children: [
                        Icon(Icons.attach_file_rounded),
                        SizedBox(width: 8),
                        Expanded(child: Text('Belum ada lampiran.')),
                      ],
                    ),
                  ),
                for (final it in items) _baris(it),
                const SizedBox(height: 8),
                if (_locked)
                  const Text(
                    'Pengajuan ini sudah diputuskan, jadi lampiran tidak bisa diubah.',
                    key: Key('lampiran-terkunci'),
                  )
                else if (!bisaTambahLampiran(items.length, terkunci: _locked))
                  const Text('Lampiran sudah $maxLampiran berkas. Hapus satu dulu bila ingin menambah.')
                else ...[
                  if (_busy) const Padding(padding: EdgeInsets.only(bottom: 8), child: LinearProgressIndicator()),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _tombol(const Key('lampiran-kamera'), Icons.photo_camera_rounded, 'Kamera', DocumentPickSource.camera),
                      _tombol(const Key('lampiran-galeri'), Icons.photo_library_rounded, 'Galeri', DocumentPickSource.gallery),
                      _tombol(const Key('lampiran-berkas'), Icons.description_rounded, 'Berkas', DocumentPickSource.file),
                    ],
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _baris(Map<String, dynamic> it) {
    final dapatHapus = bisaHapusLampiran(it, terkunci: _locked);
    final mime = it['mime_type'] as String? ?? '';
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 56),
      child: Row(
        children: [
          Expanded(
            child: InkWell(
              key: Key('lampiran-buka-${it['file_id']}'),
              onTap: () => _open(it),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    Icon(mime.startsWith('image/') ? Icons.image_rounded : Icons.description_rounded),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${it['file_name']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                          Text(ukuranLampiran((it['byte_size'] as num?) ?? 0), style: VmsTextStyles.bodySm),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (dapatHapus)
            IconButton(
              key: Key('lampiran-hapus-${it['file_id']}'),
              tooltip: 'Hapus lampiran',
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed: _busy ? null : () => _remove(it),
              icon: const Icon(Icons.delete_outline_rounded),
            ),
        ],
      ),
    );
  }
}
