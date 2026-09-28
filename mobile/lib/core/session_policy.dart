import 'dart:convert';

/// Kebijakan umur sesi: user WAJIB login ulang dengan password minimal
/// sekali setiap 1x24 jam, dan paling lambat pada pukul 02:00 dini hari
/// berikutnya setelah login.
///
/// Dievaluasi MURNI LOKAL — tidak ada panggilan jaringan sama sekali — supaya
/// aturannya tetap berlaku sama persis saat online maupun offline. Bahan
/// pembandingnya adalah klaim `auth_time` di JWT (diterbitkan server saat login
/// password, dan sengaja tidak ikut diperbarui saat token di-refresh), bukan
/// jam yang dicatat HP saat login.
class SessionPolicy {
  const SessionPolicy._();

  /// Batas maksimum umur sesi sejak login password terakhir.
  static const maxSessionAge = Duration(hours: 24);

  /// Jam dini hari yang menutup sesi hari sebelumnya.
  static const dailyCutoffHour = 2;

  /// Baca klaim `auth_time` (detik epoch UTC) dari JWT tanpa memverifikasi
  /// tanda tangannya — verifikasi tetap tugas server. Di sini kita hanya
  /// membaca metadata waktu untuk gerbang lokal, jadi tidak butuh kunci.
  ///
  /// Mengembalikan null bila token tidak bisa dibaca atau tidak punya klaim itu
  /// (mis. token lama yang diterbitkan sebelum fitur ini ada).
  static int? authTimeFromJwt(String? token) {
    if (token == null) return null;
    final parts = token.split('.');
    if (parts.length != 3) return null;
    try {
      final normalized = base64Url.normalize(parts[1]);
      final payload = jsonDecode(utf8.decode(base64Url.decode(normalized)));
      if (payload is! Map) return null;
      final value = payload['auth_time'];
      if (value is int) return value;
      if (value is String) return int.tryParse(value);
      return null;
    } catch (_) {
      return null;
    }
  }

  /// Kapan sesi yang dimulai pada [authTime] harus berakhir: mana yang lebih
  /// DULU tercapai antara (a) 24 jam sejak login, dan (b) pukul 02:00 dini hari
  /// berikutnya menurut waktu lokal perangkat.
  static DateTime expiryFor(DateTime authTime) {
    final local = authTime.toLocal();
    final byAge = local.add(maxSessionAge);

    // Cutoff 02:00 berikutnya SETELAH waktu login. Login pukul 01:00 ditutup
    // pukul 02:00 di hari yang sama (1 jam kemudian) — bukan 02:00 besok.
    var cutoff = DateTime(local.year, local.month, local.day, dailyCutoffHour);
    if (!cutoff.isAfter(local)) {
      cutoff = cutoff.add(const Duration(days: 1));
    }

    return byAge.isBefore(cutoff) ? byAge : cutoff;
  }

  /// True bila sesi sudah harus diakhiri dan user wajib memasukkan password
  /// lagi. Sidik jari saja TIDAK cukup untuk melewati batas ini.
  ///
  /// [authTimeEpochSeconds] null berarti sesi lama yang diterbitkan sebelum
  /// klaim ini ada — sengaja dianggap MASIH BERLAKU supaya pembaruan aplikasi
  /// tidak melempar semua user yang sedang bekerja ke layar login; sesi itu
  /// akan tunduk pada aturan ini setelah login berikutnya.
  static bool isExpired(int? authTimeEpochSeconds, {DateTime? now}) {
    if (authTimeEpochSeconds == null) return false;
    final authTime = DateTime.fromMillisecondsSinceEpoch(
      authTimeEpochSeconds * 1000,
      isUtc: true,
    );
    final current = now ?? DateTime.now();
    return !current.isBefore(expiryFor(authTime));
  }
}
