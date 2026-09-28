import 'dart:io';

import 'package:dio/dio.dart';

import '../core/api_client.dart';

/// Panggilan REST MVP ke backend VMS (api/app/api/*). Bentuk data mengikuti
/// OpenAPI backend apa adanya (Map JSON) supaya tidak ada lapisan model ganda.
class VmsApi {
  VmsApi(this._client);

  final ApiClient _client;
  Dio get _dio => _client.dio;

  static const _p = '/api/v1';

  List<Map<String, dynamic>> _list(dynamic data) =>
      (data as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  // --- SK / rencana kerja -------------------------------------------------
  Future<List<Map<String, dynamic>>> workPlans() async =>
      _list((await _dio.get('$_p/work-plans')).data);

  Future<Map<String, dynamic>> workPlan(String planId) async =>
      Map<String, dynamic>.from(
        (await _dio.get('$_p/work-plans/$planId')).data as Map,
      );

  Future<List<Map<String, dynamic>>> planDays(String planId) async =>
      _list((await _dio.get('$_p/work-plans/$planId/days')).data);

  /// Penerimaan SK wajib daring karena menandatangani dokumen di server.
  Future<Map<String, dynamic>> acceptPlan(
    String planId, {
    required int rowVersion,
  }) async => Map<String, dynamic>.from(
    (await _dio.post(
          '$_p/work-plans/$planId/accept',
          data: {'row_version': rowVersion, 'reason': ''},
        )).data
        as Map,
  );

  // --- Lokasi & absensi ---------------------------------------------------
  Future<List<Map<String, dynamic>>> sites() async =>
      _list((await _dio.get('$_p/sites')).data);

  /// Absensi milik sendiri (server membatasi ke pengguna ini bila bukan HR/Finance).
  /// `today` = tanggal hari ini menurut zona waktu organisasi (O-10), bukan jam HP.
  Future<({List<Map<String, dynamic>> items, String? today})> myAttendance({
    required String employeeId,
  }) async {
    final res = await _dio.get(
      '$_p/attendance',
      queryParameters: {
        if (employeeId.isNotEmpty) 'employee_id': employeeId,
        'size': 60,
      },
    );
    final data = res.data as Map;
    return (items: _list(data['items']), today: data['today'] as String?);
  }

  Future<Map<String, dynamic>> checkIn({
    required String siteId,
    required double lat,
    required double lng,
    double? accuracyM,
    String? selfieFileId,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/check-in',
      data: {
        'site_id': siteId,
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
        'accuracy_m': ?accuracyM,
        'selfie_file_id': ?selfieFileId,
        if (selfieFileId != null) 'face_result': 'SKIPPED',
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> checkOut({
    required double lat,
    required double lng,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/check-out',
      data: {
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> explainAttendance(String attendanceId, String explanation) =>
      _dio.post(
        '$_p/attendance/$attendanceId/explain',
        data: {'explanation': explanation},
      );

  // --- Lembur -------------------------------------------------------------
  Future<List<Map<String, dynamic>>> myOvertime() async =>
      _list((await _dio.get('$_p/overtime')).data);

  // --- Berkas & sinkronisasi ---------------------------------------------
  /// Unggah satu berkas (foto bukti/swafoto) → `file_id`.
  Future<String> uploadFile(File file) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: file.uri.pathSegments.last,
      ),
    });
    final res = await _dio.post('$_p/files/upload', data: form);
    return (res.data as Map)['file_id'] as String;
  }

  /// `POST /sync/operations` (M12) — hasil per operasi: APPLIED | REJECTED | CONFLICT | PENDING.
  Future<List<Map<String, dynamic>>> syncOperations(
    String deviceId,
    List<Map<String, dynamic>> ops,
  ) async {
    final res = await _dio.post(
      '$_p/sync/operations',
      data: {'device_id': deviceId, 'operations': ops},
    );
    return _list((res.data as Map)['results']);
  }
}
