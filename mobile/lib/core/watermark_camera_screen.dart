import 'dart:async';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';

import 'geofence_confirm.dart';
import 'location_helper.dart';
import 'reverse_geocode.dart';
import 'system_ui.dart';

/// Logo Visiontech di watermark setiap foto (R-11) — versi putih transparan di atas kotak gelap (R-14).
/// Bila tim punya logo sendiri, logo itu yang dipakai (lihat team_logo.dart).
const watermarkLogoAsset = 'assets/branding/logo_visiontech_white.png';

/// Kotak logo standar di panel watermark: logo dimuat 'contain', jadi logo persegi tampil lebih kecil.
const watermarkLogoBoxWidth = 96.0;
const watermarkLogoBoxHeight = 30.0;

/// Flash hanya tersedia di kamera belakang; kamera depan (swafoto) tidak punya lampu flash.
@visibleForTesting
bool flashAvailableFor(CameraLensDirection lens) =>
    lens == CameraLensDirection.back;

/// Siklus tombol flash: mati ⇄ nyala (nyala = lampu menyala saat rana ditekan).
@visibleForTesting
FlashMode nextFlashMode(FlashMode current) =>
    current == FlashMode.off ? FlashMode.always : FlashMode.off;

/// Tombol flash di layar kamera dengan status yang terlihat ("Flash mati" / "Flash nyala").
class CameraFlashToggle extends StatelessWidget {
  const CameraFlashToggle({
    required this.mode,
    required this.onPressed,
    super.key,
  });

  final FlashMode mode;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final on = mode != FlashMode.off;
    return Tooltip(
      message: on ? 'Matikan flash' : 'Nyalakan flash',
      child: TextButton.icon(
        key: const Key('camera-flash-toggle'),
        onPressed: onPressed,
        style: TextButton.styleFrom(
          foregroundColor: on ? Colors.yellowAccent : Colors.white,
        ),
        icon: Icon(on ? Icons.flash_on : Icons.flash_off, size: 20),
        label: Text(on ? 'Flash nyala' : 'Flash mati'),
      ),
    );
  }
}

/// Hasil satu kali pemotretan lewat [WatermarkCameraScreen]. [position] dan
/// [capturedAt] di sini PERSIS sama dengan yang ditampilkan di overlay saat
/// tombol jepret ditekan -- supaya watermark yang dibakar ke file final
/// (lihat photo_capture.dart) tidak pernah beda dengan yang dilihat user di
/// layar kamera (satu sumber kebenaran, bukan dua pengambilan terpisah).
class WatermarkCaptureResult {
  const WatermarkCaptureResult({
    required this.imagePath,
    required this.position,
    required this.capturedAt,
    this.overlayPng,
    this.overlayWidthFraction = 1,
    this.address,
  });

  final String imagePath;
  final Position position;
  final DateTime capturedAt;

  /// Alamat hasil reverse-geocoding saat rana ditekan (null bila belum/tidak tersedia).
  final String? address;

  /// Panel watermark PERSIS seperti di layar saat rana ditekan (PNG). Dibakar apa adanya ke foto
  /// supaya hasil = tampilan kamera (R-14). Null → cadangan: digambar ulang di photo_capture.dart.
  final Uint8List? overlayPng;

  /// Lebar panel relatif terhadap lebar layar (untuk menjaga proporsi pada foto).
  final double overlayWidthFraction;
}

/// Layar kamera kustom (menggantikan aplikasi kamera bawaan HP) supaya
/// watermark lokasi/jam/keterangan sudah kelihatan LANGSUNG di layar bidik,
/// bukan cuma ditempel setelah foto diambil (plan "Verifikasi Kehadiran
/// Lapangan" M7 Keputusan 14). Murni GPS perangkat + jam lokal -- tidak ada
/// panggilan jaringan sama sekali di sini, jadi otomatis tetap berfungsi
/// penuh baik online maupun offline.
class WatermarkCameraScreen extends StatefulWidget {
  const WatermarkCameraScreen({
    required this.title,
    required this.hint,
    this.locationCaption,
    this.preferFrontCamera = false,
    this.geofenceCheck,
    this.logo,
    super.key,
  });

  /// Logo di panel watermark (PNG/JPEG/WebP). Null → logo default Visiontech.
  final Uint8List? logo;

  /// Label slot foto (mis. "Foto odometer kendaraan") -- ditampilkan sebagai
  /// judul pita panduan di atas layar kamera.
  final String title;

  /// Panduan singkat apa yang harus difoto -- ditampilkan di bawah [title].
  final String hint;

  /// Baris keterangan konteks yang ikut ditulis di watermark (mis. "Kantor
  /// Utama" / "Lokasi Penugasan: Pemasangan CCTV 1"). Null berarti tidak ada
  /// baris keterangan.
  final String? locationCaption;

  /// Slot yang isinya foto ORANG (mis. selfie "Foto diri di lokasi") dibuka
  /// dengan kamera DEPAN secara default -- tombol putar kamera tetap
  /// tersedia untuk berpindah manual.
  final bool preferFrontCamera;

  /// Bila diisi, dipanggil sekali setelah lokasi GPS didapat untuk
  /// menampilkan status "dalam/luar radius" LANGSUNG di layar kamera (bukan
  /// baru diketahui nanti lewat dialog konfirmasi saat submit) -- lihat
  /// permintaan susulan user setelah Fase 11. Murni tampilan; keputusan
  /// akhir tetap di dialog konfirmasi saat submit & di server.
  final Future<GeofenceProximity?> Function(double latitude, double longitude)?
  geofenceCheck;

  @override
  State<WatermarkCameraScreen> createState() => _WatermarkCameraScreenState();
}

class _WatermarkCameraScreenState extends State<WatermarkCameraScreen>
    with WidgetsBindingObserver {
  CameraController? _controller;
  Future<void>? _initFuture;
  List<CameraDescription> _availableCameras = [];
  CameraLensDirection _lensDirection = CameraLensDirection.back;
  Position? _position;
  String? _locationError;
  bool _isCapturing = false;
  Timer? _clockTimer;
  DateTime _now = DateTime.now();
  DateTime? _frozenAt; // waktu dibekukan saat rana ditekan
  final _panelKey = GlobalKey();
  bool _proximityLoading = false;
  GeofenceProximity? _proximity;
  String? _address; // alamat dari GPS; null = belum ada / gagal (watermark tetap pakai koordinat)
  FlashMode _flash = FlashMode.off; // default mati
  bool _flashAvailable = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Kamera adalah pengalaman full-screen -- sembunyikan status/navigation
    // bar sistem selama layar ini terbuka, dikembalikan lagi saat ditutup.
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
    _initFuture = _initCamera();
    _loadPosition();
  }

  Future<void> _loadPosition() async {
    setState(() {
      _locationError = null;
      _proximity = null;
      _proximityLoading = false;
      _address = null;
    });
    final result = await getCurrentPositionSafely();
    if (!mounted) return;
    setState(() {
      _position = result.position;
      _locationError = result.errorMessage;
    });

    final geofenceCheck = widget.geofenceCheck;
    final position = result.position;
    if (position != null) unawaited(_loadAddress(position));
    if (geofenceCheck == null || position == null) return;
    setState(() => _proximityLoading = true);
    final proximity = await geofenceCheck(
      position.latitude,
      position.longitude,
    );
    if (!mounted) return;
    setState(() {
      _proximity = proximity;
      _proximityLoading = false;
    });
  }

  /// Alamat dicari terpisah dan tidak menahan pengambilan foto: bila geocoder
  /// lambat/gagal, panel tetap koordinat + waktu + nama lokasi tugas.
  Future<void> _loadAddress(Position position) async {
    final address = await reverseGeocodeCached(
      position.latitude,
      position.longitude,
    );
    if (!mounted || !identical(_position, position)) return;
    setState(() => _address = address);
  }

  Future<void> _initCamera() async {
    try {
      _availableCameras = await availableCameras();
    } catch (e) {
      throw CameraException('initFailed', 'Gagal membuka kamera: $e');
    }
    if (_availableCameras.isEmpty) {
      throw CameraException(
        'noCamera',
        'Tidak ada kamera tersedia di perangkat ini.',
      );
    }

    final preferred = widget.preferFrontCamera
        ? CameraLensDirection.front
        : CameraLensDirection.back;
    final chosen = _availableCameras.firstWhere(
      (c) => c.lensDirection == preferred,
      orElse: () => _availableCameras.first,
    );
    await _open(chosen);
  }

  Future<void> _open(CameraDescription description) async {
    final controller = CameraController(
      description,
      ResolutionPreset.high,
      enableAudio: false,
    );
    await controller.initialize();
    if (!mounted) {
      await controller.dispose();
      return;
    }
    var flashOk = false;
    if (flashAvailableFor(description.lensDirection)) {
      try {
        await controller.setFlashMode(_flash);
        flashOk = true;
      } catch (_) {
        flashOk = false; // perangkat tanpa flash: tombol disembunyikan
      }
    }
    setState(() {
      _controller = controller;
      _lensDirection = description.lensDirection;
      _flashAvailable = flashOk;
    });
  }

  /// Ganti flash mati ⇄ nyala. Galat dari plugin → tombol disembunyikan, foto tetap bisa diambil.
  Future<void> _toggleFlash() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    final next = nextFlashMode(_flash);
    try {
      await controller.setFlashMode(next);
      if (mounted) setState(() => _flash = next);
    } catch (_) {
      if (mounted) {
        setState(() => _flashAvailable = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Flash tidak didukung di perangkat ini.')),
        );
      }
    }
  }

  /// Putar kamera depan/belakang -- hilang di alur sebelumnya (image_picker
  /// yang membuka aplikasi kamera bawaan HP punya ini bawaan) begitu diganti
  /// kamera kustom, jadi ditambahkan lagi secara eksplisit di sini.
  Future<void> _flipCamera() async {
    if (_availableCameras.length < 2) return;
    final target = _lensDirection == CameraLensDirection.back
        ? CameraLensDirection.front
        : CameraLensDirection.back;
    final match = _availableCameras.firstWhere(
      (c) => c.lensDirection == target,
      orElse: () => _availableCameras.first,
    );
    if (match.lensDirection == _lensDirection) return;

    final old = _controller;
    setState(() {
      _controller = null;
      _flash = FlashMode.off; // kamera berganti: flash kembali mati
    });
    await old?.dispose();
    await _open(match);
  }

  // Kamera HARUS dilepas saat app pindah ke background (mis. user buka app
  // lain sebentar) -- kalau tidak, CameraController lama jadi tidak valid
  // begitu app kembali ke depan (keterbatasan dikenal dari package camera).
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      _controller = null;
      controller.dispose();
    } else if (state == AppLifecycleState.resumed) {
      setState(() => _initFuture = _initCamera());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)
        .then((_) => hideSystemNavigation());
    _clockTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  String _twoDigits(int n) => n.toString().padLeft(2, '0');

  String get _formattedTime => _stamp(_frozenAt ?? _now);

  String _stamp(DateTime t) =>
      '${_twoDigits(t.day)}/${_twoDigits(t.month)}/${t.year} ${_twoDigits(t.hour)}:${_twoDigits(t.minute)}:${_twoDigits(t.second)}';

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _isCapturing) {
      return;
    }
    final position = _position;
    if (position == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_locationError ?? 'Menunggu lokasi GPS...'),
          action: _locationError != null
              ? SnackBarAction(label: 'Coba Lagi', onPressed: _loadPosition)
              : null,
        ),
      );
      return;
    }
    final capturedAt = DateTime.now();
    setState(() {
      _isCapturing = true;
      _frozenAt = capturedAt;
    });
    try {
      final overlay = await _snapshotPanel();
      final file = await controller.takePicture();
      if (!mounted) return;
      final screenWidth = MediaQuery.sizeOf(context).width;
      Navigator.of(context).pop(
        WatermarkCaptureResult(
          imagePath: file.path,
          position: position,
          capturedAt: capturedAt,
          overlayPng: overlay?.$1,
          overlayWidthFraction: overlay == null ? 1 : overlay.$2 / screenWidth,
          address: _address,
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Gagal mengambil foto: $e')));
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCapturing = false;
          _frozenAt = null;
        });
      }
    }
  }

  /// Tangkap panel watermark (setelah frame dengan waktu beku tergambar) → (PNG, lebar logis).
  Future<(Uint8List, double)?> _snapshotPanel() async {
    try {
      await WidgetsBinding.instance.endOfFrame;
      final boundary =
          _panelKey.currentContext?.findRenderObject()
              as RenderRepaintBoundary?;
      if (boundary == null) return null;
      final image = await boundary.toImage(pixelRatio: 4);
      final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
      final width = boundary.size.width;
      image.dispose();
      return bytes == null ? null : (bytes.buffer.asUint8List(), width);
    } catch (_) {
      return null; // cadangan: photo_capture menggambar ulang watermark
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<void>(
            future: _initFuture,
            builder: (context, snapshot) {
              final controller = _controller;
              if (controller != null && controller.value.isInitialized) {
                return Center(child: CameraPreview(controller));
              }
              if (snapshot.connectionState == ConnectionState.done &&
                  controller == null) {
                return Center(
                  child: Text(
                    snapshot.error?.toString() ?? 'Kamera tidak tersedia.',
                    style: const TextStyle(color: Colors.white),
                    textAlign: TextAlign.center,
                  ),
                );
              }
              return const Center(
                child: CircularProgressIndicator(color: Colors.white),
              );
            },
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                  Expanded(
                    child: Container(
                      margin: const EdgeInsets.only(top: 8),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xAA000000),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            widget.title,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          Text(
                            widget.hint,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 11.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_flashAvailable)
                    CameraFlashToggle(
                      mode: _flash,
                      onPressed: _toggleFlash,
                    ),
                  if (_availableCameras.length > 1)
                    IconButton(
                      icon: const Icon(
                        Icons.cameraswitch_outlined,
                        color: Colors.white,
                      ),
                      onPressed: _flipCamera,
                    ),
                ],
              ),
            ),
          ),
          Positioned(
            left: 12,
            right: 12,
            bottom: 112,
            // Panel ini (teks + logo) ditangkap apa adanya & dibakar ke foto → hasil = tampilan (R-14).
            child: RepaintBoundary(
              key: _panelKey,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xAA000000),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _position != null
                                ? '${_position!.latitude.toStringAsFixed(6)}, ${_position!.longitude.toStringAsFixed(6)}'
                                : (_locationError ?? 'Mencari lokasi...'),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontFamily: 'monospace',
                            ),
                          ),
                          if (_address != null)
                            Text(
                              _address!,
                              key: const Key('watermark-address'),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12.5,
                              ),
                            ),
                          Text(
                            _formattedTime,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontFamily: 'monospace',
                            ),
                          ),
                          if (widget.locationCaption != null)
                            Text(
                              widget.locationCaption!,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                              ),
                            ),
                          if (_position?.isMocked ?? false)
                            const Text(
                              'PERINGATAN: lokasi mock/fake GPS',
                              style: TextStyle(
                                color: Colors.orangeAccent,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          if (widget.geofenceCheck != null) ...[
                            const SizedBox(height: 4),
                            if (_proximityLoading)
                              const Text(
                                'Memeriksa radius lokasi...',
                                style: TextStyle(
                                  color: Colors.white70,
                                  fontSize: 12,
                                ),
                              )
                            else if (_proximity != null)
                              Text(
                                _proximity!.isWithin
                                    ? '✓ Dalam radius ${_proximity!.label} (~${_proximity!.distanceMeters.round()} m)'
                                    : '⚠ Di luar radius ${_proximity!.label} (~${_proximity!.distanceMeters.round()} m, radius ${_proximity!.radiusMeters.round()} m)',
                                style: TextStyle(
                                  color: _proximity!.isWithin
                                      ? Colors.greenAccent
                                      : Colors.orangeAccent,
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Logo yang sama persis ikut tertangkap bersama panel (R-11/R-14).
                    SizedBox(
                      key: const Key('watermark-logo'),
                      width: watermarkLogoBoxWidth,
                      height: watermarkLogoBoxHeight,
                      child: widget.logo != null
                          ? Image.memory(
                              widget.logo!,
                              fit: BoxFit.contain,
                              alignment: Alignment.centerRight,
                            )
                          : Image.asset(
                              watermarkLogoAsset,
                              fit: BoxFit.contain,
                              alignment: Alignment.centerRight,
                            ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 28,
            child: Center(
              child: GestureDetector(
                onTap: _isCapturing ? null : _capture,
                child: Container(
                  width: 68,
                  height: 68,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    border: Border.fromBorderSide(
                      BorderSide(color: Colors.white54, width: 4),
                    ),
                  ),
                  child: _isCapturing
                      ? const Padding(
                          padding: EdgeInsets.all(18),
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
