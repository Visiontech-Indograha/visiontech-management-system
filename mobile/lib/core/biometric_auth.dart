import 'package:local_auth/local_auth.dart';

/// Wrapper tipis di atas package local_auth -- SEMUA pemakaian sidik jari di
/// aplikasi (unlock saat buka app, toggle di Profil) lewat sini, supaya
/// penanganan error/exception seragam di satu tempat (lihat plan Keputusan 7:
/// sidik jari cuma jadi "kunci lokal" ke sesi yang sudah sah, tidak ada
/// perubahan di backend).
class BiometricAuth {
  const BiometricAuth();

  static final LocalAuthentication _auth = LocalAuthentication();

  /// True selama prompt sidik jari SISTEM sedang tampil, plus jeda singkat
  /// sesudahnya.
  ///
  /// Menampilkan prompt biometrik membuat aplikasi ter-pause lalu resume. Tanpa
  /// penanda ini, "kunci ulang saat resume" ikut terpicu oleh prompt yang kita
  /// munculkan sendiri: sukses -> resume -> kunci ulang -> prompt lagi, berulang
  /// tanpa henti. Ditemukan saat uji di perangkat asli.
  static bool _promptInFlight = false;
  static bool get isPromptInFlight => _promptInFlight;

  /// False juga dikembalikan (bukan exception) kalau perangkat tidak punya
  /// sensor sidik jari/face unlock sama sekali, atau belum ada sidik jari
  /// terdaftar di sistem -- caller cukup sembunyikan opsi biometrik.
  Future<bool> isDeviceSupported() async {
    try {
      final canCheck = await _auth.canCheckBiometrics;
      final supported = await _auth.isDeviceSupported();
      return canCheck && supported;
    } catch (_) {
      return false;
    }
  }

  /// Tampilkan prompt sistem (sidik jari/face unlock). Return `false` untuk
  /// APAPUN kegagalan (dibatalkan user, sidik jari tidak cocok, sensor
  /// error, dst) -- caller (biometric_lock_screen.dart) yang memutuskan
  /// tindak lanjutnya (coba lagi / jatuh ke form password biasa), bukan
  /// fungsi ini.
  Future<bool> authenticate(String reason) async {
    _promptInFlight = true;
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        biometricOnly: true,
        persistAcrossBackgrounding: true,
      );
    } catch (_) {
      return false;
    } finally {
      // Jeda kecil: event resume kadang tiba SESUDAH authenticate() selesai,
      // jadi penanda ini harus bertahan sebentar setelah promptnya tertutup.
      Future.delayed(const Duration(seconds: 2), () => _promptInFlight = false);
    }
  }
}
