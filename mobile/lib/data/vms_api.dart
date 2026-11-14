import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import 'pengajuan_idempotency.dart';

part 'vms_api_jadwal.dart';
part 'vms_api_lembur_notif.dart';
part 'vms_api_absensi_wajah.dart';
part 'vms_api_survei.dart';
part 'vms_api_wo_mess.dart';
part 'vms_api_aset_cuti.dart';

/// Ukuran halaman keyset (batas API: absensi maks 200, lembur maks 100).
const kAttendancePageSize = 60;
const kOvertimePageSize = 30;

/// Pesan saat kursor ditolak server (422): daftar dimuat ulang dari awal.
const kPesanKursorBerubah = 'Daftar sudah berubah, jadi dimuat ulang dari awal.';

/// Kursor ditolak server (422) = daftar berubah; mulai lagi dari halaman pertama.
bool isCursorRejected(Object e) =>
    e is DioException && e.response?.statusCode == 422;

String? _nextCursor(Response res) {
  final v = res.headers.value('x-next-cursor');
  return (v == null || v.isEmpty) ? null : v;
}

/// Panggilan REST MVP ke backend VMS (api/app/api/*). Bentuk data mengikuti
/// OpenAPI backend apa adanya (Map JSON) supaya tidak ada lapisan model ganda.
abstract class _VmsApiBase {
  _VmsApiBase(this._client);

  final ApiClient _client;
  Dio get _dio => _client.dio;

  String get _p => '/api/v1';

  List<Map<String, dynamic>> _list(dynamic data) =>
      (data as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  Map<String, dynamic> _map(dynamic data) =>
      Map<String, dynamic>.from(data as Map);

  /// Satu-satunya jalur POST pengajuan yang memakai `Idempotency-Key`.
  /// [idem] null = tanpa header (perilaku lama). Kunci dibuat/dipakai ulang oleh [idem];
  /// bila server menolak kunci yang sudah dipakai untuk isi lain (422), kunci diganti.
  Future<Map<String, dynamic>> _postPengajuan(
    String path,
    Map<String, dynamic> data,
    PengajuanIdempotency? idem,
  ) async {
    if (idem == null) return _map((await _dio.post(path, data: data)).data);
    try {
      final res = await _dio.post(
        path,
        data: data,
        options: Options(
          headers: {'Idempotency-Key': idem.kunciUntuk(data)},
        ),
      );
      idem.selesai();
      return _map(res.data);
    } on DioException catch (e) {
      if (_kodeGalat(e) == 'IDEMPOTENCY_KUNCI_DIPAKAI') idem.selesai();
      rethrow;
    }
  }

  static String? _kodeGalat(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map) {
      final code = (data['error'] as Map)['code'];
      if (code is String) return code;
    }
    return null;
  }
}

class VmsApi extends _VmsApiBase with _VmsApiJadwal, _VmsApiLemburNotif, _VmsApiAbsensiWajah, _VmsApiSurvei, _VmsApiWoMess, _VmsApiAsetCuti {
  VmsApi(super.client);
}
