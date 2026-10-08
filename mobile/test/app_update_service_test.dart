import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart' as crypto;
import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/data/vms_api.dart';
import 'package:vms_mobile/features/update/app_update_service.dart';

/// Unduhan pembaruan (docs/32): URL relatif saja, ukuran + SHA-256 wajib cocok, berkas cocok dipakai ulang.
class _BytesAdapter implements HttpClientAdapter {
  _BytesAdapter(this.bytes);
  final List<int> bytes;
  int calls = 0;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls++;
    return ResponseBody.fromBytes(
      bytes,
      200,
      headers: {
        Headers.contentLengthHeader: ['${bytes.length}'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('vms/app_update');
  late Directory dir;

  setUp(() {
    dir = Directory.systemTemp.createTempSync('pembaruan');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          switch (call.method) {
            case 'updatesDir':
              return dir.path;
            case 'sha256':
              final path = (call.arguments as Map)['path'] as String;
              return crypto.sha256
                  .convert(File(path).readAsBytesSync())
                  .toString();
          }
          return null;
        });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
    dir.deleteSync(recursive: true);
  });

  final apk = utf8.encode('isi apk uji ' * 50);
  ReleaseDownload release({
    String? sha,
    int? size,
    String url = '/api/v1/app/android/files/vms-1.2.0-6-arm64-v8a.apk',
  }) => ReleaseDownload(
    abi: 'arm64-v8a',
    url: url,
    sha256: sha ?? crypto.sha256.convert(apk).toString(),
    size: size ?? apk.length,
  );

  AppUpdateService service(_BytesAdapter adapter) => AppUpdateService(
    api: VmsApi(
      ApiClient(tokenStorage: const TokenStorage(), baseUrl: 'http://uji'),
    ),
    downloader: Dio()..httpClientAdapter = adapter,
    baseUrl: 'http://uji',
  );

  test('respons server dibaca: status, catatan, berkas, label build', () {
    final info = UpdateInfo.fromJson({
      'status': 'REQUIRED',
      'current_build': 3,
      'latest_build': 6,
      'latest_version': '1.2.0',
      'notes': ['Perbaikan'],
      'download': {
        'abi': 'arm64-v8a',
        'url': '/x.apk',
        'sha256': 'ab',
        'size': 1048576,
      },
    });
    expect(info.status, UpdateStatus.required);
    expect(info.hasUpdate, isTrue);
    expect(info.latestLabel, '1.2.0 (build 6)');
    expect(info.download!.sizeLabel, '1.0 MB');
    expect(
      UpdateInfo.fromJson({'status': 'UP_TO_DATE', 'current_build': 6})
          .hasUpdate,
      isFalse,
    );
  });

  test(
    'unduhan cocok disimpan, lalu dipakai ulang tanpa mengunduh lagi',
    () async {
      final adapter = _BytesAdapter(apk);
      final s = service(adapter);
      final file = await s.download(release());
      expect(file.readAsBytesSync(), apk);
      expect(file.path.endsWith('vms-1.2.0-6-arm64-v8a.apk'), isTrue);
      await s.download(release());
      expect(adapter.calls, 1);
    },
  );

  test(
    'SHA-256 tidak cocok: ditolak dan berkas setengah jadi dihapus',
    () async {
      final s = service(_BytesAdapter(apk));
      await expectLater(
        s.download(release(sha: '0' * 64)),
        throwsA(isA<UpdateVerificationException>()),
      );
      expect(dir.listSync(), isEmpty);
    },
  );

  test('URL absolut dari server ditolak (hanya host API sendiri)', () async {
    final adapter = _BytesAdapter(apk);
    await expectLater(
      service(adapter).download(release(url: 'https://lain.example/x.apk')),
      throwsA(isA<UpdateVerificationException>()),
    );
    expect(adapter.calls, 0);
  });
}
