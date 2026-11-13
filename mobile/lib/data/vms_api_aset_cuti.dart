part of 'vms_api.dart';

/// Panggilan API per domain (aset_cuti); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiAsetCuti on _VmsApiBase {
  // --- Aset: pinjam & kembali -------------------------------------------------
  Future<List<Map<String, dynamic>>> assetsAvailable(String kind) async =>
      _list(
        (await _dio.get(
          '$_p/assets/$kind',
          queryParameters: {'status': 'ready'},
        )).data,
      );

  Future<List<Map<String, dynamic>>> myLoans() async => _list(
    (await _dio.get('$_p/assets/loans', queryParameters: {'open': true})).data,
  );

  Future<List<Map<String, dynamic>>> myInspections() async =>
      _list((await _dio.get('$_p/hse/inspections/mine')).data);

  Future<Map<String, dynamic>> inspectionChecklistTemplate() async =>
      _map((await _dio.get('$_p/hse/inspections/checklist-template')).data);

  Future<Map<String, dynamic>> inspectionDetail(String id) async =>
      _map((await _dio.get('$_p/hse/inspections/$id')).data);

  Future<List<Map<String, dynamic>>> vehiclesForInspection() async =>
      _list((await _dio.get('$_p/assets/vehicles')).data);

  Future<Map<String, dynamic>> createInspection(Map<String, dynamic> body) async =>
      _map((await _dio.post('$_p/hse/inspections', data: body)).data);

  Future<List<Map<String, dynamic>>> myLoanRequests() async =>
      _list((await _dio.get('$_p/assets/loan-requests')).data);

  Future<Map<String, dynamic>> requestLoan({
    required String assetType,
    required String assetId,
    required String purpose,
    PengajuanIdempotency? idem,
  }) => _postPengajuan(
    '$_p/assets/loan-requests',
    {
      'asset_type': assetType,
      if (assetType == 'TOOL') 'tool_id': assetId else 'vehicle_id': assetId,
      'purpose': purpose,
    },
    idem,
  );

  Future<Map<String, dynamic>> cancelLoanRequest(String requestId) async =>
      _map(
        (await _dio.post('$_p/assets/loan-requests/$requestId/cancel')).data,
      );

  Future<Map<String, dynamic>> requestReturn({
    required String assignmentId,
    required String condition,
    required String photoFileId,
    String? note,
  }) async => _map(
    (await _dio.post(
      '$_p/assets/loans/$assignmentId/return-request',
      data: {
        'condition': condition,
        'photo_file_id': photoFileId,
        if (note != null && note.isNotEmpty) 'note': note,
      },
    )).data,
  );

  // --- Rekap absen --------------------------------------------------------------
  Future<Map<String, dynamic>> myRecap(String month) async => _map(
    (await _dio.get(
      '$_p/attendance/me/recap',
      queryParameters: {'month': month},
    )).data,
  );

  // --- Cuti -----------------------------------------------------------------
  Future<List<Map<String, dynamic>>> leaveTypes() async =>
      _list((await _dio.get('$_p/leaves/types')).data);

  Future<List<Map<String, dynamic>>> myLeaves(String employeeId) async => _list(
    (await _dio.get(
      '$_p/leaves',
      queryParameters: {'employee_id': employeeId},
    )).data,
  );

  Future<Map<String, dynamic>> leaveBalance(String employeeId) async =>
      _map((await _dio.get('$_p/leaves/balances/$employeeId')).data);

  Future<Map<String, dynamic>> applyLeave({
    required String leaveType,
    required String startDate,
    required String endDate,
    required String reason,
    PengajuanIdempotency? idem,
  }) => _postPengajuan(
    '$_p/leaves',
    {
      'leave_type': leaveType,
      'start_date': startDate,
      'end_date': endDate,
      'reason': reason,
    },
    idem,
  );

  Future<Map<String, dynamic>> cancelLeave(String leaveId) async =>
      _map((await _dio.post('$_p/leaves/$leaveId/cancel')).data);

  // --- Berkas & sinkronisasi ---------------------------------------------
  /// Unggah satu berkas (foto bukti/swafoto) → `file_id`.
  /// [onProgress] (opsional) melapor byte terkirim dan total, untuk indikator unggah.
  Future<String> uploadFile(File file, {void Function(int sent, int total)? onProgress}) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: file.uri.pathSegments.last,
      ),
    });
    final res = await _dio.post('$_p/files/upload', data: form, onSendProgress: onProgress);
    return (res.data as Map)['file_id'] as String;
  }

  // --- Logo tim -------------------------------------------------------------
  /// Detail tim (memuat `logo_file_id` & `logo_url`). Anggota tanpa izin lihat tim memperoleh 403.
  Future<Map<String, dynamic>> teamDetail(String teamId) async =>
      _map((await _dio.get('$_p/teams/$teamId')).data);

  /// Gambar logo tim; null bila tim belum punya logo (404).
  Future<Uint8List?> teamLogoBytes(String teamId) async {
    try {
      final res = await _dio.get<List<int>>(
        '$_p/teams/$teamId/logo',
        options: Options(responseType: ResponseType.bytes),
      );
      final data = res.data;
      return data == null ? null : Uint8List.fromList(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Unggah logo tim (multipart `file`). Hanya ketua tim; 403 bila bukan.
  Future<Map<String, dynamic>> uploadTeamLogo(
    String teamId,
    Uint8List bytes,
    String filename,
  ) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });
    return _map((await _dio.put('$_p/teams/$teamId/logo', data: form)).data);
  }

  Future<void> deleteTeamLogo(String teamId) async {
    await _dio.delete('$_p/teams/$teamId/logo');
  }

  /// Daftar perangkat/sesi login akun ini (`current` = perangkat ini).
  Future<List<Map<String, dynamic>>> authSessions() async =>
      _list((await _dio.get('$_p/auth/sessions')).data);

  Future<void> revokeAuthSession(String id) async {
    await _dio.post('$_p/auth/sessions/$id/revoke');
  }

  Future<void> revokeOtherAuthSessions() async {
    await _dio.post('$_p/auth/sessions/revoke-others');
  }

  /// Mengganti (atau menghapus bila null) foto profil sendiri dengan berkas hasil unggah.
  Future<void> setMyPhoto(String? fileId) async {
    await _dio.put('$_p/employees/me/photo', data: {'file_id': fileId});
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
