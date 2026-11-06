import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/biometric_auth.dart';
import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/session_policy.dart';
import 'auth_state.dart';

/// Pesan tunggal saat sesi ditutup oleh kebijakan 1x24 jam -- dipakai di
/// beberapa tempat, jadi disatukan supaya tidak berbeda-beda bunyinya.
const kSessionExpiredMessage =
    'Demi keamanan, sesi diperbarui setiap hari. Silakan masuk lagi dengan sandi.';

/// Riverpod 3.x tidak lagi punya StateNotifier/StateNotifierProvider (dulu
/// ada di flutter_riverpod 2.x) -- polanya sekarang Notifier/NotifierProvider.
class AuthController extends Notifier<AuthState> {
  // Flag sekali-pakai: true persis setelah login PASSWORD baru berhasil
  // (bukan restore sesi) -- dibaca sekali oleh HomeShell begitu tab utama
  // pertama kali mount untuk menawarkan aktivasi sidik jari (plan Keputusan
  // 7), lalu langsung direset supaya tidak ditawarkan berulang tiap re-render.
  bool _justLoggedIn = false;

  bool consumeJustLoggedIn() {
    final value = _justLoggedIn;
    _justLoggedIn = false;
    return value;
  }

  @override
  AuthState build() {
    // ApiClient dibuat lewat provider terpisah (lihat core/providers.dart) --
    // callback session-expired diisi di sini, bukan lewat constructor
    // ApiClient, supaya tidak ada circular dependency antar provider.
    ref.read(apiClientProvider).onSessionExpired = () {
      state = const AuthUnauthenticated(
        error: 'Sesi Anda berakhir, silakan login ulang.',
      );
    };
    ref.onDispose(() => _exchangeTimer?.cancel());
    ref.read(apiClientProvider).sessionPending = () => _sessionPending;
    _restoreSession();
    return const AuthInitial();
  }

  /// Restore sesi saat aplikasi dibuka. SETIAP cabang di sini WAJIB berakhir
  /// pada salah satu state final -- kalau ada jalur yang keluar tanpa menyetel
  /// state, aplikasi macet selamanya di splash screen tanpa jalan keluar
  /// selain menutup paksa (bug yang pernah terjadi untuk error 5xx/403/
  /// sertifikat, karena diasumsikan interceptor yang menyetel state).
  Future<void> _restoreSession() async {
    final tokenStorage = ref.read(tokenStorageProvider);
    final accessToken = await tokenStorage.readAccessToken();
    if (accessToken == null) {
      // Sesi offline dari login sidik jari yang belum ditukar ke server
      // (aplikasi ditutup saat tanpa sinyal): buka lagi lewat gerbang sidik
      // jari selama token perangkat belum kedaluwarsa.
      if (await tokenStorage.readDeviceExchangePending() &&
          await hasUsableDeviceCredential()) {
        final user = await _cachedUser();
        if (user != null) {
          state = AuthLocked(user);
          _sessionPending = true;
          _startExchangeRetry();
          return;
        }
      }
      state = const AuthUnauthenticated();
      return;
    }

    // Gerbang kebijakan 1x24 jam dievaluasi LEBIH DULU dan sepenuhnya lokal,
    // sehingga berlaku sama persis baik online maupun offline. Sidik jari
    // tidak boleh bisa melewati batas ini.
    if (await _enforceSessionPolicy()) return;

    // Batas total probe ini 6 dtk (termasuk waktu menyambung): tanpa sinyal kita ingin cepat jatuh ke profil
    // cache, bukan menahan splash selama timeout sambung global (15 dtk).
    // Pembatalan Dio tidak memutus proses menyambung yang sedang berjalan, jadi batasnya dipasang di level Dart.
    final probeCancel = CancelToken();
    const probeLimit = Duration(seconds: 6);
    try {
      final response = await ref
          .read(apiClientProvider)
          .dio
          .get('/api/v1/auth/me', cancelToken: probeCancel, options: Options(receiveTimeout: probeLimit))
          .timeout(
            probeLimit,
            onTimeout: () {
              probeCancel.cancel('probe lambat');
              throw DioException.connectionTimeout(
                timeout: probeLimit,
                requestOptions: RequestOptions(path: '/api/v1/auth/me'),
              );
            },
          );
      await tokenStorage.saveCachedProfile(jsonEncode(response.data));
      final user = AuthUser.fromJson(response.data as Map<String, dynamic>);
      state = await _stateForRestoredUser(user);
    } on DioException catch (e) {
      if (isNetworkFailure(e)) {
        NetworkHint.markOffline();
        // TIDAK ADA SINYAL -- ini BUKAN alasan untuk logout paksa. Token yang
        // tersimpan mungkin masih sah; pakai profil hasil login/restore
        // terakhir supaya user tetap bisa bekerja (cek-in dkk tetap diqueue).
        state =
            await _stateFromCachedProfile() ??
            const AuthUnauthenticated(
              error: 'Tidak ada koneksi dan belum ada sesi tersimpan di perangkat ini.',
            );
        return;
      }

      final status = e.response?.statusCode;
      if (status == 401) {
        // Interceptor sudah mencoba refresh; kalau sampai di sini artinya
        // benar-benar ditolak & sesi sudah dibersihkan di sana.
        state = const AuthUnauthenticated(
          error: 'Sesi Anda berakhir, silakan login ulang.',
        );
        return;
      }
      if (status == 403) {
        state = const AuthUnauthenticated(
          error: 'Akun ini terikat dengan perangkat lain. Hubungi HR untuk reset perangkat.',
        );
        return;
      }
      // Server bermasalah (5xx), sertifikat, request dibatalkan, dll. Sesi
      // lokal belum tentu salah -- kalau ada profil cache, tetap izinkan masuk
      // dan biarkan sinkronisasi menyusul. Kalau tidak ada, jatuh ke login
      // dengan pesan apa adanya (JANGAN diam di splash).
      state =
          await _stateFromCachedProfile() ??
          AuthUnauthenticated(
            error:
                'Server sedang bermasalah (${status ?? e.type.name}). Coba lagi nanti.',
          );
    } catch (_) {
      state = const AuthUnauthenticated();
    }
  }

  /// Kembalikan state dari profil yang tersimpan lokal, atau null bila belum
  /// pernah ada sesi berhasil di perangkat ini.
  Future<AuthState?> _stateFromCachedProfile() async {
    final cached = await ref.read(tokenStorageProvider).readCachedProfile();
    if (cached == null) return null;
    try {
      final user = AuthUser.fromJson(
        jsonDecode(cached) as Map<String, dynamic>,
      );
      return await _stateForRestoredUser(user);
    } catch (_) {
      return null;
    }
  }

  /// True bila sesi sudah melewati batas 1x24 jam / cutoff 02:00 -- dalam hal
  /// itu sesi lokal dibersihkan dan state diarahkan ke layar login.
  Future<bool> _enforceSessionPolicy() async {
    final tokenStorage = ref.read(tokenStorageProvider);
    var authTime = await tokenStorage.readAuthTime();
    // Sesi yang dibuat sebelum fitur ini ada belum menyimpan auth_time --
    // ambil dari klaim token yang tersimpan bila memang ada di sana.
    authTime ??= SessionPolicy.authTimeFromJwt(
      await tokenStorage.readAccessToken(),
    );

    if (!SessionPolicy.isExpired(authTime)) return false;

    await tokenStorage.clearSession();
    state = const AuthUnauthenticated(error: kSessionExpiredMessage);
    return true;
  }

  /// Sesi yang di-restore (bukan login password baru) dikunci dulu di balik
  /// sidik jari LOKAL kalau user pernah mengaktifkannya (plan Keputusan 7) --
  /// otorisasi ke server tidak berubah, cuma gerbang tampilan konten di HP.
  /// Login password baru (lihat [login]) TIDAK lewat gerbang ini -- baru
  /// ditawari aktivasi, bukan langsung dikunci.
  Future<AuthState> _stateForRestoredUser(AuthUser user) async {
    final biometricEnabled = await ref
        .read(tokenStorageProvider)
        .readBiometricEnabled();
    return biometricEnabled == true
        ? AuthLocked(user)
        : AuthAuthenticated(user);
  }

  /// Dipanggil dari biometric_lock_screen.dart setelah prompt sidik jari
  /// sukses -- TIDAK ADA panggilan server di sini, sesi memang sudah sah
  /// sejak _restoreSession; ini murni membuka gerbang lokalnya. Kebijakan
  /// 1x24 jam tetap diperiksa: sidik jari tidak boleh melewatinya.
  Future<void> unlockWithBiometrics(AuthUser user) async {
    if (await _enforceSessionPolicy()) return;
    state = AuthAuthenticated(user);
  }

  /// Kunci ulang konten saat aplikasi kembali dari latar belakang. Tanpa ini
  /// gerbang sidik jari hanya berlaku pada cold start, sehingga HP yang cuma
  /// di-minimize lalu berpindah tangan langsung menampilkan isi aplikasi.
  Future<void> relockIfBiometricEnabled() async {
    final current = state;
    if (current is! AuthAuthenticated) return;
    // Prompt sidik jari SISTEM juga membuat aplikasi pause/resume. Tanpa
    // penjagaan ini, aplikasi mengunci ulang dirinya sendiri tepat setelah
    // verifikasi berhasil, lalu memunculkan prompt lagi -- berulang tanpa
    // henti. Ditemukan saat uji di perangkat asli.
    if (BiometricAuth.isPromptInFlight) return;
    if (await _enforceSessionPolicy()) return;
    final enabled = await ref.read(tokenStorageProvider).readBiometricEnabled();
    if (enabled == true) {
      state = AuthLocked(current.user);
    }
  }

  Future<void> login({
    required String username,
    required String password,
  }) async {
    state = const AuthLoading();
    final apiClient = ref.read(apiClientProvider);
    final tokenStorage = ref.read(tokenStorageProvider);
    final deviceId = ref.read(deviceIdProvider);

    try {
      final clientId = await deviceId.getClientId();
      final loginResponse = await apiClient.dio.post(
        '/api/v1/auth/login',
        data: {'email': username, 'password': password, 'platform': 'mobile'},
        options: Options(
          headers: {
            'X-Device-Id': clientId,
            'X-Device-Fingerprint': clientId,
            'X-Device-Label': 'Aplikasi Android',
          },
        ),
      );

      final accessToken = (loginResponse.data as Map)['access_token'] as String;
      final refreshToken = refreshTokenFromResponse(loginResponse.headers);
      await tokenStorage.saveTokens(
        accessToken: accessToken,
        refreshToken: refreshToken,
      );

      // Waktu login password menurut SERVER (klaim auth_time), bukan jam HP --
      // dasar kebijakan 1x24 jam. Token lama tanpa klaim ini tidak menutup
      // sesi siapa pun (lihat SessionPolicy.isExpired).
      final authTime = SessionPolicy.authTimeFromJwt(accessToken);
      if (authTime != null) {
        await tokenStorage.saveAuthTime(authTime);
      }

      final meResponse = await apiClient.dio.get('/api/v1/auth/me');
      final me = AuthUser.fromJson(meResponse.data as Map<String, dynamic>);
      // Masuk lewat "Masuk dengan Password" tidak menghapus antrean offline
      // (milik orang yang sama biasanya). Bila ternyata akun BERBEDA dari
      // pemilik profil cache, antrean itu milik orang lain: buang sebelum
      // tersinkron atas nama akun baru.
      final previous = await tokenStorage.readCachedProfile();
      if (previous != null) {
        String? previousId;
        try {
          previousId = (jsonDecode(previous) as Map<String, dynamic>)['user_id']
              as String?;
        } catch (_) {
          previousId = null;
        }
        if (previousId != me.id) {
          await ref.read(appDatabaseProvider).wipeAllLocalData();
        }
      }
      await tokenStorage.saveCachedProfile(jsonEncode(meResponse.data));
      _justLoggedIn = true;
      state = AuthAuthenticated(me);
    } on DioException catch (e) {
      state = AuthUnauthenticated(
        error: _extractErrorMessage(e),
        lockedUntil: _lockedUntil(e),
      );
    }
  }

  // ---- Login sidik jari dengan kredensial perangkat (30 hari) ----

  static const kDeviceLoginRejectedMessage = 'Silakan masuk dengan sandi.';
  static const kFingerprintCancelledMessage =
      'Sidik jari dibatalkan. Anda tetap bisa masuk dengan email dan sandi.';
  static const kFingerprintNoNetworkMessage =
      'Tidak ada sinyal dan belum ada sesi tersimpan di perangkat ini. '
      'Coba lagi atau masuk dengan sandi.';
  static const _deviceHeaders = {'X-Device-Label': 'Aplikasi Android'};
  static const _rejectCodes = {
    'BIOMETRIC_INVALID',
    'BIOMETRIC_REUSED',
    'INACTIVE',
    'NOT_FIELD_STAFF',
  };

  Timer? _exchangeTimer;

  /// True selama sesi offline belum ditukar (belum ada token akses).
  bool _sessionPending = false;
  bool _exchanging = false;

  /// Jarak coba ulang tukar token perangkat di latar belakang.
  static Duration exchangeRetryInterval = const Duration(seconds: 20);

  /// True bila ada token perangkat yang belum kedaluwarsa.
  Future<bool> hasUsableDeviceCredential() async {
    final cred = await ref.read(tokenStorageProvider).readDeviceCredential();
    return cred != null && cred.expiresAt.isAfter(DateTime.now().toUtc());
  }

  /// Dipanggil saat saklar "Login sidik jari" dinyalakan (butuh login).
  /// Mengembalikan pesan galat awam, atau null bila berhasil.
  Future<String?> enableDeviceCredential() async {
    try {
      final r = await ref.read(apiClientProvider).dio.post(
        '/api/v1/auth/device-credential',
        options: Options(headers: _deviceHeaders),
      );
      final data = r.data as Map;
      await ref.read(tokenStorageProvider).saveDeviceCredential(
        token: data['device_token'] as String,
        expiresAt: DateTime.parse(data['expires_at'] as String),
      );
      return null;
    } on DioException catch (e) {
      return isNetworkFailure(e)
          ? 'Butuh sinyal untuk mengaktifkan masuk dengan sidik jari. Coba lagi saat ada sinyal.'
          : apiErrorMessage(
              e,
              fallback: 'Sidik jari belum bisa diaktifkan. Coba lagi.',
            );
    } catch (_) {
      return 'Sidik jari belum bisa diaktifkan. Coba lagi.';
    }
  }

  /// Tukar token perangkat -> token sesi + token perangkat baru. Token baru
  /// disimpan SEGERA dalam satu kunci; bila gagal menyimpan, nilai lama utuh.
  Future<void> _exchangeDeviceToken(String deviceToken) async {
    final storage = ref.read(tokenStorageProvider);
    final clientId = await ref.read(deviceIdProvider).getClientId();
    final r = await ref.read(apiClientProvider).dio.post(
      '/api/v1/auth/biometric-login',
      data: {'device_token': deviceToken},
      options: Options(
        headers: {
          'X-Device-Id': clientId,
          'X-Device-Fingerprint': clientId,
          ..._deviceHeaders,
        },
      ),
    );
    final data = r.data as Map;
    await storage.saveDeviceCredential(
      token: data['device_token'] as String,
      expiresAt: DateTime.parse(data['device_token_expires_at'] as String),
    );
    final access = data['access_token'] as String;
    await storage.saveTokens(
      accessToken: access,
      refreshToken: refreshTokenFromResponse(r.headers),
    );
    final authTime = SessionPolicy.authTimeFromJwt(access);
    await storage.saveAuthTime(
      authTime ?? DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000,
    );
    await storage.saveDeviceExchangePending(false);
    _sessionPending = false;
  }

  Future<AuthUser?> _cachedUser() async {
    final cached = await ref.read(tokenStorageProvider).readCachedProfile();
    if (cached == null) return null;
    try {
      return AuthUser.fromJson(jsonDecode(cached) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> _rejectDeviceLogin() async {
    _exchangeTimer?.cancel();
    _sessionPending = false;
    final storage = ref.read(tokenStorageProvider);
    await storage.clearDeviceCredential();
    await storage.clearSession();
    state = const AuthUnauthenticated(error: kDeviceLoginRejectedMessage);
  }

  /// Tombol "Masuk dengan sidik jari" di layar login.
  Future<void> loginWithDeviceCredential() async {
    final storage = ref.read(tokenStorageProvider);
    final cred = await storage.readDeviceCredential();
    if (cred == null || !cred.expiresAt.isAfter(DateTime.now().toUtc())) {
      await _rejectDeviceLogin();
      return;
    }
    final ok = await ref
        .read(biometricAuthProvider)
        .authenticate('Verifikasi sidik jari untuk masuk ke VMS Mobile');
    if (!ok) {
      state = const AuthUnauthenticated(error: kFingerprintCancelledMessage);
      return;
    }
    state = const AuthLoading();
    try {
      await _exchangeDeviceToken(cred.token);
      final me = await ref.read(apiClientProvider).dio.get('/api/v1/auth/me');
      final user = AuthUser.fromJson(me.data as Map<String, dynamic>);
      await _wipeIfOtherUser(user.id);
      await storage.saveCachedProfile(jsonEncode(me.data));
      state = AuthAuthenticated(user);
    } on DioException catch (e) {
      if (isNetworkFailure(e)) {
        NetworkHint.markOffline();
        // Tanpa sinyal: sidik jari lolos, buka sesi lokal selama token
        // perangkat belum kedaluwarsa (dicek di atas). Tanpa panggilan server.
        final user = await _cachedUser();
        if (user == null) {
          state = const AuthUnauthenticated(
            error: kFingerprintNoNetworkMessage,
          );
          return;
        }
        await storage.saveDeviceExchangePending(true);
        _sessionPending = true;
        state = AuthAuthenticated(user);
        _startExchangeRetry();
        return;
      }
      if (_rejectCodes.contains(apiErrorCode(e))) {
        await _rejectDeviceLogin();
        return;
      }
      state = AuthUnauthenticated(
        error: apiErrorMessage(
          e,
          fallback: 'Masuk dengan sidik jari gagal. Coba lagi.',
        ),
      );
    } catch (_) {
      state = const AuthUnauthenticated(
        error: 'Masuk dengan sidik jari gagal. Coba lagi atau masuk dengan sandi.',
      );
    }
  }

  Future<void> _wipeIfOtherUser(String newId) async {
    final previous = await ref.read(tokenStorageProvider).readCachedProfile();
    if (previous == null) return;
    String? previousId;
    try {
      previousId =
          (jsonDecode(previous) as Map<String, dynamic>)['user_id'] as String?;
    } catch (_) {}
    if (previousId != newId) {
      await ref.read(appDatabaseProvider).wipeAllLocalData();
    }
  }

  void _startExchangeRetry() {
    _exchangeTimer?.cancel();
    _exchangeTimer = Timer.periodic(
      exchangeRetryInterval,
      (_) => unawaited(retryDeviceExchange()),
    );
  }

  /// Tukar token perangkat di latar belakang setelah sesi offline. Berhasil:
  /// berhenti. Tanpa sinyal: coba lagi nanti. Ditolak atau kedaluwarsa:
  /// keluarkan ke layar login.
  Future<void> retryDeviceExchange() async {
    if (_exchanging) return;
    final storage = ref.read(tokenStorageProvider);
    if (!await storage.readDeviceExchangePending()) {
      _exchangeTimer?.cancel();
      return;
    }
    final cred = await storage.readDeviceCredential();
    if (cred == null || !cred.expiresAt.isAfter(DateTime.now().toUtc())) {
      await _rejectDeviceLogin();
      return;
    }
    _exchanging = true;
    try {
      await _exchangeDeviceToken(cred.token);
      _exchangeTimer?.cancel();
      // Token akses sudah ada: kirim antrean yang tertahan, sekali.
      unawaited(ref.read(syncEngineProvider).syncAll().then((_) {}));
    } on DioException catch (e) {
      if (!isNetworkFailure(e) && _rejectCodes.contains(apiErrorCode(e))) {
        await _rejectDeviceLogin();
      }
    } catch (_) {
      // Coba lagi pada detak berikutnya.
    } finally {
      _exchanging = false;
    }
  }

  /// Cooldown dari server (`LOCKED`, details.retry_after_seconds) dihitung
  /// relatif terhadap jam HP saat jawaban diterima -- hanya untuk hitung
  /// mundur tampilan; server tetap yang memutuskan kapan login dibuka lagi.
  DateTime? _lockedUntil(DioException e) {
    final data = e.response?.data;
    if (data is! Map || data['error'] is! Map) return null;
    final error = data['error'] as Map;
    if (error['code'] != 'LOCKED') return null;
    final details = error['details'];
    final seconds = details is Map ? details['retry_after_seconds'] : null;
    if (seconds is! num || seconds <= 0) return null;
    return DateTime.now().add(Duration(seconds: seconds.ceil()));
  }

  /// Logout MANUAL dari layar Profil: bersihkan seluruh jejak sesi di HP,
  /// termasuk preferensi sidik jari & profil cache.
  Future<void> logout() async {
    final apiClient = ref.read(apiClientProvider);
    final tokenStorage = ref.read(tokenStorageProvider);
    try {
      final refreshToken = await tokenStorage.readRefreshToken();
      await apiClient.dio.post(
        '/api/v1/auth/logout',
        options: Options(
          headers: refreshToken == null
              ? null
              : refreshCookieHeader(refreshToken),
        ),
      );
    } catch (_) {
      // Tidak masalah -- tetap hapus sesi lokal apapun hasilnya.
    }
    await tokenStorage.clearAll();
    // Bersihkan juga antrian & cache lokal. Tanpa ini, data yang belum terkirim
    // milik user sebelumnya akan tersinkron ATAS NAMA user berikutnya yang login
    // di HP yang sama -- server selalu menimpa employee_id dari token pengirim.
    await ref.read(appDatabaseProvider).wipeAllLocalData();
    state = const AuthUnauthenticated();
  }

  /// Jalan keluar dari layar kunci sidik jari ("Masuk dengan Password").
  ///
  /// Berbeda dari [logout]: TIDAK menunggu panggilan ke server lebih dulu.
  /// Staf yang gagal sidik jari (jari basah/kotor -- hal biasa di lapangan)
  /// sambil berada di area tanpa sinyal harus tetap bisa sampai ke form login
  /// seketika, bukan menunggu timeout jaringan.
  Future<void> switchToPasswordLogin() async {
    final tokenStorage = ref.read(tokenStorageProvider);
    await tokenStorage.clearSession();
    state = const AuthUnauthenticated();

    // Beri tahu server belakangan, tanpa menahan UI. Gagal pun tidak apa-apa:
    // token lokal sudah dibuang, dan token lama akan kedaluwarsa sendiri.
    unawaited(_notifyServerLogout());
  }

  Future<void> _notifyServerLogout() async {
    try {
      await ref.read(apiClientProvider).dio.post('/api/v1/auth/logout');
    } catch (_) {
      // Sengaja diabaikan -- ini best-effort.
    }
  }

  String _extractErrorMessage(DioException e) {
    if (isNetworkFailure(e)) {
      return 'Tidak bisa terhubung ke server. Periksa koneksi dan alamat server.';
    }
    // Dulu hanya membaca `detail` (format FastAPI) sehingga pesan VMS
    // (`error.message`: salah sandi, sisa percobaan, terkunci) tak pernah tampil.
    return apiErrorMessage(e, fallback: 'Login gagal. Coba lagi.');
  }
}

/// Menjalankan future tanpa menunggunya, dan tanpa memicu unhandled error.
void unawaited(Future<void> future) {
  future.catchError((_) {});
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
