/// Konfigurasi dasar koneksi API.
///
/// PENTING (lihat plan Keputusan 3): saat testing di real device, base URL
/// HARUS IP LAN laptop (mis. http://192.168.1.23:8000), BUKAN localhost --
/// localhost dari HP akan merujuk ke HP itu sendiri, bukan laptop.
///
/// Ganti nilai ini sesuai jaringan Anda, atau override lewat
/// `--dart-define=API_BASE_URL=http://192.168.x.x:8000` saat `flutter run`.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000', // alias emulator Android ke localhost host; ganti ke IP LAN untuk real device
  );

  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 20);
  // Tanpa ini, upload foto di jaringan lambat/lag bisa "menggantung" tanpa
  // batas waktu (Dio tidak punya default sendTimeout) -- lebih longgar dari
  // connect/receive karena body multipart foto jauh lebih besar dari JSON
  // biasa, tapi tetap dibatasi supaya gagal jelas & masuk antrian retry
  // offline (lihat SyncEngine.submitOrQueue), bukan menggantung selamanya.
  static const Duration sendTimeout = Duration(seconds: 45);
}

/// Nama grup sinkronisasi, harus sama persis dengan yang dipakai di
/// docs/requirements/MOBILE_SYNC_CONTRACT.md backend (attendance/fieldwork/logbook).
class SyncGroup {
  static const String attendance = 'attendance';
  static const String fieldwork = 'fieldwork';
  static const String logbook = 'logbook';

  static const all = [attendance, fieldwork, logbook];
}
