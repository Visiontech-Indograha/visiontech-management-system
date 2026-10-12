import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';

import 'support/fake_backend.dart';

Map<String, dynamic> _record(PendingSyncRow row) =>
    Map<String, dynamic>.from(jsonDecode(row.payloadJson) as Map);

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

  group('submit() — dicatat dulu, lalu dikirim', () {
    test(
      'luring: tersimpan di antrean dan menunggu sinyal, bukan error',
      () async {
        final sent = await engine.submit(OfflineOp.taskToggle, {
          'task_id': 't-1',
        });

        expect(sent, isFalse);
        final row = (await engine.allPendingOperations()).single;
        expect(row.entityType, OfflineOp.taskToggle);
        expect(row.deadLetter, isFalse);
        final record = _record(row);
        expect(record['op_type'], OfflineOp.taskToggle);
        expect(record['payload'], {'task_id': 't-1'});
        expect(record['client_op_id'], isA<String>());
        expect(record['client_created_at'], isA<String>());
      },
    );

    test(
      'setiap operasi mendapat client_op_id unik (kunci idempoten server)',
      () async {
        await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
        await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});

        final ids = (await engine.allPendingOperations())
            .map((r) => _record(r)['client_op_id'])
            .toSet();
        expect(ids, hasLength(2));
      },
    );

    test(
      'daring & APPLIED: terkirim dengan device_id lalu hilang dari antrean',
      () async {
        backend.answerSync((_) => 'APPLIED');

        final sent = await engine.submit(OfflineOp.incidentReport, {
          'plan_id': 'p-1',
        });

        expect(sent, isTrue);
        expect(await engine.allPendingOperations(), isEmpty);
        final batch = backend.syncBatches.single;
        expect(batch['device_id'], 'device-uji');
        expect(backend.sentOps.single['op_type'], OfflineOp.incidentReport);
        expect(backend.sentOps.single['payload'], {'plan_id': 'p-1'});
      },
    );

    test(
      'REJECTED: melempar SyncRejectedException, data TIDAK hilang',
      () async {
        backend.answerSync(
          (_) => 'REJECTED',
          errorMessage: 'SK sudah ditutup.',
        );

        await expectLater(
          engine.submit(OfflineOp.dailyReportSubmit, {'day_id': 'd-1'}),
          throwsA(
            isA<SyncRejectedException>().having(
              (e) => e.message,
              'message',
              'SK sudah ditutup.',
            ),
          ),
        );

        final row = (await engine.allPendingOperations()).single;
        expect(row.deadLetter, isTrue, reason: 'masuk "Perlu perhatian"');
        expect(row.lastError, 'SK sudah ditutup.');
      },
    );

    test('CONFLICT diperlakukan sama dengan penolakan', () async {
      backend.answerSync((_) => 'CONFLICT');

      await expectLater(
        engine.submit(OfflineOp.dailyReportSave, {'day_id': 'd-1'}),
        throwsA(isA<SyncRejectedException>()),
      );
      expect(
        (await engine.allPendingOperations()).single.lastError,
        'Ditolak server.',
      );
    });

    test(
      'galat server non-jaringan (500) diteruskan ke pemanggil, antrean utuh',
      () async {
        backend.routes['/sync/operations'] = (o) =>
            throw httpError(o, 500, {'detail': 'Server sibuk'});

        await expectLater(
          engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'}),
          throwsA(isA<DioException>()),
        );
        final row = (await engine.allPendingOperations()).single;
        expect(row.deadLetter, isFalse, reason: '500 bukan penolakan permanen');
      },
    );
  });

  group('percobaan ulang & dead-letter', () {
    test(
      'status PENDING dari server: tetap antre, attemptCount bertambah',
      () async {
        backend.answerSync((_) => 'PENDING');

        expect(
          await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'}),
          isFalse,
        );
        await engine.syncAll();

        final row = (await engine.allPendingOperations()).single;
        expect(row.attemptCount, 2);
        expect(row.deadLetter, isFalse);
      },
    );

    test(
      'gagal jaringan saat syncAll: dilaporkan, antrean tidak berubah',
      () async {
        await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});

        final summary = await engine.syncAll();

        expect(summary.pushErrors, ['Tidak ada koneksi.']);
        expect(summary.hasErrors, isTrue);
        final row = (await engine.allPendingOperations()).single;
        expect(row.deadLetter, isFalse);
        expect(row.attemptCount, 0);
      },
    );

    test(
      'galat server saat syncAll: pesan detail diteruskan ke ringkasan',
      () async {
        await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
        backend.routes['/sync/operations'] = (o) =>
            throw httpError(o, 500, {'detail': 'Server sibuk'});

        final summary = await engine.syncAll();

        expect(summary.pushErrors, ['Server sibuk']);
        expect(
          (await engine.allPendingOperations()).single.deadLetter,
          isFalse,
        );
      },
    );

    test(
      'item dead-letter tidak dikirim ulang dan tidak menyandera item baru',
      () async {
        backend.answerSync((_) => 'REJECTED', errorMessage: 'Data tidak valid');
        await expectLater(
          engine.submit(OfflineOp.taskToggle, {'task_id': 'buruk'}),
          throwsA(isA<SyncRejectedException>()),
        );

        backend.answerSync((_) => 'APPLIED');
        backend.requests.clear();
        expect(
          await engine.submit(OfflineOp.taskToggle, {'task_id': 'baik'}),
          isTrue,
        );

        expect(backend.sentOps.map((o) => (o['payload'] as Map)['task_id']), ['baik']);
        final rows = await engine.allPendingOperations();
        expect(rows.single.deadLetter, isTrue);
        expect((_record(rows.single)['payload'] as Map)['task_id'], 'buruk');
      },
    );

    test(
      'retryOperation menghidupkan lagi item dead-letter lalu mengirimnya',
      () async {
        backend.answerSync((_) => 'REJECTED', errorMessage: 'ditolak');
        await expectLater(
          engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'}),
          throwsA(isA<SyncRejectedException>()),
        );
        final stuck = (await engine.allPendingOperations()).single;

        backend.answerSync((_) => 'APPLIED');
        await engine.retryOperation(stuck.id);

        expect(await engine.allPendingOperations(), isEmpty);
      },
    );

    test(
      'retryOperation saat luring: kembali ke antrean aktif, galat dibersihkan',
      () async {
        backend.answerSync((_) => 'REJECTED', errorMessage: 'ditolak');
        await expectLater(
          engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'}),
          throwsA(isA<SyncRejectedException>()),
        );
        final stuck = (await engine.allPendingOperations()).single;

        backend.offline();
        await engine.retryOperation(stuck.id);

        final revived = (await engine.allPendingOperations()).single;
        expect(revived.deadLetter, isFalse);
        expect(revived.lastError, isNull);
        expect(await engine.pendingOperationCount(), 1);
        expect(await engine.deadLetterCount(), 0);
      },
    );

    test('deleteOperation membuang baris sepenuhnya', () async {
      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
      final row = (await engine.allPendingOperations()).single;

      await engine.deleteOperation(row.id);

      expect(await engine.allPendingOperations(), isEmpty);
    });
  });

  group('foto bukti (_local_files)', () {
    test('dihitung sebagai foto tertunda selama luring', () async {
      final fotos = [
        for (final n in ['a', 'b'])
          File('${Directory.systemTemp.path}/vms_uji_luring_$n.jpg')
            ..writeAsBytesSync([1, 2, 3]),
      ];
      addTearDown(() {
        for (final f in fotos) {
          f.deleteSync();
        }
      });

      final sent = await engine.submit(
        OfflineOp.incidentReport,
        {'plan_id': 'p-1'},
        localFiles: [for (final f in fotos) f.path],
      );

      expect(sent, isFalse);
      expect(await engine.pendingPhotoCount(), 2);
    });

    test(
      'diunggah dulu, lalu operasinya dikirim dengan evidence_file_ids',
      () async {
        final foto = File('${Directory.systemTemp.path}/vms_uji_bukti.jpg')
          ..writeAsBytesSync([1, 2, 3]);
        addTearDown(foto.deleteSync);
        backend.routes['/files/upload'] = (_) => {'file_id': 'f-1'};
        backend.answerSync((_) => 'APPLIED');

        final sent = await engine.submit(
          OfflineOp.incidentReport,
          {
            'plan_id': 'p-1',
            'evidence_file_ids': ['f-lama'],
          },
          localFiles: [foto.path],
        );

        expect(sent, isTrue);
        final payload = backend.sentOps.single['payload'] as Map;
        expect(payload['evidence_file_ids'], ['f-lama', 'f-1']);
        expect(payload.containsKey('_local_files'), isFalse);
      },
    );

    test(
      'file lokal hilang: DITANDAI dead-letter, tidak dibuang diam-diam',
      () async {
        backend.answerSync((_) => 'APPLIED');

        await expectLater(
          engine.submit(
            OfflineOp.incidentReport,
            {'plan_id': 'p-1'},
            localFiles: ['${Directory.systemTemp.path}/vms_uji_tidak_ada.jpg'],
          ),
          throwsA(isA<SyncRejectedException>()),
        );

        final row = (await engine.allPendingOperations()).single;
        expect(row.deadLetter, isTrue);
        expect(row.lastError, 'Foto bukti tidak ditemukan di HP.');
        expect(backend.syncBatches, isEmpty);
        expect(await engine.pendingPhotoCount(), 0);
        expect(await engine.deadLetterCount(), 1);
      },
    );
  });

  group('hitungan untuk layar Profil', () {
    test(
      'pendingOperationCount tidak menghitung yang sudah dead-letter',
      () async {
        await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
        expect(await engine.pendingOperationCount(), 1);

        backend.answerSync((_) => 'REJECTED');
        await engine.syncAll();

        expect(await engine.pendingOperationCount(), 0);
        expect(await engine.deadLetterCount(), 1);
      },
    );
  });

  group('wipeAllLocalData', () {
    test('logout manual membersihkan antrean supaya tidak tersinkron atas nama user lain', () async {
      await engine.submit(OfflineOp.taskToggle, {'task_id': 't-1'});
      await engine.submit(OfflineOp.overtimeReport, {'plan_id': 'p-1'});
      await engine.cachePut('work_plans', [
        {'id': 'p-1'},
      ]);

      await db.wipeAllLocalData();

      expect(await engine.allPendingOperations(), isEmpty);
      expect(await engine.allPendingAttachments(), isEmpty);
      expect((await engine.cacheGet('work_plans')).data, isNull);
    });
  });
}
