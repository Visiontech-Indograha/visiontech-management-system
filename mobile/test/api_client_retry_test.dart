// Interceptor 401 → refresh → kirim ulang, lewat HTTP sungguhan (server lokal), termasuk unggahan berkas.
// Uji nyata prod 2026-10-02 (HP Realme, 4G + Tailscale): token habis tepat saat absen; refresh berhasil
// tetapi kiriman ulang putus di jaringan → interceptor meneruskan 401 lama, layar Absensi tidak
// menyimpan absen luring dan absen hilang.
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/token_storage.dart';

/// Server uji: token `lama` → 401, `/auth/refresh` → token `baru`. [dropRetry]: kiriman ulang
/// (bertoken `baru`) diputus di tengah jalan seperti sinyal hilang.
Future<(HttpServer, List<String>)> _server({bool dropRetry = false}) async {
  final calls = <String>[];
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((req) async {
    final auth = req.headers.value('authorization');
    calls.add('${req.method} ${req.uri.path} $auth');
    if (dropRetry && auth == 'Bearer baru') {
      (await req.response.detachSocket()).destroy();
      return;
    }
    await req.drain<void>();
    req.response.headers.contentType = ContentType.json;
    if (req.uri.path.endsWith('/auth/refresh')) {
      req.response.headers.add('set-cookie', '$refreshCookieName=r2; Path=/');
      req.response.write('{"access_token":"baru"}');
    } else if (auth != 'Bearer baru') {
      req.response.statusCode = 401;
      req.response.write('{"error":{"code":"UNAUTHENTICATED","message":"Sesi berakhir."}}');
    } else {
      req.response.write('{"file_id":"f-1"}');
    }
    await req.response.close();
  });
  return (server, calls);
}

Future<FormData> _selfie() async {
  final dir = await Directory.systemTemp.createTemp('vms_retry');
  final file = File('${dir.path}/swafoto.jpg')..writeAsBytesSync(List.filled(300000, 7));
  return FormData.fromMap({'file': await MultipartFile.fromFile(file.path, filename: 'swafoto.jpg')});
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    HttpOverrides.global = null; // binding uji memblok HTTP; uji ini memakai server lokal sungguhan
    FlutterSecureStorage.setMockInitialValues({'vms_access_token': 'lama', 'vms_refresh_token': 'r1'});
  });

  test('unggahan yang ditolak 401 dikirim ulang dengan token baru setelah refresh', () async {
    final (server, calls) = await _server();
    addTearDown(() => server.close(force: true));
    final client = ApiClient(tokenStorage: const TokenStorage(), baseUrl: 'http://127.0.0.1:${server.port}');

    final res = await client.dio.post('/api/v1/files/upload', data: await _selfie());

    expect(res.data, {'file_id': 'f-1'});
    expect(calls, [
      'POST /api/v1/files/upload Bearer lama',
      'POST /api/v1/auth/refresh null',
      'POST /api/v1/files/upload Bearer baru',
    ]);
  });

  test('kiriman ulang yang putus di jaringan dilaporkan sebagai gangguan jaringan, bukan 401', () async {
    final (server, calls) = await _server(dropRetry: true);
    addTearDown(() => server.close(force: true));
    final client = ApiClient(tokenStorage: const TokenStorage(), baseUrl: 'http://127.0.0.1:${server.port}');

    final error = await client.dio
        .post<dynamic>('/api/v1/files/upload', data: await _selfie())
        .then<DioException?>((_) => null, onError: (Object e) => e as DioException);

    expect(calls.last, 'POST /api/v1/files/upload Bearer baru');
    expect(error, isNotNull);
    expect(error!.response?.statusCode, isNot(401));
    // Layar Absensi memakai pemeriksaan yang sama untuk beralih ke absen luring (R-34).
    expect(isNetworkFailure(error), isTrue);
    // Sesi tidak dihapus: refresh berhasil, yang gagal hanya sinyal.
    expect(await const TokenStorage().readAccessToken(), 'baru');
  });
}
