import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import 'photo_slots.dart' show PhotoOrigin, pickReportPhoto;

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
  Map<String, dynamic>? _order;
  String? _error;
  bool _busy = false;

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
      final order = await ref.read(syncEngineProvider).api.workCompletion(widget.completionId);
      if (!mounted) return;
      setState(() {
        _order = order;
        _summary.text = '${order['summary_notes'] ?? ''}';
        _obstacles.text = '${order['obstacles'] ?? ''}';
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _submit() async {
    if (_summary.text.trim().isEmpty) return _snack('Isi ringkasan pekerjaan.');
    final png = await _pad.currentState?.toPng();
    if (png == null) return _snack('Bubuhkan tanda tangan Anda.');
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      final ids = [for (final path in _photoPaths) await api.uploadFile(File(path))];
      await api.signCompletion(
        widget.completionId,
        signaturePng: base64Encode(png),
        summary: _summary.text.trim(),
        obstacles: _obstacles.text.trim().isEmpty ? null : _obstacles.text.trim(),
        photoFileIds: ids,
      );
      _snack('BAST ditandatangani. Menunggu pengesahan PM.');
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    final locked = order?['pm_signed_at'] != null;
    return Scaffold(
      appBar: AppBar(title: const Text('BAST order')),
      body: order == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(padding: const EdgeInsets.all(16), child: NoticeBanner(icon: Icons.error_outline, text: _error!)),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${order['project_title']}', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      InfoRow(icon: Icons.business_rounded, text: '${order['client_name']}'),
                      if (order['order_number'] != null) ...[
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.tag_rounded, text: '${order['order_number']}'),
                      ],
                      if (order['leader_signed_at'] != null) ...[
                        const SizedBox(height: 8),
                        NoticeBanner(
                          icon: Icons.verified_rounded,
                          text: locked
                              ? 'Sudah disahkan PM — berita acara terkunci.'
                              : 'Sudah Anda tandatangani; menandatangani ulang menggantikan yang lama.',
                        ),
                      ],
                    ],
                  ),
                ),
                if (!locked) ...[
                  const SectionTitle('Ringkasan'),
                  TextField(
                    controller: _summary,
                    maxLines: 4,
                    decoration: const InputDecoration(labelText: 'Ringkasan pekerjaan (wajib)'),
                  ),
                  const SizedBox(height: 8),
                  TextField(controller: _obstacles, maxLines: 2, decoration: const InputDecoration(labelText: 'Kendala')),
                  const SectionTitle('Foto realisasi'),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final path in _photoPaths)
                        InkWell(
                          onLongPress: () => setState(() => _photoPaths.remove(path)),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.file(File(path), width: 72, height: 72, fit: BoxFit.cover),
                          ),
                        ),
                      IconButton.filledTonal(
                        tooltip: 'Tambah foto',
                        onPressed: () async {
                          final p = await pickReportPhoto(
                            context: context,
                            slot: 'Foto realisasi BAST',
                            origin: PhotoOrigin.camera,
                            onError: _snack,
                          );
                          if (p != null && mounted) setState(() => _photoPaths.add(p.path));
                        },
                        icon: const Icon(Icons.add_a_photo_rounded),
                      ),
                    ],
                  ),
                  SectionTitle(
                    'Tanda tangan ketua tim',
                    trailing: TextButton(onPressed: () => _pad.currentState?.clear(), child: const Text('Hapus')),
                  ),
                  _SignaturePad(key: _pad),
                  const SizedBox(height: 16),
                  PrimaryAction(label: 'Tandatangani BAST', icon: Icons.draw_rounded, busy: _busy, onTap: _submit),
                ],
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
    if (_strokes.fold<int>(0, (n, s) => n + s.length) < 10 || _size.isEmpty) return null;
    final recorder = ui.PictureRecorder();
    _SignaturePainter(_strokes).paint(Canvas(recorder), _size);
    final image = await recorder.endRecording().toImage(_size.width.ceil(), _size.height.ceil());
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
            onPanUpdate: (d) => setState(() => _strokes.last.add(d.localPosition)),
            child: CustomPaint(painter: _SignaturePainter(_strokes), size: Size.infinite),
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
