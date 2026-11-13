part of 'vms_api.dart';

/// Panggilan API per domain (wo_mess); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiWoMess on _VmsApiBase {
  // --- Work Orders (Revamp V2) --------------------------------------------
  /// Eksekusi hari ini untuk mobile: rencana hari ini + lokasi client_sites + item tugas terstruktur
  Future<Map<String, dynamic>> myExecutionToday() async =>
      _map((await _dio.get('$_p/daily-plans/my-execution-today')).data);

  /// Submit survei Work Order dari mobile (status WAITING_SURVEY/SURVEY_IN_PROGRESS -> SURVEY_SUBMITTED)
  Future<Map<String, dynamic>> submitWorkOrderSurvey(
    String workOrderId,
    Map<String, dynamic> payload,
  ) async => _map(
    (await _dio.post(
      '$_p/work-orders/$workOrderId/submit-survey',
      data: payload,
    )).data,
  );

  /// Update progres item Work Order (target_qty vs completed_qty + slot foto)
  Future<Map<String, dynamic>> updateWorkOrderItemProgress(
    String itemId, {
    required double completedQty,
    String? status,
    List<Map<String, dynamic>>? photoSlotsSnapshot,
  }) async => _map(
    (await _dio.post(
      '$_p/work-orders/items/$itemId/progress',
      data: {
        'completed_qty': completedQty,
        'status': ?status,
        'photo_slots_snapshot': ?photoSlotsSnapshot,
      },
    )).data,
  );

  /// Update realisasi aktual material BOM Work Order
  Future<Map<String, dynamic>> updateWorkOrderBomActual(
    String bomId,
    double actualQty,
  ) async => _map(
    (await _dio.post(
      '$_p/work-orders/bom/$bomId/actual',
      data: {'actual_qty': actualQty},
    )).data,
  );

  /// Tanda tangan BAST Work Order dari mobile
  Future<Map<String, dynamic>> signWorkOrderBast(
    String workOrderId, {
    required String signerName,
    String? signatureDataUri,
    String? notes,
  }) async => _map(
    (await _dio.post(
      '$_p/work-orders/$workOrderId/sign-bast',
      data: {
        'signer_name': signerName,
        'signature_data_uri': ?signatureDataUri,
        'notes': ?notes,
      },
    )).data,
  );

  // --- Lembur -------------------------------------------------------------
  /// Satu halaman riwayat lembur (keyset). [cursor] kosong = halaman pertama.
  /// Tidak membaca total; lanjutan lewat `nextCursor` (header X-Next-Cursor).
  Future<({List<Map<String, dynamic>> items, String? nextCursor})> myOvertime({
    String cursor = '',
  }) async {
    final res = await _dio.get(
      '$_p/overtime',
      queryParameters: {'cursor': cursor, 'size': kOvertimePageSize},
    );
    return (items: _list(res.data), nextCursor: _nextCursor(res));
  }

  /// Setujui (APPROVED) atau tolak (REJECTED) lembur tim. Online saja: keputusan tidak diantrikan offline.
  Future<Map<String, dynamic>> reviewOvertime({
    required String id,
    required String decision,
    String? note,
  }) async => _map(
    (await _dio.post(
      '$_p/overtime/$id/review',
      data: {'decision': decision, 'note': ?note},
    )).data,
  );

  // --- Mess, dokumen, koreksi laporan -------------------------------------------
  Future<List<Map<String, dynamic>>> myMess() async => _list((await _dio.get('$_p/mess/me')).data);

  Future<List<Map<String, dynamic>>> messPlaces() async => _list((await _dio.get('$_p/mess/places')).data);

  Future<Map<String, dynamic>> requestMess({
    required String messId,
    required String start,
    required String end,
    String note = '',
    PengajuanIdempotency? idem,
  }) => _postPengajuan(
    '$_p/mess/requests',
    {'mess_id': messId, 'stay_start_date': start, 'stay_end_date': end, 'note': note.isEmpty ? null : note},
    idem,
  );

  Future<Map<String, dynamic>> cancelMess(String stayId) async =>
      _map((await _dio.post('$_p/mess/$stayId/cancel')).data);

  Future<Map<String, dynamic>> endMess(String stayId) async => _map((await _dio.post('$_p/mess/$stayId/end')).data);

  Future<List<Map<String, dynamic>>> myDocuments(String employeeId) async =>
      _list(((await _dio.get('$_p/employees/$employeeId/documents')).data as Map)['items']);

  /// Catat dokumen pribadi dari berkas yang sudah diunggah (`fileId`). Karyawan hanya untuk dirinya sendiri.
  /// [expiredAt] opsional (tanggal saja, WIB); berlaku mulai hari ini menurut server.
  Future<Map<String, dynamic>> uploadDocument(
    String employeeId, {
    required String docType,
    required String fileId,
    DateTime? expiredAt,
  }) async => _map(
    (await _dio.post(
      '$_p/employees/$employeeId/documents',
      data: {
        'doc_type': docType,
        'file_id': fileId,
        'expired_at': ?(expiredAt == null ? null : DateFormat('yyyy-MM-dd').format(expiredAt)),
      },
    )).data,
  );

  Future<List<Map<String, dynamic>>> planCorrections(String dailyPlanId) async =>
      _list((await _dio.get('$_p/work-plans/daily/$dailyPlanId/corrections')).data);

  Future<Map<String, dynamic>> requestCorrection(String dailyPlanId, String reason) async => _map(
    (await _dio.post('$_p/work-plans/daily/$dailyPlanId/corrections', data: {'reason': reason})).data,
  );

  Future<Map<String, dynamic>> submitCorrection(String correctionId) async =>
      _map((await _dio.post('$_p/work-plans/corrections/$correctionId/submit')).data);
}
