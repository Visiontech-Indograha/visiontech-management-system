import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/biometric_auth.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/auth/login_screen.dart';

/// Penyimpanan di memori (tanpa Keystore).
class _MemStorage extends TokenStorage {
  final Map<String, String> m = {};
  bool failDeviceWrite = false;

  @override
  Future<String?> readAccessToken() async => m['access'];
  @override
  Future<String?> readRefreshToken() async => m['refresh'];
  @override
  Future<void> saveTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    m['access'] = accessToken;
    if (refreshToken != null) m['refresh'] = refreshToken;
  }

  @override
  Future<void> clearSession() async {
    m.remove('access');
    m.remove('refresh');
  }

  @override
  Future<String?> readClientId() async => 'cid';
  @override
  Future<void> saveClientId(String id) async {}
  @override
  Future<String?> readCachedProfile() async => m['profile'];
  @override
  Future<void> saveCachedProfile(String j) async => m['profile'] = j;
  @override
  Future<int?> readAuthTime() async => null;
  @override
  Future<void> saveAuthTime(int e) async {}
  @override
  Future<bool?> readBiometricEnabled() async => true;
  @override
  Future<void> saveDeviceCredential({
    required String token,
    required DateTime expiresAt,
  }) async {
    if (failDeviceWrite) throw StateError('gagal simpan');
    m['dev'] = '$token|${expiresAt.toUtc().toIso8601String()}';
  }

  @override
  Future<({String token, DateTime expiresAt})?> readDeviceCredential() async {
    final v = m['dev'];
    if (v == null) return null;
    final p = v.split('|');
    return (token: p[0], expiresAt: DateTime.parse(p[1]));
  }

  @override
  Future<void> clearDeviceCredential() async {
    m.remove('dev');
    m.remove('pending');
  }

  @override
  Future<bool> readDeviceExchangePending() async => m['pending'] == 'true';
  @override
  Future<void> saveDeviceExchangePending(bool p) async =>
      p ? m['pending'] = 'true' : m.remove('pending');
}

class _FakeBio extends BiometricAuth {
  _FakeBio(this.ok);
  bool ok;
  int calls = 0;
  @override
  Future<bool> authenticate(String reason) async {
    calls++;
    return ok;
  }

  @override
  Future<bool> isDeviceSupported() async => true;
}

/// Adapter HTTP palsu: `handler` menerima path, mengembalikan respons atau
/// melempar DioException jaringan.
class _Adapter implements HttpClientAdapter {
  _Adapter(this.handler);
  final ResponseBody Function(RequestOptions o) handler;
  final List<String> paths = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions o,
    Stream<Uint8List>? s,
    Future<void>? c,
  ) async {
    paths.add(o.path);
    return handler(o);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Object body, [int status = 200]) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: ['application/json'],
    if (status == 200)
      'set-cookie': ['refresh_token=r1; Path=/; HttpOnly'],
  },
);

ResponseBody _err(String code, int status) =>
    _json({'error': {'code': code, 'message': 'x'}}, status);

const _me = {
  'user_id': 'u1',
  'email': 'a@b.id',
  'role': 'MEMBER',
  'employee_id': 'e1',
};

ResponseBody _ok(RequestOptions o) {
  if (o.path.contains('biometric-login')) {
    return _json({
      'access_token': 'acc2',
      'token_type': 'bearer',
      'device_token': 'dev-baru',
      'device_token_expires_at': DateTime.now()
          .toUtc()
          .add(const Duration(days: 30))
          .toIso8601String(),
    });
  }
  return _json(_me);
}

ResponseBody _offline(RequestOptions o) => throw DioException.connectionError(
  requestOptions: o,
  reason: 'tidak ada sinyal',
);

({ProviderContainer c, _MemStorage st, _FakeBio bio, _Adapter ad}) _setup(
  ResponseBody Function(RequestOptions) h, {
  bool bioOk = true,
  bool withDevice = true,
  bool withProfile = true,
  Duration deviceAge = const Duration(days: 10),
}) {
  final st = _MemStorage();
  if (withDevice) {
    st.m['dev'] =
        'dev-lama|${DateTime.now().toUtc().add(deviceAge).toIso8601String()}';
  }
  if (withProfile) st.m['profile'] = jsonEncode(_me);
  final bio = _FakeBio(bioOk);
  final api = ApiClient(tokenStorage: st, baseUrl: 'http://x');
  final ad = _Adapter(h);
  api.dio.httpClientAdapter = ad;
  final c = ProviderContainer(
    overrides: [
      tokenStorageProvider.overrideWithValue(st),
      biometricAuthProvider.overrideWithValue(bio),
      apiClientProvider.overrideWithValue(api),
    ],
  );
  addTearDown(c.dispose);
  return (c: c, st: st, bio: bio, ad: ad);
}

Future<void> _settle(ProviderContainer c) async {
  c.read(authControllerProvider);
  await Future<void>.delayed(const Duration(milliseconds: 50));
}

void main() {
  test('online: sidik jari lolos -> masuk, token perangkat dirotasi', () async {
    final t = _setup(_ok);
    await _settle(t.c);
    await t.c.read(authControllerProvider.notifier).loginWithDeviceCredential();
    expect(t.c.read(authControllerProvider), isA<AuthAuthenticated>());
    expect(t.st.m['dev'], startsWith('dev-baru|'));
    expect(t.st.m['access'], 'acc2');
    expect(t.st.m['refresh'], 'r1');
  });

  test('rotasi: gagal simpan token baru -> token lama tidak hilang', () async {
    final t = _setup(_ok);
    t.st.failDeviceWrite = true;
    await _settle(t.c);
    await t.c.read(authControllerProvider.notifier).loginWithDeviceCredential();
    expect(t.st.m['dev'], startsWith('dev-lama|'));
    expect(t.c.read(authControllerProvider), isA<AuthUnauthenticated>());
  });

  test('offline: buka sesi lokal tanpa memanggil server lain', () async {
    final t = _setup(_offline);
    await _settle(t.c);
    await t.c.read(authControllerProvider.notifier).loginWithDeviceCredential();
    expect(t.c.read(authControllerProvider), isA<AuthAuthenticated>());
    expect(t.st.m['pending'], 'true');
    expect(t.st.m['dev'], startsWith('dev-lama|'));
  });

  test('offline lalu online: token ditukar sekali di latar belakang', () async {
    var online = false;
    final t = _setup((o) => online ? _ok(o) : _offline(o));
    await _settle(t.c);
    final n = t.c.read(authControllerProvider.notifier);
    await n.loginWithDeviceCredential();
    await n.retryDeviceExchange(); // masih offline: tetap masuk
    expect(t.c.read(authControllerProvider), isA<AuthAuthenticated>());
    expect(t.st.m['pending'], 'true');
    online = true;
    await n.retryDeviceExchange();
    expect(t.st.m['pending'], isNull);
    expect(t.st.m['dev'], startsWith('dev-baru|'));
    expect(t.c.read(authControllerProvider), isA<AuthAuthenticated>());
    final jumlah = t.ad.paths.length;
    await n.retryDeviceExchange(); // sekali saja
    expect(t.ad.paths.length, jumlah);
  });

  for (final kode in ['BIOMETRIC_INVALID', 'BIOMETRIC_REUSED', 'INACTIVE']) {
    test('ditolak $kode -> ke login, token perangkat dihapus', () async {
      final t = _setup((o) => _err(kode, kode == 'INACTIVE' ? 403 : 401));
      await _settle(t.c);
      await t.c
          .read(authControllerProvider.notifier)
          .loginWithDeviceCredential();
      final s = t.c.read(authControllerProvider);
      expect(s, isA<AuthUnauthenticated>());
      expect((s as AuthUnauthenticated).error, 'Silakan masuk dengan sandi.');
      expect(t.st.m['dev'], isNull);
    });
  }

  test('token perangkat kedaluwarsa (>30 hari): tidak ada sesi offline', () async {
    final t = _setup(_offline, deviceAge: const Duration(days: -1));
    await _settle(t.c);
    await t.c.read(authControllerProvider.notifier).loginWithDeviceCredential();
    expect(t.c.read(authControllerProvider), isA<AuthUnauthenticated>());
    expect(t.st.m['dev'], isNull);
    expect(t.bio.calls, 0);
  });

  test('sidik jari dibatalkan: tetap bisa sandi, token tersimpan', () async {
    final t = _setup(_ok, bioOk: false);
    await _settle(t.c);
    await t.c.read(authControllerProvider.notifier).loginWithDeviceCredential();
    final s = t.c.read(authControllerProvider) as AuthUnauthenticated;
    expect(s.error, AuthController.kFingerprintCancelledMessage);
    expect(t.st.m['dev'], isNotNull);
  });

  test('aktifkan saklar: simpan token perangkat dari server', () async {
    final t = _setup(
      (o) => _json({
        'device_token': 'dev-awal',
        'expires_at': DateTime.now()
            .toUtc()
            .add(const Duration(days: 30))
            .toIso8601String(),
        'device_label': 'Aplikasi Android',
      }),
      withDevice: false,
    );
    await _settle(t.c);
    final galat = await t.c
        .read(authControllerProvider.notifier)
        .enableDeviceCredential();
    expect(galat, isNull);
    expect(t.st.m['dev'], startsWith('dev-awal|'));
  });

  test('aktifkan saklar tanpa sinyal: pesan awam, tidak tersimpan', () async {
    final t = _setup(_offline, withDevice: false);
    await _settle(t.c);
    final galat = await t.c
        .read(authControllerProvider.notifier)
        .enableDeviceCredential();
    expect(galat, contains('sinyal'));
    expect(t.st.m['dev'], isNull);
  });

  Widget app(ProviderContainer c) => UncontrolledProviderScope(
    container: c,
    child: ShadApp(
      theme: VmsShadTheme.light,
      materialThemeBuilder: (context, _) => VmsTheme.light,
      home: const Scaffold(body: LoginScreen()),
    ),
  );

  testWidgets('tombol sidik jari muncul bila token ada, 48dp ke atas', (
    tester,
  ) async {
    final t = _setup(_ok);
    await tester.pumpWidget(app(t.c));
    await tester.pump(const Duration(milliseconds: 500));
    final f = find.byKey(const Key('login-sidik-jari'));
    expect(f, findsOneWidget);
    expect(tester.getSize(f).height, greaterThanOrEqualTo(48));
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('tombol sidik jari hilang bila token tidak ada', (tester) async {
    final t = _setup(_ok, withDevice: false);
    await tester.pumpWidget(app(t.c));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byKey(const Key('login-sidik-jari')), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
