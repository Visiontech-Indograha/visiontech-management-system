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

  Map<String, dynamic> _map(dynamic data) =>
      Map<String, dynamic>.from(data as Map);

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
  ) async => _list(
    (await _dio.get('$_p/image-requirements/by-work-type/$workTypeId')).data,
  );

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

  // --- Lembur (jadwal ONGOING) ---------------------------------------------
  Future<Map<String, dynamic>> requestOvertime({
    required String dayId,
    required num hours,
    required String reason,
  }) async => _map(
    (await _dio.post(
      '$_p/overtime',
      data: {'daily_plan_id': dayId, 'hours': hours, 'reason': reason},
    )).data,
  );

  /// URL sementara (presigned) sebuah berkas gambar, mis. foto contoh template. `variant`: thumb | view | full.
  Future<String> fileUrl(String fileId, {String variant = 'view'}) async {
    final res = await _dio.get(
      '$_p/files/$fileId/url',
      queryParameters: {'variant': variant},
    );
    // API mengembalikan URL relatif (/api/v1/files/…?token=…); Image.network butuh URL absolut.
    final url = (res.data as Map)['url'] as String;
    return Uri.parse(_dio.options.baseUrl).resolve(url).toString();
  }

  /// Aliran peristiwa waktu nyata (SSE, T8). Tanpa batas waktu baca: sambungan sengaja berumur panjang.
  Future<ResponseBody> openEvents(CancelToken cancel) async {
    final res = await _dio.get<ResponseBody>(
      '$_p/events',
      options: Options(
        responseType: ResponseType.stream,
        headers: {'Accept': 'text/event-stream'},
        receiveTimeout: Duration.zero,
      ),
      cancelToken: cancel,
    );
    return res.data!;
  }

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
      '$_p/offices',
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
        'explanation': ?explanation,
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

  // --- Survei ACS & CCTV berformat baku (docs/37) ------------------------
  /// Daftar survei saya (ketua/anggota tim): DRAFT = sedang diisi, SUBMITTED = menunggu PM, APPROVED.
  Future<List<Map<String, dynamic>>> surveys({String? state}) async => _list(
    (await _dio.get(
      '$_p/work-plans/surveys',
      queryParameters: {'state': ?state},
    )).data,
  );

  /// Laporan mingguan tim (.pptx): semua pekerjaan tim 7 hari mulai [start] — foto, keterangan, status.
  Future<List<int>> teamWeekSlides(String teamId, String start) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/team-week',
      data: {'team_id': teamId, 'start_date': start},
      options: Options(responseType: ResponseType.bytes, receiveTimeout: const Duration(minutes: 3)),
    );
    return res.data ?? const <int>[];
  }

  /// Slide laporan pekerjaan klien (.pptx): foto per pekerjaan + keterangan + status berwarna.
  Future<List<int>> completionSlides(String completionId) async {
    final res = await _dio.post<List<int>>(
      '$_p/exports/work-completions/$completionId',
      data: {'template': 'PROGRESS_SLIDES'},
      options: Options(responseType: ResponseType.bytes, receiveTimeout: const Duration(minutes: 3)),
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

  /// Pindahkan titik di peta layout (layout laporan dibuat otomatis dari koordinat titik).
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
