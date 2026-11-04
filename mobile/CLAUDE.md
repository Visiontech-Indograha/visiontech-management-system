# Mobile VMS (Flutter 3, Dart 3)

Aturan ringkas untuk folder `mobile/`. Teks layar wajib Bahasa Indonesia sehari-hari. Pengguna utama bekerja di lapangan, sering offline.

## Aturan inti
- Offline-first: baca dari cache (`SyncEngine.fetchList` / `fetchMap`), tulis lewat `engine.submit` dengan `client_op_id` (UUID dibuat di HP).
- Drift adalah sumber kebenaran lokal. Token hanya di `flutter_secure_storage`.
- Riverpod 3: `Notifier` / `AsyncNotifier`. `ref.watch` hanya di `build`.
- Pekerjaan berat (JSON besar, watermark, kompresi) di isolate (`compute`).
- Target sentuh minimal 48 dp. Tombol ikon punya `tooltip`.
- Pesan galat lewat `core/error_message.dart`. Jangan tampilkan `e.toString()`.
- Parameter API baru harus opsional: APK lapangan lama tetap jalan.
- Jangan sentuh aplikasi produksi di HP pengguna. Jangan restart adb atau putus pairing wireless-debug.

## Skill terkait
- `vms-mobile`: struktur, outbox, kamera, lokasi, token, tes, performa, flavor, anti-pola.
- `vms-ux-design-system`: token, glosarium istilah, popup K3, uji awam.

## Perintah (dari root repo atau `mobile/`)
- Semua langkah mobile: `bash scripts/verify.sh mobile` (flutter analyze + flutter test).
- Analisis: `~/flutter/bin/flutter.bat analyze`.
- Tes: `~/flutter/bin/flutter.bat test` (atas perintah pengguna).
- APK dev: `VMS_DEVELOPMENT=1 flutter build apk --release --dart-define=API_BASE_URL=http://<ip-lan>:8000`.

## Hindari
- `print` tertinggal atau log token, PIN, atau data pribadi.
- `ListView(children: ...)` untuk daftar yang bisa panjang. Pakai `ListView.builder`.
- Pekerjaan berat di `build()`.
- Blob foto di database (simpan path).
- Mengubah `vms_colors.dart` tanpa melihat token di `index.css` (web) yang sepadan.

## Tes
- Tes widget: pakai `ProviderScope(overrides: ...)`. Beri jeda minimum di helper tunggu (CI lebih lambat).
- Golden belum ada. Tambah atas perintah pengguna.
