import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/system_ui.dart';

/// Hasil layar kamera wajah: foto MENTAH tanpa watermark (watermark menurunkan akurasi pengenalan). Server yang
/// memeriksa: satu wajah, kualitas, dan foto-foto dari orang yang sama (wajah V2, Milestone 7).
class FaceCaptureResult {
  const FaceCaptureResult({required this.photos});

  final List<File> photos;
}

enum _Phase { starting, stills, failed }

/// Kamera depan untuk pendaftaran wajah: beberapa pose berurutan (3–5 foto, sesuai /face/policy).
class FaceCaptureScreen extends StatefulWidget {
  const FaceCaptureScreen({super.key});

  @override
  State<FaceCaptureScreen> createState() => _FaceCaptureScreenState();
}

class _FaceCaptureScreenState extends State<FaceCaptureScreen> {
  static const _prompts = [
    'Hadap lurus ke kamera',
    'Tengok sedikit ke kiri',
    'Tengok sedikit ke kanan',
    'Tersenyum ke kamera',
  ];

  CameraController? _cam;
  _Phase _phase = _Phase.starting;
  String _hint = 'Menyiapkan kamera...';
  String? _error;
  int _taken = 0;

  @override
  void initState() {
    super.initState();
    // Foto harus tegak: kunci potret selama layar ini terbuka.
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
    _initCamera();
  }

  @override
  void dispose() {
    _cam?.dispose();
    SystemChrome.setPreferredOrientations(const []);
    hideSystemNavigation();
    super.dispose();
  }

  Future<void> _initCamera() async {
    try {
      final cams = await availableCameras();
      final front = cams.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cams.first,
      );
      final ctrl = CameraController(front, ResolutionPreset.high, enableAudio: false);
      await ctrl.initialize();
      if (!mounted) {
        await ctrl.dispose();
        return;
      }
      setState(() => _cam = ctrl);
      await _takeStills();
    } on CameraException catch (e) {
      _fail(
        e.code == 'CameraAccessDenied'
            ? 'Izin kamera ditolak. Izinkan kamera di pengaturan HP.'
            : 'Kamera tidak dapat dibuka.',
      );
    } on StateError {
      _fail('Perangkat ini tidak punya kamera.');
    }
  }

  void _fail(String message) {
    if (!mounted) return;
    setState(() {
      _phase = _Phase.failed;
      _error = message;
    });
  }

  Future<void> _takeStills() async {
    final cam = _cam!;
    setState(() => _phase = _Phase.stills);
    try {
      final dir = await getTemporaryDirectory();
      final files = <File>[];
      for (var i = 0; i < _prompts.length; i++) {
        if (!mounted) return;
        setState(() => _hint = _prompts[i]);
        await Future<void>.delayed(const Duration(milliseconds: 1800)); // beri waktu berpose
        final shot = await cam.takePicture();
        final target = File('${dir.path}/face_${DateTime.now().microsecondsSinceEpoch}_$i.jpg');
        files.add(await File(shot.path).copy(target.path));
        try {
          await File(shot.path).delete();
        } on FileSystemException {
          // Berkas sementara kamera; tidak kritis.
        }
        if (mounted) setState(() => _taken = i + 1);
      }
      if (!mounted) return;
      Navigator.of(context).pop(FaceCaptureResult(photos: files));
    } on CameraException {
      _fail('Gagal mengambil gambar wajah. Coba lagi.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(child: _preview(context)),
            Positioned.fill(child: IgnorePointer(child: CustomPaint(painter: _OvalMask()))),
            Positioned(
              top: 4,
              left: 4,
              child: IconButton(
                key: const Key('face-close'),
                icon: const Icon(Icons.close_rounded, color: Colors.white),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),
            Positioned(left: 16, right: 16, bottom: 24, child: _panel(context)),
          ],
        ),
      ),
    );
  }

  Widget _preview(BuildContext context) {
    final cam = _cam;
    if (cam == null || !cam.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }
    final size = MediaQuery.sizeOf(context);
    var scale = size.aspectRatio * cam.value.aspectRatio;
    if (scale < 1) scale = 1 / scale;
    return Transform.scale(scale: scale, child: Center(child: CameraPreview(cam)));
  }

  Widget _panel(BuildContext context) {
    final theme = Theme.of(context);
    final failed = _phase == _Phase.failed;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_phase == _Phase.stills)
            Text(
              'Foto ${(_taken + 1).clamp(1, _prompts.length)} dari ${_prompts.length}',
              style: theme.textTheme.labelMedium?.copyWith(color: Colors.white70),
            ),
          const SizedBox(height: 6),
          Text(
            failed ? (_error ?? 'Terjadi kesalahan.') : _hint,
            key: const Key('face-hint'),
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 12),
          if (!failed)
            LinearProgressIndicator(
              value: _taken / _prompts.length,
              minHeight: 6,
              borderRadius: BorderRadius.circular(3),
            )
          else
            FilledButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Tutup')),
        ],
      ),
    );
  }
}

/// Lapisan gelap dengan lubang oval sebagai panduan posisi wajah.
class _OvalMask extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final hole = Rect.fromCenter(
      center: Offset(size.width / 2, size.height * 0.42),
      width: size.width * 0.72,
      height: size.width * 0.72 * 1.3,
    );
    final path = Path.combine(
      PathOperation.difference,
      Path()..addRect(Offset.zero & size),
      Path()..addOval(hole),
    );
    canvas.drawPath(path, Paint()..color = Colors.black.withValues(alpha: 0.45));
    canvas.drawOval(
      hole,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..color = Colors.white70,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
