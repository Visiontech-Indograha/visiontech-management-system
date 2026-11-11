# ADR 0003: Penerima eksternal untuk peminjaman aset
Status: Usulan (keputusan bisnis dari pemilik, autopilot 2026-11-11; rincian teknis menunggu persetujuan)
Tanggal: 2026-11-11
Pemilik keputusan bisnis: pemilik VMS.

## 1. Konteks

Bisnis rental: perusahaan juga meminjamkan/menyewakan aset (komputer, printer, alat, kendaraan) kepada pihak luar, mis. klien sewa dan subkontraktor Pertamina/PLN. Sekarang peminjaman hanya untuk karyawan.

Keadaan sekarang (diverifikasi di `db/06_master_schema_v2.sql` dan `api/alembic_v2/versions/v2_0005_asset_loan_requests.py`):
- Tabel peminjaman bernama `asset_assignment` (bukan `asset_loan`): `employee_id UUID NOT NULL`, `tool_id`/`vehicle_id`, `loaned_at`, `returned_at` (sudah ada), `handover_photo_path`, `return_*`, soft delete `delete_at`. Belum ada `due_date` maupun `handover_file_id`.
- `asset_loan_request` (pengajuan karyawan) tetap khusus karyawan; tidak diubah.
- Berkas: `file_object` (punya `office_id`), diakses lewat `/files/{id}/url`.
- Modul: `api/app/modules/assets/` (controller, repository, route, schema, service).
- Offboarding menahan karyawan selama `returned_at IS NULL`; aturan ini hanya berlaku untuk baris berpenerima karyawan.
- Migrasi Alembic head saat ini `v2_0036`.

### Keputusan pemilik (final, tidak diubah ADR ini)
1. Penerima eksternal lewat master klien kecil (nama + kontak) yang dipakai ulang.
2. Peminjaman memuat tanggal jatuh tempo dan dokumen serah terima (BAST) lewat modul berkas.
3. Biaya sewa dan denda di luar cakupan.

## 2. Keputusan

Tambah master `asset_external_borrowers`; peminjaman boleh menunjuk karyawan ATAU penerima eksternal (tepat satu). Perubahan hanya aditif.

### Model data (migrasi Alembic expand-only, nomor setelah `v2_0036`)

```
asset_external_borrowers(
  borrower_id UUID PK DEFAULT gen_random_uuid(),
  office_id   UUID NOT NULL REFERENCES office(office_id),
  nama        VARCHAR(150) NOT NULL,
  instansi    VARCHAR(150) NULL,
  kontak      VARCHAR(100) NULL,      -- telepon/email (data pribadi)
  create_at, update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  delete_at   TIMESTAMPTZ NULL)
-- indeks (office_id, lower(nama)) WHERE delete_at IS NULL; pencarian = awalan

asset_assignment:
  ALTER employee_id DROP NOT NULL
  ADD external_borrower_id UUID NULL REFERENCES asset_external_borrowers(borrower_id)
  ADD due_date DATE NULL
  ADD handover_file_id UUID NULL REFERENCES file_object(id) ON DELETE SET NULL
  ADD CONSTRAINT ck_assignment_one_borrower CHECK (num_nonnulls(employee_id, external_borrower_id) = 1)
  indeks parsial (due_date) WHERE returned_at IS NULL AND delete_at IS NULL
```

`returned_at` sudah ada, tidak ditambah. Baris lama otomatis lolos CHECK (employee_id terisi). CHECK dibuat `NOT VALID` lalu `VALIDATE` agar kunci singkat. `db/06` diperbarui sejajar dengan migrasi.

### Izin, RLS, cakupan kantor
- Izin baru `asset:borrower:read` dan `asset:borrower:write` untuk peran pengelola aset yang sudah ada (HR/GA); tidak untuk peran lapangan. Peminjaman ke eksternal memakai izin tulis aset yang sudah ada.
- Cakupan kantor: master dan peminjaman eksternal dibatasi `office_id` (seperti `tool`/`vehicle`); SUPER_ADMIN/OM semua kantor, sesuai ADR 0002. Penerima eksternal wajib sekantor dengan aset.
- RLS ikut tahap RLS bertahap (keputusan PDP); kebijakan `office_id` dipasang bersama tabel lain, bukan syarat PR pertama. Cakupan di API/SQL wajib sejak awal.
- BAST: `file_object.office_id` harus sama dengan kantor aset; unduh hanya lewat tiket `/files/{id}/url`.

### Privasi (PDP)
Kontak eksternal adalah data pribadi: dikumpulkan seminimal mungkin (nama, instansi, kontak; tanpa NIK/alamat), tidak ditulis ke log, ditutup sebagian di daftar bagi yang tidak berizin tulis. Retensi dan pemusnahan mengikuti keputusan PDP (30 hari data pribadi): penerima tanpa pinjaman aktif yang melewati masa retensi kontaknya dikosongkan (nama tetap sebagai riwayat) lewat pekerjaan retensi yang ada (`retention_policy`). BAST mengikuti retensi arsip dokumen.

### Audit
Buat/ubah/hapus penerima, pinjam, kembali, dan unggah/ganti BAST dicatat di log audit (siapa, kapan, id; tanpa isi kontak).

### Dampak APK lama
Aditif. Kolom dan field baru opsional; respons peminjaman karyawan tidak berubah. Baris eksternal tidak muncul di "pinjaman saya" dan tidak menahan offboarding. Kode yang membaca `employee_id` harus menangani NULL. Snapshot OpenAPI diperbarui.

### Notifikasi jatuh tempo (tahap 2)
Pekerjaan harian mencari `due_date` mendekati/lewat dengan `returned_at IS NULL`, lalu memberi notifikasi ke pengelola aset kantor itu. Dapat memakai mekanisme pengingat dokumen kendaraan yang direncanakan; bila belum ada, memakai tabel `notification`. Penerima eksternal tidak diberi notifikasi (tanpa akun). Di luar PR 1-3.

## 3. Alternatif yang ditolak
- Eksternal sebagai `employee` palsu: mencemari data SDM, absensi, dan offboarding.
- Teks bebas nama/kontak di baris pinjaman: tidak bisa dipakai ulang, data ganda, sulit dimusnahkan sesuai PDP.
- Tabel peminjaman terpisah: menggandakan logika kembali, ketersediaan, laporan.
- Akun login untuk klien: tidak dibutuhkan, memperbesar permukaan serangan.
- Biaya sewa/denda: di luar keputusan pemilik.

## 4. Konsekuensi
- `employee_id` nullable: semua join ke `employee` dari `asset_assignment` harus LEFT JOIN (risiko utama; dijaga tes).
- Aturan "satu aset satu pinjaman aktif" yang ada dipakai ulang untuk kedua jenis penerima.
- Rollback: kolom baru dibiarkan (expand-only); fitur dimatikan lewat izin.

## 5. Urutan PR dan definisi selesai (ke `development`, satu fase satu PR)

1. DB + API (3-4 hari). Migrasi + `db/06`; master penerima (CRUD, `ListParams`/`apply_list`, cari awalan, cakupan kantor); pinjam eksternal dengan `due_date` dan `handover_file_id`; kembalikan; LEFT JOIN di query lama; izin; audit; snapshot OpenAPI + tipe web. Selesai bila: `verify.sh api` lulus; tes matriks peran dan lintas kantor; tes CHECK (nol atau dua penerima ditolak); pinjaman karyawan lama tak berubah; `test_sql_rules` tanpa pengecualian baru; migrasi naik-turun di `vms_test`.
2. Web (2-3 hari). Layar master penerima, pilihan "Karyawan / Pihak luar" di form pinjam, kolom jatuh tempo (penanda lewat tempo), unggah dan lihat BAST. Teks Indonesia sederhana, lima kondisi layar, `applyFieldErrors`. Selesai bila `verify.sh web` lulus, tes komponen ada, batas input sama dengan skema API.
3. Tes/QA (1-2 hari). Uji nyata lewat UI per peran, audit kebocoran GET per peran (kontak tertutup, lintas kantor), uji BAST, regresi APK lama pada data campuran, uji retensi kontak. Selesai bila laporan QA standar tanpa temuan terbuka.
4. Tahap 2 (sekitar 2 hari, terpisah): notifikasi jatuh tempo dan pemusnahan kontak.

Total tahap 1: sekitar 6-9 hari kerja.

## 6. Pertanyaan terbuka untuk pemilik
- Pengingat jatuh tempo berapa hari sebelumnya (usul H-3 dan hari H)?
- BAST wajib sebelum pinjaman eksternal disimpan, atau boleh menyusul (usul: boleh menyusul, ditandai "BAST belum ada")?
