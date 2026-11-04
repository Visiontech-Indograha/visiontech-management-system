---
name: vms-db
description: >-
  Pakai skill ini untuk pekerjaan skema dan basis data VMS (folder db/ dan api/alembic_v2/): membuat atau mengubah tabel, kolom, indeks, constraint, partisi, migrasi Alembic expand-contract, RLS PostgreSQL (peran non-superuser, SET LOCAL, kebijakan dengan fungsi cakupan), enkripsi kolom sensitif (NIK, rekening, embedding wajah) dan blind index, backup dan uji pulih, urutan pasang skema (06, 08, 07, alembic), EXPLAIN ANALYZE, dan DB uji vms_test. Kata kunci: PostgreSQL 18, PostGIS, pgvector, UUIDv7, NUMERIC, TIMESTAMPTZ, soft delete delete_at, FK, indeks, B-tree, EXPLAIN, migrasi, Alembic, expand contract, RLS, row level security, partisi, backup, restore, enkripsi, AES-GCM, skema, database, tabel, kolom.
---

# vms-db · PostgreSQL 18 untuk VMS

Basis: `db/06_master_schema_v2.sql`, `db/08_master_v2_tambahan.sql`, `db/07_master_seed_v2.sql` (data uji), `api/alembic_v2/`, `api/app/database/`, dan CI `.github/workflows/ci.yml` (cabang `origin/beta`, diperiksa 2026-11-04). Target skema VMS Next: `vms-next/docs/03-SKEMA-DATA.md` dan ADR 0001 keputusan 7-10 dan ADR 0002.

Penanda:
- `(bukti: file:baris)` = kondisi kode saat ini.
- `Target:` = standar baru dari dokumen VMS Next dan panduan PDF.

## 1. Aturan keras

1. **Jangan pernah memakai DB dev atau produksi untuk tes.** Tes hanya ke `vms_test` atau host lokal dengan nama `*_test` (`api/tests/db_guard.py:16-25`). Memori `vms-master-local-test-db`: di worktree `vms-master-local`, DB uji memakai `test_migration` (V2 murni).
2. **Tes DB dan pytest hanya atas perintah user** (memori `defer-test-writing`). Tulis boleh; jalankan tidak.
3. **Migrasi baru hanya** di `api/alembic_v2/versions/`. Migrasi lama tidak diubah (baseline). Migrasi baru wajib `downgrade()` jika memungkinkan.
4. **Tanpa `CREATE INDEX` tanpa `CONCURRENTLY`** di migrasi baru. Gunakan `autocommit_block()` (Alembic, `https://alembic.sqlalchemy.org/en/latest/api/runtime.html`, akses 2026-11-04).
5. **Uang: `NUMERIC(12,2)`**. Waktu: `TIMESTAMPTZ` (UTC). Tanpa `FLOAT`, `REAL`, `DOUBLE`, dan `TIMESTAMP` tanpa zona (aturan R-31, `test_sql_rules.py:30`, dan PDF 3.1).
6. **PK baru: `uuidv7()`** (Target). Tabel lama tidak diubah tipe ID-nya.
7. **Soft delete**: kolom `delete_at` (kode sekarang) atau `deleted_at` (Target `docs/03`). Indeks parsial `WHERE … IS NULL`. Nama kolom waktu harus konsisten dalam satu tabel baru.
8. **Expand → migrate → contract.** Rilis N hanya menambah kolom `NULL`able atau tabel baru. Kolom lama dihapus di rilis N+1 atau sesudahnya (`docs/06` Rilis langkah 4).
9. **Tanpa `DROP COLUMN` / `RENAME` / `ALTER TYPE` pada tabel besar dalam rilis yang sama** dengan penambahan.
10. **Tes RLS memakai peran non-superuser.** Superuser dan `BYPASSRLS` melewati RLS (`https://www.postgresql.org/docs/current/ddl-rowsecurity.html`, akses 2026-11-04).

## 2. Urutan pasang skema (penting)

Urutan yang benar di CI dan `db/README.md:12`: **`06` → `08` → `alembic upgrade head`**. CI melakukannya di `ci.yml:62-75` dengan `ON_ERROR_STOP=1`.

### 2.1 Bug urutan `client` (catatan kejadian)
- Di `origin/beta`, `db/06_master_schema_v2.sql:799` (`client_sites`) dan `:817` (`client_work_orders`) memakai `REFERENCES client(client_id)`. Tabel `client` baru dibuat di `db/08_master_v2_tambahan.sql:14`. Akibatnya `06` gagal sebelum `08` berjalan, dan CI gagal pasang skema.
- Perbaikan: pindahkan blok `client_sites` sampai `work_order_bom` ke `08` agar dibuat setelah `client`. Perbaikan ini ada di commit `d8a12df5` pada cabang `integrasi/uji-ulang`. Diperiksa dengan `git merge-base --is-ancestor d8a12df5 HEAD`: **belum** ada di HEAD `origin/beta`.
- Pelajaran untuk skill: setiap tabel baru yang punya FK harus dibuat setelah tabel rujukannya. Tambah langkah CI yang memasang `06` lalu `08` dengan `ON_ERROR_STOP=1` (sudah ada); jangan menambah file SQL baru tanpa memeriksa urutan.
- Catatan: `api/alembic_v2` juga memuat DDL. Tes `test_sql_matches_schema.py` mencocokkan model dengan skema. Jika ada kolom baru di `06/08`, pastikan migrasi Alembic tidak membuat ulang tabel yang sama.

## 3. Peta skema (bukti)

| Area | Lokasi | Catatan |
|---|---|---|
| Ekstensi | `06:9` | `pgcrypto` dibuat. PostGIS dan pgvector ada di image (`db/Dockerfile`) tetapi belum dipakai |
| Pengguna | `06:119` (`users`) | `user_id UUID PK DEFAULT gen_random_uuid()` |
| Sesi | `06:135-150` (`user_sessions`) | `refresh_token_hash CHAR(64) NOT NULL` (`:139`) tanpa indeks. Indeks hanya `idx_user_sessions_user` (`:754`) |
| Wajah | `06:109` | `face_embedding JSONB NULL` (teks biasa, belum terenkripsi) |
| Berkas | `06:724-735` (`file_object`) | `storage_key UNIQUE`; `sha256 BYTEA`; `UNIQUE (office_id, sha256)` |
| Log aktivitas | `06:667-688` | `app_activity_logs` dipartisi `RANGE (created_at)`; partisi per bulan dibuat runtime (`migration_v3.py:83-113`, `lifespan.py:24-33`) |
| Lampiran jadwal | `06:741` | `work_plan_attachment` |
| Klien | `08:14` (`client`), `08:89` (`project`) | Tabel tambahan |
| Indeks | `06` (±58), `08` (±19) | Hampir semua parsial `WHERE delete_at IS NULL` |
| Migrasi | `api/alembic_v2/versions/v2_0001` … `v2_0019` | Head `v2_0019` (`test_alembic_v2.py`) |
| Konteks sesi | `api/app/database/session.py:107-112` | `set_config('app.user_id'…, true)`, `app.organization_id`, `app.actor_label` (`true` = LOCAL) |

Pola ID yang ada: `gen_random_uuid()` (UUIDv4) di hampir semua tabel. Target: `uuidv7()` untuk tabel baru (PostgreSQL 18, `https://www.postgresql.org/docs/18/functions-uuid.html`, akses 2026-11-04).

## 4. Tipe data dan constraint

| Kebutuhan | Pakai | Hindari |
|---|---|---|
| Uang | `NUMERIC(12,2)` (ADR 0001 keputusan 8) | `FLOAT`, `NUMERIC(14,2)` lama |
| Waktu | `TIMESTAMPTZ`, default `now()`, disimpan UTC | `TIMESTAMP` tanpa zona |
| Status | `TEXT` + `CHECK (status IN (...))` (`docs/03`) | tipe `ENUM` PostgreSQL (sulit diubah) |
| ID | `uuid` (`uuidv7()` untuk baru) | `SERIAL` lintas shard |
| Teks pendek | `VARCHAR(n)` | `TEXT` tanpa batas bila ada aturan panjang |
| Berkas | `file_object_id` (FK), bukan path | path atau URL di kolom |
| Koordinat | `site_lat/site_lng NUMERIC` (sekarang) | jika butuh radius: `geography(Point,4326)` + GiST (`vms-db` referensi B-6) |

Constraint bisnis di database (Target `docs/03`): satu absen masuk per hari per karyawan, `EXCLUDE` untuk tabrakan cuti. Contoh sudah ada: `uq_work_plan_daily_team_day` (riset 01 T3).

Aturan nama: constraint dan indeks diberi nama eksplisit (`ix_`, `uq_`, `fk_`, `ck_`). Pola konvensi naming di `zhanymkanov/fastapi-best-practices` (ide, tanpa lisensi) dan ADR 0003 A3.

## 5. Indeks

Referensi detail: `references/skema-indeks-dan-explain.md`.

Ringkas:
- B-tree untuk kesamaan dan rentang. Komposit mengikuti leftmost prefix (PDF 3.2 baris 215-219). `attendance(employee_id, attendance_date)` ada di `v2_0003` (`:21`), tetapi filter tanggal tanpa `employee_id` tidak terlayani (riset 01 F-11).
- Parsial untuk soft delete: `WHERE delete_at IS NULL` (kode sekarang) atau `WHERE deleted_at IS NULL` (Target).
- **Kekurangan nyata**: `user_sessions.refresh_token_hash` tanpa indeks (`06:139`). Setiap refresh memindai tabel. Tambahkan `UNIQUE` parsial (`CONCURRENTLY`, lihat `migrasi-expand-contract.md`).
- **Foreign key tanpa indeks**: Target (ADR 0003 A5) indeks penuh di setiap kolom FK. Periksa FK di `06`/`08` yang belum punya indeks sebelum migrasi.
- Covering index (`INCLUDE (...)`) bila `EXPLAIN` menunjukkan heap fetch besar.
- Indeks yang tidak dipakai menambah biaya tulis. Pantau dengan `pg_stat_user_indexes` (ADR 0003 R9: pghero sebagai usulan fase 9).
- Verifikasi: `EXPLAIN (ANALYZE, BUFFERS)` di `vms_test` atas perintah user. Pakai pev2 (`dalibo/pev2`) untuk membaca hasil. Jangan `ANALYZE` pada data produksi.

## 6. Migrasi Alembic

Detail dan contoh ada di `references/migrasi-expand-contract.md`.

Kondisi sekarang (bukti):
- `api/alembic.ini` mengarah ke `alembic_v2`. `env.py:17` memakai `MIGRATION_DATABASE_URL` jika ada (peran migrasi terpisah, baik). `env.py` bukan sumber kebenaran peran.
- Tidak ada `CONCURRENTLY` di `api/alembic_v2/versions` (0 kecocokan). `autocommit_block` dipakai di 2 tempat.
- `v2_0003_performance_composite_indexes.py:21-31` memakai `CREATE INDEX IF NOT EXISTS` biasa. Ini baseline lama; jangan diubah.
- **DDL saat startup**: `migration_v3.py:103-117` membuat partisi bulanan saat aplikasi start (`lifespan.py:24-33`). Ini bertentangan dengan aturan "skema hanya lewat Alembic". Target: pindahkan ke migrasi Alembic atau job terjadwal.
- `test_alembic_v2.py` memeriksa rantai revisi dan head `v2_0019`.

Target:
- Lint migrasi di CI: squawk (`https://github.com/sbdchd/squawk`, ADR 0003 R8). Belum dipasang.
- Aturan tertulis (ADR 0003 A5, riset 02 B-3): `CONCURRENTLY` untuk indeks, `NOT VALID` lalu `VALIDATE CONSTRAINT`, `SET NOT NULL` setelah backfill, backfill dibatch.
- Alat expand-contract: pola disiplin cukup. pgroll (`https://github.com/xataio/pgroll`, akses 2026-11-04) membutuhkan PostgreSQL 14+ dan versioned schema lewat `search_path`; itu berisiko untuk APK lapangan lama. Dicatat sebagai pilihan, bukan default.

## 7. RLS (Row-Level Security)

Detail ada di `references/rls-enkripsi-dan-peran.md`.

Kondisi sekarang:
- **Tidak ada `CREATE POLICY` maupun `ENABLE ROW LEVEL SECURITY`** di `db/` dan `api/alembic_v2/` (0 kecocokan; riset 01 T20, F-28).
- Konteks `set_config` dipasang di `session.py:107-112` tetapi tidak dipakai policy mana pun. Komentar kode menyebut RLS, padahal belum aktif.
- **Peran kontainer**: `docker-compose.yml:28-31` membuat `POSTGRES_USER: vms_app`. Image PostgreSQL resmi membuat peran itu sebagai superuser. Jika benar, aplikasi melewati RLS. **Perlu cek**: `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='vms_app';`. Jika `rolsuper` true, buat peran aplikasi terpisah.
- `ci.yml:31` memakai `postgres:postgres` (superuser) untuk tes. Tes RLS wajib memakai peran non-superuser (`TEST_SETUP_DATABASE_URL`, `conftest.py:43`).

Target (ADR 0001 keputusan 9):
- Tabel inti: `employee`, `employee_address`, `work_order`, `work_plan`/`daily_plan`, `attendance`, `leave`, `overtime`, asset assignment, `file_object`, dokumen karyawan.
- Peran: `vms_app` (NOBYPASSRLS, bukan owner), `vms_migrator` (owner, untuk migrasi), `vms_job` (job terjadwal, dibatasi). Lihat `references/rls-enkripsi-dan-peran.md`.
- `ALTER TABLE … ENABLE ROW LEVEL SECURITY` dan `FORCE ROW LEVEL SECURITY`.
- Policy memakai fungsi cakupan SQL yang sama dengan service, dengan `(select current_setting('app.user_id', true))` agar di-cache per pernyataan (Supabase guide, ADR 0003 A6, R10).
- Konteks di-set `SET LOCAL` di awal transaksi (session factory atau dependency, bukan repository).
- Fail closed: `current_setting(..., true)` NULL → policy menolak. Tanpa policy, RLS menolak semua baris (default-deny, dokumentasi PostgreSQL).
- Tes: query tanpa konteks mengembalikan 0 baris; ID lintas divisi tidak terlihat.

## 8. Enkripsi kolom sensitif dan blind index

Detail di `references/rls-enkripsi-dan-peran.md` bagian 4.

- Kondisi: NIK dan rekening belum terenkripsi (riset 01 T12). `pgcrypto` dibuat tetapi tidak dipakai (`pgp_sym_encrypt` tidak ditemukan). `face_embedding` JSONB teks biasa (`06:109`).
- Target (`docs/06`, `docs/03`, ADR 0001 keputusan 10): AES-256-GCM di aplikasi, awalan key id, nonce acak 96-bit per nilai, kunci dari rahasia terpasang (bukan git, bukan DB). Blind index HMAC-SHA256 dengan kunci terpisah untuk pencarian persis. Tidak ada pencarian awalan pada nilai terenkripsi.
- Kunci hilang berarti data tidak terbaca. Simpan cadangan kunci terpisah.
- Embedding wajah hanya dicocokkan saat absen (`docs/06` wajah). Jangan tulis embedding ke log.

## 9. Partisi, retensi, dan backup

- **Partisi log** (`app_activity_logs`): bulanan. Retensi belum ada (riset 02 B-2). Target: `DETACH PARTITION` lalu arsip atau `DROP`, bukan `DELETE` massal. pg_partman (`https://github.com/pgpartman/pg_partman`) membutuhkan `shared_preload_libraries` dan restart; cron SQL sederhana cukup untuk sekarang.
- **Backup** (kode dan skrip ada di `deploy/`): `backup.sh`, `backup-offsite.sh`, `siapkan-offsite.sh`, `uji-pulih-cadangan.sh`. `docs/06` Cadangan: `pg_dump` harian ke MinIO plus salinan luar situs, uji pulih berkala.
- RPO dan RTO belum tertulis di kode (riset 01 F-30). Tulis di ADR atau runbook dan catat hasil uji pulih.
- Uji pulih hanya ke DB uji. Jangan restore ke produksi (riset 01 F-30 risiko).
- `pg_dump` sebelum migrasi wajib (`docs/06` Rilis langkah 3a).

## 10. Pengujian skema

- `test_sql_matches_schema.py` mencocokkan SQL dengan skema.
- `test_alembic_v2.py` memeriksa head dan rantai.
- Tambahkan (Target): tes `alembic upgrade head` dari kosong, `downgrade -1` untuk migrasi yang mendukungnya, dan tes RLS (query tanpa konteks → 0 baris).
- Jalankan pytest di DB uji `vms_test` atas perintah user.

## 11. Checklist selesai (db)

- [ ] Migrasi baru di `alembic_v2/versions/`, linear, dengan `downgrade()` atau alasan tertulis.
- [ ] Indeks baru `CONCURRENTLY` di `autocommit_block()`.
- [ ] Tidak ada `FLOAT` untuk uang; `TIMESTAMPTZ`; `NUMERIC(12,2)`.
- [ ] FK punya indeks; kolom filter punya indeks yang cocok dengan pola kueri.
- [ ] Urutan `06` → `08` → alembic dijaga: tabel dibuat setelah rujukannya.
- [ ] Kolom sensitif dienkripsi di aplikasi atau ada alasan tertulis.
- [ ] Tabel inti: RLS ENABLE + FORCE + policy dengan fungsi cakupan, dan peran non-superuser (sebelum merilis, bukan tanpa).
- [ ] Tes dijalankan hanya di `vms_test` atas perintah user.
- [ ] Pertanyaan tentang peran `vms_app` (superuser?) sudah dijawab.

## 12. Skill global yang boleh dipanggil atau dilebur

- **`security-review`**: tinjau RLS, peran, enkripsi, dan blind index sebelum merge.
- **`code-review`**: tinjau migrasi dan SQL di diff. Gunakan `--max-findings` sesuai kebutuhan.
- **`simplify`**: merapikan SQL dan helper. Jangan mengubah urutan DDL atau nama constraint tanpa migrasi.
- **`postman:api-testing`** atau **`postman:api-engineer`**: hanya bila kontrak API ikut berubah karena skema. Lengkapi dengan `vms-api`.

Skill ini tidak memakai `postman:datasets` untuk tes DB. Tes DB memakai DB uji sendiri, bukan data dari database luar.

## 13. Berkas referensi

- `references/skema-indeks-dan-explain.md`: tipe, indeks, EXPLAIN, UUIDv7, partisi.
- `references/migrasi-expand-contract.md`: aturan migrasi, contoh Alembic, squawk, pgroll.
- `references/rls-enkripsi-dan-peran.md`: RLS, peran, SET LOCAL, enkripsi AES-GCM, blind index.
- `references/urutan-pasang-dan-db-uji.md`: urutan 06/08/07/alembic, bug client, DB uji `vms_test`, backup dan uji pulih.
