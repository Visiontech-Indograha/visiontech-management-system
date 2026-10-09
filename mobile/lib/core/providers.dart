import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/app_database.dart';
import '../data/sync_engine.dart';
import 'api_client.dart';
import 'biometric_auth.dart';
import 'device_id.dart';
import 'local_notifier.dart';
import 'token_storage.dart';

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => const TokenStorage(),
);

final biometricAuthProvider = Provider<BiometricAuth>(
  (ref) => const BiometricAuth(),
);

final deviceIdProvider = Provider<DeviceIdProvider>((ref) {
  return DeviceIdProvider(ref.watch(tokenStorageProvider));
});

final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

/// Provider murni (tanpa dependency ke authControllerProvider di sini) --
/// authControllerProvider yang akan mengisi `onSessionExpired` setelah
/// dibuat, supaya tidak terjadi circular provider dependency.
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(tokenStorage: ref.watch(tokenStorageProvider));
});

final syncEngineProvider = Provider<SyncEngine>((ref) {
  return SyncEngine(
    apiClient: ref.watch(apiClientProvider),
    db: ref.watch(appDatabaseProvider),
    deviceId: ref.watch(deviceIdProvider),
  );
});

/// Ditambah tiap kali sinkronisasi (manual ATAU otomatis di latar belakang lewat
/// ConnectivitySyncWatcher) selesai -- layar-layar (Absensi/Cuti/Logbook) yang
/// menyimpan riwayatnya sendiri sebagai State lokal (bukan lewat provider
/// reaktif) mendengarkan angka ini via ref.listen untuk tahu kapan harus
/// _loadHistory() ulang. Tanpa ini, sync yang jalan diam-diam di background
/// (mis. saat app baru resume dari background) tidak pernah terlihat user
/// sampai mereka pull-to-refresh atau pindah layar manual.
///
/// Riverpod 3.x tidak lagi punya StateProvider bawaan (lihat catatan yang sama
/// soal StateNotifier di auth_controller.dart) -- `Notifier<int>` polos ini
/// perannya sama persis, cuma beda cara deklarasi.
class SyncTickNotifier extends Notifier<int> {
  @override
  int build() => 0;

  void bump() => state++;
}

final syncTickProvider = NotifierProvider<SyncTickNotifier, int>(
  SyncTickNotifier.new,
);

/// Dinaikkan tiap peristiwa waktu nyata (SSE, T8) masuk: layar yang menampilkan rencana kerja, notifikasi, atau
/// absensi mendengarkannya lewat `ref.listen` dan memuat ulang datanya.
final liveEventTickProvider = NotifierProvider<SyncTickNotifier, int>(
  SyncTickNotifier.new,
);

final localNotifierProvider = Provider<LocalNotifier>((ref) => LocalNotifier());
