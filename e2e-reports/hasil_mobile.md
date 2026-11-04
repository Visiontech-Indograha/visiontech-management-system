# Hasil uji E2E mobile (HP fisik, APK dev com.visiontech.vms_mobile.dev)

Setup: APK dev (applicationIdSuffix .dev, terpisah dari produksi/beta; aplikasi produksi tidak disentuh). API lokal :8000 hanya bind 127.0.0.1 -> dipakai `adb reverse tcp:8000 tcp:8000` (bukan restart adb), build dengan API_BASE_URL=http://127.0.0.1:8000. Layar 720x1600.
Screenshot: e2e-reports/screenshots/{role}/mobile_*.png

## ketua11 (Ketua tim) - lengkap
Diuji: Absensi, sheet Lokasi kerja, Notifikasi, Rencana, detail jadwal harian, dialog Laporan harian (tidak dikirim), Survei (detail, peta layout 3 titik, detail titik), Galeri, Profil, Rekap Absen, Cuti & Izin + sheet Ajukan cuti, Kendaraan & Alat + sheet pilih aset, Riwayat Lembur, Mess + sheet pilih mess, Dokumen Saya + form Unggah, dialog Keluar. Tidak ada submit/hapus.
Temuan:
- [DIPERBAIKI] Dialog "Laporan harian" sempit (~55% lebar) dan label "Ringkasan hasil ker..." terpotong. Sebelum/sesudah: mobile_laporan_harian_sesudah_perbaikan.png.
- Kartu titik survei (status Menunggu PM) ada ruang kosong besar antara judul dan chip "0 foto"; detail titik: slot "Foto sesudah pemasangan" kosong tanpa placeholder (data uji tanpa foto). Kosmetik, belum diubah.
- Dokumen Saya: Sertifikat K3 menampilkan kotak abu dengan ikon gambar (thumbnail gagal/tidak ada). Kosmetik.
- FAB "Ajukan cuti" menimpa kartu terakhir (normal untuk FAB).
- Peta survei (satelit Esri, penanda bernomor + label) normal.
## anggota111 (Karyawan lapangan)
Diuji: login, dialog Aktifkan Login Sidik Jari, Absensi, sheet Ubah penjelasan, Rencana, Galeri, Profil (menu sama dengan ketua). Temuan: tidak ada; badge notifikasi 10 tampil.
## bayu.tech (Karyawan lapangan)
Diuji: Absensi, Rencana (kosong: "Tidak ada jadwal minggu ini"), Galeri, Profil. Temuan: tidak ada.
## gudang
Login berhasil tetapi tertahan gerbang "Daftarkan wajah Anda" (wajib daftar wajah/kamera; tidak dilanjutkan). mobile_gate_daftar_wajah.png. Catatan: ikon status bar putih di atas latar terang di layar ini (hampir tak terbaca).
## hse, pm1, finance, hr
Ditolak di app: "Akun kantor tidak dapat masuk lewat aplikasi HP. Silakan masuk lewat web." (perilaku sesuai desain). mobile_login_ditolak.png di tiap folder.

## Perubahan kode (hanya mobile)
- mobile/lib/features/plans/daily_plan_screen.dart (_dailyReportForm): AlertDialog diberi insetPadding horizontal 16 dan content dibungkus SizedBox(width: double.maxFinite). Build ulang + install terverifikasi.

## Catatan proses
- HP auto-rotate (sempat landscape); menekan Back di root tab keluar app. Ada 1 login gagal tak sengaja (anggota111, salah ketik karena fokus field) -> "sisa 4 percobaan", lalu berhasil.
- Sesi akhir: HP login sebagai ketua11 di app dev.
