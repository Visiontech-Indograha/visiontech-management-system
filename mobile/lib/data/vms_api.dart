import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

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

  /// HTML A4 sembarang dari API (laporan harian/mingguan yang disetujui).
  Future<String> html(String path) async =>
      (await _dio.get<String>(
        '$_p$path',
        options: Options(responseType: ResponseType.plain),
      )).data ??
      '';

  // --- Laporan berjenjang (alur SK v2 PR2) --------------------------------
  Future<List<Map<String, dynamic>>> memberReports(
    String planId,
    String dayId,
  ) async => _list(
    (await _dio.get('$_p/work-plans/$planId/days/$dayId/member-reports')).data,
  );

  Future<Map<String, dynamic>?> myMemberReport(
    String planId,
    String dayId,
  ) async {
    final data = (await _dio.get(
      '$_p/work-plans/$planId/days/$dayId/member-report',
    )).data;
    return data == null ? null : Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> saveMemberReport(
    String planId,
    String dayId, {
    required String body,
    required String obstacle,
    required List<String> evidenceFileIds,
  }) async => Map<String, dynamic>.from(
    (await _dio.put(
          '$_p/work-plans/$planId/days/$dayId/member-report',
          data: {
            'body': body,
            'obstacle': obstacle,
            'evidence_file_ids': evidenceFileIds,
          },
        )).data
        as Map,
  );

  Future<Map<String, dynamic>> sendMemberReport(
    String planId,
    String dayId,
  ) async => Map<String, dynamic>.from(
    (await _dio.post('$_p/work-plans/$planId/days/$dayId/member-report/send'))
            .data
        as Map,
  );

  Future<List<Map<String, dynamic>>> weeklyReports(String planId) async =>
      _list((await _dio.get('$_p/work-plans/$planId/weekly')).data);

  Future<void> saveWeekly(
    String planId,
    int week, {
    required String body,
    required String obstacle,
  }) async => _dio.put(
    '$_p/work-plans/$planId/weekly/$week',
    data: {'body': body, 'obstacle': obstacle},
  );

  Future<void> submitWeekly(String planId, int week) async =>
      _dio.post('$_p/work-plans/$planId/weekly/$week/submit');

  // --- Adendum saat berjalan, aset, laporan akhir (alur SK v2 PR3) ----------
  Future<List<Map<String, dynamic>>> planChanges(String planId) async =>
      _list((await _dio.get('$_p/work-plans/$planId/changes')).data);

  Future<void> requestRunningAmendment(String planId, String reason) async =>
      _dio.post('$_p/work-plans/$planId/amendments', data: {'reason': reason});

  Future<void> acceptAmendment(String planId, String changeId) async =>
      _dio.post('$_p/work-plans/$planId/amendments/$changeId/accept');

  Future<List<Map<String, dynamic>>> planAssets(String planId) async =>
      _list((await _dio.get('$_p/work-plans/$planId/assets')).data);

  Future<void> returnAsset(
    String allocationId, {
    String condition = 'Baik',
  }) async => _dio.post(
    '$_p/assets/allocations/$allocationId/return',
    data: {'condition_on_return': condition, 'note': null},
  );

  Future<Map<String, dynamic>?> finalReport(String planId) async {
    final data = (await _dio.get('$_p/work-plans/$planId/completion')).data;
    return data == null ? null : Map<String, dynamic>.from(data as Map);
  }

  Future<void> requestCompletion(
    String planId, {
    required int rowVersion,
    required String body,
    required String obstacle,
    required List<String> evidenceFileIds,
  }) async => _dio.post(
    '$_p/work-plans/$planId/request-completion',
    data: {
      'row_version': rowVersion,
      'body': body,
      'obstacle': obstacle,
      'evidence_file_ids': evidenceFileIds,
    },
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
  Future<List<Map<String, dynamic>>> sites() async => _list(
    (await _dio.get(
      '$_p/sites',
      queryParameters: {'for_attendance': true},
    )).data,
  );

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
    String? faceProbeId,
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
        'face_probe_id': ?faceProbeId,
        'explanation': ?explanation,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> checkOut({
    required double lat,
    required double lng,
    String? faceProbeId,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/check-out',
      data: {
        'channel': 'MOBILE',
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
        'face_probe_id': ?faceProbeId,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  // --- Biometrik Wajah (Face API) ------------------------------------------
  /// Pemeriksaan pembaruan aplikasi (docs/32) — rute publik, juga dipanggil sebelum login.
  Future<Map<String, dynamic>> appUpdate({
    required int build,
    required List<String> abis,
  }) async {
    final res = await _dio.get(
      '$_p/app/android/update',
      queryParameters: {'build': build, 'abi': abis},
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> faceStatus() async {
    final res = await _dio.get('$_p/face/status');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> facePolicy() async {
    final res = await _dio.get('$_p/face/policy');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> setFaceConsent(
    String state, {
    required String policyVersion,
  }) async => _dio.post(
    '$_p/face/consent',
    data: {'state': state, 'policy_version': policyVersion},
  );

  /// Memeriksa satu bingkai kamera terhadap tantangan liveness (online). Bila gerakan terlihat, server
  /// mengembalikan `proof` bertanda tangan yang nanti dikirim kembali di `liveness.proofs`.
  Future<Map<String, dynamic>> faceChallengeCheck(
    Uint8List jpeg,
    String challenge,
  ) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(jpeg, filename: 'frame.jpg'),
      'challenge': challenge,
    });
    final res = await _dio.post('$_p/face/challenge-check', data: form);
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// Unggah gambar wajah sementara (bukan foto absensi) beserta hasil tantangan; → `probe_id` untuk absen.
  Future<String> createFaceProbe(
    File photo, {
    required Map<String, dynamic> liveness,
  }) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        photo.path,
        filename: photo.uri.pathSegments.last,
      ),
      'liveness': jsonEncode(liveness),
    });
    final res = await _dio.post('$_p/face/probe', data: form);
    return (res.data as Map)['probe_id'] as String;
  }

  Future<Map<String, dynamic>> enrollFace(
    List<File> photos, {
    required Map<String, dynamic> liveness,
  }) async {
    final fileParts = <MultipartFile>[];
    for (final photo in photos) {
      fileParts.add(
        await MultipartFile.fromFile(
          photo.path,
          filename: photo.uri.pathSegments.last,
        ),
      );
    }
    final form = FormData.fromMap({
      'files': fileParts,
      'liveness': jsonEncode(liveness),
    });
    final res = await _dio.post('$_p/face/enroll', data: form);
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
