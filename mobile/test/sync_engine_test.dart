import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';

import 'support/fake_backend.dart';

void main() {
  late AppDatabase db;
  late FakeBackend backend;
  late SyncEngine engine;

  setUp(() {
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend);
  });

  tearDown(() async => db.close());

  group('urutan pengiriman antrean', () {
    test(
      'operasi luring dikirim dalam SATU batch sesuai urutan dicatat',
      () async {
        for (final id in ['t-1', 't-2', 't-3']) {
          await engine.submit(OfflineOp.taskToggle, {'task_id': id});
        }
        backend.answerSync((_) => 'APPLIED');
        backend.requests.clear();

        final summary = await engine.syncAll();

        expect(summary.pushErrors, isEmpty);
        expect(backend.syncBatches, hasLength(1));
        expect(backend.sentOps.map((o) => (o['payload'] as Map)['task_id']), [
          't-1',
          't-2',
          't-3',
        ]);
        expect(await engine.allPendingOperations(), isEmpty);
      },
    );

    test(
      'hasil per operasi: hanya yang ditolak tertinggal sebagai dead-letter',
      () async {
        for (final id in ['t-1', 't-2', 't-3']) {
          await engine.submit(OfflineOp.taskToggle, {'task_id': id});
        }
        backend.answerSync(
          (op) => (op['payload'] as Map)['task_id'] == 't-2' ? 'REJECTED' : 'APPLIED',
        );

        await engine.syncAll();

        final rows = await engine.allPendingOperations();
        expect(rows, hasLength(1));
        expect(rows.single.payloadJson, contains('t-2'));
        expect(rows.single.deadLetter, isTrue);
      },
    );

    test('unggah foto putus sinyal: berhenti di situ, operasi sesudahnya ikut menunggu', () async {
      final foto = File('${Directory.systemTemp.path}/vms_uji_urutan.jpg')
        ..writeAsBytesSync([1, 2, 3]);
      addTearDown(foto.deleteSync);

      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
      await engine.submit(
        OfflineOp.incidentReport,
        {'plan_id': 'p-1'},
        localFiles: [foto.path],
      );
      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-3'});

      // Server sinkron hidup, tapi unggah berkas gagal karena jaringan.
      backend.answerSync((_) => 'APPLIED');
      backend.routes['/files/upload'] = (o) => throw networkError(o);
      backend.requests.clear();

      await engine.syncAll();

      expect(backend.sentOps.map((o) => o['op_type']), [OfflineOp.taskToggle]);
      expect((backend.sentOps.single['payload'] as Map)['task_id'], 't-1');
      final rows = await engine.allPendingOperations();
      expect(rows.map((r) => r.entityType), [
        OfflineOp.incidentReport,
        OfflineOp.taskToggle,
      ]);
      expect(
        rows.every((r) => !r.deadLetter),
        isTrue,
        reason: 'putus sinyal bukan penolakan',
      );
    });

    test('unggah foto ditolak server: hanya operasi itu dead-letter, sisanya tetap jalan', () async {
      final foto = File('${Directory.systemTemp.path}/vms_uji_tolak.jpg')
        ..writeAsBytesSync([1, 2, 3]);
      addTearDown(foto.deleteSync);

      await engine.submit(
        OfflineOp.incidentReport,
        {'plan_id': 'p-1'},
        localFiles: [foto.path],
      );
      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-2'});

      backend.answerSync((_) => 'APPLIED');
      backend.routes['/files/upload'] = (o) => throw httpError(o, 413, {
        'detail': {'message': 'Berkas terlalu besar'},
      });

      await engine.syncAll();

      final row = (await engine.allPendingOperations()).single;
      expect(row.entityType, OfflineOp.incidentReport);
      expect(row.deadLetter, isTrue);
      expect(row.lastError, 'Foto gagal diunggah: Berkas terlalu besar');
      expect((backend.sentOps.single['payload'] as Map)['task_id'], 't-2');
    });
  });

  group('cache baca-luring', () {
    test('cachePut menimpa isi lama untuk kunci yang sama', () async {
      await engine.cachePut('work_plans', [
        {'id': 'lama'},
      ]);
      await engine.cachePut('work_plans', [
        {'id': 'baru'},
      ]);

      final cached = await engine.cacheGet('work_plans');
      expect(cached.data, [
        {'id': 'baru'},
      ]);
      expect(cached.at, isNotNull);
      expect(await db.select(db.cachedSyncGroups).get(), hasLength(1));
    });

    test('cacheGet untuk kunci yang belum pernah disimpan', () async {
      final cached = await engine.cacheGet('tidak_ada');
      expect(cached.data, isNull);
      expect(cached.at, isNull);
    });

    test(
      'fetchList daring: kembalikan data server dan simpan ke cache',
      () async {
        final res = await engine.fetchList(
          'days',
          () async => [
            {'id': 'd-1'},
          ],
        );

        expect(res.items, [
          {'id': 'd-1'},
        ]);
        expect(res.cachedAt, isNull, reason: 'data segar, bukan dari cache');
        expect((await engine.cacheGet('days')).data, [
          {'id': 'd-1'},
        ]);
      },
    );

    test('fetchList luring: kembalikan isi cache beserta waktunya', () async {
      await engine.cachePut('days', [
        {'id': 'd-1'},
      ]);

      final res = await engine.fetchList(
        'days',
        () async => throw networkError(RequestOptions(path: '/days')),
      );

      expect(res.items, [
        {'id': 'd-1'},
      ]);
      expect(res.cachedAt, isNotNull);
    });

    test('fetchList luring tanpa cache: daftar kosong, bukan crash', () async {
      final res = await engine.fetchList(
        'days',
        () async => throw networkError(RequestOptions(path: '/days')),
      );

      expect(res.items, isEmpty);
      expect(res.cachedAt, DateTime.fromMillisecondsSinceEpoch(0));
    });

    test('fetchList: galat server non-jaringan diteruskan, bukan disembunyikan cache', () async {
      await engine.cachePut('days', [
        {'id': 'd-1'},
      ]);
      final o = RequestOptions(path: '/days');

      await expectLater(
        engine.fetchList('days', () async => throw httpError(o, 403, null)),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('syncAll — tarik data', () {
    test('menyimpan daftar SK ke cache work_plans', () async {
      backend.routes['/work-plans'] = (_) => [
        {'id': 'p-1', 'title': 'Pasang CCTV'},
      ];

      final summary = await engine.syncAll();

      expect(summary.hasErrors, isFalse);
      expect((await engine.cacheGet('work_plans')).data, [
        {'id': 'p-1', 'title': 'Pasang CCTV'},
      ]);
    });

    test('galat tarik dilaporkan terpisah dari galat kirim', () async {
      backend.routes['/work-plans'] = (o) =>
          throw httpError(o, 500, {'detail': 'DB mati'});

      final summary = await engine.syncAll();

      expect(summary.pushErrors, isEmpty);
      expect(summary.pullErrors, ['Rencana Kerja: DB mati']);
    });

    test('luring total: dua-duanya melapor tidak ada koneksi', () async {
      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});

      final summary = await engine.syncAll();

      expect(summary.pushErrors, ['Tidak ada koneksi.']);
      expect(summary.pullErrors, ['Tidak ada koneksi.']);
    });
  });

  group('tabel drift', () {
    test('PendingSyncOperations: nilai bawaan baris baru', () async {
      await db
          .into(db.pendingSyncOperations)
          .insert(
            PendingSyncOperationsCompanion.insert(
              entityType: OfflineOp.taskToggle,
              payloadJson: '{}',
            ),
          );

      final row = (await db.select(db.pendingSyncOperations).get()).single;
      expect(row.attemptCount, 0);
      expect(row.deadLetter, isFalse);
      expect(row.lastError, isNull);
    });

    test('CachedSyncGroups: waktu sinkron tersimpan (bandingkan via epoch)', () async {
      await db
          .into(db.cachedSyncGroups)
          .insertOnConflictUpdate(
            CachedSyncGroupsCompanion.insert(
              syncGroup: 'work_plans',
              dataJson: '[]',
              lastSyncedAt: DateTime.utc(2026, 1, 2),
            ),
          );

      final row = await (db.select(
        db.cachedSyncGroups,
      )..where((t) => t.syncGroup.equals('work_plans'))).getSingle();
      // drift/sqlite3 membaca kembali DateTime sebagai waktu lokal, bukan UTC.
      expect(
        row.lastSyncedAt.millisecondsSinceEpoch,
        DateTime.utc(2026, 1, 2).millisecondsSinceEpoch,
      );
    });
  });
}
