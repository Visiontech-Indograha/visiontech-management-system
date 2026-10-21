import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/data/vms_api.dart';

import 'support/fake_backend.dart';

/// Kontrak panggilan REST aplikasi ↔ API (api/app/api/*): metode, path, dan
/// isi yang dikirim. Rusak di sini = server menolak (422) atau salah endpoint.
void main() {
  late FakeBackend backend;
  late VmsApi api;

  setUp(() {
    backend = FakeBackend();
    final client = ApiClient(tokenStorage: const TokenStorage());
    client.dio.interceptors
      ..clear()
      ..add(backend);
    api = VmsApi(client);
  });

  RequestOptions last() => backend.requests.last;

  group('absensi', () {
    test('absen masuk mengirim titik, asal GPS, dan akurasi (K-12)', () async {
      backend.routes['/attendance/check-in'] = (_) => {'id': 'a1'};
      final out = await api.checkIn(
        siteId: 's1',
        lat: -6.2,
        lng: 106.8,
        accuracyM: 12.5,
      );

      expect(out['id'], 'a1');
      expect(last().method, 'POST');
      expect(last().path, '/api/v1/attendance/check-in');
      expect(last().data, {
        'channel': 'MOBILE',
        'site_id': 's1',
        'location': {'lat': -6.2, 'lng': 106.8},
        'location_origin': 'GPS',
        'accuracy_m': 12.5,
      });
    });

    test(
      'swafoto di luar radius ikut terkirim dengan hasil wajah SKIPPED',
      () async {
        backend.routes['/attendance/check-in'] = (_) => {'id': 'a2'};
        await api.checkIn(siteId: 's1', lat: 1, lng: 2, selfieFileId: 'f1');

        final data = last().data as Map;
        expect(data['selfie_file_id'], 'f1');
        expect(data['face_result'], 'SKIPPED');
        // Perangkat tak melaporkan akurasi → kunci tidak dikirim, server tidak menolak.
        expect(data.containsKey('accuracy_m'), isFalse);
      },
    );

    test('absen pulang dan penjelasan', () async {
      backend.routes['/attendance/check-out'] = (_) => {'id': 'a1'};
      backend.routes['/attendance/a1/explain'] = (_) => {'message': 'ok'};

      await api.checkOut(lat: -6.2, lng: 106.8);
      expect(last().data, {
        'channel': 'MOBILE',
        'location': {'lat': -6.2, 'lng': 106.8},
        'location_origin': 'GPS',
      });

      await api.explainAttendance('a1', 'Kendaraan mogok');
      expect(last().path, '/api/v1/attendance/a1/explain');
      expect(last().data, {'explanation': 'Kendaraan mogok'});
    });

    test('riwayat absensi sendiri dibatasi 60 baris', () async {
      backend.routes['/attendance'] = (_) => {
        'items': [
          {'id': 'a1'},
        ],
        'total': 1,
        'today': '2026-09-28',
      };
      final rows = await api.myAttendance(employeeId: 'e1');
      expect(rows.items.single['id'], 'a1');
      expect(rows.today, '2026-09-28');
      expect(last().queryParameters, {'employee_id': 'e1', 'size': 60});
    });
  });

  test('jadwal harian, lokasi, lembur: path baca', () async {
    backend.routes['/work-plans/daily'] = (_) => [
      {'daily_plan_id': 'd1'},
    ];
    backend.routes['/work-plans/daily/d1'] = (_) => {'daily_plan_id': 'd1', 'items': <Object>[]};
    backend.routes['/work-plans/daily/d1/items'] = (_) => [
      {'item_id': 'i1'},
    ];
    backend.routes['/offices'] = (_) => [
      {'id': 's1'},
    ];
    backend.routes['/overtime'] = (_) => <Object>[];

    expect((await api.dailyPlans(start: '2026-10-19', end: '2026-10-25')).single['daily_plan_id'], 'd1');
    expect(backend.requests.last.queryParameters, {'start': '2026-10-19', 'end': '2026-10-25'});
    expect((await api.dailyPlan('d1'))['daily_plan_id'], 'd1');
    expect((await api.dayItems('d1')).single['item_id'], 'i1');
    expect((await api.sites()).single['id'], 's1');
    expect(await api.myOvertime(), isEmpty);
    expect(backend.requests.map((r) => r.method).toSet(), {'GET'});
  });

  test('progres titik & minta geser', () async {
    backend.routes['/work-plans/items/i1/progress'] = (_) => {'item_id': 'i1', 'status': 'DONE'};
    backend.routes['/work-plans/items/i1/request-rollover'] = (_) => {'status': 'PENDING_ROLLOVER'};

    await api.updateProgress('i1', completedQty: 1, photos: [
      {'file_id': 'f1', 'requirement_id': 'r1'},
    ]);
    expect(last().method, 'PATCH');
    expect(last().data, {
      'completed_qty': 1,
      'photos': [
        {'file_id': 'f1', 'requirement_id': 'r1'},
      ],
    });

    await api.requestRollover('i1', reason: 'Hujan', completedQty: 0);
    expect(last().data, {'delay_reason': 'Hujan', 'completed_qty': 0});
  });

  test('ketua menandatangani BAST: PNG data URL + foto realisasi', () async {
    backend.routes['/work-completions/c1/sign'] = (_) => {'completion_id': 'c1'};
    await api.signCompletion('c1', signaturePng: 'QUJD', summary: 'Selesai', photoFileIds: ['f1']);
    expect(last().path, '/api/v1/work-completions/c1/sign');
    expect(last().data, {
      'signature_data_url': 'data:image/png;base64,QUJD',
      'summary_notes': 'Selesai',
      'realization_photos': ['f1'],
    });
  });

  group('berkas & sinkron', () {
    test('unggah berkas mengembalikan file_id', () async {
      final dir = await Directory.systemTemp.createTemp('vms-uji');
      final file = File('${dir.path}/bukti.jpg')..writeAsBytesSync([1, 2, 3]);
      backend.routes['/files/upload'] = (_) => {
        'file_id': 'f9',
        'message': 'ok',
      };

      expect(await api.uploadFile(file), 'f9');
      expect(last().path, '/api/v1/files/upload');
      expect(last().data, isA<FormData>());
      await dir.delete(recursive: true);
    });

    test('batch sinkron membawa device_id', () async {
      backend.routes['/sync/operations'] = (_) => {
        'results': [
          {'client_op_id': 'c1', 'status': 'APPLIED'},
        ],
      };
      final results = await api.syncOperations('dev-1', [
        {'client_op_id': 'c1'},
      ]);
      expect(results.single['status'], 'APPLIED');
      expect(last().data, {
        'device_id': 'dev-1',
        'operations': [
          {'client_op_id': 'c1'},
        ],
      });
    });
  });

  group('wajah V2 (Face API)', () {
    test('status & kebijakan', () async {
      backend.routes['/face/status'] = (_) => {'enrolled': true, 'required': true};
      backend.routes['/face/policy'] = (_) => {'match_threshold': 0.8, 'min_images': 3, 'max_images': 5};

      final status = await api.faceStatus();
      expect(status['enrolled'], isTrue);
      expect(last().path, '/api/v1/face/status');

      final pol = await api.facePolicy();
      expect(pol['min_images'], 3);
      expect(last().path, '/api/v1/face/policy');
    });

    test('pendaftaran: banyak berkas, tanpa liveness', () async {
      final dir = await Directory.systemTemp.createTemp('vms-face-enroll');
      final files = [
        for (var i = 0; i < 4; i++) File('${dir.path}/p$i.jpg')..writeAsStringSync('x$i'),
      ];
      backend.routes['/face/enroll'] = (_) => {'enrolled': true, 'images_used': 4};
      final res = await api.enrollFace(files);
      expect(res['images_used'], 4);
      final form = last().data as FormData;
      expect(form.files.where((f) => f.key == 'files'), hasLength(4));
      expect(form.fields.where((f) => f.key == 'liveness'), isEmpty);
      await dir.delete(recursive: true);
    });

    test('absen masuk: swafoto, tanpa face_probe_id', () async {
      backend.routes['/attendance/check-in'] = (_) => {'id': 'a1'};
      await api.checkIn(siteId: 's1', lat: 1, lng: 2, selfieFileId: 'f1');
      final body = last().data as Map;
      expect(body['selfie_file_id'], 'f1');
      expect(body.containsKey('face_probe_id'), isFalse);
      expect(body.containsKey('face_result'), isFalse);
    });
  });
}
