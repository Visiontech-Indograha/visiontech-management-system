import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_text_field.dart';
import '../../shared/ui/vms_ui.dart';
import 'photo_slots.dart' show PhotoOrigin, pickReportPhoto;
import 'survey_screen.dart' show openReportFile;

/// Ketua tim menandatangani BAST order (Milestone 8): ringkasan wajib, kendala, foto realisasi, tanda tangan.
/// Setelah itu PM mengesahkan di web; sidik SHA-256 & QR verifikasi dibuat server.
class BastSignScreen extends ConsumerStatefulWidget {
  const BastSignScreen({super.key, required this.completionId});

  final String completionId;

  @override
  ConsumerState<BastSignScreen> createState() => _BastSignScreenState();
}

class _BastSignScreenState extends ConsumerState<BastSignScreen> {
  final _summary = TextEditingController();
  final _obstacles = TextEditingController();
  final _pad = GlobalKey<_SignaturePadState>();
  final List<String> _photoPaths = [];

  /// Foto realisasi yang sudah tersimpan di order (ikut dikirim saat tanda tangan ulang agar tidak hilang).
  final List<String> _photoIds = [];
  Map<String, dynamic>? _order;
  Uint8List? _savedSignature;
  String? _error;
  bool _busy = false;
  bool _picking = false; // cegah kamera terbuka dua kali bila tombol diketuk beruntun

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _summary.dispose();
    _obstacles.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = ref.read(syncEngineProvider).api;
      final order = await api.workCompletion(widget.completionId);
      final sig = order['leader_signed_at'] == null
          ? null
          : await api.completionSignature(widget.completionId, 'leader');
      if (!mounted) return;
      _savedSignature = sig == null ? null : Uint8List.fromList(sig);
      setState(() {
        _order = order;
        _summary.text = '${order['summary_notes'] ?? ''}';
        _obstacles.text = '${order['obstacles'] ?? ''}';
        _photoIds
          ..clear()
          ..addAll([
            for (final ph
                in (order['realization_photos_json'] as List? ?? const []))
              ph is Map ? '${ph['file_id']}' : '$ph',
          ]);
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  /// Foto tersimpan di order: hapus langsung dari server setelah dikonfirmasi.
  Future<void> _removeSaved(String fileId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus foto hasil kerja?'),
        content: const Text('Foto dihapus dari serah terima pekerjaan ini.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref
          .read(syncEngineProvider)
          .api
          .deleteCompletionPhoto(widget.completionId, fileId);
      if (mounted) setState(() => _photoIds.remove(fileId));
      _snack('Foto hasil kerja dihapus.');
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    }
  }

  void _snack(String text, {bool error = false}) =>
      showVmsToast(context, text, error: error);

  bool _exporting = false;

  /// Slide laporan (.pptx) berisi foto tiap pekerjaan, keterangan, dan status — dibuka di HP / dibagikan.
  Future<void> _slides() async {
    setState(() => _exporting = true);
    try {
      final bytes = await ref
          .read(syncEngineProvider)
          .api
          .completionSlides(widget.completionId);
      final msg = await openReportFile(
        bytes,
        'Laporan-${widget.completionId.substring(0, 8)}.pptx',
      );
      if (msg != null) _snack(msg, error: true);
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  /// Work completion (.docx) untuk ketua: hanya item timnya (server membatasi). Disimpan ke folder dokumen aplikasi
  /// lalu dibuka; dari pemilih aplikasi itu pengguna bisa membagikannya.
  Future<void> _bastDocx() async {
    setState(() => _exporting = true);
    try {
      final bytes = await ref
          .read(syncEngineProvider)
          .api
          .completionBastDocx(widget.completionId);
      final dir = await getApplicationDocumentsDirectory();
      final name = 'Work-completion-${widget.completionId.substring(0, 8)}.docx';
      final file = File('${dir.path}/$name');
      await file.writeAsBytes(bytes, flush: true);
      final opened = await OpenFilex.open(file.path);
      if (opened.type != ResultType.done) {
        _snack('Tersimpan di aplikasi sebagai $name. Pasang Word/WPS untuk membukanya.');
      }
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (_summary.text.trim().isEmpty) return _snack('Isi ringkasan pekerjaan.');
    final png = await _pad.currentState?.toPng();
    if (png == null) return _snack('Bubuhkan tanda tangan Anda.');
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      final ids = [
        ..._photoIds,
        for (final path in _photoPaths) await api.uploadFile(File(path)),
      ];
      await api.signCompletion(
        widget.completionId,
        signaturePng: base64Encode(png),
        summary: _summary.text.trim(),
        obstacles: _obstacles.text.trim().isEmpty
            ? null
            : _obstacles.text.trim(),
        photoFileIds: ids,
      );
      _snack('Serah terima ditandatangani. Menunggu persetujuan atasan.');
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    final locked = order?['pm_signed_at'] != null;
    return Scaffold(
      appBar: AppBar(title: const Text('Serah terima pekerjaan')),
      body: order == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(
                      padding: const EdgeInsets.all(16),
                      child: NoticeBanner(
                        icon: Icons.error_outline,
                        text: _error!,
                      ),
                    ),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        textOr(order['project_title'], 'Proyek'),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      InfoRow(
                        icon: Icons.business_rounded,
                        text: '${order['client_name']}',
                      ),
                      if (order['order_number'] != null) ...[
                        const SizedBox(height: 4),
                        InfoRow(
                          icon: Icons.tag_rounded,
                          text: '${order['order_number']}',
                        ),
                      ],
                      if (order['leader_signed_at'] != null) ...[
                        const SizedBox(height: 8),
                        NoticeBanner(
                          icon: Icons.verified_rounded,
                          accent: locked ? Accent.emerald : Accent.amber,
                          text: locked
                              ? 'Sudah disetujui atasan — tidak bisa diubah lagi.'
                              : 'Sudah Anda tandatangani; menandatangani ulang menggantikan yang lama.',
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: _exporting ? null : _slides,
                  icon: _exporting
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.slideshow_rounded),
                  label: Text(
                    _exporting
                        ? 'Menyiapkan slide…'
                        : 'Unduh laporan slide (.pptx)',
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _exporting ? null : _bastDocx,
                  icon: const Icon(Icons.description_rounded),
                  label: const Text('Unduh work completion (.docx)'),
                ),
                ...[
                  // Setelah disetujui PM tetap tampil (hanya baca) agar hasil kerja bisa dilihat ulang.
                  const SectionTitle('Ringkasan'),
                  VmsTextField(
                    controller: _summary,
                    maxLength: 2000,
                    readOnly: locked,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Ringkasan pekerjaan (wajib)',
                    ),
                  ),
                  const SizedBox(height: 8),
                  VmsTextField(
                    controller: _obstacles,
                    maxLength: 2000,
                    readOnly: locked,
                    maxLines: 2,
                    decoration: const InputDecoration(labelText: 'Kendala'),
                  ),
                  const SectionTitle('Foto hasil kerja'),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final id in _photoIds)
                        _PhotoTile(
                          onRemove: locked ? null : () => _removeSaved(id),
                          child: VmsNetworkImage(fileId: id),
                        ),
                      for (final path in _photoPaths)
                        _PhotoTile(
                          onRemove: () =>
                              setState(() => _photoPaths.remove(path)),
                          child: Image.file(File(path), fit: BoxFit.cover),
                        ),
                      if (!locked)
                        IconButton.filledTonal(
                          tooltip: 'Tambah foto',
                          onPressed: _picking
                              ? null
                              : () async {
                                  setState(() => _picking = true);
                                  final p = await pickReportPhoto(
                                    context: context,
                                    slot: 'Foto hasil kerja',
                                    origin: PhotoOrigin.camera,
                                    onError: _snack,
                                  );
                                  if (!mounted) return;
                                  setState(() {
                                    _picking = false;
                                    if (p != null) _photoPaths.add(p.path);
                                  });
                                },
                          icon: const Icon(Icons.add_a_photo_rounded),
                        ),
                    ],
                  ),
                  if (_savedSignature != null) ...[
                    SectionTitle(
                      'Tanda tangan tersimpan · ${order['leader_signer_name'] ?? ''}',
                    ),
                    Container(
                      height: 140,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.black12),
                      ),
                      padding: const EdgeInsets.all(8),
                      child: Image.memory(
                        _savedSignature!,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ],
                  if (!locked) ...[
                    SectionTitle(
                      _savedSignature != null
                          ? 'Tanda tangan baru (mengganti yang tersimpan)'
                          : 'Tanda tangan ketua tim',
                      trailing: TextButton(
                        onPressed: () => _pad.currentState?.clear(),
                        child: const Text('Hapus'),
                      ),
                    ),
                    _SignaturePad(key: _pad),
                    const SizedBox(height: 16),
                    PrimaryAction(
                      label: _savedSignature != null
                          ? 'Tanda tangan ulang'
                          : 'Tanda tangan serah terima',
                      icon: Icons.draw_rounded,
                      busy: _busy,
                      onTap: _submit,
                    ),
                  ],
                ],
              ],
            ),
    );
  }
}

/// Kotak foto 72×72 dengan tombol hapus (×) di pojok.
class _PhotoTile extends StatelessWidget {
  const _PhotoTile({required this.child, this.onRemove});
  final Widget child;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 72,
      height: 72,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ClipRRect(borderRadius: BorderRadius.circular(8), child: child),
          if (onRemove != null)
            Positioned(
              top: 2,
              right: 2,
              child: InkWell(
                onTap: onRemove,
                child: const CircleAvatar(
                  radius: 12,
                  backgroundColor: Colors.black54,
                  child: Icon(
                    Icons.close_rounded,
                    size: 16,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Bantalan tanda tangan sederhana: goresan jari → PNG transparan.
class _SignaturePad extends StatefulWidget {
  const _SignaturePad({super.key});

  @override
  State<_SignaturePad> createState() => _SignaturePadState();
}

class _SignaturePadState extends State<_SignaturePad> {
  final List<List<Offset>> _strokes = [];
  Size _size = Size.zero;

  void clear() => setState(_strokes.clear);

  /// PNG goresan, atau null bila belum ada tanda tangan berarti (kurang dari ~10 titik).
  Future<List<int>?> toPng() async {
    if (_strokes.fold<int>(0, (n, s) => n + s.length) < 10 || _size.isEmpty) {
      return null;
    }
    final recorder = ui.PictureRecorder();
    _SignaturePainter(_strokes).paint(Canvas(recorder), _size);
    final image = await recorder.endRecording().toImage(
      _size.width.ceil(),
      _size.height.ceil(),
    );
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    return bytes?.buffer.asUint8List();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.black26),
      ),
      child: LayoutBuilder(
        builder: (context, box) {
          _size = Size(box.maxWidth, box.maxHeight);
          return GestureDetector(
            onPanStart: (d) => setState(() => _strokes.add([d.localPosition])),
            onPanUpdate: (d) =>
                setState(() => _strokes.last.add(d.localPosition)),
            child: CustomPaint(
              painter: _SignaturePainter(_strokes),
              size: Size.infinite,
            ),
          );
        },
      ),
    );
  }
}

class _SignaturePainter extends CustomPainter {
  _SignaturePainter(this.strokes);

  final List<List<Offset>> strokes;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF0F172A)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    for (final s in strokes) {
      if (s.length < 2) continue;
      final path = Path()..moveTo(s.first.dx, s.first.dy);
      for (final p in s.skip(1)) {
        path.lineTo(p.dx, p.dy);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _SignaturePainter oldDelegate) => true;
}
