# Hasil mobile perbaikan (HP fisik, APK dev dibangun ulang)

## 1. Logo cap foto terlalu kecil: DIPERBAIKI
- Penyebab: kotak logo watermark 96x30, dibagi dua sel sama lebar, sehingga logo Visiontech (632x184) hanya ~45x13 px.
- Perbaikan: mobile/lib/core/watermark_camera_screen.dart (kotak 156x56, sel Visiontech 94 + sel logo tim 56, gap 6, skala render 3x) dan mobile/lib/core/photo_capture.dart (composeKopLogos pakai sel berbobot, PNG 3x supaya tajam). Cap waktu/koordinat/alamat tidak diubah.
- Bukti: screenshots/ketua11/mobile_kamera_logo.png (pratinjau kamera swafoto absen; panel yang sama dibakar ke foto). Logo Visiontech kini terbaca jelas (~2x lebih besar).
- Catatan: logo tim milik tim uji di server tampak berupa kotak tipis hampir kosong (data uji, bukan bug tata letak). Foto tidak sampai diambil agar tidak membuat data absensi.
- Tes: kop_logo_compose_test (disesuaikan) dan kamera_alamat_flash_test lulus; flutter analyze lib/core bersih.

## 2. Build + install: OK
APK dev dibangun ulang (app-release.apk), adb install -r Success. Judul ganda di Profil sudah hilang (mobile_profil_scroll.png).

## 3. Pencabutan sesi: LULUS
- Sesi kedua ketua11 dibuat lewat curl POST /api/v1/auth/login dengan "platform":"mobile" (platform web ditolak untuk akun ini).
- Muncul di "Perangkat yang masuk" sebagai curl/8.22.0 (mobile_sesi_dua_perangkat.png). Dicabut lewat Cabut > Keluarkan (mobile_sesi_cabut_konfirmasi.png).
- Setelah dicabut: sesi hilang dari daftar (mobile_sesi_setelah_cabut.png); token curl: auth/sessions 401, auth/me 401, refresh 401. Sesi HP ("Perangkat ini") tidak disentuh.

## 4. Gerbang wajah gudang: DIATASI
- Server dev memakai FACE_FAKE_MODE=true (api/.env), jadi pendaftaran wajah lewat kamera HP lolos tanpa wajah nyata (4 foto otomatis). Login gudang@uji-nyata.test, sandi 123.
- Setelah daftar: beranda Absensi, Rencana (kosong, "Tidak ada jadwal minggu ini"), Galeri, Profil terbuka. Menu gudang di HP hanya 4 tab itu. Bukti di screenshots/gudang/mobile_gate_daftar_wajah_baru.png, mobile_beranda_setelah_daftar_wajah.png, mobile_rencana.png, mobile_galeri.png.
- Efek samping: akun gudang kini punya wajah terdaftar (palsu) dan satu sesi curl uji. HP kini login sebagai gudang (ketua11 keluar).
- Temuan lama masih ada: ikon status bar putih di atas latar terang pada layar gerbang wajah.
