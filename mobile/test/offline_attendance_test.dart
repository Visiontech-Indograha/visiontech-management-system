import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/offline_attendance.dart';
import 'package:vms_mobile/data/sync_engine.dart';

import 'support/fake_backend.dart';

/// R-34 · Absen lapangan luring di HP: rekam bertanda tangan → antre → kirim otomatis saat online.
/// Kunci Keystore & jam internal Android diganti `MethodChannel` tiruan; server diganti [FakeBackend].
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('vms/attendance_attest');
  late AppDatabase db;
  late FakeBackend backend;
  late SyncEngine engine;
  late List<String> signed;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    signed = [];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          switch (call.method) {
            case 'clock':
              return {'elapsed_ms': 9_000_000, 'boot_count': 7};
            case 'publicKey':
              return 'KUNCI-PUBLIK-UJI';
            case 'sign':
              final data = (call.arguments as Map)['data'] as String;
              signed.add(data);
              return 'TTD(${data.length})';
            case 'sha256':
              return 'ab' * 32;
          }
          return null;
        });
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend);
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
    await db.close();
  });

  Future<void> recordCheckIn({String? explanation}) =>
      engine.offlineAttendance.record(
        kind: 'CHECK_IN',
        site: {'id': 'site-1', 'name': 'Proyek Fiber Optik Bekasi'},
        lat: -6.2264,
        lng: 107.0004,
        accuracyM: 5,
        mocked: false,
        gpsTime: DateTime.fromMillisecondsSinceEpoch(1_790_000_000_000),
        explanation: explanation,
      );

  Future<List<PendingSyncRow>> queue() => engine.allPendingOperations();

  Map<String, dynamic> payloadOf(PendingSyncRow row) => Map<String, dynamic>.from(
    jsonDecode((jsonDecode(row.payloadJson) as Map)['payload'] as String) as Map,
  );

  /// Baris antrean absen luring dengan swafoto di berkas sementara (seperti hasil `record` di HP).
  Future<File> queueWithSelfie() async {
    final selfie = File(
      '${Directory.systemTemp.path}/vms_uji_luring_${DateTime.now().microsecondsSinceEpoch}.jpg',
    )..writeAsBytesSync([1, 2, 3]);
    await db
        .into(db.pendingSyncOperations)
        .insert(
          PendingSyncOperationsCompanion.insert(
            entityType: OfflineAttendance.entityType,
            payloadJson: jsonEncode({
              'client_op_id': 'op-selfie',
              'kind': 'CHECK_IN',
              'payload': jsonEncode({'kind': 'CHECK_IN', 'site_name': 'Proyek', 'device_time_ms': 1}),
              'signature': 'TTD',
              'selfie_path': selfie.path,
              'selfie_file_id': null,
            }),
          ),
        );
    return selfie;
  }

  group('merekam absen luring', () {
    test('payload ditandatangani persis apa adanya & memuat jangkar jam server', () async {
      await engine.offlineAttendance.saveAnchor('JANGKAR-SERVER');
      await recordCheckIn(explanation: 'Jalan proyek ditutup');

      final rows = await queue();
      expect(rows, hasLength(1));
      expect(rows.single.entityType, OfflineAttendance.entityType);
      final rec = jsonDecode(rows.single.payloadJson) as Map;
      expect(signed, [rec['payload']]);
      expect(rec['signature'], 'TTD(${(rec['payload'] as String).length})');

      final p = payloadOf(rows.single);
      expect(p['kind'], 'CHECK_IN');
      expect(p['device_id'], 'device-uji');
      expect(p['client_op_id'], rec['client_op_id']);
      expect(p['anchor_token'], 'JANGKAR-SERVER');
      expect(p['anchor_elapsed_ms'], 9_000_000);
      expect(p['event_elapsed_ms'], 9_000_000);
      expect(p['event_boot_count'], 7);
      expect(p['gps_time_ms'], 1_790_000_000_000);
      expect(p['lat'], -6.2264);
      expect(p['explanation'], 'Jalan proyek ditutup');
    });

    test('daftar luring untuk kartu "hari ini" membaca jenis, lokasi & jam rekam', () async {
      await recordCheckIn();
      final pending = await engine.offlineAttendance.pending();
      expect(pending.single['kind'], 'CHECK_IN');
      expect(pending.single['site_name'], 'Proyek Fiber Optik Bekasi');
      expect(pending.single['dead'], isFalse);
      expect(pending.single['device_time_ms'], isA<int>());
    });

    test('kunci perangkat didaftarkan sekali per akun & perangkat', () async {
      backend.routes['/attendance/device-key'] = (_) => {'message': 'ok'};
      await engine.offlineAttendance.ensureDeviceKey('user-1');
      await engine.offlineAttendance.ensureDeviceKey('user-1');
      final sent = backend.requests.where((r) => r.path.endsWith('/attendance/device-key')).toList();
      expect(sent, hasLength(1));
      expect(sent.single.data, {'device_id': 'device-uji', 'public_key': 'KUNCI-PUBLIK-UJI'});
    });
  });

  group('mengirim saat online', () {
    test('terkirim lewat endpoint luring lalu hilang dari antrean; tidak ikut /sync/operations', () async {
      await recordCheckIn();
      backend.routes['/attendance/offline'] = (_) => {'result': 'AUTO_VALID', 'duplicate': false};
      backend.answerSync((_) => 'APPLIED');

      await engine.syncAll();

      final sent = backend.requests.where((r) => r.path.endsWith('/attendance/offline')).single;
      final body = sent.data as Map;
      expect(body['kind'], 'CHECK_IN');
      expect(body['device_id'], 'device-uji');
      expect(signed, [body['payload']]);
      expect(backend.sentOps, isEmpty);
      expect(await queue(), isEmpty);
    });

    for (final (label, status) in [('sesi diperbarui (401)', 401), ('server bermasalah (503)', 503)]) {
      test('$label: antrean tetap & tidak ditandai gagal, urutan dijaga', () async {
        await recordCheckIn();
        await engine.offlineAttendance.record(
          kind: 'CHECK_OUT',
          site: {'id': null, 'name': 'Proyek'},
          lat: -6.2264,
          lng: 107.0004,
          accuracyM: 5,
          mocked: false,
          gpsTime: null,
        );
        backend.routes['/attendance/offline'] = (o) => throw httpError(o, status, {'error': {'message': 'x'}});

        await engine.offlineAttendance.push();

        final rows = await queue();
        expect(rows, hasLength(2));
        expect(rows.every((r) => !r.deadLetter), isTrue);
        // Absen pulang tidak dikirim sebelum absen masuknya sampai.
        expect(backend.requests.where((r) => r.path.endsWith('/attendance/offline')), hasLength(1));
      });
    }

    test('tanpa sinyal: berhenti & coba lagi nanti', () async {
      await recordCheckIn();
      backend.offline();
      await engine.offlineAttendance.push();
      final rows = await queue();
      expect(rows.single.deadLetter, isFalse);
    });

    test('ditolak server (data diubah): ditandai gagal dengan alasan dari server', () async {
      await recordCheckIn();
      backend.routes['/attendance/offline'] = (o) => throw httpError(o, 422, {
        'error': {
          'code': 'OFFLINE_TAMPERED',
          'message': 'Data absen luring tidak utuh — tanggal, jam, atau lokasi diubah setelah direkam. Absen ditolak.',
          'details': <String, dynamic>{},
        },
      });

      await engine.offlineAttendance.push();

      final row = (await queue()).single;
      expect(row.deadLetter, isTrue);
      expect(row.lastError, contains('diubah setelah direkam'));
      expect((await engine.offlineAttendance.pending()).single['dead'], isTrue);
    });
  });

  group('swafoto absen luring', () {
    test('diunggah dulu, file_id ikut terkirim, berkas internal dihapus setelah sukses', () async {
      final selfie = await queueWithSelfie();
      backend.routes['/files/upload'] = (_) => {'file_id': 'file-1'};
      backend.routes['/attendance/offline'] = (_) => {'result': 'NEEDS_REVIEW', 'duplicate': false};

      await engine.offlineAttendance.push();

      final sent = backend.requests.where((r) => r.path.endsWith('/attendance/offline')).single;
      expect((sent.data as Map)['selfie_file_id'], 'file-1');
      expect(await queue(), isEmpty);
      expect(selfie.existsSync(), isFalse);
    });

    test('foto tertunda dihitung; menghapus item antrean ikut membuang swafotonya', () async {
      final selfie = await queueWithSelfie();
      expect(await engine.pendingPhotoCount(), 1);

      await engine.deleteOperation((await queue()).single.id);

      expect(await queue(), isEmpty);
      expect(selfie.existsSync(), isFalse);
    });

    test('swafoto hilang dari HP: ditandai gagal dengan pesan jelas', () async {
      final selfie = await queueWithSelfie();
      selfie.deleteSync();
      backend.routes['/files/upload'] = (_) => {'file_id': 'file-1'};

      await engine.offlineAttendance.push();

      final row = (await queue()).single;
      expect(row.deadLetter, isTrue);
      expect(row.lastError, 'Swafoto absen offline tidak ditemukan di HP.');
    });
  });

  test('item gagal dicoba lagi lewat antrean → dikirim ulang', () async {
    await recordCheckIn();
    await (db.update(db.pendingSyncOperations)).write(
      const PendingSyncOperationsCompanion(deadLetter: Value(true), lastError: Value('Sesi berakhir.')),
    );
    backend.routes['/attendance/offline'] = (_) => {'result': 'AUTO_VALID', 'duplicate': false};

    await engine.retryOperation((await queue()).single.id);

    expect(await queue(), isEmpty);
  });
}
