part of 'vms_api.dart';

/// Panggilan API per domain (absensi_wajah); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiAbsensiWajah on _VmsApiBase {
  // --- Lokasi & absensi ---------------------------------------------------
  Future<List<Map<String, dynamic>>> sites() async => _list(
    (await _dio.get(
      '$_p/offices',
      queryParameters: {'for_attendance': true},
    )).data,
  );

  /// Absensi milik sendiri (server membatasi ke pengguna ini bila bukan HR/Finance).
  /// `today` = tanggal hari ini menurut zona waktu organisasi (O-10), bukan jam HP.
  Future<
    ({
      List<Map<String, dynamic>> items,
      String? today,
      String? timeAnchor,
      String? requiredOutAt,
      int reportPendingCount,
      String? reportPendingPlanId,
      String? nextCursor,
    })
  >
  myAttendance({required String employeeId, String cursor = ''}) async {
    final res = await _dio.get(
      '$_p/attendance',
      queryParameters: {
        if (employeeId.isNotEmpty) 'employee_id': employeeId,
        'cursor': cursor,
        'size': kAttendancePageSize,
      },
    );
    final data = res.data as Map;
    return (
      nextCursor: _nextCursor(res),
      items: _list(data['items']),
      today: data['today'] as String?,
      timeAnchor: data['time_anchor'] as String?,
      requiredOutAt: data['required_out_at'] as String?,
      reportPendingCount: (data['report_pending_count'] as num?)?.toInt() ?? 0,
      reportPendingPlanId: data['report_pending_plan_id'] as String?,
    );
  }

  Future<Map<String, dynamic>> checkIn({
    required String siteId,
    required double lat,
    required double lng,
    double? accuracyM,
    String? selfieFileId,
    String? evidenceFileId,
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
        'evidence_file_id': ?evidenceFileId,
        'explanation': ?explanation,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> checkOut({
    required double lat,
    required double lng,
    double? accuracyM,
    String? selfieFileId,
    String? evidenceFileId,
    String? explanation,
  }) async {
    final res = await _dio.post(
      '$_p/attendance/check-out',
      data: {
        'channel': 'MOBILE',
        'location': {'lat': lat, 'lng': lng},
        'location_origin': 'GPS',
        'accuracy_m': ?accuracyM,
        'selfie_file_id': ?selfieFileId,
        'evidence_file_id': ?evidenceFileId,
        'explanation': ?explanation,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  // --- Pengenalan wajah ------------------------------------------
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

  /// Hapus pendaftaran wajah sendiri (DELETE /face/enrollment/me); server mencatat di log aktivitas.
  Future<Map<String, dynamic>> deleteOwnFaceEnrollment() async {
    final res = await _dio.delete('$_p/face/enrollment/me');
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// Wajah V2: 3–5 foto milik sendiri → `employee.face_embedding` (server memeriksa kualitas & duplikat).
  Future<Map<String, dynamic>> enrollFace(List<File> photos) async {
    final form = FormData.fromMap({
      'files': [
        for (final photo in photos)
          await MultipartFile.fromFile(
            photo.path,
            filename: photo.uri.pathSegments.last,
          ),
      ],
    });
    final res = await _dio.post('$_p/face/enroll', data: form);
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// R-34: daftarkan kunci publik Android Keystore untuk absen offline.
  Future<void> registerDeviceKey({
    required String deviceId,
    required String publicKey,
  }) => _dio.post(
    '$_p/attendance/device-key',
    data: {'device_id': deviceId, 'public_key': publicKey},
  );

  /// R-34: kirim satu absen offline bertanda tangan (idempoten per client_op_id).
  Future<Map<String, dynamic>> submitOfflineAttendance({
    required String deviceId,
    required String clientOpId,
    required String kind,
    required String payload,
    required String signature,
    String? selfieFileId,
    String? evidenceFileId,
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
        'evidence_file_id': ?evidenceFileId,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// Foto bukti biasa (mis. terlambat) untuk absensi sendiri; server tidak mencocokkan wajah.
  Future<void> attachAttendanceEvidence(String attendanceId, String evidenceFileId) =>
      _dio.post(
        '$_p/attendance/$attendanceId/evidence',
        data: {'evidence_file_id': evidenceFileId},
      );

  Future<void> explainAttendance(String attendanceId, String explanation) =>
      _dio.post(
        '$_p/attendance/$attendanceId/explain',
        data: {'explanation': explanation},
      );
}
