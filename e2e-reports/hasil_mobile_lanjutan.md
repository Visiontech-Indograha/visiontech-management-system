# Hasil mobile lanjutan (HP fisik, ketua11, APK dev)

## A. Perangkat yang masuk (baru)
- mobile/lib/features/profile/sessions_screen.dart (baru), menu "Perangkat yang masuk" di Profil (bagian Keamanan), method authSessions/revokeAuthSession/revokeOtherAuthSessions di mobile/lib/data/vms_api.dart.
- Tampil: penanda "Perangkat ini", tombol Cabut per sesi lain (dialog konfirmasi), "Keluarkan semua perangkat lain", pesan "Perlu internet" + Coba lagi saat gagal muat.
- Bukti: screenshots/ketua11/mobile_sesi_login.png, mobile_sesi_login_konfirmasi.png (dialog dibatalkan; tidak ada sesi dicabut).
- Catatan: judul "Keamanan akun" ganda dengan "Keamanan" sudah dihapus di kode, tetapi APK di HP belum dibangun ulang (masih ada judul ganda).

## B. Foto profil
- Ganti foto lewat galeri (gambar uji di /sdcard/Download): foto tampil di avatar Profil segera dan tetap tampil setelah force-stop + buka ulang. Beranda (Absensi) tidak punya avatar, hanya Profil. Tidak ada bug di mobile; tidak ada perubahan kode.
- Foto uji dihapus lewat "Hapus foto" -> kembali ke inisial "U1". File uji di HP dihapus.
- Temuan: sebelum uji, menu menampilkan "Hapus foto" padahal avatar inisial (photo_file_id ada tetapi gambar tak termuat; kemungkinan data seed/berkas tanpa blob). Fallback inisial rapi. Akar ada di data/API bila ingin diselidiki.
- Bukti: mobile_foto_profil.png, mobile_foto_profil_beranda_restart.png, mobile_foto_profil_setelah_restart.png, mobile_foto_profil_dihapus.png.

## C. Placeholder foto kosong
- survey_point_screen.dart: slot tanpa foto (mode lihat) menampilkan kotak "Tidak ada foto".
- survey_screen.dart: kartu titik tanpa foto menampilkan teks "Tidak ada foto" (ruang kosong 64px hilang).
- Bukti: mobile_detail_titik_tanpa_foto.png, mobile_kartu_titik_tanpa_foto.png.

flutter analyze (profile, survey_screen, survey_point_screen, vms_api): bersih.
