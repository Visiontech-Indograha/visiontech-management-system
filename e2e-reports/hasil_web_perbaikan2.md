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
