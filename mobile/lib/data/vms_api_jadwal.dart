part of 'vms_api.dart';

/// Panggilan API per domain (jadwal); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiJadwal on _VmsApiBase {
  // --- Jadwal harian (Milestone 5–6, daily-first) -------------------------
  /// Jadwal tim saya dalam rentang tanggal (lapangan hanya melihat yang sudah disetujui).
  Future<List<Map<String, dynamic>>> dailyPlans({
    required String start,
    required String end,
  }) async => _list(
    (await _dio.get(
      '$_p/work-plans/daily',
      queryParameters: {'start': start, 'end': end},
    )).data,
  );

  Future<Map<String, dynamic>> dailyPlan(String id) async =>
      _map((await _dio.get('$_p/work-plans/daily/$id')).data);

  Future<Map<String, dynamic>> dailyReport(String id) async =>
      _map((await _dio.get('$_p/work-plans/daily/$id/report')).data);

  /// Ketua tim memulai hari kerja (APPROVED → ONGOING) / menutupnya (→ COMPLETED).
  Future<Map<String, dynamic>> startDay(String id) async =>
      _map((await _dio.post('$_p/work-plans/daily/$id/start')).data);

  Future<Map<String, dynamic>> completeDay(String id) async =>
      _map((await _dio.post('$_p/work-plans/daily/$id/complete')).data);

  Future<List<Map<String, dynamic>>> dayItems(String dayId) async =>
      _list((await _dio.get('$_p/work-plans/daily/$dayId/items')).data);

  Future<Map<String, dynamic>> planItem(String itemId) async =>
      _map((await _dio.get('$_p/work-plans/items/$itemId')).data);

  /// Progres titik (jadwal ONGOING): `photos` = [{file_id, requirement_id?}] menggantikan foto sebelumnya.
  Future<Map<String, dynamic>> updateProgress(
    String itemId, {
    required num completedQty,
    List<Map<String, String?>>? photos,
    String? notes,
  }) async => _map(
    (await _dio.patch(
      '$_p/work-plans/items/$itemId/progress',
      data: {'completed_qty': completedQty, 'photos': ?photos, 'notes': ?notes},
    )).data,
  );

  /// Ketua: pekerjaan belum selesai → minta digeser (diputus PM).
  Future<Map<String, dynamic>> requestRollover(
    String itemId, {
    required String reason,
    required num completedQty,
  }) async => _map(
    (await _dio.post(
      '$_p/work-plans/items/$itemId/request-rollover',
      data: {'delay_reason': reason, 'completed_qty': completedQty},
    )).data,
  );

  /// Syarat foto (slot) jenis pekerjaan item.
  Future<List<Map<String, dynamic>>> imageRequirements(
    String workTypeId,
  ) async {
    final types = _list((await _dio.get('$_p/work-types')).data);
    final type = types.firstWhere(
      (t) => '${t['id']}' == workTypeId,
      orElse: () => const <String, dynamic>{},
    );
    return _list(type['photos'] ?? const []).map((s) => <String, dynamic>{
          'image_requirement_id': s['id'],
          'name': s['label'],
          'description': s['hint'],
          'is_mandatory': s['required'] == true,
          'path_image': s['example_file_id'],
        }).toList();
  }

  /// Aset yang dialokasikan ke jadwal tim (Milestone 4).
  Future<List<Map<String, dynamic>>> dayAssets(String dayId) async =>
      _list((await _dio.get('$_p/work-plans/daily/$dayId/assets')).data);

  // --- Order klien & BAST (Milestone 8) ------------------------------------
  Future<Map<String, dynamic>> workCompletion(String id) async =>
      _map((await _dio.get('$_p/work-completions/$id')).data);

  /// Hapus satu foto realisasi BAST (langsung tersimpan; ditolak bila BAST sudah disahkan PM).
  Future<Map<String, dynamic>> deleteCompletionPhoto(
    String id,
    String fileId,
  ) async =>
      _map((await _dio.delete('$_p/work-completions/$id/photos/$fileId')).data);

  /// Gambar tanda tangan tersimpan (`leader` / `pm`); null bila belum ada.
  Future<List<int>?> completionSignature(String id, String role) async {
    try {
      final res = await _dio.get<List<int>>(
        '$_p/work-completions/$id/signatures/$role',
        options: Options(responseType: ResponseType.bytes),
      );
      return res.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Ketua tim menandatangani BAST lebih dulu (ringkasan wajib, foto realisasi = id file), lalu PM mengesahkan.
  Future<Map<String, dynamic>> signCompletion(
    String id, {
    required String signaturePng,
    required String summary,
    String? obstacles,
    List<String> photoFileIds = const [],
  }) async => _map(
    (await _dio.post(
      '$_p/work-completions/$id/sign',
      data: {
        'signature_data_url': 'data:image/png;base64,$signaturePng',
        'summary_notes': summary,
        'obstacles': ?obstacles,
        'realization_photos': photoFileIds,
      },
    )).data,
  );
}
