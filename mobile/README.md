# VMS Mobile

Aplikasi mobile (Flutter, Android) untuk Field Staff Visiontech Management
System (VMS) -- absensi geofence offline-first, pengajuan cuti, laporan
progres lapangan, dan logbook peminjaman kendaraan/alat.

Rencana kerja lengkap (keputusan teknis, package, urutan pengembangan,
pengujian): lihat artifact "Peta Jalan Mobile VMS" yang dibagikan bersama
proyek ini.

## Menjalankan secara lokal

1. Pastikan backend VMS berjalan dan dapat diakses dari HP lewat jaringan
   WiFi yang sama (LAN) -- **bukan** `localhost`, karena `localhost` dari HP
   merujuk ke HP itu sendiri.
2. Cari IP LAN laptop Anda (`ipconfig` di Windows, cari "IPv4 Address").
3. Jalankan dengan base URL API yang sesuai:

   ```bash
   flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000
   ```

   Tanpa `--dart-define`, default-nya `http://10.0.2.2:8000` (alias emulator
   Android ke localhost host) -- **tidak akan berfungsi di real device**,
   wajib di-override.

4. Pastikan Windows Firewall mengizinkan koneksi masuk ke port backend
   (biasanya 8000) dari jaringan lokal.

## Login & Device Binding

Login mewajibkan `client_id` (dibuat otomatis, UUID acak tersimpan di secure
storage sejak instalasi pertama) untuk role FIELD_STAFF -- akun akan
terikat ke device pertama yang dipakai login. Login dari device lain akan
ditolak (403) sampai HR mereset device lewat aplikasi web
(`PATCH /employees/{id}/reset-device`).

## Struktur proyek

Lihat `lib/*/README.md` di tiap folder untuk tanggung jawab modulnya
masing-masing. Ringkasan:

- `lib/core/` -- HTTP client (dio) + auto-refresh token, secure storage,
  konstanta.
- `lib/data/` -- database lokal (drift) + mesin sinkronisasi offline-first
  (`SyncEngine`).
- `lib/features/` -- satu folder per fitur (auth, attendance, leave,
  fieldwork, logbook, profile).
- `lib/shared/` -- router (go_router), shell navigasi, widget umum.

## Testing

```bash
flutter analyze
flutter test
```

## Build APK

APK rilis ditandatangani dengan **kunci rilis milik pemilik** (bukan kunci debug). Kunci dan sandinya
disimpan pemilik di luar repositori; kalau kunci hilang atau berganti, semua pengguna harus mencopot
dan memasang ulang APK (data luring yang belum terkirim ikut hilang).

1. Salin `android/key.properties.example` menjadi `android/key.properties` (diabaikan Git), isi path
   keystore (garis miring biasa) dan sandinya.
2. Build dengan alamat produksi (satu domain untuk web, API, dan berkas):

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://portal.visiontechindo.com
```

APK hasil build ada di `build/app/outputs/flutter-apk/app-release.apk` --
untuk distribusi internal, sideload langsung ke HP teknisi (belum perlu Play Store).

Tanpa `key.properties`, build rilis **gagal** dengan pesan yang jelas, supaya APK bertanda kunci debug
tidak sampai ke pengguna. Untuk uji lokal saja: tambahkan `-PallowDebugSigning=true` (jangan dibagikan).
Periksa penanda APK: `apksigner verify --print-certs app-release.apk`.

## Keterbatasan yang diketahui

- Endpoint `GET /fieldwork/work-plans` di backend untuk role FIELD_STAFF
  hanya mengembalikan Work Plan di mana teknisi adalah **ketua tim**
  (`assignee_id`) -- Work Plan di mana dia cuma **anggota**
  (`work_plan_member`) belum ikut kefilter di endpoint list ini. Ini
  keterbatasan backend yang sudah ada, dicatat di sini supaya tidak
  dikira bug baru dari sisi mobile.
- `docs/requirements/MOBILE_SYNC_CONTRACT.md` di repo backend punya bagian
  (§2D, lampiran) yang sudah usang -- acuan yang benar untuk skema
  lampiran adalah kode endpoint aktual (multi-file, field `attachments[]`),
  bukan dokumen itu.
- Background sync berkala (`workmanager`) belum diimplementasikan --
  sinkronisasi berjalan otomatis tiap kali entri baru dibuat (langsung
  kirim, atau diantrikan bila offline) dan lewat tombol manual di halaman
  Profil. Sync otomatis saat app di-background bisa jadi peningkatan
  lanjutan.
