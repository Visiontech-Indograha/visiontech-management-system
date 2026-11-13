part of 'vms_api.dart';

/// Panggilan API per domain (survei); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiSurvei on _VmsApiBase {
  // --- Survei ACS & CCTV berformat baku (docs/37) ------------------------
  /// Daftar survei saya (ketua/anggota tim): DRAFT = sedang diisi, SUBMITTED = menunggu PM, APPROVED.
  Future<List<Map<String, dynamic>>> surveys({String? state}) async => _list(
    (await _dio.get(
      '$_p/work-plans/surveys',
      queryParameters: {'state': ?state},
    )).data,
  );

  /// Jenis pekerjaan (kunci id) untuk rekomendasi titik survei.
  Future<List<Map<String, dynamic>>> workTypes() async =>
      _list((await _dio.get('$_p/work-types')).data);

  /// Survei work order milik tim saya (ketua atau anggota aktif), untuk bagian "Survei dari work order".
  Future<List<Map<String, dynamic>>> teamSurveys() async =>
      _list((await _dio.get('$_p/work-orders/team-surveys')).data);

  /// Laporan mingguan tim (.pptx): semua pekerjaan tim 7 hari mulai [start] — foto, keterangan, status.
  Future<List<int>> teamWeekSlides(String teamId, String start) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/team-week',
      data: {'team_id': teamId, 'start_date': start},
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return res.data ?? const <int>[];
  }

  /// Work completion (BAST .docx). Ketua tim: hanya berisi item timnya sendiri (server membatasi per peran).
  Future<List<int>> completionBastDocx(String completionId) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/work-completions/$completionId',
      data: {'template': 'BAST'},
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return res.data ?? const <int>[];
  }

  /// Slide laporan pekerjaan klien (.pptx): foto per pekerjaan + keterangan + status berwarna.
  Future<List<int>> completionSlides(String completionId) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/work-completions/$completionId',
      data: {'template': 'PROGRESS_SLIDES'},
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return res.data ?? const <int>[];
  }

  /// Laporan survei resmi (.docx, tercatat di riwayat dokumen) — setelah survei dikirim.
  Future<List<int>> surveyOfficialReport(String taskId) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/surveys/$taskId',
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return res.data ?? const <int>[];
  }

  /// Survei: format, slot foto, katalog material, titik, BoM, status, `can_edit`.
  Future<Map<String, dynamic>> survey(String taskId) async =>
      _map((await _dio.get('$_p/work-plans/surveys/$taskId')).data);

  /// Titik baru / ganti isi titik: `{name, remarks[], photos[{file_id, requirement_id}], lines[{category, name, qty, unit, notes}]}`.
  Future<Map<String, dynamic>> addSurveyPoint(
    String taskId,
    Map<String, dynamic> point,
  ) async => _map(
    (await _dio.post(
      '$_p/work-plans/surveys/$taskId/points',
      data: point,
    )).data,
  );

  Future<Map<String, dynamic>> updateSurveyPoint(
    String pointId,
    Map<String, dynamic> point,
  ) async => _map(
    (await _dio.put(
      '$_p/work-plans/surveys/points/$pointId',
      data: point,
    )).data,
  );

  Future<Map<String, dynamic>> deleteSurveyPoint(String pointId) async =>
      _map((await _dio.delete('$_p/work-plans/surveys/points/$pointId')).data);

  /// Pindahkan titik di peta titik (layout laporan dibuat otomatis dari koordinat titik).
  Future<Map<String, dynamic>> moveSurveyPoint(
    String pointId,
    double lat,
    double lng,
  ) async => _map(
    (await _dio.put(
      '$_p/work-plans/surveys/points/$pointId/location',
      data: {
        'site_lat': double.parse(lat.toStringAsFixed(7)),
        'site_lng': double.parse(lng.toStringAsFixed(7)),
      },
    )).data,
  );

  /// Narasi, tujuan, dan lokasi laporan.
  /// Material umum lokasi (bukan milik satu titik) — rack, panel, kabel tray utama.
  Future<Map<String, dynamic>> addSurveyLine(
    String taskId,
    Map<String, dynamic> line,
  ) async => _map(
    (await _dio.post('$_p/work-plans/surveys/$taskId/lines', data: line)).data,
  );

  Future<Map<String, dynamic>> deleteSurveyLine(String bomId) async =>
      _map((await _dio.delete('$_p/work-plans/surveys/lines/$bomId')).data);

  Future<Map<String, dynamic>> saveSurveyReport(
    String taskId,
    Map<String, dynamic> report,
  ) async => _map(
    (await _dio.put(
      '$_p/work-plans/surveys/$taskId/report',
      data: report,
    )).data,
  );

  Future<Map<String, dynamic>> submitSurvey(String taskId) async =>
      _map((await _dio.post('$_p/work-plans/surveys/$taskId/submit')).data);

  /// Pratinjau laporan (tidak disimpan di server): PDF, atau .docx bila server tak punya konverter.
  Future<({List<int> bytes, bool isPdf})> surveyPreview(String taskId) async {
    final res = await _dio.get<List<int>>(
      '$_p/exports/surveys/$taskId/preview',
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return (
      bytes: res.data ?? const <int>[],
      isPdf: res.headers.value('x-preview-format') == 'PDF',
    );
  }
}
