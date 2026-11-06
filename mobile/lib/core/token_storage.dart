import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Menyimpan access/refresh token dan client_id perangkat di Android Keystore
/// (lewat flutter_secure_storage), bukan SharedPreferences biasa.
class TokenStorage {
  const TokenStorage();

  static const _storage = FlutterSecureStorage();
  static const _accessKey = 'vms_access_token';
  static const _refreshKey = 'vms_refresh_token';
  static const _clientIdKey = 'vms_client_id';
  static const _cachedProfileKey = 'vms_cached_profile';
  static const _biometricEnabledKey = 'vms_biometric_enabled';
  static const _authTimeKey = 'vms_auth_time';
  static const _deviceCredKey = 'vms_device_credential';
  static const _deviceExchangePendingKey = 'vms_device_exchange_pending';

  Future<String?> readAccessToken() => _storage.read(key: _accessKey);
  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> saveTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    await _storage.write(key: _accessKey, value: accessToken);
    if (refreshToken != null) {
      await _storage.write(key: _refreshKey, value: refreshToken);
    }
  }

  Future<void> saveAccessToken(String accessToken) =>
      _storage.write(key: _accessKey, value: accessToken);

  /// Sesi kedaluwarsa / ditolak server: buang token, TAPI pertahankan
  /// preferensi sidik jari & profil cache. Menghapus keduanya membuat gerbang
  /// sidik jari "hilang sendiri" setelah satu kali gangguan jaringan, padahal
  /// user tidak pernah mematikannya.
  Future<void> clearSession() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _authTimeKey);
  }

  /// Logout MANUAL oleh user: bersihkan semuanya, termasuk preferensi sidik
  /// jari & profil cache -- penting di HP yang dipakai bergantian.
  Future<void> clearAll() async {
    await clearSession();
    await _storage.delete(key: _cachedProfileKey);
    await _storage.delete(key: _biometricEnabledKey);
    await clearDeviceCredential();
  }

  /// Kredensial perangkat (login sidik jari, 30 hari). Token dan kedaluwarsa
  /// disimpan dalam SATU nilai supaya rotasi atomik: bila tulis gagal, nilai
  /// lama tetap utuh. Keterbatasan: flutter_secure_storage memakai Keystore
  /// tetapi tidak mendukung kunci terikat sidik jari; penjagaannya lewat
  /// prompt sidik jari di aplikasi.
  Future<void> saveDeviceCredential({
    required String token,
    required DateTime expiresAt,
  }) => _storage.write(
    key: _deviceCredKey,
    value: jsonEncode({
      'token': token,
      'expires_at': expiresAt.toUtc().toIso8601String(),
    }),
  );

  /// Null bila tidak ada atau rusak. Kedaluwarsa TIDAK disaring di sini.
  Future<({String token, DateTime expiresAt})?> readDeviceCredential() async {
    final raw = await _storage.read(key: _deviceCredKey);
    if (raw == null) return null;
    try {
      final m = jsonDecode(raw) as Map<String, dynamic>;
      final token = m['token'] as String;
      final exp = DateTime.parse(m['expires_at'] as String);
      return (token: token, expiresAt: exp);
    } catch (_) {
      return null;
    }
  }

  Future<void> clearDeviceCredential() async {
    await _storage.delete(key: _deviceCredKey);
    await _storage.delete(key: _deviceExchangePendingKey);
  }

  /// True bila sesi dibuka offline dan token perangkat belum ditukar ke server.
  Future<bool> readDeviceExchangePending() async =>
      (await _storage.read(key: _deviceExchangePendingKey)) == 'true';

  Future<void> saveDeviceExchangePending(bool pending) => pending
      ? _storage.write(key: _deviceExchangePendingKey, value: 'true')
      : _storage.delete(key: _deviceExchangePendingKey);

  Future<String?> readClientId() => _storage.read(key: _clientIdKey);

  Future<void> saveClientId(String id) =>
      _storage.write(key: _clientIdKey, value: id);

  /// Profil user (JSON hasil GET /auth/me) yang tersimpan sejak login/restore
  /// sukses TERAKHIR -- dipakai _restoreSession untuk tetap mengizinkan user
  /// masuk ke aplikasi saat TIDAK ADA sinyal sama sekali (network error, bukan
  /// token ditolak server), supaya cek-in dkk tetap bisa dilakukan offline.
  Future<String?> readCachedProfile() => _storage.read(key: _cachedProfileKey);

  Future<void> saveCachedProfile(String profileJson) =>
      _storage.write(key: _cachedProfileKey, value: profileJson);

  /// Null berarti belum pernah diputuskan sama sekali (device baru/belum
  /// pernah ditawari) -- dibedakan dari `false` (user pernah menolak secara
  /// eksplisit) supaya LoginScreen tahu kapan harus menawarkan aktivasi lagi
  /// vs kapan sudah pernah ditolak (lihat plan Keputusan 7).
  Future<bool?> readBiometricEnabled() async {
    final raw = await _storage.read(key: _biometricEnabledKey);
    if (raw == null) return null;
    return raw == 'true';
  }

  Future<void> saveBiometricEnabled(bool enabled) =>
      _storage.write(key: _biometricEnabledKey, value: enabled.toString());

  /// Detik epoch UTC saat user TERAKHIR membuktikan identitasnya dengan
  /// password -- diambil dari klaim `auth_time` di JWT (bukan dari jam HP saat
  /// login), dan sengaja TIDAK ikut berubah saat token di-refresh. Dipakai
  /// SessionPolicy untuk memaksa login penuh minimal 1x24 jam, dan bisa dibaca
  /// tanpa jaringan sama sekali.
  Future<int?> readAuthTime() async {
    final raw = await _storage.read(key: _authTimeKey);
    if (raw == null) return null;
    return int.tryParse(raw);
  }

  Future<void> saveAuthTime(int epochSeconds) =>
      _storage.write(key: _authTimeKey, value: epochSeconds.toString());
}
