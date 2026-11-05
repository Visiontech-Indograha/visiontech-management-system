# Anti-pola mobile VMS (dengan bukti)

Format: temuan, bukti (berkas dan baris), dampak, dan perbaikan. "Perlu cek" berarti belum diverifikasi di perangkat.

## A1. Berkas absen terlalu besar (tinggi)

- Bukti: `mobile/lib/features/attendance/attendance_screen.dart` 52.411 byte (sekitar 52 KB). Berkas paling besar di `features/`.
- Dampak: absen adalah fitur inti dan paling sering dipakai. Perubahan kecil berisiko regresi. Sulit dites.
- Perbaikan bertahap: pecah ke widget (`CheckInCard`, `SelfieStep`, `LocationStep`, `StatusBanner`) di `features/attendance/widgets/`. Logika ke `AsyncNotifier`. Logika offline tetap di `data/offline_attendance.dart`.
- Syarat: golden test dulu (lihat `rilis-tes-performa.md`), lalu refaktor bertahap, lalu uji di HP. Jangan sentuh APK produksi di HP pengguna.

## A2. Outbox tanpa backoff dan batas percobaan (tinggi)

- Bukti: `mobile/lib/data/sync_engine.dart`: `submit` (baris 111-130) dan `_push` (baris 132). `attemptCount` ada, backoff tidak (grep `backoff` di `lib/` hanya README).
- Dampak: galat sementara bisa membuat op terus dicoba, atau tidak ada jeda sehingga boros baterai. Dead-letter hanya untuk penolakan server.
- Perbaikan: lihat `arsitektur-sinkron.md` bagian 4.

## A3. Daftar tanpa lazy rendering (sedang)

- Bukti: `ListView(` dengan `children:` atau `.map(` di 25 lokasi. `ListView.builder` atau `SliverList` hanya di 3 berkas (riset `01` F-24). Contoh: `features/attendance/attendance_screen.dart:749`, `recap_screen.dart:100`, `notifications_screen.dart:201`, `leaves_screen.dart:151`.
- Dampak: semua item dibangun sekaligus. Terasa di HP kelas bawah dengan data panjang.
- Perbaikan: `ListView.builder` untuk daftar yang bisa panjang. Uji dengan 100+ item.

## A4. Tanpa golden test (sedang)

- Bukti: `grep -rn matchesGoldenFile mobile/test` kosong (dicek di sesi riset ini).
- Dampak: perubahan tampilan tidak tertangkap.
- Perbaikan: golden untuk layar kritis (absen, cuti, sinkron) per ukuran layar dan skala teks.

## A5. Tanpa flavor native (sedang)

- Bukti: `android/app/build.gradle.kts` tanpa `productFlavors`. Dev dan produksi lewat `--dart-define` saja (`CLAUDE.md`).
- Dampak: APK dev dan produksi bisa tertukar di HP lapangan.
- Perbaikan: usulan flavor dengan `applicationIdSuffix`. Perlu keputusan pemilik (mengubah ID aplikasi).

## A6. Tiga jalur kamera tanpa dokumen (sedang)

- Bukti: `pubspec.yaml` memuat `camera`, `camera_android`, `image_picker`.
- Dampak: perilaku berbeda antar perangkat. Sulit dirawat.
- Perbaikan: dokumentasikan alasan tiap jalur. Pilih satu untuk absen dan satu untuk galeri. Uji di HP nyata (emulator tidak cukup).

## A7. Antrean absen di secure storage (sedang, perlu cek)

- Bukti: riset `01` F-32: `mobile/lib/data/offline_attendance.dart:43` menyimpan antrean di `flutter_secure_storage`.
- Dampak: secure storage tidak untuk data besar. Ukuran antrean tidak dibatasi.
- Perbaikan: periksa ukuran nyata. Pindahkan ke Drift bila perlu, dengan migrasi dan tes.

## A8. Pesan galat mentah ke layar (rendah)

- Bukti: pola `e.toString()` atau `DioException` di 48 tempat (riset `01` F-33, hasil grep). Tidak semua sampai ke UI.
- Dampak: pesan teknis tampil ke pengguna lapangan.
- Perbaikan: arahkan ke `core/error_message.dart`. Audit 48 tempat satu per satu.

## A9. Shimmer hanya di satu berkas (rendah)

- Bukti: riset `01` F-27: skeleton atau shimmer di 1 berkas mobile. Kosong dan coba lagi sudah di 38 berkas.
- Dampak: layout bergeser saat data datang.
- Perbaikan: skeleton berbentuk seperti daftar utama (absensi, jadwal, notifikasi).

## A10. Warna literal di luar tema (rendah)

- Bukti: `Color(0x...)` di 67 tempat. 43 di `core/theme/vms_colors.dart` (wajar, sumber token). Sisanya di `core/watermark_camera_screen.dart` (2), `features/plans/survey_screen.dart` (1), `shared/ui/vms_ui.dart` (11), `core/theme/vms_theme.dart` (7).
- Perbaikan: pindahkan ke `vms_colors.dart` atau `ThemeExtension`.

## A11. Tap target dan tooltip belum diuji (sedang)

- Bukti: tidak ada tes `androidTapTargetGuideline`. Semantics, semanticLabel, atau tooltip di 15 berkas (riset `03` M8).
- Perbaikan: `tooltip` untuk tombol ikon, tes target 48 dp, skala teks 1.5.

## A12. Tidak ada SSL pinning dan deteksi root (sedang, keputusan operasional)

- Bukti: tidak ada `pinning`, `badCertificateCallback`, `SecurityContext`, atau deteksi root di `mobile/lib` (riset `01` F-23).
- Dampak: lalu lintas LAN bisa disadap di perangkat dengan sertifikat palsu. Pinning bisa membuat login gagal bila sertifikat berganti.
- Perbaikan: keputusan pemilik dulu. Pinning memerlukan rencana sertifikat.

## A13. Sealed class jarang dipakai (rendah)

- Bukti: sealed class dipakai 1 kali (riset `01` T16). Panduan PDF menganjurkan untuk state banyak kondisi.
- Perbaikan: tidak wajib. Gunakan untuk state yang punya banyak kondisi dan dicek `switch` exhaustive.

## Kekuatan yang sudah baik (jangan dirusak)

- `flutter_riverpod ^3.4.3` dengan banyak pemakaian `ref.watch` dan `ref.read`.
- `flutter_secure_storage` untuk token.
- Drift untuk data lokal. Antrean dengan `client_op_id` dan server idempoten.
- `compute()` untuk watermark foto.
- `dispose()` di 26 berkas.
- Interceptor refresh token dengan tes.
- `error_message.dart` sebagai helper pesan galat.
