import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_list_filter.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

String _fmt(dynamic iso) => iso == null ? '-' : _date.format(DateTime.parse(iso as String));

/// Label status lembur untuk karyawan.
String overtimeStatusLabel(String status) => switch (status) {
  'PENDING' => 'Menunggu persetujuan',
  'APPROVED' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  _ => status,
};

/// Label status dokumen pribadi menurut masa berlakunya.
/// Nama jenis dokumen yang ramah dibaca (sama dengan web); jenis lain ditampilkan apa adanya.
String documentTypeLabel(String type) => switch (type) {
  'KTP' => 'KTP',
  'SIM_A' => 'SIM A',
  'SIM_B1' => 'SIM B I',
  'SIM_B2' => 'SIM B II',
  'SIM_C' => 'SIM C',
  'MCU' => 'Medical check-up',
  'SERTIFIKAT_K3' => 'Sertifikat K3',
  'SERTIFIKAT_TEKNIS' => 'Sertifikat teknis',
  'KONTRAK_PKWT' => 'Kontrak PKWT',
  _ => type.replaceAll('_', ' '),
};

String documentStatusLabel(String status) => switch (status) {
  'active' => 'Berlaku',
  'extended' => 'Diperpanjang',
  'expired' => 'Kedaluwarsa',
  _ => status,
};

/// Dokumen yang akan habis dalam [days] hari (atau sudah lewat) perlu diperingatkan.
bool documentExpiresSoon(Map<String, dynamic> doc, DateTime today, {int days = 30}) {
  final raw = doc['expired_at'] as String?;
  if (raw == null || doc['status'] != 'active') return false;
  final left = DateTime.parse(raw).difference(DateTime(today.year, today.month, today.day)).inDays;
  return left <= days;
}

/// Kerangka layar daftar sederhana: judul, muat ulang, kosong/galat, lalu isi.
class _ListScreen extends ConsumerStatefulWidget {
  const _ListScreen({
    required this.title,
    required this.empty,
    required this.load,
    required this.builder,
    this.action,
  });

  final String title;
  final String empty;
  final Future<List<Map<String, dynamic>>> Function(WidgetRef ref) load;
  final Widget Function(Map<String, dynamic> item) builder;

  /// Aksi di bawah judul (mis. Unggah); menerima `reload` untuk memuat ulang daftar setelah aksi selesai.
  final Widget Function(BuildContext context, Future<void> Function() reload)? action;

  @override
  ConsumerState<_ListScreen> createState() => _ListScreenState();
}

class _ListScreenState extends ConsumerState<_ListScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;
  final _query = ListQuery();

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await widget.load(ref);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = apiErrorMessage(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            HeroHeader(eyebrow: 'Layanan', title: widget.title, horizontal: 4),
            if (widget.action != null) widget.action!(context, _reload),
            if (_loading)
              const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            if (!_loading && _error == null && _items.isEmpty)
              Padding(padding: const EdgeInsets.all(32), child: Center(child: Text(widget.empty))),
            if (_items.length > 3) VmsSearchBar(query: _query, hint: 'Cari...'),
            ListenableBuilder(
              listenable: _query,
              builder: (context, _) {
                final all = _query.filter<Map<String, dynamic>>(
                  _items,
                  (it) => [for (final v in it.values) if (v is String || v is num) v],
                );
                return Column(
                  children: [
                    if (all.isEmpty && _items.isNotEmpty) VmsNoMatch(query: _query),
                    for (final item in _query.visible(all))
                      Padding(padding: const EdgeInsets.only(top: 12), child: widget.builder(item)),
                    VmsLoadMore(query: _query, total: all.length),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

String _employeeId(WidgetRef ref) {
  final s = ref.read(authControllerProvider);
  return s is AuthAuthenticated ? s.user.employeeId : '';
}

/// Riwayat dan status pengajuan lembur milik sendiri.
class OvertimeHistoryScreen extends StatelessWidget {
  const OvertimeHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) => _ListScreen(
    title: 'Riwayat Lembur',
    empty: 'Belum ada pengajuan lembur. Ajukan lembur lewat Rencana kerja harian (tombol Ajukan lembur).',
    load: (ref) => ref.read(syncEngineProvider).api.myOvertime(),
    builder: (o) => SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${_fmt(o['work_date'])} · ${o['hours']} jam',
            style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(o['reason'] as String? ?? '', style: VmsTextStyles.bodySm),
          const SizedBox(height: 8),
          Chip(label: Text(overtimeStatusLabel(o['status'] as String))),
          if ((o['review_note'] as String?)?.isNotEmpty == true)
            Text('Catatan: ${o['review_note']}', style: VmsTextStyles.bodySm),
        ],
      ),
    ),
  );
}

/// Ikon, label, dan ekstensi berkas dari tipe MIME asli (dipakai ikon & pratinjau dokumen).
({IconData icon, String label, String ext}) documentFileKind(String? mime) => switch (mime) {
  'application/pdf' => (icon: Icons.picture_as_pdf_rounded, label: 'PDF', ext: 'pdf'),
  'application/msword' => (icon: Icons.description_rounded, label: 'DOC', ext: 'doc'),
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document' => (
    icon: Icons.description_rounded,
    label: 'DOCX',
    ext: 'docx',
  ),
  _ => (icon: Icons.insert_drive_file_rounded, label: 'Berkas', ext: 'bin'),
};

/// Dokumen pribadi (SIM, sertifikat, dll.) beserta masa berlakunya; karyawan dapat mengunggah dokumennya sendiri.
class DocumentsScreen extends StatelessWidget {
  const DocumentsScreen({super.key});

  @override
  Widget build(BuildContext context) => _ListScreen(
    title: 'Dokumen Saya',
    empty: 'Belum ada dokumen yang tercatat. Ketuk "Unggah dokumen" untuk menambahkan.',
    load: (ref) => ref.read(syncEngineProvider).api.myDocuments(_employeeId(ref)),
    action: (context, reload) => Padding(
      padding: const EdgeInsets.only(top: 12),
      child: PrimaryAction(
        key: const Key('dokumen-unggah'),
        label: 'Unggah dokumen',
        icon: Icons.upload_file_rounded,
        onTap: () async {
          final saved = await Navigator.of(
            context,
          ).push<bool>(MaterialPageRoute(builder: (_) => const DocumentUploadScreen()));
          if (saved == true) await reload();
        },
      ),
    ),
    builder: (d) {
      final soon = documentExpiresSoon(d, DateTime.now());
      return SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              documentTypeLabel(d['doc_type'] as String),
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              d['expired_at'] == null
                  ? 'Berlaku sejak ${_fmt(d['active_at'])}'
                  : 'Berlaku ${_fmt(d['active_at'])} s.d. ${_fmt(d['expired_at'])}',
              style: VmsTextStyles.bodySm,
            ),
            if (d['file_id'] != null) ...[
              const SizedBox(height: 8),
              _DocumentFile(fileId: d['file_id'] as String, mime: d['file_mime'] as String?),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(label: Text(documentStatusLabel(d['status'] as String))),
                if (soon) const Chip(label: Text('Segera habis')),
              ],
            ),
          ],
        ),
      );
    },
  );
}

/// Pratinjau berkas dokumen. Gambar tampil sebagai thumbnail; PDF/DOC/DOCX tampil sebagai ikon tipe berkas
/// (tanpa meminta thumbnail yang memang tidak ada). Ketuk: gambar diperbesar, berkas dibuka di aplikasi lain.
class _DocumentFile extends ConsumerWidget {
  const _DocumentFile({required this.fileId, required this.mime});
  final String fileId;
  final String? mime;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isImage = mime?.startsWith('image/') ?? false;
    final kind = documentFileKind(mime);

    Future<void> open() async {
      if (isImage) {
        await showVmsImageViewer(context, fileId);
        return;
      }
      try {
        final bytes = await ref.read(syncEngineProvider).api.fileBytes(fileId, variant: 'view');
        final file = File('${(await getTemporaryDirectory()).path}/$fileId.${kind.ext}');
        await file.writeAsBytes(bytes, flush: true);
        final res = await OpenFilex.open(file.path);
        if (res.type != ResultType.done && context.mounted) {
          showVmsToast(context, 'Tidak ada aplikasi untuk membuka ${kind.label}.', error: true);
        }
      } catch (e) {
        if (context.mounted) showVmsToast(context, apiErrorMessage(e), error: true);
      }
    }

    return InkWell(
      key: const Key('dokumen-berkas'),
      onTap: open,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          height: 120,
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.05),
          child: isImage
              ? VmsNetworkImage(
                  fileId: fileId,
                  fallback: const Center(child: Icon(Icons.broken_image_outlined, color: Colors.black38)),
                )
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(kind.icon, size: 40, color: VmsColors.brand700),
                    const SizedBox(height: 6),
                    Text(kind.label, style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700)),
                    Text('Ketuk untuk membuka', style: VmsTextStyles.bodySm),
                  ],
                ),
        ),
      ),
    );
  }
}

/// Sumber berkas unggahan dokumen: kamera, galeri foto, atau berkas (PDF/DOC/DOCX).
enum DocumentPickSource { camera, gallery, file }

/// Berkas yang dipilih: jalur lokal dan nama asli berkas.
typedef PickedDocument = ({String path, String name});

/// Uji: pengganti pemilih kamera/galeri/berkas (plugin native tidak tersedia di uji widget).
Future<PickedDocument?> Function(DocumentPickSource source)? documentPickOverride;

/// Batas dan jenis berkas, sama dengan API `/files/upload` (maks. 10 MB; JPEG, PNG, WEBP, HEIC, PDF, DOC, DOCX).
const documentUploadMaxBytes = 10 * 1024 * 1024;
const documentUploadExtensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'webp', 'heic'];

/// Jenis dokumen yang dapat dipilih karyawan (kode baku API; label memakai [documentTypeLabel]).
const documentUploadTypes = [
  'KTP',
  'SIM_A',
  'SIM_B1',
  'SIM_B2',
  'SIM_C',
  'SERTIFIKAT_K3',
  'SERTIFIKAT_TEKNIS',
  'KONTRAK_PKWT',
  'MCU',
];

/// Null bila berkas boleh diunggah; selain itu kalimat galat untuk teknisi.
String? validateDocumentFile({required String name, required int bytes}) {
  if (bytes == 0) return 'Berkas kosong. Pilih berkas lain.';
  final dot = name.lastIndexOf('.');
  final ext = dot < 0 ? '' : name.substring(dot + 1).toLowerCase();
  if (!documentUploadExtensions.contains(ext)) {
    return 'Jenis berkas tidak didukung. Pilih PDF, DOC/DOCX, JPG, PNG, WEBP, atau HEIC.';
  }
  if (bytes > documentUploadMaxBytes) return 'Ukuran berkas melebihi batas 10 MB.';
  return null;
}

String _ukuranBerkas(int bytes) =>
    bytes < 1024 * 1024 ? '${(bytes / 1024).ceil()} KB' : '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';

/// Unggah dokumen pribadi: pilih jenis, berkas (kamera/galeri/berkas), dan tanggal kedaluwarsa opsional.
/// Kembali dengan `true` bila dokumen tersimpan.
class DocumentUploadScreen extends ConsumerStatefulWidget {
  const DocumentUploadScreen({super.key});

  @override
  ConsumerState<DocumentUploadScreen> createState() => _DocumentUploadScreenState();
}

class _DocumentUploadScreenState extends ConsumerState<DocumentUploadScreen> {
  String? _type;
  DateTime? _expiry;
  PickedDocument? _picked;
  int _size = 0;
  String? _pickError;
  String? _error;
  bool _busy = false;
  bool _saving = false; // berkas sudah terkirim, dokumen sedang dicatat
  double? _progress;

  bool get _canSubmit => !_busy && _type != null && _picked != null;

  Future<PickedDocument?> _pickFromDevice(DocumentPickSource source) async {
    if (source == DocumentPickSource.file) {
      final files = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: documentUploadExtensions);
      if (files.isEmpty) return null;
      final f = files.first;
      final path = f.path;
      return path == null ? null : (path: path, name: f.name);
    }
    final shot = await ImagePicker().pickImage(
      source: source == DocumentPickSource.camera ? ImageSource.camera : ImageSource.gallery,
    );
    return shot == null ? null : (path: shot.path, name: shot.name);
  }

  Future<void> _pick(DocumentPickSource source) async {
    final PickedDocument? picked;
    try {
      final override = documentPickOverride;
      picked = override != null ? await override(source) : await _pickFromDevice(source);
    } catch (_) {
      if (mounted) setState(() => _pickError = 'Berkas tidak bisa dipilih. Coba lagi.');
      return;
    }
    if (picked == null || !mounted) return; // dibatalkan
    final size = await File(picked.path).length();
    if (!mounted) return;
    final error = validateDocumentFile(name: picked.name, bytes: size);
    setState(() {
      _pickError = error;
      _picked = error == null ? picked : null;
      _size = size;
      _error = null;
    });
  }

  Future<void> _pickExpiry() async {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = await showDatePicker(
      context: context,
      initialDate: _expiry ?? today,
      firstDate: today,
      lastDate: DateTime(now.year + 30),
    );
    if (d != null && mounted) setState(() => _expiry = d);
  }

  Future<void> _submit() async {
    final picked = _picked;
    final type = _type;
    if (!_canSubmit || picked == null || type == null) return;
    final employeeId = _employeeId(ref);
    if (employeeId.isEmpty) {
      setState(() => _error = 'Akun Anda belum terhubung ke data karyawan.');
      return;
    }
    setState(() {
      _busy = true;
      _saving = false;
      _progress = 0;
      _error = null;
    });
    try {
      final api = ref.read(syncEngineProvider).api;
      final fileId = await api.uploadFile(
        File(picked.path),
        onProgress: (sent, total) {
          if (mounted && total > 0) setState(() => _progress = sent / total);
        },
      );
      if (mounted) setState(() => _saving = true);
      await api.uploadDocument(employeeId, docType: type, fileId: fileId, expiredAt: _expiry);
      if (!mounted) return;
      showVmsToast(context, 'Dokumen disimpan.');
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _saving = false;
          _progress = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final picked = _picked;
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
        children: [
          const HeroHeader(eyebrow: 'Dokumen Saya', title: 'Unggah dokumen', horizontal: 4),
          SurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                VmsSelectField<String>(
                  label: 'Jenis dokumen',
                  icon: Icons.badge_rounded,
                  placeholder: 'Pilih jenis',
                  options: [for (final t in documentUploadTypes) VmsOption(t, documentTypeLabel(t))],
                  value: _type,
                  onChanged: _busy ? (_) {} : (v) => setState(() => _type = v),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        key: const Key('dokumen-kedaluwarsa'),
                        onPressed: _busy ? null : _pickExpiry,
                        icon: const Icon(Icons.event_rounded),
                        label: Text(
                          _expiry == null ? 'Berlaku sampai (opsional)' : 'Berlaku sampai ${_date.format(_expiry!)}',
                        ),
                      ),
                    ),
                    if (_expiry != null)
                      IconButton(
                        tooltip: 'Hapus tanggal',
                        onPressed: _busy ? null : () => setState(() => _expiry = null),
                        icon: const Icon(Icons.close_rounded),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        key: const Key('dokumen-kamera'),
                        onPressed: _busy ? null : () => _pick(DocumentPickSource.camera),
                        icon: const Icon(Icons.photo_camera_rounded),
                        label: const Text('Kamera'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        key: const Key('dokumen-galeri'),
                        onPressed: _busy ? null : () => _pick(DocumentPickSource.gallery),
                        icon: const Icon(Icons.photo_library_rounded),
                        label: const Text('Galeri'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        key: const Key('dokumen-berkas-pilih'),
                        onPressed: _busy ? null : () => _pick(DocumentPickSource.file),
                        icon: const Icon(Icons.attach_file_rounded),
                        label: const Text('Berkas'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'PDF, DOC/DOCX, JPG, PNG, WEBP, atau HEIC · maks. 10 MB',
                  style: VmsTextStyles.bodySm.copyWith(color: Colors.black54),
                ),
                if (picked != null) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Icon(Icons.check_circle_rounded, color: Colors.green),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${picked.name} (${_ukuranBerkas(_size)})',
                          key: const Key('dokumen-terpilih'),
                          style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                ],
                if (_pickError != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(_pickError!, key: const Key('dokumen-galat-berkas'), style: const TextStyle(color: Colors.red)),
                  ),
              ],
            ),
          ),
          if (_busy) ...[
            const SizedBox(height: 12),
            LinearProgressIndicator(value: _saving ? null : _progress),
            const SizedBox(height: 6),
            Text(
              _saving
                  ? 'Menyimpan dokumen…'
                  : 'Mengunggah berkas… ${((_progress ?? 0) * 100).round()}%',
              key: const Key('dokumen-progres'),
              style: VmsTextStyles.bodySm,
            ),
          ],
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, key: const Key('dokumen-galat'), style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 16),
          PrimaryAction(
            key: const Key('dokumen-simpan'),
            label: 'Simpan dokumen',
            icon: Icons.cloud_upload_rounded,
            busy: _busy,
            onTap: _canSubmit ? _submit : null,
          ),
          if (!_canSubmit && !_busy)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Pilih jenis dokumen dan berkasnya dahulu.',
                style: VmsTextStyles.bodySm.copyWith(color: Colors.black54),
              ),
            ),
        ],
      ),
    );
  }
}
