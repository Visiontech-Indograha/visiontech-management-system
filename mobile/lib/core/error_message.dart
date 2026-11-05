import 'package:dio/dio.dart';

import '../data/sync_engine.dart';
import 'api_client.dart';

/// Ubah kegagalan apa pun menjadi kalimat yang berarti bagi teknisi lapangan.
///
/// Sebelumnya tiap layar menangani error sendiri-sendiri dengan mutu berbeda:
/// satu layar membuang `e.toString()` mentah ke pengguna (yang membaca
/// "DioException [bad response]..."), layar lain menampilkan pesan generik
/// tanpa pernah mengambil `detail` dari server, padahal backend menulis pesan
/// Indonesia yang bagus seperti "Anda di luar radius kantor".
///
/// Prioritasnya: pesan dari server dulu (paling spesifik), lalu penjelasan per
/// jenis kegagalan, dan terakhir kalimat umum yang tetap bisa ditindaklanjuti.
String apiErrorMessage(Object error, {String? fallback}) {
  if (error is SyncRejectedException) return error.message;

  if (error is DioException) {
    // Pengajuan yang sama masih diproses server: bukan gagal permanen, cukup coba lagi nanti.
    if (apiErrorCode(error) == 'IDEMPOTENCY_SEDANG_DIPROSES') {
      return 'Pengajuan ini masih diproses server. Coba lagi sebentar lagi; isian Anda tidak hilang.';
    }
    final detail = _serverDetail(error);
    if (detail != null) return detail;

    if (isNetworkFailure(error)) {
      return 'Tidak ada koneksi ke server. Data Anda tidak hilang — coba lagi '
          'setelah ada sinyal.';
    }

    final status = error.response?.statusCode;
    return switch (status) {
      401 => 'Sesi Anda berakhir. Silakan masuk lagi.',
      403 => 'Anda tidak punya akses untuk tindakan ini.',
      404 => 'Data yang dituju tidak ditemukan di server.',
      409 => 'Data ini sudah diubah dari perangkat lain.',
      413 => 'Ukuran file terlalu besar untuk dikirim.',
      429 => 'Terlalu banyak permintaan. Tunggu sebentar lalu coba lagi.',
      _ when status != null && status >= 500 =>
        'Server sedang bermasalah (kode $status). Coba lagi nanti.',
      _ => fallback ?? 'Gagal memproses permintaan. Coba lagi.',
    };
  }

  return fallback ?? 'Terjadi kesalahan. Coba lagi.';
}

/// Kode galat backend VMS (`{"error": {"code": ...}}`), atau null bila bukan galat berformat itu.
String? apiErrorCode(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['error'] is Map) {
      final code = (data['error'] as Map)['code'];
      if (code is String) return code;
    }
  }
  return null;
}

/// Ambil pesan `detail` dari respons FastAPI bila ada & masuk akal ditampilkan.
String? _serverDetail(DioException error) {
  final data = error.response?.data;
  if (data is Map) {
    // Format galat backend VMS: {"error": {"code", "message", "details"}}.
    final err = data['error'];
    if (err is Map &&
        err['message'] is String &&
        (err['message'] as String).trim().isNotEmpty) {
      return (err['message'] as String).trim();
    }
    final detail = data['detail'];
    if (detail is String && detail.trim().isNotEmpty) return detail.trim();
    // 422 Pydantic: detail berupa daftar error per field.
    if (detail is List && detail.isNotEmpty) {
      final pesan = detail
          .whereType<Map>()
          .map((e) => e['msg']?.toString())
          .whereType<String>()
          .where((m) => m.trim().isNotEmpty)
          .join('; ');
      if (pesan.isNotEmpty) return pesan;
    }
  }
  return null;
}
