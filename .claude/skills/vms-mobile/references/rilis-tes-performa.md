# Kamera, lokasi, token, tes, performa, dan rilis mobile

## 1. Kamera dengan watermark

Kondisi nyata (bukti: riset `03` M4, `core/photo_capture.dart`, `core/watermark_camera_screen.dart`, `core/kamera_*`):
- Watermark memuat jam, koordinat, alamat, logo tim dan logo perusahaan (sumber: `docs/04-DESAIN-UI.md`, pola VMS).
- Pemrosesan gambar di `compute` (isolate). Dua fungsi di `compute`: watermark (baris 87) dan logo kop (baris 123).
- Tiga jalur kamera: `camera`, `camera_android`, `image_picker`. Pilih satu jalur utama untuk absen dan satu untuk unggah galeri. Dokumentasikan alasannya (riset `03` M-F).

Aturan:
- Jangan membuat jalur kamera baru tanpa alasan tertulis.
- Pemotretan di luar ruang (cahaya terang): uji dengan kontras teks watermark. Teks watermark memakai latar gelap semi transparan.
- Simpan berkas dengan nama unik (UUID). Simpan path di Drift.
- Ukuran berkas: kompres sebelum antre. Ukur ukuran rata-rata di HP kelas menengah.
- Izin kamera dan galeri: alasan dalam Bahasa Indonesia, dan jalan keluar bila ditolak.

Tes kamera: `test/kamera_alamat_flash_test.dart`, `test/kamera_jepretan_ganda_test.dart`, `test/kop_logo_compose_test.dart`, `test/logo_tim_test.dart`.

## 2. Lokasi

- Paket `geolocator ^14.1.2`. Layanan lokasi dan izin dicek sebelum dipakai.
- Tampilkan koordinat dan alamat. Bila belum dapat, tampilkan "Lokasi belum ditemukan" dan tombol "Coba lagi". Jangan mengirim absen tanpa lokasi jika aturan proyek mewajibkan (cek `attendance_screen.dart`).
- Lokasi terdekat dihitung di `features/attendance/nearest_site.dart` dan dites (`test/nearest_site_test.dart`).
- Batas waktu pengambilan lokasi: beri timeout, jangan menahan UI.

## 3. Token dan keamanan

- `core/token_storage.dart`: access dan refresh token di `flutter_secure_storage` (Keystore Android, Keychain iOS). Sumber: panduan PDF baris 606-608.
- Jangan log token, PIN, atau data pribadi. Jangan simpan token di SharedPreferences.
- Interceptor refresh (`core/api_client.dart`): satu refresh berjalan pada satu waktu. Tes: `test/api_client_retry_test.dart`.
- Biometrik (`local_auth`) sudah ada: `biometric_auth.dart`. Jangan diganti (riset `03` M11).
- Belum ada SSL pinning dan deteksi root (bukti: riset `01` F-23). Keputusan operasional diperlukan: server LAN memakai sertifikat internal.
- Logout: hapus token dari secure storage dan bersihkan cache sesi (bukan data antrean yang belum terkirim tanpa peringatan).

## 4. Tes

### Peta

| Jenis | Lokasi | Jumlah (bukti) |
|---|---|---|
| Unit dan logika | `test/*.dart` | 39 berkas bersama widget |
| Widget | `test/screens_test.dart`, `test/mess_screen_test.dart`, `test/widget_test.dart` | sebagian |
| Golden | - | 0 |
| Tap target dan skala teks | - | 0 |
| Pendukung | `test/support/fake_backend.dart` | 1 |

### Pola tes widget

```dart
testWidgets('tombol kirim nonaktif saat antrean penuh', (tester) async {
  await tester.pumpWidget(ProviderScope(
    overrides: [syncEngineProvider.overrideWithValue(fakeEngine)],
    child: const MaterialApp(home: LeaveFormScreen()),
  ));
  await tester.pump(const Duration(milliseconds: 300)); // beri waktu render (jeda minimum)
  expect(find.byKey(const Key('btn-kirim')), findsOneWidget);
});
```

- Helper tunggu: beri jeda minimum yang cukup untuk CI yang lebih lambat (memori `vms-cek-seperti-ci`: tes widget lolos di laptop tapi gagal di CI). Jangan `pumpAndSettle` tanpa batas bila ada animasi berulang.
- Override provider dengan `ProviderScope(overrides: ...)`, bukan mock global.

### Golden (usulan, belum ada)

Dari riset `03` M-B:
- Layar absen (idle, loading, sukses, offline), form cuti (valid dan galat), layar sinkron (ada antrean dan kosong).
- Ukuran layar 320 dp dan 411 dp. Skala teks 1.0 dan 1.5.
- Jalankan di satu lingkungan (Linux di CI). Golden berbeda antar OS. `flutter test --update-goldens` hanya bila perlu.

### Tap target dan skala teks (usulan)

- `androidTapTargetGuideline` dan `textScaler` 1.5 di layar absen, cuti, login (riset `03` M-G).

### Konkurensi sinkron (usulan)

- Dua submit dengan `client_op_id` sama hanya terkirim sekali di sisi server (tes di API, `sync_engine_test.dart` di HP untuk sisi klien).

## 5. Performa

Dari dokumentasi Flutter (https://docs.flutter.dev/perf/best-practices, diakses 2026-11-04):
- `ListView.builder` (lazy): hanya widget yang terlihat dibangun.
- Hindari pekerjaan mahal di `build()`. Build bisa dipanggil berulang.
- Batasi `setState` ke subtree yang berubah.
- `StatelessWidget` untuk UI yang dipakai ulang, bukan fungsi helper yang dipanggil di `build`. Hindari meng-override `operator ==` pada widget.
- Target 16 ms per frame (build sekitar 8 ms, render sekitar 8 ms). Gunakan DevTools Performance view.

Dari panduan PDF bagian 5 (bukan halaman resmi yang dibuka di sesi ini):
- `const` untuk widget statis agar dilewati saat rebuild.
- `RepaintBoundary` untuk animasi berulang (indikator, sheet). Mencegah repaint tetangga.
- `Isolate.run` untuk JSON besar dan pemrosesan gambar.
- Dispose controller, subscription, dan animasi di `dispose()`.

Kondisi VMS: 26 berkas punya `dispose()`. Daftar dengan `children:` atau `.map` di 25 lokasi (bukti: riset `01` F-24). Contoh: `features/attendance/attendance_screen.dart` (baris 749), `recap_screen.dart` (100), `notifications_screen.dart` (201), `leaves_screen.dart` (151).

Ukur, jangan tebak. Uji dengan data 100+ item dan HP kelas menengah.

## 6. Flavor dan rilis

- Belum ada flavor native (`productFlavors` tidak ditemukan di `android/app/build.gradle.kts`). Dev dan produksi dibedakan lewat `--dart-define` (`VMS_DEVELOPMENT`, `API_BASE_URL` di `core/constants.dart`).
- Risiko: APK dev dan produksi bisa tertukar di HP lapangan (riset `03` M-C).
- Usulan (bukan keputusan): flavor `dev`, `beta`, `prod` dengan `applicationIdSuffix`. Mengubah ID aplikasi. Data lokal di HP pengguna tidak ikut pindah. Jangan pasang flavor baru di HP produksi tanpa izin pemilik.
- Alur branch: `development` lalu PR ke `beta`, lalu PR ke `prod` (memori `vms-alur-branch`). Lokal memakai layanan test di server, bukan `vms_beta` atau `vms_v2`.
- Perintah APK dev: `VMS_DEVELOPMENT=1 flutter build apk --release --dart-define=API_BASE_URL=http://<ip-lan>:8000`.
- Rilis: tambahkan `--obfuscate --split-debug-info=build/symbols` dan simpan folder simbol. Belum ada di skrip (`scripts/`).
- Versi aplikasi: ikuti SemVer lewat `VERSION` dan `scripts/versi.sh --tulis` (bukti: `CLAUDE.md`).
- Pembaruan wajib: fitur `update/` (`app_update_service.dart`). Pastikan APK lama masih bisa memanggil API selama masa transisi.

## 7. Aturan kompatibilitas API

- APK lapangan lama harus tetap jalan. Parameter baru pada API wajib opsional (bukti: `CLAUDE.md`, "tanpa parameter = perilaku lama").
- Perubahan kontrak: ubah API dulu, lalu klien. Naikkan MINOR untuk fitur, MAJOR untuk perubahan yang memutus klien lama.
- Batas input di HP sama dengan skema API.
