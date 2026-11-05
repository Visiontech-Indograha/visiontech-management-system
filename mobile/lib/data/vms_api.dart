import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import 'pengajuan_idempotency.dart';

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

  // --- Lembur (jadwal ONGOING) ---------------------------------------------
  Future<Map<String, dynamic>> requestOvertime({
    required String dayId,
    required num hours,
    required String reason,
    PengajuanIdempotency? idem,
  }) => _postPengajuan(
    '$_p/overtime',
    {'daily_plan_id': dayId, 'hours': hours, 'reason': reason},
    idem,
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

  /// Isi berkas (gambar) sebagai bita, untuk disimpan di cache disk perangkat.
  Future<List<int>> fileBytes(String fileId, {String variant = 'thumb'}) async {
    final url = await fileUrl(fileId, variant: variant);
    final res = await _dio.get<List<int>>(url, options: Options(responseType: ResponseType.bytes));
    return res.data ?? const <int>[];
  }

  /// Popup K3 wajib baca yang belum dikonfirmasi pengguna: `{campaign: {...} | null}`.
  Future<Map<String, dynamic>> activeK3Popup() async =>
      _map((await _dio.get('$_p/hse/campaigns/active-popup')).data);

  /// Konfirmasi telah membaca dan memahami kampanye K3 (`read_duration_seconds` = waktu baca sebenarnya).
  Future<void> acknowledgeK3(String campaignId, int readSeconds, String deviceInfo) async {
    await _dio.post(
      '$_p/hse/campaigns/$campaignId/acknowledge',
      data: {
        'platform': 'mobile',
        'device_info': deviceInfo,
        'scroll_completed': true,
        'read_duration_seconds': readSeconds,
      },
    );
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

  /// Ringkasan antrean per peran (GET /home/summary): hitungan menunggu tindakan; kunci tak dikenal diabaikan.
  Future<Map<String, int>> homeSummary() async {
    final data = (await _dio.get('$_p/home/summary')).data as Map;
    return {
      for (final e in data.entries)
        if (e.value is num) '${e.key}': (e.value as num).toInt(),
    };
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
    ({
      List<Map<String, dynamic>> items,
      String? today,
      String? timeAnchor,
      String? requiredOutAt,
      int reportPendingCount,
      String? reportPendingPlanId,
    })
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
  Future<List<Map<String, dynamic>>> myOvertime() async =>
      _list((await _dio.get('$_p/overtime')).data);

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
