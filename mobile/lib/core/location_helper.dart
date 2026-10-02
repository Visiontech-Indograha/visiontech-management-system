import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

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

/// K-12 (docs/10): titik GPS dengan akurasi lebih buruk dari ini ditolak server.
const double maxGpsAccuracyM = 100;

/// Pesan yang sama dengan server (`GPS_INACCURATE`) agar pengguna tahu harus berbuat apa.
String gpsAccuracyMessage(double accuracyM) =>
    'Akurasi GPS ${accuracyM.round()} m terlalu rendah (maksimal ${maxGpsAccuracyM.round()} m). '
    'Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.';
