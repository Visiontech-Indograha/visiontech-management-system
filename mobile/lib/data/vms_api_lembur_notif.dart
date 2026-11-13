part of 'vms_api.dart';

/// Panggilan API per domain (lembur_notif); dipisah dari VmsApi, perilaku sama.
mixin _VmsApiLemburNotif on _VmsApiBase {
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

  /// Lampiran pengajuan. [kind]: `overtime` (id lembur) atau `mess` (mess_stay_id). Maks. 5 berkas.
  Future<List<Map<String, dynamic>>> attachments(String kind, String id) async =>
      _list((await _dio.get('$_p/$kind/$id/attachments')).data);

  /// Tautkan berkas yang sudah diunggah (`/files/upload`); mengembalikan daftar terbaru.
  Future<List<Map<String, dynamic>>> addAttachment(String kind, String id, String fileId) async =>
      _list((await _dio.post('$_p/$kind/$id/attachments', data: {'file_id': fileId})).data);

  Future<List<Map<String, dynamic>>> removeAttachment(String kind, String id, String fileId) async =>
      _list((await _dio.delete('$_p/$kind/$id/attachments/$fileId')).data);

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

  /// Dokumen kendaraan yang dikemudikan akun ini (STNK, SIM, dll).
  Future<List<Map<String, dynamic>>> vehicleDocumentsMine() async =>
      _list((await _dio.get('$_p/vehicle-documents/mine')).data);

  /// HSE/OM: dokumen kantor yang jatuh tempo dalam [days] hari (yang lewat ikut).
  Future<List<Map<String, dynamic>>> vehicleDocumentsExpiring({int days = 30}) async =>
      _list((await _dio.get('$_p/vehicle-documents/expiring', queryParameters: {'days': days})).data);
}
