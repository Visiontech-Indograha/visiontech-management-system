# Laporan E2E Multi-Role Lengkap

Tanggal: 2026-11-03. Web: Chrome (desktop 1536x655). Mobile: HP fisik via ADB (APK dev `com.visiontech.vms_mobile.dev`). Data: DB dev lokal.

## 1. Matriks kelayakan per role

| Role | Web (Chrome) | Mobile (HP fisik) | Peta & foto survei | Modal global |
|---|---|---|---|---|
| Super Admin | Lulus | Tidak diuji di HP (akun kantor, login HP ditolak sesuai desain) | Peta+marker terverifikasi | Lebar adaptif terverifikasi pada modal yang dibuka |
| PM (Project Manager) | Lulus (peta, 2 marker, popup marker) | Login HP ditolak sesuai desain | Peta+marker terverifikasi | Lebar adaptif terverifikasi pada modal yang dibuka |
| OM (Operational Manager) | Lulus (setelah konfirmasi K3) | Login HP ditolak | Tidak ada akses modul survei | Lebar adaptif terverifikasi pada modal yang dibuka |
| Employee / Ketua Tim (lapangan) | Akun lapangan tidak login web | Lulus; peta survei 3 titik; gudang tertahan gerbang wajah | Peta+marker terverifikasi | Lebar adaptif terverifikasi pada modal yang dibuka |
| HSE | Lulus; modal kampanye & audit pembaca diuji | Login HP ditolak | Tidak ada akses modul survei | Lebar adaptif terverifikasi pada modal yang dibuka |
| AdminGR (ADMIN_HR_GA) | Menu lulus; modal belum teruji (popup K3) | Login HP ditolak | Tidak ada akses modul survei | Lebar adaptif terverifikasi pada modal yang dibuka |
| Finance | Menu lulus; modal belum teruji (popup K3) | Login HP ditolak | Tidak ada akses modul survei | Lebar adaptif terverifikasi pada modal yang dibuka |

Catatan jujur: popup wajib K3 memblokir klik untuk HR/Office/Finance, sehingga modal mereka belum teruji; viewport web-mobile 390px tidak bisa diatur; foto di popup marker belum terverifikasi dengan data nyata karena DB dev tidak punya foto titik survei (0 dari 15).

## 2. Analisis per role

### Super Admin

- Web: Lulus
- Mobile: Tidak diuji di HP (akun kantor, login HP ditolak sesuai desain)

**SUPER_ADMIN/web_audit_log**

![web_audit_log](screenshots/SUPER_ADMIN/web_audit_log.png)

**SUPER_ADMIN/web_dashboard**

![web_dashboard](screenshots/SUPER_ADMIN/web_dashboard.png)

**SUPER_ADMIN/web_k3_hse**

![web_k3_hse](screenshots/SUPER_ADMIN/web_k3_hse.png)

**SUPER_ADMIN/web_kendaraan_alat**

![web_kendaraan_alat](screenshots/SUPER_ADMIN/web_kendaraan_alat.png)

**SUPER_ADMIN/web_lokasi_kerja**

![web_lokasi_kerja](screenshots/SUPER_ADMIN/web_lokasi_kerja.png)

**SUPER_ADMIN/web_wo_detail_modal**

![web_wo_detail_modal](screenshots/SUPER_ADMIN/web_wo_detail_modal.png)

### PM (Project Manager)

- Web: Lulus (peta, 2 marker, popup marker)
- Mobile: Login HP ditolak sesuai desain

**PM/web_absensi**

![web_absensi](screenshots/PM/web_absensi.png)

**PM/web_alokasi_mingguan**

![web_alokasi_mingguan](screenshots/PM/web_alokasi_mingguan.png)

**PM/web_jadwal_harian**

![web_jadwal_harian](screenshots/PM/web_jadwal_harian.png)

**PM/web_klien**

![web_klien](screenshots/PM/web_klien.png)

**PM/web_mess**

![web_mess](screenshots/PM/web_mess.png)

**PM/web_wo_detail_modal_bawah**

![web_wo_detail_modal_bawah](screenshots/PM/web_wo_detail_modal_bawah.png)

**PM/web_wo_detail_modal_peta**

![web_wo_detail_modal_peta](screenshots/PM/web_wo_detail_modal_peta.png)

**PM/web_wo_list**

![web_wo_list](screenshots/PM/web_wo_list.png)

**PM/web_wo_marker_popup**

![web_wo_marker_popup](screenshots/PM/web_wo_marker_popup.png)

**pm1/mobile_login_ditolak**

![mobile_login_ditolak](screenshots/pm1/mobile_login_ditolak.png)

### OM (Operational Manager)

- Web: Lulus (setelah konfirmasi K3)
- Mobile: Login HP ditolak

**OM/web_absensi**

![web_absensi](screenshots/OM/web_absensi.png)

**OM/web_akun_keamanan**

![web_akun_keamanan](screenshots/OM/web_akun_keamanan.png)

**OM/web_alokasi**

![web_alokasi](screenshots/OM/web_alokasi.png)

**OM/web_beranda_setelah_baca**

![web_beranda_setelah_baca](screenshots/OM/web_beranda_setelah_baca.png)

**OM/web_cuti**

![web_cuti](screenshots/OM/web_cuti.png)

**OM/web_dashboard_diblokir_popup**

![web_dashboard_diblokir_popup](screenshots/OM/web_dashboard_diblokir_popup.png)

**OM/web_jadwal**

![web_jadwal](screenshots/OM/web_jadwal.png)

**OM/web_klien**

![web_klien](screenshots/OM/web_klien.png)

**OM/web_rekap**

![web_rekap](screenshots/OM/web_rekap.png)

**OM/web_tim**

![web_tim](screenshots/OM/web_tim.png)

**OM/web_tugas_wo**

![web_tugas_wo](screenshots/OM/web_tugas_wo.png)

### Employee / Ketua Tim (lapangan)

- Web: Akun lapangan tidak login web
- Mobile: Lulus; peta survei 3 titik; gudang tertahan gerbang wajah

**ketua11/mobile_detail_titik_tanpa_foto**

![mobile_detail_titik_tanpa_foto](screenshots/ketua11/mobile_detail_titik_tanpa_foto.png)

**ketua11/mobile_foto_profil**

![mobile_foto_profil](screenshots/ketua11/mobile_foto_profil.png)

**ketua11/mobile_foto_profil_beranda_restart**

![mobile_foto_profil_beranda_restart](screenshots/ketua11/mobile_foto_profil_beranda_restart.png)

**ketua11/mobile_foto_profil_dihapus**

![mobile_foto_profil_dihapus](screenshots/ketua11/mobile_foto_profil_dihapus.png)

**ketua11/mobile_foto_profil_setelah_restart**

![mobile_foto_profil_setelah_restart](screenshots/ketua11/mobile_foto_profil_setelah_restart.png)

**ketua11/mobile_galeri**

![mobile_galeri](screenshots/ketua11/mobile_galeri.png)

**ketua11/mobile_kartu_titik_tanpa_foto**

![mobile_kartu_titik_tanpa_foto](screenshots/ketua11/mobile_kartu_titik_tanpa_foto.png)

**ketua11/mobile_laporan_harian_sesudah_perbaikan**

![mobile_laporan_harian_sesudah_perbaikan](screenshots/ketua11/mobile_laporan_harian_sesudah_perbaikan.png)

**ketua11/mobile_m_ajukan_cuti**

![mobile_m_ajukan_cuti](screenshots/ketua11/mobile_m_ajukan_cuti.png)

**ketua11/mobile_m_ajukan_mess**

![mobile_m_ajukan_mess](screenshots/ketua11/mobile_m_ajukan_mess.png)

**ketua11/mobile_m_ajukan_pinjam**

![mobile_m_ajukan_pinjam](screenshots/ketua11/mobile_m_ajukan_pinjam.png)

**ketua11/mobile_m_keluar_dialog**

![mobile_m_keluar_dialog](screenshots/ketua11/mobile_m_keluar_dialog.png)

**ketua11/mobile_m_lokasi_kerja**

![mobile_m_lokasi_kerja](screenshots/ketua11/mobile_m_lokasi_kerja.png)

**ketua11/mobile_m_unggah_dok**

![mobile_m_unggah_dok](screenshots/ketua11/mobile_m_unggah_dok.png)

**ketua11/mobile_notifikasi**

![mobile_notifikasi](screenshots/ketua11/mobile_notifikasi.png)

**ketua11/mobile_profil**

![mobile_profil](screenshots/ketua11/mobile_profil.png)

**ketua11/mobile_profil_Cuti**

![mobile_profil_Cuti](screenshots/ketua11/mobile_profil_Cuti.png)

**ketua11/mobile_profil_Dokumen_Saya**

![mobile_profil_Dokumen_Saya](screenshots/ketua11/mobile_profil_Dokumen_Saya.png)

**ketua11/mobile_profil_Kendaraan**

![mobile_profil_Kendaraan](screenshots/ketua11/mobile_profil_Kendaraan.png)

**ketua11/mobile_profil_Mess**

![mobile_profil_Mess](screenshots/ketua11/mobile_profil_Mess.png)

**ketua11/mobile_profil_Rekap_Absen**

![mobile_profil_Rekap_Absen](screenshots/ketua11/mobile_profil_Rekap_Absen.png)

**ketua11/mobile_profil_Riwayat_Lembur**

![mobile_profil_Riwayat_Lembur](screenshots/ketua11/mobile_profil_Riwayat_Lembur.png)

**ketua11/mobile_profil_bawah**

![mobile_profil_bawah](screenshots/ketua11/mobile_profil_bawah.png)

**ketua11/mobile_rencana**

![mobile_rencana](screenshots/ketua11/mobile_rencana.png)

**ketua11/mobile_rencana_kartu**

![mobile_rencana_kartu](screenshots/ketua11/mobile_rencana_kartu.png)

**ketua11/mobile_sesi_login**

![mobile_sesi_login](screenshots/ketua11/mobile_sesi_login.png)

**ketua11/mobile_sesi_login_konfirmasi**

![mobile_sesi_login_konfirmasi](screenshots/ketua11/mobile_sesi_login_konfirmasi.png)

**ketua11/mobile_survei_detail**

![mobile_survei_detail](screenshots/ketua11/mobile_survei_detail.png)

**ketua11/mobile_survei_peta**

![mobile_survei_peta](screenshots/ketua11/mobile_survei_peta.png)

**ketua11/mobile_survei_titik**

![mobile_survei_titik](screenshots/ketua11/mobile_survei_titik.png)

**anggota111/mobile_absensi**

![mobile_absensi](screenshots/anggota111/mobile_absensi.png)

**anggota111/mobile_galeri**

![mobile_galeri](screenshots/anggota111/mobile_galeri.png)

**anggota111/mobile_home**

![mobile_home](screenshots/anggota111/mobile_home.png)

**anggota111/mobile_m_dialog_sidik_jari**

![mobile_m_dialog_sidik_jari](screenshots/anggota111/mobile_m_dialog_sidik_jari.png)

**anggota111/mobile_m_ubah_penjelasan**

![mobile_m_ubah_penjelasan](screenshots/anggota111/mobile_m_ubah_penjelasan.png)

**anggota111/mobile_profil**

![mobile_profil](screenshots/anggota111/mobile_profil.png)

**anggota111/mobile_rencana**

![mobile_rencana](screenshots/anggota111/mobile_rencana.png)

**bayu/mobile_absensi**

![mobile_absensi](screenshots/bayu/mobile_absensi.png)

**bayu/mobile_galeri**

![mobile_galeri](screenshots/bayu/mobile_galeri.png)

**bayu/mobile_profil**

![mobile_profil](screenshots/bayu/mobile_profil.png)

**bayu/mobile_rencana**

![mobile_rencana](screenshots/bayu/mobile_rencana.png)

**gudang/mobile_gate_daftar_wajah**

![mobile_gate_daftar_wajah](screenshots/gudang/mobile_gate_daftar_wajah.png)

**login/mobile_login**

![mobile_login](screenshots/login/mobile_login.png)

### HSE

- Web: Lulus; modal kampanye & audit pembaca diuji
- Mobile: Login HP ditolak

**HSE/mobile_login_ditolak**

![mobile_login_ditolak](screenshots/HSE/mobile_login_ditolak.png)

**HSE/web_absensi**

![web_absensi](screenshots/HSE/web_absensi.png)

**HSE/web_akun_keamanan**

![web_akun_keamanan](screenshots/HSE/web_akun_keamanan.png)

**HSE/web_aset**

![web_aset](screenshots/HSE/web_aset.png)

**HSE/web_beranda**

![web_beranda](screenshots/HSE/web_beranda.png)

**HSE/web_berkas**

![web_berkas](screenshots/HSE/web_berkas.png)

**HSE/web_cuti**

![web_cuti](screenshots/HSE/web_cuti.png)

**HSE/web_dashboard_popup_k3**

![web_dashboard_popup_k3](screenshots/HSE/web_dashboard_popup_k3.png)

**HSE/web_direktori**

![web_direktori](screenshots/HSE/web_direktori.png)

**HSE/web_jadwal**

![web_jadwal](screenshots/HSE/web_jadwal.png)

**HSE/web_jadwal_diblokir_popup**

![web_jadwal_diblokir_popup](screenshots/HSE/web_jadwal_diblokir_popup.png)

**HSE/web_k3_kampanye**

![web_k3_kampanye](screenshots/HSE/web_k3_kampanye.png)

**HSE/web_k3_kampanye_modal**

![web_k3_kampanye_modal](screenshots/HSE/web_k3_kampanye_modal.png)

**HSE/web_modal_audit_pembaca**

![web_modal_audit_pembaca](screenshots/HSE/web_modal_audit_pembaca.png)

**HSE/web_modal_terbitkan**

![web_modal_terbitkan](screenshots/HSE/web_modal_terbitkan.png)

**HSE/web_popup_k3_detail**

![web_popup_k3_detail](screenshots/HSE/web_popup_k3_detail.png)

**HSE/web_rekap**

![web_rekap](screenshots/HSE/web_rekap.png)

**hse/mobile_login_ditolak**

![mobile_login_ditolak](screenshots/hse/mobile_login_ditolak.png)

**hse/web_absensi**

![web_absensi](screenshots/hse/web_absensi.png)

**hse/web_akun_keamanan**

![web_akun_keamanan](screenshots/hse/web_akun_keamanan.png)

**hse/web_aset**

![web_aset](screenshots/hse/web_aset.png)

**hse/web_beranda**

![web_beranda](screenshots/hse/web_beranda.png)

**hse/web_berkas**

![web_berkas](screenshots/hse/web_berkas.png)

**hse/web_cuti**

![web_cuti](screenshots/hse/web_cuti.png)

**hse/web_dashboard_popup_k3**

![web_dashboard_popup_k3](screenshots/hse/web_dashboard_popup_k3.png)

**hse/web_direktori**

![web_direktori](screenshots/hse/web_direktori.png)

**hse/web_jadwal**

![web_jadwal](screenshots/hse/web_jadwal.png)

**hse/web_jadwal_diblokir_popup**

![web_jadwal_diblokir_popup](screenshots/hse/web_jadwal_diblokir_popup.png)

**hse/web_k3_kampanye**

![web_k3_kampanye](screenshots/hse/web_k3_kampanye.png)

**hse/web_k3_kampanye_modal**

![web_k3_kampanye_modal](screenshots/hse/web_k3_kampanye_modal.png)

**hse/web_modal_audit_pembaca**

![web_modal_audit_pembaca](screenshots/hse/web_modal_audit_pembaca.png)

**hse/web_modal_terbitkan**

![web_modal_terbitkan](screenshots/hse/web_modal_terbitkan.png)

**hse/web_popup_k3_detail**

![web_popup_k3_detail](screenshots/hse/web_popup_k3_detail.png)

**hse/web_rekap**

![web_rekap](screenshots/hse/web_rekap.png)

### AdminGR (ADMIN_HR_GA)

- Web: Menu lulus; modal belum teruji (popup K3)
- Mobile: Login HP ditolak

**ADMIN_HR_GA/web_hr_absensi**

![web_hr_absensi](screenshots/ADMIN_HR_GA/web_hr_absensi.png)

**ADMIN_HR_GA/web_hr_akun_keamanan**

![web_hr_akun_keamanan](screenshots/ADMIN_HR_GA/web_hr_akun_keamanan.png)

**ADMIN_HR_GA/web_hr_aset**

![web_hr_aset](screenshots/ADMIN_HR_GA/web_hr_aset.png)

**ADMIN_HR_GA/web_hr_beranda_dim**

![web_hr_beranda_dim](screenshots/ADMIN_HR_GA/web_hr_beranda_dim.png)

**ADMIN_HR_GA/web_hr_berkas**

![web_hr_berkas](screenshots/ADMIN_HR_GA/web_hr_berkas.png)

**ADMIN_HR_GA/web_hr_cuti**

![web_hr_cuti](screenshots/ADMIN_HR_GA/web_hr_cuti.png)

**ADMIN_HR_GA/web_hr_direktori**

![web_hr_direktori](screenshots/ADMIN_HR_GA/web_hr_direktori.png)

**ADMIN_HR_GA/web_hr_direktori_klik_tambah**

![web_hr_direktori_klik_tambah](screenshots/ADMIN_HR_GA/web_hr_direktori_klik_tambah.png)

**ADMIN_HR_GA/web_hr_jadwal**

![web_hr_jadwal](screenshots/ADMIN_HR_GA/web_hr_jadwal.png)

**ADMIN_HR_GA/web_hr_mess**

![web_hr_mess](screenshots/ADMIN_HR_GA/web_hr_mess.png)

**ADMIN_HR_GA/web_hr_offboarding**

![web_hr_offboarding](screenshots/ADMIN_HR_GA/web_hr_offboarding.png)

**ADMIN_HR_GA/web_hr_popup_k3_wajib**

![web_hr_popup_k3_wajib](screenshots/ADMIN_HR_GA/web_hr_popup_k3_wajib.png)

**ADMIN_HR_GA/web_hr_rekap**

![web_hr_rekap](screenshots/ADMIN_HR_GA/web_hr_rekap.png)

**ADMIN_HR_GA/web_hr_tim**

![web_hr_tim](screenshots/ADMIN_HR_GA/web_hr_tim.png)

**ADMIN_HR_GA/web_office_akun_keamanan**

![web_office_akun_keamanan](screenshots/ADMIN_HR_GA/web_office_akun_keamanan.png)

**ADMIN_HR_GA/web_office_aset**

![web_office_aset](screenshots/ADMIN_HR_GA/web_office_aset.png)

**ADMIN_HR_GA/web_office_beranda**

![web_office_beranda](screenshots/ADMIN_HR_GA/web_office_beranda.png)

**ADMIN_HR_GA/web_office_mess**

![web_office_mess](screenshots/ADMIN_HR_GA/web_office_mess.png)

**hr/mobile_login_ditolak**

![mobile_login_ditolak](screenshots/hr/mobile_login_ditolak.png)

### Finance

- Web: Menu lulus; modal belum teruji (popup K3)
- Mobile: Login HP ditolak

**finance/mobile_login_ditolak**

![mobile_login_ditolak](screenshots/finance/mobile_login_ditolak.png)

**finance/web_absensi**

![web_absensi](screenshots/finance/web_absensi.png)

**finance/web_akun_keamanan**

![web_akun_keamanan](screenshots/finance/web_akun_keamanan.png)

**finance/web_aset**

![web_aset](screenshots/finance/web_aset.png)

**finance/web_beranda**

![web_beranda](screenshots/finance/web_beranda.png)

**finance/web_berkas**

![web_berkas](screenshots/finance/web_berkas.png)

**finance/web_cuti**

![web_cuti](screenshots/finance/web_cuti.png)

**finance/web_direktori**

![web_direktori](screenshots/finance/web_direktori.png)

**finance/web_jadwal**

![web_jadwal](screenshots/finance/web_jadwal.png)

**finance/web_lokasi**

![web_lokasi](screenshots/finance/web_lokasi.png)

**finance/web_rekap**

![web_rekap](screenshots/finance/web_rekap.png)

**finance/web_rekap_lembur**

![web_rekap_lembur](screenshots/finance/web_rekap_lembur.png)

## 3. Log teknis

### Perbaikan kode
- web/SurveyLayoutMap.tsx: fitBounds hanya saat jumlah titik berubah (peta tidak loncat saat marker digeser).
- web/WorkOrderSurveyReviewModal.tsx: foto titik (file_id) dimuat via useFileUrl, popup marker + galeri.
- web/RouteGuards, RequireAccess, pageTitle, 3 tes: /forbidden -> /403.
- web/routes.tsx: RequireAccess dikembalikan untuk /directory/:id (view:users) dan /surveys/:surveyId (create:plan).
- web/VmsDialog.tsx: ukuran default `auto` (lebar mengikuti isi, 36rem..96vw).
- web/atoms/Avatar.tsx: fallback inisial bila foto gagal dimuat.
- mobile/vms_api.dart: imageRequirements memakai photos dari /work-types (endpoint lama dihapus); tes diperbarui.
- mobile/vms_ui.dart, vms_theme.dart: lebar sheet/dialog adaptif (maks 960/880).
- mobile/daily_plan_screen.dart: dialog Laporan harian lebar penuh, label tidak terpotong.
- mobile/sessions_screen.dart (baru) + profile_screen.dart + vms_api.dart: layar Perangkat yang masuk (lihat/cabut sesi).
- mobile/survey_point_screen.dart, survey_screen.dart: placeholder "Tidak ada foto".

### Verifikasi
- web: tsc -b bersih; vitest 400 tes (2 gagal sementara karena beban, lulus saat diulang); apiTypes sinkron. Lint: 128 error arsitektur (atomic design) di file yang tidak diubah sesi ini (mis. WorkOrdersTemplate).
- mobile: flutter analyze bersih untuk file yang diubah; screens_test 32 lulus. Suite penuh sebelum perbaikan tes: 2 gagal (sudah diperbaiki).
- api: tidak diubah; pytest tidak dijalankan (aturan: hanya atas perintah).

### Temuan terbuka
- Isi kampanye K3 tampil sebagai HTML mentah (data uji berisi tag; kolom isi teks biasa).
- Foto profil seed lama: path `/uploads/profiles/*` tanpa file_object; beberapa file_object tanpa berkas di MinIO (mis. hr@) -> inisial tampil.
- APK terpasang belum memuat penghapusan judul ganda di Profil (perlu rebuild).
- Modal HR/Office/Finance dan viewport 390px web belum teruji.

## Lampiran: catatan mentah

### hasil_web.md

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


### hasil_mobile.md

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


### hasil_mobile_lanjutan.md

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


## 4. Pembaruan perbaikan (sesi lanjutan)

Status akhir temuan sebelumnya:
- Foto titik survei: DIVERIFIKASI di Chrome (login pm1) - popup marker menampilkan foto uji; bukti `screenshots/PM/web_foto_titik_popup.jpg`. Galeri/lightbox belum diklik.
- Pencabutan sesi mobile: DIVERIFIKASI di HP (sesi curl muncul, dicabut, token ditolak 401).
- Modal HR/Office/Finance: DIVERIFIKASI (HR 23, Office 8, Finance 5 screenshot); tidak ada modal terpotong.
- Viewport 390px (iframe 390x650): PM Review Survei, HR Tambah karyawan, Finance Ajukan cuti tampil sebagai bottom-sheet, tidak terpotong.
- Akun gudang: gerbang wajah lolos karena FACE_FAKE_MODE=true di dev; wajah palsu dihapus lagi dari DB.
- APK dev dibangun ulang dan terpasang (judul ganda Profil hilang; ikon status bar gerbang wajah diperbaiki).
- K3: isi kampanye tampil sebagai teks rapi (lib/htmlToText.ts, 4 tes).
- Foto profil: 7 akun uji diunggah foto via API resmi (hr, pm1, randi.om, hendrik.pm, dian.pm, siti.hr, agus.tl); avatar gagal-muat kini jatuh ke inisial.
- Lint web: 0 error (HseCampaignsTemplate dipindah ke organisms/hse/HseCampaignsPanel.tsx; WorkOrderCreateAction baru). tsc bersih; build sukses; vitest 403/404 (1 flaky beban, lulus ulang).
- Logo cap foto mobile: kotak 96x30 -> 156x56 (Visiontech 94, tim 56, render 3x). Terlihat ~2x lebih besar di pratinjau kamera.

Masih terbuka: logo tim uji tampil sebagai kotak tipis (kemungkinan berkas logo uji; belum diperiksa); sisa catatan mentah di hasil_web_perbaikan.md, hasil_web_perbaikan2.md, hasil_mobile_perbaikan.md (lampiran di bawah).

### hasil_web_perbaikan.md

# Hasil uji web perbaikan (sebagian; terblokir di tengah jalan)

## A) Foto titik survei WO-202611-003
- Dua PNG uji diunggah lewat POST /files/upload (token pm1@uji-nyata.test): file_id e4fc413d-b33e-4199-ba34-7eb67a2e5361 dan 2929fe36-56ab-46db-9180-1c680847641c.
- Route resmi pengisi work_order_survey_points: POST /work-orders/{id}/submit-survey (SurveyPointIn.photos = larik objek bebas). Dikirim ulang dengan 2 titik yang sama + photos [{file_id, slot}]. Tabel kini berisi photos_json terisi untuk titik A dan B (status TODO; id titik baru karena submit membuat ulang titik).
- Catatan: PUT /work-plans/surveys/points/{id} (skema PointPhoto butuh requirement_id) menulis ke work_plan_item, BUKAN work_order_survey_points; jadi bukan jalur untuk WO review.
- Web membaca: usePointPhotoUrl menerima string / {url|file_url|file_id|id}; file_id UUID diubah jadi URL bertiket via useFileUrl. Format {file_id,slot} sesuai, seharusnya tampil. BELUM DIVERIFIKASI di browser (popup marker, galeri, lightbox).

## B) Foto profil via API resmi
- PUT /employees/me/photo dengan file_id hasil upload: hr@uji-nyata.test (79faf317-2630-460c-9850-2e0031a09618), pm1@uji-nyata.test (a04248be-d772-4586-b266-815e344f45ee). Respons 200.
- Akun berpath lama (/uploads/profiles/*.jpg: randi.om@, hendrik.pm@, dian.pm@, siti.hr@, agus.tl@, riko.tech@, doni.tech@, fajar.tech@, bayu.tech@, ilham.tech@ visiontech.co.id) TIDAK diubah: sandi tidak diketahui (dilarang menebak).
- Verifikasi tampilan di web (Akun & sidebar) belum dilakukan.

## C) Modal Finance (Chrome, selesai); HR/Office belum
Screenshot di e2e-reports/screenshots/FINANCE/ (.jpg): web_modal_cuti_ajukan, web_modal_aset_berkas, web_modal_lokasi_tambah, web_modal_absensi_tinjau, web_modal_konfirmasi_keluar.
- Semua modal muat di viewport 1536x711, tidak terpotong; Lokasi kerja (tinggi 620px) menggulir di dalam.
- Direktori untuk Finance hanya baca (tanpa Tambah/profil modal). Rekap lembur, Berkas saya tanpa modal.
- Temuan kecil: modal Berkas aset punya tombol ganda "Batal" dan "Tutup".
- Tab Chrome sendiri (id 125549909) TIDAK sempat ditutup (ekstensi Chrome terputus); mohon tutup manual.
- Baris hse_campaign_acknowledgments buatan uji (finance@ 08:36, hr@ 08:47 UTC) sudah dihapus.
- Server Vite web (port 5173) saya jalankan karena mati; masih berjalan.

## D) Viewport 390px: BELUM DIKERJAKAN
Penyebab: Playwright MCP mengunci profil browser (Chrome milik sesi ini, pid 1164, tak bisa dilepas; percobaan menutupnya ditolak sistem izin). Modal HR (Direktori tambah, Cuti, Aset, Mess, Offboarding, Tim, Berkas) dan Office belum dibuka.


### hasil_web_perbaikan2.md

# Hasil uji web perbaikan 2

## 1) Modal HR/Office (desktop 1536x655)
Screenshot: e2e-reports/screenshots/ADMIN_HR_GA/web_modal_*.jpg (23 berkas), OFFICE/web_modal_*.jpg (8).
Dibuka (tanpa submit): Direktori (Tambah karyawan, profil Budi Santoso halaman penuh, Ubah data, Offboarding dari profil), Cuti Ajukan, Aset (Tambah alat, Tambah kendaraan, Setujui & serahkan, Berkas, Status, Serahkan), Mess (Tempatkan, Selesai inap), Offboarding (Ajukan, Mulai, detail Doni), Absensi Tinjau, Tim (Tambah, Anggota & kontak), Berkas saya (Tambah, Perbarui). Office: Direktori tambah, Cuti, Aset alat/berkas/serahkan, Mess, Offboarding, Tim tambah. Office identik dengan HR.
Temuan:
- Tidak ada modal terpotong; modal tinggi (Tambah karyawan/alat/kendaraan/Serahkan/Tinjau) menggulir di dalam, tombol Batal/Simpan tetap terlihat.
- BUG: tombol "Nonaktifkan" di Berkas saya memakai window.confirm() bawaan browser (bukan modal VMS); dialog native ini membekukan tab (otomasi macet) dan tak seragam dengan modal lain. Tab terpaksa ditutup; dokumen tidak berubah.
- Tombol "Setujui/Tolak" (Mess permintaan, Aset pinjam) tidak diklik (bisa langsung mengeksekusi).
- Lokasi kerja (/sites) tidak ada untuk HR/Office (403, wajar).
- Tim "Anggota & kontak": banyak anggota "belum ada nomor HP" (data uji).
- Profil karyawan = halaman, bukan modal.

## 2) Viewport 390px (iframe overlay 390x650)
- PM: WO-202611-003 > Review Survei: PM/web390_review_survei.jpg. Bottom-sheet, rapi, tidak terpotong, peta dan konten menggulir. Popup K3 juga bottom-sheet.
- HR: Direktori > Tambah karyawan: ADMIN_HR_GA/web390_direktori_tambah.jpg. Bottom-sheet, tombol Simpan/Batal penuh lebar di bawah, isi menggulir.
- Finance: Cuti > Ajukan: FINANCE/web390_cuti_ajukan.jpg. Bottom-sheet, rapi, tombol penuh lebar.
- Temuan: tidak ada masalah. Catatan: tinggi iframe 650 (layar uji pendek), lebar 390 sesuai.

## 3) Foto profil akun seed lama (data uji, file gambar = PM/web_absensi.png)
Diubah via POST /files/upload + PUT /employees/me/photo (200): randi.om, hendrik.pm, dian.pm, siti.hr, agus.tl @visiontech.co.id.
Akun kantor butuh "platform":"web" (mobile ditolak NOT_FIELD_STAFF); agus.tl via mobile.
Verifikasi web: login siti.hr, avatar tampil di sidebar (ADMIN_HR_GA/web_foto_profil_siti_sidebar.jpg).

## Pembersihan
hse_campaign_acknowledgments milik hr@, office@, pm1@, finance@, siti.hr dihapus. Tab Chrome ditutup.


### hasil_mobile_perbaikan.md

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


## 5. Galeri tambahan

**ADMIN_HR_GA/web390_direktori_tambah.jpg**

![web390_direktori_tambah.jpg](screenshots/ADMIN_HR_GA/web390_direktori_tambah.jpg)

**ADMIN_HR_GA/web_foto_profil_siti_sidebar.jpg**

![web_foto_profil_siti_sidebar.jpg](screenshots/ADMIN_HR_GA/web_foto_profil_siti_sidebar.jpg)

**ADMIN_HR_GA/web_modal_absensi_tinjau.jpg**

![web_modal_absensi_tinjau.jpg](screenshots/ADMIN_HR_GA/web_modal_absensi_tinjau.jpg)

**ADMIN_HR_GA/web_modal_aset_berkas.jpg**

![web_modal_aset_berkas.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_berkas.jpg)

**ADMIN_HR_GA/web_modal_aset_serahkan.jpg**

![web_modal_aset_serahkan.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_serahkan.jpg)

**ADMIN_HR_GA/web_modal_aset_setujui_serahkan.jpg**

![web_modal_aset_setujui_serahkan.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_setujui_serahkan.jpg)

**ADMIN_HR_GA/web_modal_aset_status.jpg**

![web_modal_aset_status.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_status.jpg)

**ADMIN_HR_GA/web_modal_aset_tambah_alat.jpg**

![web_modal_aset_tambah_alat.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_tambah_alat.jpg)

**ADMIN_HR_GA/web_modal_aset_tambah_kendaraan.jpg**

![web_modal_aset_tambah_kendaraan.jpg](screenshots/ADMIN_HR_GA/web_modal_aset_tambah_kendaraan.jpg)

**ADMIN_HR_GA/web_modal_berkas_perbarui.jpg**

![web_modal_berkas_perbarui.jpg](screenshots/ADMIN_HR_GA/web_modal_berkas_perbarui.jpg)

**ADMIN_HR_GA/web_modal_berkas_perbarui.png**

![web_modal_berkas_perbarui.png](screenshots/ADMIN_HR_GA/web_modal_berkas_perbarui.png)

**ADMIN_HR_GA/web_modal_berkas_setelah_nonaktifkan.jpg**

![web_modal_berkas_setelah_nonaktifkan.jpg](screenshots/ADMIN_HR_GA/web_modal_berkas_setelah_nonaktifkan.jpg)

**ADMIN_HR_GA/web_modal_berkas_tambah.jpg**

![web_modal_berkas_tambah.jpg](screenshots/ADMIN_HR_GA/web_modal_berkas_tambah.jpg)

**ADMIN_HR_GA/web_modal_berkas_tambah.png**

![web_modal_berkas_tambah.png](screenshots/ADMIN_HR_GA/web_modal_berkas_tambah.png)

**ADMIN_HR_GA/web_modal_cuti_ajukan.jpg**

![web_modal_cuti_ajukan.jpg](screenshots/ADMIN_HR_GA/web_modal_cuti_ajukan.jpg)

**ADMIN_HR_GA/web_modal_direktori_profil.jpg**

![web_modal_direktori_profil.jpg](screenshots/ADMIN_HR_GA/web_modal_direktori_profil.jpg)

**ADMIN_HR_GA/web_modal_direktori_tambah.jpg**

![web_modal_direktori_tambah.jpg](screenshots/ADMIN_HR_GA/web_modal_direktori_tambah.jpg)

**ADMIN_HR_GA/web_modal_direktori_ubah_data.jpg**

![web_modal_direktori_ubah_data.jpg](screenshots/ADMIN_HR_GA/web_modal_direktori_ubah_data.jpg)

**ADMIN_HR_GA/web_modal_mess_permintaan.jpg**

![web_modal_mess_permintaan.jpg](screenshots/ADMIN_HR_GA/web_modal_mess_permintaan.jpg)

**ADMIN_HR_GA/web_modal_mess_selesai_inap.jpg**

![web_modal_mess_selesai_inap.jpg](screenshots/ADMIN_HR_GA/web_modal_mess_selesai_inap.jpg)

**ADMIN_HR_GA/web_modal_mess_tempatkan.jpg**

![web_modal_mess_tempatkan.jpg](screenshots/ADMIN_HR_GA/web_modal_mess_tempatkan.jpg)

**ADMIN_HR_GA/web_modal_offboarding_ajukan.jpg**

![web_modal_offboarding_ajukan.jpg](screenshots/ADMIN_HR_GA/web_modal_offboarding_ajukan.jpg)

**ADMIN_HR_GA/web_modal_offboarding_detail.jpg**

![web_modal_offboarding_detail.jpg](screenshots/ADMIN_HR_GA/web_modal_offboarding_detail.jpg)

**ADMIN_HR_GA/web_modal_offboarding_mulai.jpg**

![web_modal_offboarding_mulai.jpg](screenshots/ADMIN_HR_GA/web_modal_offboarding_mulai.jpg)

**ADMIN_HR_GA/web_modal_profil_offboarding.jpg**

![web_modal_profil_offboarding.jpg](screenshots/ADMIN_HR_GA/web_modal_profil_offboarding.jpg)

**ADMIN_HR_GA/web_modal_tim_anggota.jpg**

![web_modal_tim_anggota.jpg](screenshots/ADMIN_HR_GA/web_modal_tim_anggota.jpg)

**ADMIN_HR_GA/web_modal_tim_anggota_kontak.png**

![web_modal_tim_anggota_kontak.png](screenshots/ADMIN_HR_GA/web_modal_tim_anggota_kontak.png)

**ADMIN_HR_GA/web_modal_tim_tambah.jpg**

![web_modal_tim_tambah.jpg](screenshots/ADMIN_HR_GA/web_modal_tim_tambah.jpg)

**OFFICE/web_modal_aset_berkas.jpg**

![web_modal_aset_berkas.jpg](screenshots/OFFICE/web_modal_aset_berkas.jpg)

**OFFICE/web_modal_aset_serahkan.jpg**

![web_modal_aset_serahkan.jpg](screenshots/OFFICE/web_modal_aset_serahkan.jpg)

**OFFICE/web_modal_aset_tambah_alat.jpg**

![web_modal_aset_tambah_alat.jpg](screenshots/OFFICE/web_modal_aset_tambah_alat.jpg)

**OFFICE/web_modal_cuti_ajukan.jpg**

![web_modal_cuti_ajukan.jpg](screenshots/OFFICE/web_modal_cuti_ajukan.jpg)

**OFFICE/web_modal_direktori_tambah.jpg**

![web_modal_direktori_tambah.jpg](screenshots/OFFICE/web_modal_direktori_tambah.jpg)

**OFFICE/web_modal_mess_tempatkan.jpg**

![web_modal_mess_tempatkan.jpg](screenshots/OFFICE/web_modal_mess_tempatkan.jpg)

**OFFICE/web_modal_offboarding_mulai.jpg**

![web_modal_offboarding_mulai.jpg](screenshots/OFFICE/web_modal_offboarding_mulai.jpg)

**OFFICE/web_modal_tim_tambah.jpg**

![web_modal_tim_tambah.jpg](screenshots/OFFICE/web_modal_tim_tambah.jpg)

**PM/web390_review_survei.jpg**

![web390_review_survei.jpg](screenshots/PM/web390_review_survei.jpg)

**PM/web_foto_titik_popup.jpg**

![web_foto_titik_popup.jpg](screenshots/PM/web_foto_titik_popup.jpg)

**finance/web390_cuti_ajukan.jpg**

![web390_cuti_ajukan.jpg](screenshots/finance/web390_cuti_ajukan.jpg)

**finance/web_modal_absensi_tinjau.jpg**

![web_modal_absensi_tinjau.jpg](screenshots/finance/web_modal_absensi_tinjau.jpg)

**finance/web_modal_aset_berkas.jpg**

![web_modal_aset_berkas.jpg](screenshots/finance/web_modal_aset_berkas.jpg)

**finance/web_modal_cuti_ajukan.jpg**

![web_modal_cuti_ajukan.jpg](screenshots/finance/web_modal_cuti_ajukan.jpg)

**finance/web_modal_konfirmasi_keluar.jpg**

![web_modal_konfirmasi_keluar.jpg](screenshots/finance/web_modal_konfirmasi_keluar.jpg)

**finance/web_modal_lokasi_tambah.jpg**

![web_modal_lokasi_tambah.jpg](screenshots/finance/web_modal_lokasi_tambah.jpg)

**gudang/mobile_beranda_setelah_daftar_wajah.png**

![mobile_beranda_setelah_daftar_wajah.png](screenshots/gudang/mobile_beranda_setelah_daftar_wajah.png)

**gudang/mobile_galeri.png**

![mobile_galeri.png](screenshots/gudang/mobile_galeri.png)

**gudang/mobile_gate_daftar_wajah_baru.png**

![mobile_gate_daftar_wajah_baru.png](screenshots/gudang/mobile_gate_daftar_wajah_baru.png)

**gudang/mobile_rencana.png**

![mobile_rencana.png](screenshots/gudang/mobile_rencana.png)

**ketua11/mobile_apk_baru.png**

![mobile_apk_baru.png](screenshots/ketua11/mobile_apk_baru.png)

**ketua11/mobile_kamera_logo.png**

![mobile_kamera_logo.png](screenshots/ketua11/mobile_kamera_logo.png)

**ketua11/mobile_profil_scroll.png**

![mobile_profil_scroll.png](screenshots/ketua11/mobile_profil_scroll.png)

**ketua11/mobile_sesi_cabut_konfirmasi.png**

![mobile_sesi_cabut_konfirmasi.png](screenshots/ketua11/mobile_sesi_cabut_konfirmasi.png)

**ketua11/mobile_sesi_dua_perangkat.png**

![mobile_sesi_dua_perangkat.png](screenshots/ketua11/mobile_sesi_dua_perangkat.png)

**ketua11/mobile_sesi_setelah_cabut.png**

![mobile_sesi_setelah_cabut.png](screenshots/ketua11/mobile_sesi_setelah_cabut.png)
