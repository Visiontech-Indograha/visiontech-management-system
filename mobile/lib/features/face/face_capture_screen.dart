import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:camera/camera.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/face/liveness.dart';
import '../../core/face/nv21.dart';
import '../../core/providers.dart';
import '../../core/system_ui.dart';

/// Untuk apa kamera wajah dipakai: absen (satu gambar akhir) atau pendaftaran (beberapa pose).
enum FaceCaptureMode { attendance, enroll }

/// Hasil layar kamera wajah. `photos` MENTAH tanpa watermark (watermark GPS menurunkan akurasi pengenalan dan ini
/// bukan foto absensi). `liveness` dikirim apa adanya ke /face/probe atau /face/enroll.
class FaceCaptureResult {
  const FaceCaptureResult({
    required this.photos,
    required this.liveness,
    this.stopReason,
  });

  final List<File> photos;
  final Map<String, dynamic> liveness;

  /// Null = semua tantangan lolos. Selain itu alasan berhenti: `offline`, `unavailable`, atau `timeout`.
  final String? stopReason;

  bool get passed => liveness['passed'] == true;
}

enum _Phase { starting, challenge, stills, failed }

/// Kamera depan + dua tantangan liveness acak (anti foto layar). Tiap bingkai dikirim ke server; server yang memutuskan
/// dan menerbitkan bukti bertanda tangan. HP tidak bisa memalsukannya (aturan inti #3).
class FaceCaptureScreen extends ConsumerStatefulWidget {
  const FaceCaptureScreen({super.key, required this.mode});

  final FaceCaptureMode mode;

  @override
  ConsumerState<FaceCaptureScreen> createState() => _FaceCaptureScreenState();
}

class _FaceCaptureScreenState extends ConsumerState<FaceCaptureScreen> {
  static const _timeout = Duration(seconds: 45);
  static const _attendancePrompts = ['Hadap lurus ke kamera'];
  static const _enrollPrompts = [
    'Hadap lurus ke kamera',
    'Tengok sedikit ke kiri',
    'Tengok sedikit ke kanan',
    'Tersenyum ke kamera',
  ];

  CameraController? _cam;
  _Phase _phase = _Phase.starting;
  String _hint = 'Menyiapkan kamera...';
  String? _error;
  final _challenges = pickLivenessChallenges(Random.secure());
  final _proofs = <String>[];
  int _step = 0;
  bool _busy = false;
  DateTime _lastSent = DateTime.fromMillisecondsSinceEpoch(0);
  DateTime _deadline = DateTime.now();
  Timer? _ticker;
  String? _metrics; // hanya terisi bila API berjalan di mode pengembangan (kalibrasi)

  @override
  void initState() {
    super.initState();
    // Bingkai yang dikirim harus tegak: kunci potret selama layar ini terbuka.
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
    _initCamera();
  }

  @override
  void dispose() {
    _ticker?.cancel();
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
      final ctrl = CameraController(
        front,
        ResolutionPreset.high,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.nv21,
      );
      await ctrl.initialize();
      if (!mounted) {
        await ctrl.dispose();
        return;
      }
      _cam = ctrl;
      _deadline = DateTime.now().add(_timeout);
      setState(() {
        _phase = _Phase.challenge;
        _hint = _challenges.first.instruction;
      });
      await ctrl.startImageStream(_onFrame);
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
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

  void _tick() {
    if (_phase == _Phase.challenge && DateTime.now().isAfter(_deadline)) {
      _beginStills(reason: 'timeout');
    }
  }

  void _onFrame(CameraImage image) {
    if (_phase != _Phase.challenge || _busy) return;
    final now = DateTime.now();
    if (now.difference(_lastSent) < _challenges[_step].interval) return;
    if (image.planes.length != 1) {
      // Hanya NV21 (satu bidang) yang didukung konversi; format lain berarti fallback gambar tanpa bukti.
      _beginStills(reason: 'unavailable');
      return;
    }
    _busy = true;
    _lastSent = now;
    final plane = image.planes.first;
    final frame = FrameData(
      bytes: Uint8List.fromList(plane.bytes),
      width: image.width,
      height: image.height,
      rowStride: plane.bytesPerRow,
      rotation: _cam!.description.sensorOrientation,
    );
    unawaited(_check(frame));
  }

  Future<void> _check(FrameData frame) async {
    final step = _step;
    final challenge = _challenges[step];
    try {
      final jpeg = await compute(encodeFrame, frame);
      final res = await ref
          .read(syncEngineProvider)
          .api
          .faceChallengeCheck(jpeg, challenge.id);
      if (!mounted || _phase != _Phase.challenge || step != _step) return;
      final m = res['metrics'];
      if (m is Map && mounted) {
        setState(
          () => _metrics = m.entries.map((e) => '${e.key} ${e.value}').join('  '),
        );
      }
      final proof = res['proof'];
      if (res['status'] == 'sukses' && proof is String) {
        _proofs.add(proof);
        await HapticFeedback.mediumImpact();
        if (_proofs.length >= _challenges.length) {
          await _beginStills();
        } else if (mounted) {
          setState(() {
            _step++;
            _hint = _challenges[_step].instruction;
          });
        }
      } else if (mounted) {
        setState(
          () => _hint = friendlyChallengeHint(
            '${res['detail'] ?? challenge.instruction}',
          ),
        );
      }
    } on DioException catch (e) {
      if (!mounted) return;
      if (isNetworkFailure(e)) {
        await _beginStills(reason: 'offline');
      } else if (e.response?.statusCode == 503) {
        await _beginStills(reason: 'unavailable');
      } else if (e.response?.statusCode == 429) {
        setState(() => _hint = 'Terlalu cepat. Tunggu sebentar...');
      } else {
        setState(() => _hint = apiErrorMessage(e));
      }
    } finally {
      _busy = false;
    }
  }

  Future<void> _beginStills({String? reason}) async {
    if (_phase != _Phase.challenge) return;
    _phase = _Phase.stills;
    _ticker?.cancel();
    final cam = _cam!;
    try {
      await cam.stopImageStream();
    } on CameraException {
      // Aliran sudah berhenti.
    }
    final prompts = widget.mode == FaceCaptureMode.enroll
        ? _enrollPrompts
        : _attendancePrompts;
    final settle = Duration(
      milliseconds: widget.mode == FaceCaptureMode.enroll ? 1600 : 900,
    );
    try {
      final dir = await getTemporaryDirectory();
      final files = <File>[];
      for (var i = 0; i < prompts.length; i++) {
        if (!mounted) return;
        setState(() => _hint = prompts[i]);
        await Future<void>.delayed(settle); // beri waktu berpose sebelum jepret
        final shot = await cam.takePicture();
        final target = File(
          '${dir.path}/face_${DateTime.now().microsecondsSinceEpoch}_$i.jpg',
        );
        files.add(await File(shot.path).copy(target.path));
        try {
          await File(shot.path).delete();
        } on FileSystemException {
          // Berkas sementara kamera; tidak kritis.
        }
      }
      if (!mounted) return;
      Navigator.of(context).pop(
        FaceCaptureResult(
          photos: files,
          liveness: livenessPayload(
            challenges: [for (final c in _challenges) c.id],
            proofs: _proofs,
          ),
          stopReason: reason,
        ),
      );
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
          if (!failed && _phase != _Phase.starting)
            Text(
              _phase == _Phase.challenge
                  ? 'Tantangan ${_step + 1} dari ${_challenges.length}'
                  : 'Mengambil gambar wajah',
              style: theme.textTheme.labelMedium?.copyWith(color: Colors.white70),
            ),
          const SizedBox(height: 6),
          Text(
            failed ? (_error ?? 'Terjadi kesalahan.') : _hint,
            key: const Key('face-hint'),
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          if (_metrics != null && !failed)
            Text(
              _metrics!,
              key: const Key('face-metrics'),
              textAlign: TextAlign.center,
              style: theme.textTheme.labelSmall?.copyWith(color: Colors.amber),
            ),
          if (!failed) ...[
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: _proofs.length / _challenges.length,
              minHeight: 6,
              borderRadius: BorderRadius.circular(3),
            ),
          ] else ...[
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Tutup'),
            ),
          ],
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
