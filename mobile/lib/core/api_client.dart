import 'dart:async';

import 'package:dio/dio.dart';

import 'app_update_channel.dart';
import 'constants.dart';
import 'token_storage.dart';

typedef VoidCallback = void Function();

/// Klien HTTP terpusat: menyuntik Authorization header, dan otomatis
/// silent-refresh saat access_token (umur 30 menit, lihat Keputusan 5)
/// kedaluwarsa -- request asli diulang otomatis setelah refresh berhasil.
///
/// Kalau refresh juga gagal (refresh_token kedaluwarsa/dicabut), token
/// dibersihkan dan [onSessionExpired] dipanggil supaya lapisan UI (router)
/// bisa mengarahkan user kembali ke halaman login. Callback ini sengaja bisa
/// diisi belakangan (bukan lewat constructor) supaya tidak ada dependency
/// melingkar dengan provider auth yang justru memakai ApiClient ini.
class ApiClient {
  /// [baseUrl]: bawaan [ApiConfig.baseUrl]; diisi uji yang memakai server HTTP lokal.
  ApiClient({required TokenStorage tokenStorage, String? baseUrl})
    : _tokenStorage = tokenStorage, // ignore: prefer_initializing_formals
      _baseUrl = baseUrl ?? ApiConfig.baseUrl,
      dio = Dio(
        BaseOptions(
          baseUrl: baseUrl ?? ApiConfig.baseUrl,
          connectTimeout: ApiConfig.connectTimeout,
          receiveTimeout: ApiConfig.receiveTimeout,
          sendTimeout: ApiConfig.sendTimeout,
          contentType: 'application/json',
        ),
      ) {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final agent = await appUserAgent();
          if (agent != null) options.headers['User-Agent'] = agent;
          final token = await _tokenStorage.readAccessToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onResponse: (response, handler) {
          NetworkHint.markOnline();
          handler.next(response);
        },
        onError: (error, handler) async {
          if (isNetworkFailure(error)) NetworkHint.markOffline();
          final isUnauthorized = error.response?.statusCode == 401;
          final alreadyRetried =
              error.requestOptions.extra['retriedAfterRefresh'] == true;
          final isAuthEndpoint =
              error.requestOptions.path.contains('/auth/login') ||
              error.requestOptions.path.contains('/auth/biometric-login') ||
              error.requestOptions.path.contains('/auth/refresh');

          if (!isUnauthorized || alreadyRetried || isAuthEndpoint) {
            handler.next(error);
            return;
          }

          final refreshed = await _tryRefreshToken();
          if (refreshed == _RefreshOutcome.networkFailure) {
            // Koneksi putus di tengah refresh -- refresh token BELUM tentu
            // kedaluwarsa. Menghapus sesi di sini membuat sinyal lapangan yang
            // putus-putus terasa seperti logout paksa permanen.
            handler.next(error);
            return;
          }
          if (refreshed == _RefreshOutcome.rejected) {
            await _tokenStorage.clearSession();
            onSessionExpired?.call();
            handler.next(error);
            return;
          }

          try {
            final retryOptions = error.requestOptions;
            retryOptions.extra['retriedAfterRefresh'] = true;
            final newToken = await _tokenStorage.readAccessToken();
            retryOptions.headers['Authorization'] = 'Bearer $newToken';
            // FormData (unggahan berkas) hanya bisa dikirim sekali — kirim salinannya.
            final data = retryOptions.data;
            if (data is FormData) retryOptions.data = data.clone();
            final response = await dio.fetch(retryOptions);
            handler.resolve(response);
          } on DioException catch (retryError) {
            // Teruskan kegagalan kiriman ULANG, bukan 401 lama: bila sinyal putus di sini, pemanggil
            // harus melihat gangguan jaringan (mis. layar Absensi lalu menyimpan absen offline, R-34).
            handler.next(retryError);
          } catch (_) {
            handler.next(error);
          }
        },
      ),
    );
  }

  final Dio dio;
  final TokenStorage _tokenStorage;
  final String _baseUrl;

  /// Diisi oleh authControllerProvider setelah ApiClient dibuat.
  VoidCallback? onSessionExpired;

  Completer<_RefreshOutcome>? _refreshInFlight;

  /// Mencegah beberapa request 401 sekaligus memicu refresh berkali-kali --
  /// request kedua dst menunggu hasil refresh yang sudah berjalan.
  ///
  /// Membedakan "server menolak" dari "jaringan putus" itu KRUSIAL: hanya
  /// penolakan server yang boleh mengakhiri sesi. Sebelumnya keduanya
  /// diperlakukan sama, sehingga satu kali gangguan sinyal saat refresh bisa
  /// menghapus refresh token yang sebenarnya masih berlaku berhari-hari.
  Future<_RefreshOutcome> _tryRefreshToken() async {
    if (_refreshInFlight != null) return _refreshInFlight!.future;

    final completer = Completer<_RefreshOutcome>();
    _refreshInFlight = completer;
    try {
      final refreshToken = await _tokenStorage.readRefreshToken();
      if (refreshToken == null) {
        // Tidak ada bahan untuk refresh sama sekali -- ini memang sesi mati,
        // bukan gangguan jaringan.
        completer.complete(_RefreshOutcome.rejected);
        return _RefreshOutcome.rejected;
      }
      final freshDio = Dio(
        BaseOptions(
          baseUrl: _baseUrl,
          connectTimeout: ApiConfig.connectTimeout,
          receiveTimeout: ApiConfig.receiveTimeout,
          sendTimeout: ApiConfig.sendTimeout,
        ),
      );
      final response = await freshDio.post(
        '/api/v1/auth/refresh',
        options: Options(headers: refreshCookieHeader(refreshToken)),
      );
      final newAccessToken = (response.data as Map)['access_token'] as String;
      // Server merotasi refresh token di setiap refresh (cookie baru).
      await _tokenStorage.saveTokens(
        accessToken: newAccessToken,
        refreshToken: refreshTokenFromResponse(response.headers),
      );
      completer.complete(_RefreshOutcome.success);
      return _RefreshOutcome.success;
    } on DioException catch (e) {
      final outcome = isNetworkFailure(e)
          ? _RefreshOutcome.networkFailure
          : _RefreshOutcome.rejected;
      completer.complete(outcome);
      return outcome;
    } catch (_) {
      // Bentuk respons tak terduga (mis. access_token hilang) -- perlakukan
      // sebagai penolakan, bukan gangguan jaringan.
      completer.complete(_RefreshOutcome.rejected);
      return _RefreshOutcome.rejected;
    } finally {
      _refreshInFlight = null;
    }
  }
}

enum _RefreshOutcome { success, networkFailure, rejected }

/// True bila kegagalan ini soal KONEKSI, bukan penolakan dari server.
/// Dipakai bersama oleh interceptor, AuthController, dan SyncEngine supaya
/// ketiganya menilai "offline" dengan cara yang sama.
bool isNetworkFailure(DioException e) {
  if (e.response != null) return false;
  return e.type == DioExceptionType.connectionError ||
      e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.receiveTimeout ||
      e.type == DioExceptionType.sendTimeout ||
      e.type == DioExceptionType.unknown;
}

/// Petunjuk jaringan bersama. Tanpa sinyal, tiap permintaan menunggu timeout sendiri; bila beberapa dibaca
/// berurutan, layar bisa diam puluhan detik. Setelah SATU kegagalan jaringan, pembacaan yang punya cache
/// langsung memakai cache selama [window] — tanpa menunggu timeout lagi. Hanya untuk pembacaan; penulisan
/// (kirim/absen) tetap mencoba jaringan atau masuk antrean seperti biasa.
class NetworkHint {
  static const Duration window = Duration(seconds: 12);
  static DateTime? _offlineUntil;

  static bool get probablyOffline {
    final until = _offlineUntil;
    return until != null && DateTime.now().isBefore(until);
  }

  static void markOffline() => _offlineUntil = DateTime.now().add(window);
  static void markOnline() => _offlineUntil = null;
}

/// Backend mengirim refresh token sebagai cookie httpOnly `refresh_token`
/// (dirancang untuk web). Aplikasi mobile menyimpannya di Keystore dan
/// mengirimnya kembali sebagai header Cookie pada /auth/refresh & /auth/logout.
const refreshCookieName = 'refresh_token';

String? refreshTokenFromResponse(Headers headers) {
  for (final cookie in headers['set-cookie'] ?? const <String>[]) {
    final first = cookie.split(';').first.trim();
    if (first.startsWith('$refreshCookieName=')) {
      final value = first.substring(refreshCookieName.length + 1);
      return value.isEmpty ? null : value;
    }
  }
  return null;
}

Map<String, String> refreshCookieHeader(String refreshToken) => {
  'Cookie': '$refreshCookieName=$refreshToken',
};
