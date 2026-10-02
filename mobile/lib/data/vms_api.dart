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

  /// Alur SK v2: isi lengkap SK (tim, alat & kendaraan, detail pekerjaan per hari).
  Future<Map<String, dynamic>> planDetail(String planId) async =>
      Map<String, dynamic>.from(
        (await _dio.get('$_p/work-plans/$planId/detail')).data as Map,
      );

  /// Dokumen SK (versi terbit, revisi, adendum), urut versi naik — yang terbaru di posisi terakhir.
  Future<List<Map<String, dynamic>>> planDocuments(String planId) async =>
      _list((await _dio.get('$_p/work-plans/$planId/documents')).data);

  /// HTML A4 yang sama persis dengan PDF (isi + tanda tangan + QR) untuk "Tinjau SK".
  Future<String> documentHtml(String documentId) async =>
      (await _dio.get<String>(
        '$_p/documents/$documentId/html',
        options: Options(responseType: ResponseType.plain),
      )).data ??
      '';

  /// "Ajukan adendum" ketua atas SK terbit (alasan wajib) — status menjadi Adendum diminta.
  Future<Map<String, dynamic>> requestAmendment(
    String planId, {
    required int rowVersion,
    required String reason,
  }) async => Map<String, dynamic>.from(
    (await _dio.post(
          '$_p/work-plans/$planId/appeal',
          data: {'row_version': rowVersion, 'reason': reason},
        )).data
        as Map,
  );

  // --- Notifikasi dalam aplikasi (alur SK v2) -----------------------------
  Future<({int unread, List<Map<String, dynamic>> items})>
  notifications() async {
    final data = (await _dio.get('$_p/notifications')).data as Map;
    return (
      unread: (data['unread'] as num).toInt(),
      items: _list(data['items']),
    );
  }

  Future<void> readNotification(String id) async =>
      _dio.post('$_p/notifications/$id/read');

  Future<void> readAllNotifications() async =>
      _dio.post('$_p/notifications/read-all');

  // --- Lokasi & absensi ---------------------------------------------------
  Future<List<Map<String, dynamic>>> sites() async =>
      _list((await _dio.get('$_p/sites')).data);

  /// Absensi milik sendiri (server membatasi ke pengguna ini bila bukan HR/Finance).
  /// `today` = tanggal hari ini menurut zona waktu organisasi (O-10), bukan jam HP.
  Future<
    ({List<Map<String, dynamic>> items, String? today, String? timeAnchor})
  >
  myAttendance({required String employeeId}) async {
    final res = await _dio.get(
      '$_p/attendance',
      queryParameters: {
        if (employeeId.isNotEmpty) 'employee_id': employeeId,
        'size': 60,
      },
    );
    final data = res.data as Map;
    return (
      items: _list(data['items']),
      today: data['today'] as String?,
      timeAnchor: data['time_anchor'] as String?,
    );
  }

  Future<Map<String, dynamic>> checkIn({
    required String siteId,
    required double lat,
    required double lng,
    double? accuracyM,
    String? selfieFileId,
    String? explanation,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/check-in',
      data: {
        'channel': 'MOBILE',
        'site_id': siteId,
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
        'accuracy_m': ?accuracyM,
        'selfie_file_id': ?selfieFileId,
        if (selfieFileId != null) 'face_result': 'SKIPPED',
        'explanation': ?explanation,
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
        'channel': 'MOBILE',
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// R-34: daftarkan kunci publik Android Keystore untuk absen luring.
  Future<void> registerDeviceKey({
    required String deviceId,
    required String publicKey,
  }) => _dio.post(
    '$_p/attendance/device-key',
    data: {'device_id': deviceId, 'public_key': publicKey},
  );

  /// R-34: kirim satu absen luring bertanda tangan (idempoten per client_op_id).
  Future<Map<String, dynamic>> submitOfflineAttendance({
    required String deviceId,
    required String clientOpId,
    required String kind,
    required String payload,
    required String signature,
    String? selfieFileId,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/offline',
      data: {
        'device_id': deviceId,
        'client_op_id': clientOpId,
        'kind': kind,
        'payload': payload,
        'signature': signature,
        'selfie_file_id': ?selfieFileId,
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
