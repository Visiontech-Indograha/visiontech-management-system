import 'dart:io';
import 'dart:typed_data';

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

  group('biometrik wajah (Face API)', () {
    test('status, policy, dan consent', () async {
      backend.routes['/face/status'] = (_) => {'consent_given': true, 'has_template': true};
      backend.routes['/face/policy'] = (_) => {'version': '1.0'};
      backend.routes['/face/consent'] = (_) => {'message': 'Persetujuan biometrik dicatat.'};

      final status = await api.faceStatus();
      expect(status['consent_given'], isTrue);
      expect(last().path, '/api/v1/face/status');

      final pol = await api.facePolicy();
      expect(pol['version'], '1.0');
      expect(last().path, '/api/v1/face/policy');

      await api.setFaceConsent('GRANTED', policyVersion: '1.0');
      expect(last().path, '/api/v1/face/consent');
      expect(last().data, {'state': 'GRANTED', 'policy_version': '1.0'});
    });

    test('kirim face probe mengembalikan probe_id', () async {
      final dir = await Directory.systemTemp.createTemp('vms-face-test');
      final file = File('${dir.path}/probe.jpg')..writeAsStringSync('dummy-image');
      backend.routes['/face/probe'] = (_) => {'probe_id': 'probe-123'};

      final probeId = await api.createFaceProbe(
        file,
        liveness: {
          'challenges': ['kedip', 'kiri'],
          'passed': true,
          'proofs': ['p1', 'p2'],
        },
      );
      expect(probeId, 'probe-123');
      expect(last().path, '/api/v1/face/probe');
      final form = last().data as FormData;
      expect(form, isA<FormData>());
      // Hasil tantangan ikut terkirim sebagai JSON (bukan lagi '{}' kosong).
      final liveness = form.fields.firstWhere((f) => f.key == 'liveness').value;
      expect(liveness, contains('"proofs":["p1","p2"]'));
      expect(liveness, contains('"passed":true'));
      await dir.delete(recursive: true);
    });

    test('pemeriksaan tantangan mengirim bingkai dan mengembalikan bukti', () async {
      backend.routes['/face/challenge-check'] = (_) => {
        'status': 'sukses',
        'detail': 'ok',
        'proof': 'bukti-1',
      };
      final res = await api.faceChallengeCheck(Uint8List.fromList([1, 2, 3]), 'kedip');
      expect(res['proof'], 'bukti-1');
      expect(last().path, '/api/v1/face/challenge-check');
      final form = last().data as FormData;
      expect(form.fields.firstWhere((f) => f.key == 'challenge').value, 'kedip');
      expect(form.files.single.key, 'file');
    });

    test('pendaftaran membawa liveness dan banyak berkas', () async {
      final dir = await Directory.systemTemp.createTemp('vms-face-enroll');
      final files = [
        for (var i = 0; i < 3; i++) File('${dir.path}/p$i.jpg')..writeAsStringSync('x$i'),
      ];
      backend.routes['/face/enroll'] = (_) => {'enrolled': 3};
      final res = await api.enrollFace(
        files,
        liveness: {'challenges': ['kedip', 'kiri'], 'passed': true, 'proofs': ['a', 'b']},
      );
      expect(res['enrolled'], 3);
      final form = last().data as FormData;
      expect(form.files.where((f) => f.key == 'files'), hasLength(3));
      expect(form.fields.firstWhere((f) => f.key == 'liveness').value, contains('"proofs":["a","b"]'));
      await dir.delete(recursive: true);
    });
  });
}
