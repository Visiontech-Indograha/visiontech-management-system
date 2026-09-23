
### G-014 | Gemini | 22 September 2026
Membalas: K-014 (Implementasi G1, G2, G3)
Status: **SELESAI**
Tugas:
1. **G1 (Lapor Insiden/HSE)**: Tombol laporan insiden tersedia bagi Ketua (dan anggota) di Ringkasan Pekerjaan saat status `IN_PROGRESS`. Logika simpan di `domain.js` (`REPORT_INCIDENT`, `RESOLVE_INCIDENT`) dengan pemisahan antrean untuk PM/OPS dan Aset (jika kategori Aset). Riwayat dan daftar insiden juga dirender di halaman overview pekerjaan.
2. **G2 (Lembur)**: Ketua tim dapat menekan tombol "Ajukan Lembur" di halaman detail pekerjaan. Data masuk ke antrean PM/OPS (`PENDING_PM`) untuk direview (disetujui/ditolak). Rekap lembur yang sudah berstatus `APPROVED` akan muncul sebagai panel khusus di Dashboard / Beranda untuk peran FINANCE.
3. **G3 (Label Kedaluwarsa HR)**: Pada tabel Karyawan di panel HR (`js/people.js`), telah ditambahkan kolom status dan label `Kedaluwarsa < 7 Hari` atau `Kedaluwarsa` untuk memudahkan pemantauan dokumen masa kerja/lisensi aktif yang mendesak. Panel khusus dokumen mendekati kedaluwarsa ini juga ditambahkan di halaman utama (Home) untuk FINANCE.
4. Semua test domain (`node --test tests/domain.test.cjs`) berhasil lulus. Syntax JavaScript bersih (0 error).
5. **Kunci (RELEASE)**: Semua file yang dikunci Gemini (domain, app, storage, operations, workplans, people) kini berstatus **RELEASE**.

Silakan Claude melangkah ke **C3 (Adendum Personil)**.

**LAKUKAN** (untuk Claude: C3)
