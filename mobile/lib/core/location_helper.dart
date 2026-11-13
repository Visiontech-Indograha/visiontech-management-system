import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:geolocator/geolocator.dart';

/// Pesan bila lokasi terdeteksi palsu (dipakai Absensi dan titik survei).
const mockLocationMessage = 'Lokasi palsu terdeteksi. Matikan aplikasi pemalsu lokasi.';

/// Hasil pengambilan lokasi -- [position] null berarti gagal, cek [errorMessage]
/// untuk pesan yang sudah siap ditampilkan ke user (Bahasa Indonesia).
class LocationResult {
  const LocationResult({this.position, this.errorMessage});

  final Position? position;
  final String? errorMessage;

  bool get isMocked => position?.isMocked ?? false;
}

/// Dipakai bersama oleh Absensi (check-in/out) dan pengambilan foto berbukti
/// lokasi -- awalnya cuma ada di attendance_screen.dart, diekstrak ke sini
/// begitu kebutuhan yang sama muncul lagi di photo_capture.dart (bukan
/// disiapkan lebih dulu untuk kemungkinan di masa depan).
Future<LocationResult> getCurrentPositionSafely() async {
  // Titik hangat dari [LocationWarmer] (aplikasi di depan): langsung dipakai bila masih segar & akurat.
  final warm = LocationWarmer.instance.freshFix();
  if (warm != null) return LocationResult(position: warm);
  final serviceEnabled = await Geolocator.isLocationServiceEnabled();
  if (!serviceEnabled) {
    return const LocationResult(
      errorMessage: 'Aktifkan Layanan Lokasi (GPS) terlebih dahulu.',
    );
  }
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.denied ||
      permission == LocationPermission.deniedForever) {
    return const LocationResult(
      errorMessage: 'Izin lokasi ditolak. Fitur ini butuh akses lokasi.',
    );
  }
  try {
    // GPS chip tidak butuh internet untuk dapat titik -- timeLimit di sini
    // cuma jaring pengaman supaya tidak menunggu tanpa batas di area sinyal
    // GPS lemah (mis. dalam ruangan).
    // Android: baca langsung dari LocationManager (chip GPS). Tanpa ini geolocator memakai
    // layanan lokasi Google yang memunculkan dialog "Location Accuracy" di setiap absen;
    // bila pengguna memilih "No thanks", lokasi gagal dibaca dan absen tidak bisa dilakukan.
    final settings = defaultTargetPlatform == TargetPlatform.android
        ? AndroidSettings(
            accuracy: LocationAccuracy.high,
            forceLocationManager: true,
            timeLimit: const Duration(seconds: 30),
          )
        : const LocationSettings(
            accuracy: LocationAccuracy.high,
            timeLimit: Duration(seconds: 30),
          );
    final position = await Geolocator.getCurrentPosition(
      locationSettings: settings,
    );
    return LocationResult(position: position);
  } on LocationServiceDisabledException {
    return const LocationResult(
      errorMessage: 'Aktifkan Layanan Lokasi (GPS) terlebih dahulu.',
    );
  } on TimeoutException {
    return const LocationResult(
      errorMessage: 'Gagal mendapatkan lokasi -- pastikan berada di area terbuka, lalu coba lagi.',
    );
  }
}

/// Menjaga GPS tetap "hangat" selama aplikasi di depan: stream posisi berjalan sejak aplikasi dibuka
/// dan berhenti saat aplikasi ke latar belakang (hemat baterai). Fitur berlokasi (absen, kamera
/// berbukti lokasi) memakai titik terakhir bila umurnya ≤ [maxAge] dan akurasinya lolos K-12, sehingga
/// tidak menunggu chip GPS mengunci ulang dari nol.
class LocationWarmer {
  LocationWarmer._();
  static final instance = LocationWarmer._();

  static const maxAge = Duration(seconds: 20);

  StreamSubscription<Position>? _sub;
  Position? _last;
  final _fixes = StreamController<Position>.broadcast();

  /// Titik segar & akurat sekarang, atau titik pertama berikutnya (maks [timeout]); null bila tak ada.
  Future<Position?> waitForFix({Duration timeout = const Duration(seconds: 8)}) async {
    final now = freshFix();
    if (now != null) return now;
    try {
      return await _fixes.stream.firstWhere((p) => p.accuracy <= maxGpsAccuracyM).timeout(timeout);
    } on TimeoutException {
      return null;
    }
  }

  /// Titik terakhir yang masih segar & cukup akurat; null → ambil baru.
  Position? freshFix() {
    final p = _last;
    if (p == null) return null;
    if (DateTime.now().difference(p.timestamp) > maxAge) return null;
    if (p.accuracy > maxGpsAccuracyM) return null;
    return p;
  }

  /// Mulai stream (minta izin bila belum). Aman dipanggil berulang; gagal diam-diam (fitur tetap
  /// mengambil lokasi sendiri lewat [getCurrentPositionSafely]).
  Future<void> start() async {
    if (_sub != null) return;
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return;
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        return;
      }
      if (_sub != null) return;
      final settings = defaultTargetPlatform == TargetPlatform.android
          ? AndroidSettings(
              accuracy: LocationAccuracy.high,
              forceLocationManager: true, // sama dengan getCurrentPositionSafely: tanpa dialog Google
              intervalDuration: const Duration(seconds: 5),
            )
          : const LocationSettings(accuracy: LocationAccuracy.high);
      _sub = Geolocator.getPositionStream(locationSettings: settings).listen(
        (p) {
          _last = p;
          if (!_fixes.isClosed) _fixes.add(p);
        },
        onError: (_) => stop(),
        cancelOnError: true,
      );
    } catch (_) {
      // Plugin tak tersedia (uji widget) / platform menolak — abaikan.
    }
  }

  void stop() {
    _sub?.cancel();
    _sub = null;
  }
}

/// Pembungkus aplikasi: menyalakan [LocationWarmer] saat aplikasi dibuka/kembali ke depan,
/// mematikannya saat ke latar belakang.
class LocationWarmerScope extends StatefulWidget {
  const LocationWarmerScope({super.key, required this.child});

  final Widget child;

  @override
  State<LocationWarmerScope> createState() => _LocationWarmerScopeState();
}

class _LocationWarmerScopeState extends State<LocationWarmerScope> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    LocationWarmer.instance.start();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      LocationWarmer.instance.start();
    } else if (state == AppLifecycleState.paused || state == AppLifecycleState.detached) {
      LocationWarmer.instance.stop();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    LocationWarmer.instance.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

/// K-12 (docs/10): titik GPS dengan akurasi lebih buruk dari ini ditolak server.
const double maxGpsAccuracyM = 100;

/// Pesan yang sama dengan server (`GPS_INACCURATE`) agar pengguna tahu harus berbuat apa.
String gpsAccuracyMessage(double accuracyM) =>
    'Akurasi GPS ${accuracyM.round()} m terlalu rendah (maksimal ${maxGpsAccuracyM.round()} m). '
    'Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.';
