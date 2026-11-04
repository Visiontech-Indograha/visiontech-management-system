# Hasil E2E Web (PARSIAL)
Keterbatasan: resize_window tidak mengubah viewport (tetap 1536x655) -> uji mobile 390x844 TIDAK terlaksana. Ekstensi Chrome sempat putus. Role OM, ADMIN_HR_GA, FINANCE belum diuji. Screenshot berformat jpeg (diberi ekstensi .png).
## PM (Dian Kusuma)
Menu: Beranda, WO, Jadwal harian, Alokasi mingguan, Klien, Tim, Absensi, Cuti, Rekap, Lembur, Aset, Mess, Berkas, Direktori, Offboarding, Jenis pekerjaan, Akun. Diuji: WO (tab Review Survei, modal rincian, peta+marker, popup marker), Jadwal, Alokasi, Klien, Absensi, Mess. LULUS: tak ada error konsol. Temuan: popup marker tanpa foto (data uji tanpa foto; foto belum terverifikasi); tombol "Setujui Survei & Kunci Tugas" tampak pudar (kontras rendah/disabled); tombol "Review Survei" membuka modal "Rincian Tugas & Dokumen Resmi" (bukan modal khusus review) - periksa maksud.
## SUPER_ADMIN
Diuji: Beranda, K3/HSE, Lokasi kerja, Audit log, Kendaraan & alat, modal WO (peta+2 marker tampil). LULUS, tanpa error konsol.
## HSE
Beranda menampilkan popup wajib K3. GAGAL: isi kampanye tampil sebagai teks HTML mentah ("<h3>PENTING...</h3><p>..."), perkiraan web/src/components/organisms/hse/HseMandatoryPopupGate.tsx (render sebagai teks, perlu sanitasi+render HTML). Menu HSE: Jadwal, K3/HSE, Absensi, Cuti, Rekap, Aset, Berkas, Direktori, Akun (halaman belum dibuka).
Catatan: halaman Jadwal/Alokasi/dll memuat "Memuat..." beberapa detik saat navigasi penuh (normal).

## Lanjutan HSE + OM (sesi 2, PARSIAL)
BLOKER (GAGAL, tingkat tinggi): popup wajib baca K3 "Panduan Keselamatan Kerja" menutupi SEMUA halaman (Beranda, K3/HSE, Jadwal, ...) untuk HSE dan OM. Tombol X (Close), Escape tidak menutup; hanya tombol "Saya Telah Membaca..." (mengirim konfirmasi baca, tidak ditekan karena itu submit data). Dialog "Keluar dari akun?" tampil di atas popup dan masih berfungsi. Akibatnya menu lain tak bisa diuji visual/diklik normal. Perlu keputusan: X seharusnya menutup sementara, atau memang wajib (ubah UX).
Juga: isi kampanye masih HTML mentah ("<h3>PENTING...</h3><p>") di popup DAN kartu daftar di halaman K3/HSE.
HSE terverifikasi (via teks halaman): K3/HSE tab "Kampanye & Pengumuman K3 (1)" + "Inspeksi Kendaraan (0)" (state kosong rapi), tombol "Terbitkan Kampanye K3", "Audit Pembaca" ada (modal tidak dibuka karena tertutup popup). Kendaraan & alat: 4 kendaraan, 6 alat tampil, badge STNK/KIR ok. Jadwal harian: kalender Nov 2026 kosong (0 jadwal) ok. Console: tanpa error. Rute benar: /safety-campaigns, /assets, /work-plans (bukan /hse).
OM: login sukses (menu: Tugas Klien (WO), Jadwal harian, Alokasi mingguan, Klien, Tim Lapangan, Absensi, Cuti & Izin, Rekap bulanan, Akun); dashboard hanya terlihat di balik popup. Menu OM belum diuji.
BELUM DIUJI: ADMIN_HR_GA (hr, office), FINANCE, menu OM, sisa menu HSE (Absensi, Cuti, Rekap, Berkas, Direktori, Akun), modal kampanye "Terbitkan"/"Audit Pembaca".

## Sesi 3 (OM, HSE, ADMIN_HR_GA, FINANCE) - semua menu dibuka, screenshot di screenshots/{ROLE}/web_*.png
Konfirmasi baca K3 hanya ditekan pada om@ dan hse@ (izin user). hr@, office@, finance@ TIDAK ditekan; popup disembunyikan lewat JS (display:none) hanya agar halaman terlihat.
OM: Beranda, WO (4 tab), Tim, Absensi, Cuti, Rekap, Jadwal, Alokasi, Klien, Akun diuji. LULUS tampilan. Akun: panel "Perangkat yang masuk" ada (perangkat ini + curl, tombol "Keluarkan" per sesi dan "Keluarkan perangkat lain"); tombol "Tambah foto" ada; Biometrik Wajah tampil.
HSE: popup tertutup setelah konfirmasi (OK). Jadwal, K3/HSE, Absensi, Cuti, Rekap, Aset, Berkas, Direktori, Akun diuji. Modal "Terbitkan Kampanye K3" tampil utuh (scroll internal, tidak terpotong, dibatalkan); modal "Audit Pembaca" tampil 7 pembaca (dibatalkan). Console: tanpa error.
GAGAL (masih): isi kampanye tampil sebagai teks HTML mentah ("<h3>PENTING...") di popup wajib baca dan kartu K3/HSE.
ADMIN_HR_GA (hr@, office@): menu Jadwal, Tim, Absensi, Cuti, Rekap, Kendaraan, Mess, Berkas, Direktori, Offboarding, Akun - semua memuat. FINANCE: Jadwal, Absensi, Cuti, Rekap bulanan, Rekap lembur, Kendaraan, Berkas, Direktori, Lokasi kerja, Akun - semua memuat. Tanpa error konsol.
TEMUAN: (1) Foto profil hr@ rusak: avatar menampilkan teks alt "Uji HR GA" meluber di halaman Akun dan sidebar (gambar gagal dimuat; ada tombol "Ganti foto"/"Hapus foto"). office@ & finance@ tanpa foto = inisial rapi. (2) Popup K3 wajib (native modal) membuat elemen lain inert: tombol Keluar dan tombol "Tambah karyawan" (hr Direktori) tidak merespons klik sebelum popup dikonfirmasi; modal hr/office/finance TIDAK bisa diuji (bukan bug pasti, akibat gate). (3) Logout via klik gagal saat popup aktif; logout lewat JS click berhasil dan juga mengeluarkan tab 125549879 (sesi cookie bersama), tab itu kini di halaman Masuk. (4) Halaman muat lambat (3-10 dtk, Vite dev). (5) Badge notifikasi "99+" pada lonceng.
BELUM: modal hr/office/finance, tes mobile 390px.
