---
name: vms-mobile
description: "Panduan kerja aplikasi mobile VMS (Flutter 3, Dart 3, Riverpod 3, GoRouter, Dio, Drift offline-first, camera watermark, geolokasi, flutter_secure_storage). Pakai saat menambah atau mengubah fitur di mobile/ (absen, cuti, jadwal, mess, K3, galeri, sinkron), membuat provider atau Notifier, repository, outbox sinkron, antrean foto, kamera, lokasi, token, tes widget atau golden, performa daftar, flavor, rilis APK, atau mereview kode mobile. Kata kunci: flutter, dart, mobile, aplikasi HP, android, riverpod, AsyncNotifier, provider, GoRouter, rute, Dio, interceptor, token refresh, Drift, SQLite, offline, luring, sinkron, outbox, antrean, client_op_id, idempotency, dead letter, backoff, kamera, watermark, foto, GPS, geolokasi, secure storage, Keystore, ListView.builder, RepaintBoundary, Isolate, tes widget, golden, flavor, APK, release, obfuscate, tap target 48dp, skala teks, Bahasa Indonesia."
---

# vms-mobile

Skill kerja untuk `mobile/` (Flutter). Pengguna utama adalah pekerja lapangan dengan HP kelas menengah, sering tanpa sinyal, sarung tangan, dan cahaya terang. Teks layar wajib Bahasa Indonesia sehari-hari (lihat `vms-ux-design-system`).

Pendamping: `references/arsitektur-sinkron.md` (struktur, Riverpod, Dio, Drift, outbox, foto), `references/rilis-tes-performa.md` (kamera, lokasi, token, flavor, tes, performa), `references/anti-pola.md` (temuan nyata dan perbaikan).

## 1. Aturan inti (wajib)

1. Setiap fitur baru harus offline-first. Baca lewat cache (`SyncEngine.fetchList` atau `fetchMap`). Tulis lewat `engine.submit` dengan `client_op_id` yang dibuat di HP. Permintaan pemilik: semua fitur HP jalan offline dan sinkron otomatis saat online (sumber: memori `vms-offline-first`; rancangan di `docs/38-RANCANGAN-MODE-OFFLINE-HP.md`).
2. Drift (SQLite) adalah sumber kebenaran lokal. UI membaca dari database lokal, bukan langsung dari respons jaringan.
3. Token di `flutter_secure_storage`. Jangan di SharedPreferences atau berkas biasa (bukti: `mobile/lib/core/token_storage.dart`).
4. Target sentuh minimal 48x48 dp. Tombol aksi utama di zona jempol (bawah layar).
5. Teks tidak memakai singkatan dan istilah teknis di layar. Padanan ada di skill `vms-ux-design-system`.
6. Riverpod 3: `Notifier` dan `AsyncNotifier`. Jangan kembali ke `StateNotifier` atau `ChangeNotifier` untuk fitur baru.
7. Pekerjaan berat (JSON besar, watermark foto, kompresi) di isolate (`compute` atau `Isolate.run`). Jangan di build atau di `await` yang memblokir UI.
8. Batas input dan rentang tanggal harus sama dengan skema API (bukti: `CLAUDE.md`).
9. Tes: jangan jalankan `flutter test` tanpa perintah pengguna jika memori "tes hanya atas perintah" berlaku. Tulis tes dulu. Untuk Flutter, beri jeda minimum di helper tunggu (memori `vms-cek-seperti-ci`).
10. Jangan sentuh APK produksi di HP pengguna. Jangan restart adb atau putus pairing wireless-debug (bukti: `CLAUDE.md`).

## 2. Versi dan paket (bukti: `mobile/pubspec.yaml`)

- Dart SDK `^3.13.3`.
- `flutter_riverpod ^3.4.3`, `go_router ^18.1.2`, `dio ^5.11.1`, `dio_cookie_manager`, `drift ^2.35.3`, `flutter_secure_storage ^11.2.0`, `connectivity_plus ^7.3.1`, `geolocator ^14.1.2`, `local_auth ^3.0.2`, `image ^4.12.0`, `uuid ^4.6.0`, `flutter_map ^8.3.2`, `flutter_local_notifications`, `shadcn_ui ^0.57.1`.
- Kamera: `camera ^0.12.2`, `camera_android ^0.10.12`, `image_picker ^1.2.4` (tiga jalur, lihat `anti-pola.md` A6).

## 3. Struktur folder (bukti: `mobile/lib/`)

```
lib/
  core/       api_client (Dio), token_storage, constants (--dart-define), router, theme/ (vms_colors, vms_sizes, vms_text_styles), photo_capture, error_message, watermark_camera_screen
  data/       app_database.dart (Drift), sync_engine.dart (outbox), offline_attendance.dart, vms_api.dart, connectivity_sync.dart
  features/   attendance, auth, face, gallery, hse, leaves, mess, notifications, plans, profile, records, sync, update, assets
  shared/ui/  vms_ui, vms_text_field, vms_select_field, vms_list_filter, vms_network_image, floating_nav
```

Catatan: `docs/02` (VMS Next) mengusulkan `features/<fitur>/{data,domain,presentation}`. Kode nyata lebih datar (berkas di `features/<fitur>/`). Ikuti kode nyata. Folder `data/` dan `core/` sudah ada.

## 4. Pola state (Riverpod 3)

```dart
@riverpod
class LeaveList extends _$LeaveList {
  @override
  Future<List<Leave>> build() => ref.read(leaveRepoProvider).fetchAll();

  Future<void> submit(LeaveDraft d) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => ref.read(leaveRepoProvider).submit(d));
  }
}
```

(Pola dari `riset-best-practice/03-WEB-MOBILE.md` M2. Codegen `@riverpod` belum terbukti dipakai di VMS. Cek `grep -rn "@riverpod" mobile/lib` sebelum mengasumsikan.)

Aturan:
- `ref.watch` hanya di `build`. `ref.read` di callback.
- Riverpod 3 mengecek `ref.mounted` sebelum memakai `ref` setelah `await` (sumber: https://riverpod.dev/docs/whats_new, diakses 2026-11-04).
- Retry otomatis Riverpod (backoff eksponensial) berlaku untuk provider, bukan untuk antrean outbox. Outbox harus punya backoff sendiri.
- State lokal widget (animasi, fokus, tab) di `StatefulWidget`. Data dari server di provider.
- Sealed class untuk state yang punya banyak kondisi (contoh panduan PDF `5.1`). Di VMS baru dipakai sekali; tidak wajib untuk fitur kecil.

## 5. Dio dan token

- Interceptor di `core/api_client.dart` (baris 34-71): refresh token otomatis lalu ulang request. Tes: `test/api_client_retry_test.dart`.
- Galat jaringan ditandai `isNetworkFailure(e)`. Galat ini tidak dibuang ke pengguna sebagai teks teknis.
- Pesan galat ke layar lewat `core/error_message.dart` (helper). Jangan tampilkan `e.toString()` atau `DioException` mentah (bukti: `anti-pola.md` A8).

## 6. Offline dan sinkron (ringkas, detail di `arsitektur-sinkron.md`)

- `SyncEngine.submit(opType, payload, localFiles)`: simpan op ke `PendingSyncOperations` dengan `client_op_id` (UUID v4), lalu coba kirim (`_push`). Kegagalan jaringan ditelan dan op tetap pending. Penolakan server menandai `deadLetter` dan melempar `SyncRejectedException`.
- Server idempoten per `client_op_id` (`api/app/modules/system/services/sync_service.py:112-137`). Kirim ulang aman.
- `attemptCount` naik tiap kirim. Batas percobaan dan backoff belum ada (bukti: `grep -rn backoff mobile/lib` hanya menemukan README).
- Absen offline dikirim lewat endpoint sendiri (`offlineAttendance.push()` di `_push`).

## 7. Kamera, foto, lokasi

- Watermark foto dan logo kop di isolate (`compute`) di `core/photo_capture.dart` (baris 87, 123). Pertahankan pola ini.
- Foto disimpan sebagai berkas lokal. Metadata dan path di Drift. Blob tidak di database.
- Foto dihapus dari perangkat hanya setelah server mengonfirmasi (riset `03` M4).
- Lokasi: `geolocator`. Minta izin dengan alasan yang jelas dalam Bahasa Indonesia. Tampilkan status "lokasi belum didapat" bila gagal, dengan tombol coba lagi.
- Detail kamera dan lokasi di `rilis-tes-performa.md`.

## 8. Tes

- 39 berkas di `mobile/test/` (bukti). Contoh: `sync_engine_test.dart`, `offline_attendance_test.dart`, `k3_campaign_test.dart`, `error_message_test.dart`, `leaves_status_test.dart`, `api_client_retry_test.dart`.
- Golden: 0 (bukti: `grep -rn matchesGoldenFile mobile/test` kosong). Usulan di `rilis-tes-performa.md`.
- Tap target: belum ada tes `androidTapTargetGuideline`.
- Helper: `mobile/test/support/fake_backend.dart`.

## 9. Performa (ringkas, detail di `rilis-tes-performa.md`)

- Daftar panjang: `ListView.builder` atau `SliverList`. 25 lokasi masih `ListView(children:)` atau `.map` (bukti: `anti-pola.md` A3).
- Build bersih: pekerjaan mahal tidak di `build()`. `const` untuk widget statis.
- `RepaintBoundary` untuk animasi berulang (indikator, sheet). Hanya 1 berkas yang memakainya.
- Target frame 16 ms (sumber: https://docs.flutter.dev/perf/best-practices, diakses 2026-11-04).

## 10. Rilis dan flavor

- Saat ini tidak ada flavor native (`productFlavors` nol di `android/app/build.gradle.kts`). Dev dan produksi dibedakan lewat `--dart-define`.
- Perintah APK dev di `CLAUDE.md`: `VMS_DEVELOPMENT=1 flutter build apk --release --dart-define=API_BASE_URL=http://<ip-lan>:8000`.
- Flutter ada di `~/flutter/bin/flutter.bat`.
- Rilis produksi sebaiknya memakai `--obfuscate --split-debug-info=build/symbols` dan menyimpan simbol (sumber: panduan PDF baris 606-609; riset `01` F-23). Belum dipakai di skrip.

## 11. Perintah verifikasi (sama dengan CI)

Dari root repo:

```
bash scripts/verify.sh mobile          # flutter analyze, flutter test
```

Manual di `mobile/`:

```
~/flutter/bin/flutter.bat analyze
~/flutter/bin/flutter.bat test
```

Jalankan hanya atas perintah pengguna jika aturan "tes hanya atas perintah" berlaku.

## 12. Checklist selesai

- [ ] Fitur bisa dipakai offline: data dibaca dari cache, tulisan lewat `submit` dengan `client_op_id`.
- [ ] Tidak ada `e.toString()` atau `DioException` ke layar.
- [ ] Target sentuh 48 dp. Tombol ikon punya `tooltip` dan `Semantics`.
- [ ] Skala teks 1.5 tidak memecah layout (uji manual atau tes).
- [ ] Daftar memakai builder. Data tidak dimuat seluruhnya ke widget.
- [ ] Token tidak keluar dari secure storage. Tidak ada log token.
- [ ] Pekerjaan berat di isolate.
- [ ] Teks Indonesia sehari-hari, tanpa istilah (lihat `vms-ux-design-system`).
- [ ] `flutter analyze` bersih; tes relevan lulus (sesuai perintah pengguna).
- [ ] Aturan API: parameter baru opsional. APK lapangan lama tetap jalan.

## 13. Skill global yang boleh dipanggil atau dilebur

- `simplify`: merapikan duplikasi setelah fitur selesai. Tidak mencari bug.
- `code-review`: sebelum PR, di diff.
- Untuk tampilan yang juga dibuat di web, ikuti `vms-web` dan `vms-ux-design-system` agar token dan istilah sama.
- Untuk aset gambar (ikon, ilustrasi) pakai `anthropic-skills:canvas-design` atau `anthropic-skills:theme-factory` lewat skill `vms-ux-design-system`.

## 14. Sumber (diakses 2026-11-04)

- Riverpod, What's new (Riverpod 3): https://riverpod.dev/docs/whats_new
- Flutter, Best practices (performa): https://docs.flutter.dev/perf/best-practices
- Riset repo referensi (diverifikasi 2026-11-04): `riset-best-practice/03-WEB-MOBILE.md` (bagian 1b dan M1-M11).
- Audit VMS: `riset-best-practice/01-PDF-DAN-AUDIT-VMS.md` (T16, T17, F-23, F-24, F-32, F-33).
- Belum dibuka langsung di sesi ini (verifikasi sebelum dikutip): Drift (https://drift.simonbinding.de), Dart 3 (https://dart.dev), Flutter test/golden (https://docs.flutter.dev/testing), Dio (https://pub.dev/packages/dio), GoRouter (https://pub.dev/packages/go_router).
