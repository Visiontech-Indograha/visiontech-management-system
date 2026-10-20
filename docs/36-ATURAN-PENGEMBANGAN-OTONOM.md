# 36 — Aturan & Panduan Pengembangan Otonom VMS V2

Dokumen ini menjadi acuan operasional bagi agen otonom untuk merekayasa, menguji, dan meluncurkan setiap fitur sistem VMS V2 secara mandiri dan disiplin.

---

## 1. Prinsip Utama Pengembangan Otonom

1. **Gunakan Fondasi Skema Teruji**: Setiap penulisan endpoint dan UI wajib mengacu pada tabel yang sudah aktif di `test_migration` (`db/06_master_schema_v2.sql` dan `db/07_master_seed_v2.sql`).
2. **Kesesuaian dengan Flowchart**: Jangan mengubah atau mengasumsikan alur di luar yang didefinisikan pada `docs/35-FLOWCHART-DAN-ALUR-BISNIS-V2.md`.
3. **Penyelesaian Per-Page**: Selesaikan modul secara utuh (API $\rightarrow$ Web/Mobile $\rightarrow$ Build Test) sebelum melangkah ke milestone berikutnya.
4. **Fokus Stabilitas Lokal**: Pastikan aplikasi berjalan stabil di lokal sebelum menambahkan layer kompleksitas testing tambahan.

---

## 2. Checklist Roadmap 9 Milestone

Status per 2026-10-20 (API + uji Postman; UI web/HP belum disesuaikan sehingga belum dicentang penuh):

- [ ] **Milestone 1**: Auth, Sesi & Profil Pengguna (`users`, `employee`, `user_sessions`, `address`) — API ✔, Postman ✔
- [ ] **Milestone 2**: Master Kantor & Divisi Operasional (`office`, `division`) — API ✔, Postman ✔
- [ ] **Milestone 3**: Manajemen Tim & Personel Lapangan (`team`, `member`, `employee_file`) — API ✔, Postman ✔, web
      (berkas karyawan) ✔. Aturan: ketua wajib TEAM_LEADER & otomatis anggota; anggota hanya peran lapangan; PM
      hanya mengelola tim di divisinya (`division.pm_id`); nama tim unik per divisi; tim yang dirujuk
      `work_plan_daily` tidak bisa dihapus. `employee_file`: HR/GA mencatat dari `file_object` (`path_file` =
      `storage_key`), dokumen sejenis yang baru → lama `extended`, lewat tanggal → `not_active`; tanpa alur
      verifikasi/nomor dokumen (tidak ada kolomnya di V2).
- [ ] **Milestone 4**: Inventaris Aset (Alat Pribadi/Umum & Kendaraan) (`tool`, `vehicle`, `asset_assignment`) — API ✔, Postman ✔,
      web ✔. Serah terima: aset `ready`, karyawan aktif, alat pribadi tanpa jadwal, jadwal belum lewat & karyawan
      anggota timnya; kendaraan wajib STNK berlaku (KIR untuk Truck) + SIM sesuai jenis. Jadwal → `allocated`,
      pribadi → `loaned`; kembali → ready/damaged/lost. Inspeksi oleh pengelola aset atau pemegang.
- [ ] **Milestone 5**: Order Klien & Perencanaan Harian Daily-First (`work_completion` sebagai order, `work_plan_daily`,
      `company_mess_stay`) — **tanpa** `work_plan_weekly`
- [ ] **Milestone 6**: Item Pekerjaan per Titik, Fase & Rollover (`work_plan_item`, `work_type`, `image_requirement`,
      `work_type_default_materials`, `work_completion_bom`)
- [ ] **Milestone 7**: Presensi Biometrik Wajah & Otomasi Uang Makan (`attendance`, `employee.face_embedding`)
- [ ] **Milestone 8**: Laporan Penyelesaian & Ekspor Multi-Format, termasuk Survey Report .docx
      (`work_completion`, `document_template_export`)
- [ ] **Milestone 9**: Penghentian Kerja (PKWT) & Clearance Aset (`employee_offboarding`, `offboarding_clearance_item`)

---

## 3. Keputusan Pemilik yang Mengikat (2026-10-20)

1. **Daily-first**: `work_plan_daily` adalah induk; minggu = rentang tanggal. Kode/seed/dokumen yang masih memakai
   `work_plan_weekly` ditulis ulang ke model ini.
2. **Rollover**: ke hari yang sudah ada atau tanggal baru (hari dibuat otomatis); tanggal tujuan > asal; tim & divisi sama;
   sisa volume terbawa; satu rantai aktif; `delay_reason` ketua tidak ditimpa — catatan PM ke `app_activity_logs` (docs/35 §4).
3. **Fase item** `task_phase`: SURVEY, PREPARATION, INSTALLATION, REPLACEMENT, MAINTENANCE — dipilih per item; template
   per divisi lewat `work_type`.
4. **Skema**: jangan asal menambah tabel/kolom — pakai relasi FK yang ada. Perubahan yang disetujui:
   `work_plan_item.notes` (remark titik), `overtime.weekly_plan_id → daily_plan_id` (FK `work_plan_daily`),
   `file_object` & `work_plan_attachment` diformalkan ke DDL 06 dengan FK (`office`, `users`, `work_plan_daily`).
   Setiap perubahan: migrasi baru + `db/06_master_schema_v2.sql` + `.agents/rules/01_database_context.md` disamakan.
5. **Wajah V2**: daftar → `employee.face_embedding`; swafoto absen dicocokkan server → `attendance.face_match_score`;
   tidak cocok ditolak; layanan wajah mati → PENDING_OM.
6. **Platform**: web hanya peran kantor (SUPER_ADMIN, OM, PM, HR); aplikasi HP hanya TEAM_LEADER & EMPLOYEE (docs/35 §1).
7. **Uji**: jangan menjalankan tes sebelum diminta pemilik; uji Postman (`scripts/run_postman_validation.py`, DB
   `test_migration`) di akhir milestone, perbaiki galat yang ditemukan.
8. **Commit**: tanpa trailer AI/Co-authored-by; stage per path (`.agents/rules/02` §4).
