import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/api_client.dart';
import 'package:vms_mobile/core/error_message.dart';
import 'package:vms_mobile/core/token_storage.dart';
import 'package:vms_mobile/data/pengajuan_idempotency.dart';
import 'package:vms_mobile/data/vms_api.dart';

import 'support/fake_backend.dart';

/// Kunci Idempotency-Key per niat pengajuan: retry memakai kunci yang sama,
/// pengajuan baru memakai kunci baru (kontrak server: api/app/api/deps.py).
void main() {
  group('PengajuanIdempotency (helper)', () {
    test('isi sama → kunci sama (percobaan ulang)', () {
      final idem = PengajuanIdempotency();
      final a = idem.kunciUntuk({'reason': 'sakit', 'hours': 2});
      final b = idem.kunciUntuk({'reason': 'sakit', 'hours': 2});
      expect(b, a);
    });

    test('isi berubah → kunci baru (pengajuan lain)', () {
      final idem = PengajuanIdempotency();
      final a = idem.kunciUntuk({'reason': 'sakit'});
      final b = idem.kunciUntuk({'reason': 'keluarga'});
      expect(b, isNot(a));
    });

    test('setelah selesai → kunci berikutnya baru', () {
      final idem = PengajuanIdempotency();
      final a = idem.kunciUntuk({'reason': 'sakit'});
      idem.selesai();
      final b = idem.kunciUntuk({'reason': 'sakit'});
      expect(b, isNot(a));
    });

    test('format kunci UUID v4 dan lolos pola server (8-128, A-Za-z0-9._:-)', () {
      final kunci = PengajuanIdempotency().kunciUntuk({'x': 1});
      expect(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ).hasMatch(kunci),
        isTrue,
      );
      expect(PengajuanIdempotency.pola.hasMatch(kunci), isTrue);
    });
  });

  group('VmsApi mengirim Idempotency-Key', () {
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

    String? headerTerakhir() => backend.requests.last.headers['Idempotency-Key'] as String?;

    test('tanpa idem → tanpa header (perilaku lama)', () async {
      backend.routes['/leaves'] = (_) => {'id': 'l1'};
      await api.applyLeave(leaveType: 'ANNUAL', startDate: '2026-11-10', endDate: '2026-11-11', reason: 'liburan');
      expect(backend.requests.last.headers.containsKey('Idempotency-Key'), isFalse);
    });

    test('cuti: gagal sinyal lalu kirim ulang → kunci SAMA; sukses → pengajuan berikutnya kunci BARU', () async {
      final idem = PengajuanIdempotency();
      Future<void> ajukan() => api.applyLeave(
        leaveType: 'ANNUAL',
        startDate: '2026-11-10',
        endDate: '2026-11-11',
        reason: 'liburan',
        idem: idem,
      );

      // Percobaan 1: tidak ada sinyal.
      await expectLater(ajukan(), throwsA(isA<DioException>()));
      final kunciPertama = headerTerakhir();
      expect(kunciPertama, isNotNull);

      // Percobaan 2 (retry): server menerima.
      backend.routes['/leaves'] = (_) => {'id': 'l1'};
      await ajukan();
      expect(headerTerakhir(), kunciPertama);
      expect(backend.requests.where((r) => r.path.endsWith('/leaves')).length, 2);

      // Pengajuan baru (isi sama, tetapi sudah selesai) → kunci baru.
      await ajukan();
      expect(headerTerakhir(), isNot(kunciPertama));
    });

    test('409 IDEMPOTENCY_SEDANG_DIPROSES: kunci tetap, pesan "coba lagi", bukan galat permanen', () async {
      final idem = PengajuanIdempotency();
      Future<void> ajukan() => api.requestMess(
        messId: 'm1',
        start: '2026-11-10',
        end: '2026-11-12',
        idem: idem,
      );

      backend.routes['/mess/requests'] = (o) => throw httpError(o, 409, {
        'error': {
          'code': 'IDEMPOTENCY_SEDANG_DIPROSES',
          'message': 'Permintaan dengan kunci ini sedang diproses. Tunggu sebentar lalu coba lagi.',
        },
      });
      Object? galat;
      try {
        await ajukan();
      } catch (e) {
        galat = e;
      }
      expect(galat, isA<DioException>());
      expect(apiErrorMessage(galat!), contains('Coba lagi sebentar lagi'));
      final kunci409 = headerTerakhir();

      // Coba lagi nanti: server sudah selesai, kunci yang sama dipakai.
      backend.routes['/mess/requests'] = (_) => {'id': 's1'};
      await ajukan();
      expect(headerTerakhir(), kunci409);
    });

    test('422 IDEMPOTENCY_KUNCI_DIPAKAI: kunci diganti pada percobaan berikutnya', () async {
      final idem = PengajuanIdempotency();
      Future<void> ajukan() => api.requestLoan(
        assetType: 'TOOL',
        assetId: 't1',
        purpose: 'pengecoran',
        idem: idem,
      );

      backend.routes['/assets/loan-requests'] = (o) => throw httpError(o, 422, {
        'error': {'code': 'IDEMPOTENCY_KUNCI_DIPAKAI', 'message': 'Idempotency-Key ini sudah dipakai.'},
      });
      await expectLater(ajukan(), throwsA(isA<DioException>()));
      final kunciDitolak = headerTerakhir();

      backend.routes['/assets/loan-requests'] = (_) => {'id': 'r1'};
      await ajukan();
      expect(headerTerakhir(), isNot(kunciDitolak));
    });

    test('lembur memakai jalur yang sama dan membawa kunci', () async {
      final idem = PengajuanIdempotency();
      backend.routes['/overtime'] = (_) => {'id': 'o1'};
      await api.requestOvertime(dayId: 'd1', hours: 2, reason: 'selesaikan pengecoran', idem: idem);
      expect(headerTerakhir(), isNotNull);
      expect(backend.requests.last.data, {'daily_plan_id': 'd1', 'hours': 2, 'reason': 'selesaikan pengecoran'});
    });
  });
}
