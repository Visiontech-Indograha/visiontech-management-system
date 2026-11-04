# Database VMS (PostgreSQL 18) · aturan untuk agen

Dibaca otomatis saat bekerja di `db/`. Aturan lengkap di skill `vms-db`.

## Aturan inti
- Urutan pasang: `06_master_schema_v2.sql` → `08_master_v2_tambahan.sql` → `alembic upgrade head`. Tabel dengan FK dibuat setelah tabel rujukannya (bug `client` di `06:799,817`).
- `07_master_seed_v2.sql` hanya data uji. Jangan dijalankan di produksi.
- Uang `NUMERIC(12,2)`; waktu `TIMESTAMPTZ`; PK baru `uuidv7()` (PostgreSQL 18); soft delete dengan indeks parsial.
- Perubahan skema baru hanya lewat migrasi Alembic di `api/alembic_v2/versions/` (expand → migrate → contract). Indeks baru `CREATE INDEX CONCURRENTLY`.
- RLS: peran aplikasi non-superuser tanpa `BYPASSRLS`. Tes RLS tidak boleh memakai superuser.

## Skill
- `vms-db`: skema, indeks, EXPLAIN, migrasi, RLS, enkripsi, urutan pasang, DB uji.

## Perintah (jalankan dari `db/` atau `api/`)
- Pasang dari kosong (hanya ke DB uji): `psql -h localhost -U <superuser> -d vms_test -v ON_ERROR_STOP=1 -q -f 06_master_schema_v2.sql` lalu `-f 08_master_v2_tambahan.sql`, lalu `cd ../api && python -m alembic upgrade head`.
- Cek peran: `SELECT rolname, rolsuper, rolbypassrls FROM pg_roles;`
- EXPLAIN (uji saja, atas perintah user): `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <kueri>;`

## Larangan
- Jangan menjalankan DDL, `ANALYZE`, atau pemasangan ke `vms-dev-db` atau DB produksi.
- Jangan mengubah `06`/`08` untuk tabel yang sudah ada di produksi tanpa migrasi Alembic.
- Jangan menyimpan NIK, rekening, atau embedding wajah dalam bentuk teks biasa pada kolom baru.
- Jangan commit tanpa perintah user.
