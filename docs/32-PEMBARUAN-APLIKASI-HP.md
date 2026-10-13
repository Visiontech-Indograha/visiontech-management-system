# 32 · Pembaruan Otomatis Aplikasi HP (tanpa Google Play)

Keputusan pemilik 2026-10-07:
- Pembaruan bawaan **opsional**; rilis tertentu bisa ditandai **wajib**.
- Unduhan APK **publik** lewat portal.
- APK dibangun dan ditandatangani di **laptop pemilik**. Keystore tidak pernah keluar dari laptop.

## 1. Cara kerja

```
laptop pemilik ── scripts/rilis-apk.sh bangun ──► mobile/build/rilis/<build>/  (APK + latest.json, terverifikasi)
               └─ scripts/rilis-apk.sh kirim  ──► server ~/deploy/vms-mvp/rilis/android/  (read-only di vms_api)
HP ── GET /api/v1/app/android/update?build=N&abi=… ──► UP_TO_DATE | OPTIONAL | REQUIRED
   └─ unduh /api/v1/app/android/files/<nama>.apk → cek ukuran + SHA-256 → izin "instal aplikasi tak dikenal" → installer Android
```

**Rute API publik**
- `update`: status pembaruan, catatan rilis, ukuran, URL relatif, SHA-256 (tidak di-cache).
- `files/{nama}`: berkas APK. Hanya nama yang tercantum di manifest yang dilayani. Nama berversi, jadi aman di-cache Cloudflare.
- `latest.apk`: redirect 302 ke APK terbaru untuk pemasangan pertama (tautan di halaman login web). Pakai `?abi=armeabi-v7a` untuk HP 32-bit.

**Perilaku di HP**
- Pemeriksaan berjalan saat aplikasi dibuka, dan saat kembali aktif bila sudah ≥ 30 menit sejak pemeriksaan terakhir.
- Luring atau galat server **tidak pernah mengunci**. Status wajib hanya berasal dari jawaban server yang berhasil.
- **Opsional:** muncul pita "Versi baru … tersedia" di atas navigasi. Lembar detailnya menampilkan catatan rilis, ukuran, dan saran Wi-Fi. Tombol "Nanti" menunda 24 jam.
- **Wajib:** layar penuh "Pembaruan wajib" menutupi seluruh aplikasi, termasuk layar login. Sinkronisasi antrean luring tetap berjalan di belakangnya.
- APK yang sudah terverifikasi dipakai ulang, misalnya setelah izin diberikan atau aplikasi ditutup paksa. Pemasangan tetap bisa dilakukan **tanpa sinyal**.
- Data aplikasi tetap utuh karena kunci tanda tangan sama: sesi login, antrean absen luring, kunci Keystore, dan catatan pengguna.
- Profil memuat kartu "Tentang aplikasi": versi terpasang dan tombol "Periksa pembaruan".
- `User-Agent` API memuat versi aplikasi, sehingga versi tiap perangkat terlihat di daftar sesi halaman Akun.

**Kapan fitur ini mati**
- Pada build debug.
- Bila dibangun dengan `--dart-define=UPDATE_CHANNEL=play`. Kebijakan Google Play melarang pembaruan di luar Play; bila suatu saat pindah ke Play, hapus juga izin `REQUEST_INSTALL_PACKAGES`.

## 2. Pemasangan server (sekali)

Jalankan setelah rilis API yang memuat `/app/android/*` ter-deploy di prod:

```
ssh ageng@192.168.88.160 "bash -s" < deploy\pasang-rilis-apk.sh
```

Skrip ini membuat `rilis/android/` dan `compose.override.yml`, yang me-mount folder itu read-only ke API. `compose.yml` dan `api.env` tidak disentuh.

## 3. Menerbitkan versi baru

1. Naikkan `version:` di `mobile/pubspec.yaml`, misalnya `1.1.0+2` → `1.2.0+3`.
   - Angka setelah `+` adalah **build**. Nilainya wajib selalu naik.
   - Commit, lalu merge sampai prod seperti biasa.
2. Di laptop, dari checkout `prod` yang bersih:
   ```
   scripts\rilis-apk.bat bangun --catatan "Perbaikan absensi" --catatan "Tampilan baru SK"
   scripts\rilis-apk.bat kirim
   ```
   - `bangun` membangun APK untuk arm64 dan armv7 (±25 MB masing-masing).
   - Setiap APK diverifikasi: nama paket, versionCode, dan **sidik sertifikat rilis** (`deploy/android-release-cert.sha256`).
   - `bangun` menolak build yang tidak lebih tinggi dari yang sudah terbit.
3. Untuk rilis **wajib**, tambahkan `--wajib` saat `bangun`. Untuk mewajibkan rilis yang sudah terbit: `scripts\rilis-apk.bat wajib <build>`.
4. Cek rilis yang sedang terbit: `scripts\rilis-apk.bat status`.

**Rollback:** Android tidak bisa turun versi. Terbitkan perbaikan sebagai build yang lebih tinggi; APK lama tetap ada di folder rilis.

**Pemasangan pertama:** HP yang masih build 1 (APK sebelum fitur ini) harus memasang build 2 **sekali secara manual**, lewat tautan "Unduh aplikasi Android" di halaman login web. Setelah itu pembaruan berjalan otomatis.

## 4. Keystore — WAJIB dicadangkan

- Semua pembaruan harus ditandatangani kunci yang sama, yaitu `android/key.properties` + berkas `.jks` di laptop pemilik.
- **Kunci hilang = HP tidak bisa diperbarui.** Setiap karyawan harus uninstall dulu, dan data luring yang belum terkirim di HP hilang.
- Simpan salinan `.jks` beserta sandinya di tempat aman yang terpisah dari laptop.

## 5. Yang dilihat karyawan & pemecahan masalah

| Layar | Arti / tindakan |
|---|---|
| "Install unknown apps" (sekali) | Pilih **Always allow** / Izinkan dari sumber ini, lalu kembali ke aplikasi. Installer muncul sendiri. |
| "Update this app?" | Tekan **Update**. Data dan login tetap ada. |
| **Google Play Protect — "App scan recommended"** (setiap APK baru, saat online) | Muncul karena APK tidak berasal dari Play. **Panduan karyawan (keputusan pemilik 2026-10-08): tekan "Scan app"**, tunggu pemindaian selesai (beberapa detik), lalu pasang. APK memang publik dan tidak berisi rahasia. Alternatif "More details → Install without scanning" tidak dipakai di panduan. |
| "App not installed" / paket bentrok | APK ditandatangani kunci lain (mis. APK debug). Pakai APK dari portal; jangan bagikan APK dari build lokal. |
| Unduhan gagal / "Berkas pembaruan rusak" | Sinyal putus atau berkas tidak lengkap. Tekan "Coba lagi"; berkas yang rusak sudah dihapus otomatis. |

Hasil uji di emulator (Android 16): langkah-langkah di atas lulus, dengan rincian:
- Opsional, Nanti, izin, installer, terpasang, masih login.
- Wajib: tampil di login maupun setelah login, dan **tidak** mengunci saat mode pesawat.
- Installer dibatalkan → "Pasang pembaruan" tanpa unduh ulang.
- Antrean absen luring selamat melewati pembaruan dan tersinkron setelah online (`AUTO_VALID`).

Hasil uji di HP nyata (Realme RMX3933, Android 15, 2026-10-08, rilis prod):
- Build 1 → 2 dipasang manual. Tanda tangan sama dengan kunci rilis, jadi data lokal (login sidik jari, status wajah) tetap ada.
- Build 2 → 3 dari dalam aplikasi: lembar pembaruan muncul, unduhan terverifikasi, lalu Play Protect "Pindai aplikasi" dan "Aplikasi terinstal". Aplikasi terbuka sebagai build 3 dan masih login.
- Izin "instal aplikasi tak dikenal" tidak ditanyakan lagi bila sudah pernah diberikan.
- Setelah "Nanti", pita tidak tampil 24 jam untuk build itu (sesuai rancangan). "Periksa pembaruan" di Profil tetap menampilkan lembar pembaruan.

## 6. Keputusan pemilik

- 2026-10-07: opsional + wajib per rilis; unduhan publik; build & tanda tangan di laptop.
- 2026-10-08: panduan Play Protect = **Scan app**; alur disetujui sampai prod; uji di Realme setelah prod.
