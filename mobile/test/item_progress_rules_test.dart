import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/plans/item_progress_screen.dart';

void main() {
  group('progressProblem', () {
    test('jumlah melebihi target ditolak', () {
      expect(progressProblem(qty: 11, target: 10, mandatorySlots: 0, filledMandatory: 0), contains('melebihi target'));
    });

    test('selesai tanpa foto wajib lengkap ditolak, progres sebagian boleh', () {
      expect(progressProblem(qty: 10, target: 10, mandatorySlots: 2, filledMandatory: 1), contains('1/2'));
      expect(progressProblem(qty: 4, target: 10, mandatorySlots: 2, filledMandatory: 0), isNull);
    });

    test('selesai dengan foto lengkap dan tanpa target valid', () {
      expect(progressProblem(qty: 10, target: 10, mandatorySlots: 2, filledMandatory: 2), isNull);
      expect(progressProblem(qty: 99, target: 0, mandatorySlots: 3, filledMandatory: 0), isNull);
    });
  });

  group('retryUpload', () {
    DioException offline() => DioException(
      requestOptions: RequestOptions(path: '/files/upload'),
      type: DioExceptionType.connectionError,
    );

    test('mengulang gangguan jaringan sampai berhasil', () async {
      var calls = 0;
      final result = await retryUpload(() async {
        calls++;
        if (calls < 3) throw offline();
        return 'ok';
      }, step: Duration.zero);
      expect(result, 'ok');
      expect(calls, 3);
    });

    test('menyerah setelah 3 percobaan', () async {
      var calls = 0;
      await expectLater(
        retryUpload(() async {
          calls++;
          throw offline();
        }, step: Duration.zero),
        throwsA(isA<DioException>()),
      );
      expect(calls, 3);
    });

    test('galat server tidak diulang', () async {
      var calls = 0;
      await expectLater(
        retryUpload(() async {
          calls++;
          throw DioException(
            requestOptions: RequestOptions(path: '/files/upload'),
            type: DioExceptionType.badResponse,
            response: Response(requestOptions: RequestOptions(path: '/files/upload'), statusCode: 422),
          );
        }, step: Duration.zero),
        throwsA(isA<DioException>()),
      );
      expect(calls, 1);
    });
  });

  test('foto bukti lama (string id) dan baru (objek) sama-sama terbaca', () {
    final refs = photoRefsOf([
      {'file_id': 'a', 'requirement_id': 'r1'},
      'b',
      null,
      3,
      {'file_id': ''},
    ]);
    expect(refs.map((r) => r.fileId), ['a', 'b']);
    expect(refs.first.requirementId, 'r1');
    expect(photoRefsOf(null), isEmpty);
  });
}
