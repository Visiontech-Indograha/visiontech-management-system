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

- [ ] **Milestone 1**: Auth, Sesi & Profil Pengguna (`users`, `employee`, `user_sessions`, `address`)
- [ ] **Milestone 2**: Master Kantor & Divisi Operasional (`office`, `division`)
- [ ] **Milestone 3**: Manajemen Tim & Personel Lapangan (`team`, `member`, `employee_file`)
- [ ] **Milestone 4**: Inventaris Aset (Alat Pribadi/Umum & Kendaraan) (`tool`, `vehicle`, `asset_assignment`)
- [ ] **Milestone 5**: Perencanaan Kerja Mingguan & Harian Site (`work_plan_weekly`, `work_plan_daily`, `company_mess_stay`)
- [ ] **Milestone 6**: Item Pekerjaan & Engine Rollover Geser Hari (`work_plan_item`)
- [ ] **Milestone 7**: Presensi Biometrik Wajah & Otomasi Uang Makan (`attendance`)
- [ ] **Milestone 8**: Laporan Penyelesaian & Ekspor Multi-Format (`work_completion`, `document_template_export`)
- [ ] **Milestone 9**: Penghentian Kerja (PKWT) & Clearance Aset (`employee_offboarding`, `offboarding_clearance_item`)
