import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/error_message.dart';
import 'package:vms_mobile/core/location_helper.dart';
import 'package:vms_mobile/data/sync_engine.dart';

/// Pesan galat yang dibaca teknisi lapangan — tidak boleh "DioException [...]".
void main() {
  final o = RequestOptions(path: '/api/v1/x');

  DioException http(int status, [Object? data]) => DioException(
    requestOptions: o,
    type: DioExceptionType.badResponse,
    response: Response(requestOptions: o, statusCode: status, data: data),
  );

  test('pesan server (format VMS) diutamakan', () {
    final e = http(422, {
      'error': {
        'code': 'GPS_INACCURATE',
        'message': '  Akurasi GPS 150 m terlalu rendah.  ',
        'details': <String, Object>{},
      },
    });
    expect(apiErrorMessage(e), 'Akurasi GPS 150 m terlalu rendah.');
  });

  test('detail FastAPI: teks maupun daftar galat per kolom', () {
    expect(
      apiErrorMessage(http(400, {'detail': 'Tidak ada perubahan.'})),
      'Tidak ada perubahan.',
    );
    expect(
      apiErrorMessage(
        http(422, {
          'detail': [
            {'msg': 'Field required'},
            {'msg': 'Input should be a valid UUID'},
          ],
        }),
      ),
      'Field required; Input should be a valid UUID',
    );
  });

  test('putus sinyal: pengguna diberi tahu datanya tidak hilang', () {
    final e = DioException(
      requestOptions: o,
      type: DioExceptionType.connectionError,
    );
    expect(apiErrorMessage(e), contains('Data Anda tidak hilang'));
  });

  test('kode status tanpa pesan server', () {
    expect(
      apiErrorMessage(http(401)),
      'Sesi Anda berakhir. Silakan masuk lagi.',
    );
    expect(
      apiErrorMessage(http(403)),
      'Anda tidak punya akses untuk tindakan ini.',
    );
    expect(
      apiErrorMessage(http(404)),
      'Data yang dituju tidak ditemukan di server.',
    );
    expect(
      apiErrorMessage(http(409)),
      'Data ini sudah diubah dari perangkat lain.',
    );
    expect(
      apiErrorMessage(http(413)),
      'Ukuran file terlalu besar untuk dikirim.',
    );
    expect(apiErrorMessage(http(429)), contains('Terlalu banyak permintaan'));
    expect(apiErrorMessage(http(503)), contains('kode 503'));
    expect(
      apiErrorMessage(http(418), fallback: 'Gagal menyimpan.'),
      'Gagal menyimpan.',
    );
  });

  test('penolakan sinkron & galat lain', () {
    expect(
      apiErrorMessage(SyncRejectedException('Laporan sudah dikirim.')),
      'Laporan sudah dikirim.',
    );
    expect(apiErrorMessage(StateError('x')), 'Terjadi kesalahan. Coba lagi.');
    expect(apiErrorMessage(StateError('x'), fallback: 'Gagal.'), 'Gagal.');
  });

  test('K-12: batas & pesan akurasi GPS sama dengan server', () {
    expect(maxGpsAccuracyM, 100);
    expect(
      gpsAccuracyMessage(149.6),
      'Akurasi GPS 150 m terlalu rendah (maksimal 100 m). '
      'Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.',
    );
  });
}
