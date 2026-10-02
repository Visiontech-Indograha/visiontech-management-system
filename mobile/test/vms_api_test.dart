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

  test('SK, lokasi, lembur: path baca', () async {
    backend.routes['/work-plans'] = (_) => [
      {'id': 'p1'},
    ];
    backend.routes['/work-plans/p1'] = (_) => {'id': 'p1'};
    backend.routes['/work-plans/p1/days'] = (_) => [
      {'id': 'd1'},
    ];
    backend.routes['/sites'] = (_) => [
      {'id': 's1'},
    ];
    backend.routes['/overtime'] = (_) => <Object>[];

    expect((await api.workPlans()).single['id'], 'p1');
    expect((await api.workPlan('p1'))['id'], 'p1');
    expect((await api.planDays('p1')).single['id'], 'd1');
    expect((await api.sites()).single['id'], 's1');
    expect(await api.myOvertime(), isEmpty);
    expect(backend.requests.map((r) => r.method).toSet(), {'GET'});
  });

  test('ketua menerima SK secara daring dengan row version terbaru', () async {
    backend.routes['/work-plans/p1/accept'] = (_) => {
      'id': 'p1',
      'status': 'ACCEPTED',
      'row_version': 8,
    };

    final accepted = await api.acceptPlan('p1', rowVersion: 7);

    expect(accepted['status'], 'ACCEPTED');
    expect(last().method, 'POST');
    expect(last().path, '/api/v1/work-plans/p1/accept');
    expect(last().data, {'row_version': 7, 'reason': ''});
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
}
