# RLS, peran database, dan enkripsi (vms-db)

Sumber: PDF 21.1 (baris 2420-2441), PDF 10.2 (baris 1427-1429), ADR 0001 keputusan 9 dan 10, `docs/03` (RLS, Kolom sensitif), `docs/06` (Otorisasi, Berkas dan wajah). Dokumentasi resmi PostgreSQL (https://www.postgresql.org/docs/current/ddl-rowsecurity.html, akses 2026-11-04). Supabase RLS guide (https://github.com/supabase/supabase, `apps/docs/content/guides/database/postgres/row-level-security.mdx`, akses melalui riset 02, ADR 0003 R10). aws-saas-factory RLS (https://github.com/aws-samples/aws-saas-factory-postgresql-rls, MIT-0, pola peran terpisah, riset 02).

## 1. Dasar RLS (dari dokumentasi PostgreSQL)

- `ENABLE ROW LEVEL SECURITY`: policy berlaku untuk pengguna biasa. Pemilik tabel tetap melewati RLS.
- `FORCE ROW LEVEL SECURITY`: pemilik tabel juga tunduk RLS.
- Superuser dan peran `BYPASSRLS` **selalu** melewati RLS.
- RLS aktif tanpa policy = default-deny: tidak ada baris yang terlihat atau berubah.
- `USING` menentukan baris yang terlihat (SELECT) dan yang bisa diubah atau dihapus. `WITH CHECK` memvalidasi baris baru dan hasil UPDATE. Jika `WITH CHECK` tidak ditulis, `USING` dipakai.
- Pelanggaran `WITH CHECK` pada UPDATE menghasilkan error. Baris yang hanya tidak lolos `USING` diabaikan diam-diam (`UPDATE 0`).
- Policy default permissive (digabung `OR`). `AS RESTRICTIVE` digabung `AND`.
- `TRUNCATE`, `REFERENCES`, dan pemeriksaan integritas referensial (unique, PK, FK) tidak tunduk RLS.
- `row_security = off` tidak melewati RLS; ia membuat error jika ada policy yang akan memfilter (misalnya saat `pg_dump`).

## 2. Kondisi VMS (bukti)

| Hal | Kondisi | Bukti |
|---|---|---|
| Policy | Tidak ada `CREATE POLICY` atau `ENABLE ROW LEVEL SECURITY` di `db/` dan `api/alembic_v2/` | pencarian (0 kecocokan), riset 01 T20 |
| Konteks | `set_config('app.user_id', …, true)`, `app.organization_id`, `app.actor_label` | `api/app/database/session.py:107-112` (`true` = LOCAL) |
| Komentar | Menyebut RLS, padahal belum aktif | `session.py` blok "Request context (RLS & audit)" |
| Peran kontainer | `POSTGRES_USER: vms_app` | `docker-compose.yml:28-31`. Image resmi membuat peran ini sebagai superuser. **Perlu cek** dengan `pg_roles` |
| Tes | CI memakai `postgres:postgres` | `ci.yml:31`. Superuser; tidak menguji RLS |
| Pemisahan | `TEST_SETUP_DATABASE_URL` untuk data uji; komentar P9-2 "isi superuser bila DATABASE_URL memakai peran yang tunduk RLS" | `api/tests/conftest.py:41-43` |
| Migrasi | `MIGRATION_DATABASE_URL` | `api/alembic_v2/env.py:17` |
| Dependensi | `require_permission`, cakupan di service | `api/app/api/deps.py:176`, `shared/access/access_service.py:74,153` |

Kesimpulan: konteks sudah dipasang di transaksi, tetapi tidak ada yang memeriksanya. Isolasi bergantung sepenuhnya pada kode aplikasi.

## 3. Target (ADR 0001 keputusan 9; `docs/06`; `docs/03`)

### 3.1 Peran
- `vms_app`: login aplikasi. `NOSUPERUSER`, `NOBYPASSRLS`, bukan owner tabel. Hanya `SELECT, INSERT, UPDATE, DELETE` pada tabel yang dibutuhkan.
- `vms_migrator`: owner skema, dipakai Alembic (`MIGRATION_DATABASE_URL`). Tidak dipakai API.
- `vms_job`: job terjadwal yang sengaja lintas organisasi (mis. retensi). Jika perlu `BYPASSRLS`, batasi ke job itu saja; jangan dipakai API.
- Peran dibuat oleh skrip operator (`deploy/pakai-peran-runtime.sh` sudah ada, periksa isinya sebelum dipakai), bukan oleh migrasi biasa.

Pemeriksaan (perlu dijalankan user, bukan otomatis):
```sql
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname IN ('vms_app','vms_migrator','vms_job');
```
`rolsuper` dan `rolbypassrls` untuk `vms_app` harus `false`.

### 3.2 Konteks per transaksi (`SET LOCAL`)
Di awal transaksi (session factory atau dependency, bukan repository):
```sql
SELECT set_config('app.user_id', :user_id, true),
       set_config('app.role', :role, true),
       set_config('app.division_ids', :division_ids, true),
       set_config('app.pm_scope', :pm_scope, true);
```
- Parameter ketiga `true` = berlaku hanya sampai COMMIT atau ROLLBACK (`SET LOCAL`). Ini mencegah bocornya konteks antar request pada koneksi pool.
- Jika konteks tidak di-set, `current_setting(..., true)` mengembalikan NULL dan policy menolak (fail closed).
- Riset 01 T20 mencatat bahwa `session.py:107-112` sudah memakai pola ini untuk `user_id`, `organization_id`, `actor_label`. Lanjutkan dengan nama konteks Target.

### 3.3 Policy dengan fungsi cakupan
```sql
-- fungsi cakupan: satu definisi, dipakai service dan RLS
CREATE OR REPLACE FUNCTION app_can_see_division(d uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT d = ANY (string_to_array(current_setting('app.division_ids', true), ',')::uuid[])
      OR current_setting('app.role', true) = 'SUPER_ADMIN'
$$;

ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_orders FORCE ROW LEVEL SECURITY;

CREATE POLICY work_orders_scope ON work_orders
  USING (app_can_see_division(division_id))
  WITH CHECK (app_can_see_division(division_id));
```
Catatan:
- Contoh di atas ilustrasi, bukan skema final. Nama kolom dan konteks harus disesuaikan dengan tabel yang ada (`docs/03` memakai `employee`, `work_order`, `daily_plan`).
- Supabase guide (ADR 0003 A6, R10): bungkus fungsi konteks dalam `(select ...)` agar di-cache per pernyataan, misalnya `USING (division_id = ANY((SELECT string_to_array(current_setting('app.division_ids', true), ','))::uuid[]))`. Ini mengurangi pemanggilan fungsi per baris.
- **Indeks** pada kolom yang difilter policy (`division_id`), agar RLS tidak membuat sequential scan.
- Fungsi `SECURITY DEFINER` wajib `SET search_path` dan dicek (riset 02 §2.2 pgrls). Pakai `SECURITY INVOKER` bila memungkinkan.
- View melewati RLS jika dibuat oleh pemilik. Hindari view yang membaca tabel inti tanpa `security_invoker` (PostgreSQL 15+).
- Admin lintas kantor (OM) membutuhkan policy khusus yang eksplisit (riset 02 B-1).

### 3.4 Tes RLS (wajib)
- Query tanpa konteks mengembalikan **0 baris** (`docs/03` Migrasi, ADR 0001 keputusan 9e).
- Dua divisi: peran divisi A tidak melihat baris divisi B; ID lintas divisi mengembalikan 404 di API.
- Tes harus memakai `vms_app` (non-superuser). Superuser melewati RLS dan membuat tes palsu hijau.
- Jalankan hanya di `vms_test`, atas perintah user.

### 3.5 Urutan pilot
Riset 02 B-1: pilot dua tabel (`file_object` dan `app_activity_logs`), lalu perluas bertahap. Riset 02 menyarankan RLS setelah scope terpusat di service (agar lapisan kode dan database tidak saling menimpa).

Risiko yang harus diingat:
- Job tanpa konteks mendapat 0 baris. Pakai `vms_job` dengan BYPASSRLS atau set konteks eksplisit.
- Setiap kueri membawa predikat RLS; pastikan indeks.
- `pg_dump` dengan `row_security` default; cadangan harus dijalankan sebagai peran yang tepat.

## 4. Enkripsi kolom sensitif

### 4.1 Pola (ADR 0001 keputusan 10; `docs/06`)
- Algoritma: AES-256-GCM di aplikasi (library `cryptography`, sudah ada di `security.py:19`).
- Format nilai tersimpan: `key_id || nonce(12 byte) || ciphertext+tag` dalam `bytea`. Key id di depan memungkinkan rotasi kunci.
- Nonce acak 96-bit per nilai. Jangan pakai nonce yang sama dengan kunci yang sama.
- Kunci dari rahasia terpasang (Docker secret atau berkas di luar git). Bukan dari DB, bukan dari git, bukan dari environment yang ikut ke image.
- **Tanpa KMS** (ADR 0001 keputusan 4).

Contoh kolom:
```sql
ALTER TABLE employee ADD COLUMN nik_enc bytea NULL;
ALTER TABLE employee ADD COLUMN nik_bidx bytea NULL;   -- blind index HMAC-SHA256
CREATE UNIQUE INDEX ux_employee_nik_bidx ON employee (nik_bidx) WHERE nik_bidx IS NOT NULL AND delete_at IS NULL;
```

### 4.2 Blind index
- HMAC-SHA256 dengan kunci terpisah dari kunci enkripsi (`hmac.new(key, nilai, sha256)`).
- Pencarian persis: hitung blind index dari input lalu cocokkan. Tidak ada pencarian awalan.
- Nilai ternormalisasi dulu (tanpa spasi atau tanda hubung) sebelum HMAC, konsisten di semua jalur tulis.

### 4.3 Tampilan dan akses
- Default dimask: hanya 4 digit terakhir (`docs/06`, ADR 0001 keputusan 10).
- Nilai penuh hanya HR dan Super Admin. Setiap akses dicatat di audit dengan aksi "lihat data sensitif".
- Tidak ada nilai sensitif di log, galat, atau ekspor tanpa izin. Atur `hide_parameters=True` pada engine agar parameter SQL tidak tercetak (riset 02 A-7; belum ada di `session.py`).

### 4.4 Yang belum ada (bukti)
- NIK dan rekening: belum terenkripsi (riset 01 T12). Tidak ada `pgp_sym_encrypt` meskipun `pgcrypto` dibuat (`06:9`).
- `face_embedding JSONB` (`06:109`): teks biasa. Target: enkripsi aplikasi, dan jangan tulis embedding ke log.

### 4.5 Migrasi data sensitif (Target)
Expand: tambah kolom `_enc` dan `_bidx`. Migrate: skrip dibatch yang membaca nilai lama, mengenkripsi, mengisi kolom baru, dan menghapus nilai lama setelah verifikasi. Contract: `DROP` kolom lama di rilis berikutnya. Simpan cadangan kunci terpisah; kehilangan kunci berarti data hilang (riset 02 B-7).

## 5. Checklist RLS dan enkripsi

- [ ] Peran aplikasi `vms_app`: `rolsuper=false`, `rolbypassrls=false`, bukan owner.
- [ ] Setiap tabel inti: `ENABLE` dan `FORCE`, policy memakai fungsi cakupan yang sama dengan service.
- [ ] Konteks di-set `SET LOCAL` di awal transaksi (bukan di repository).
- [ ] Indeks pada kolom yang difilter policy.
- [ ] Tes: 0 baris tanpa konteks; lintas divisi tidak terlihat; memakai `vms_app`.
- [ ] Kolom NIK dan rekening terenkripsi; blind index untuk pencarian persis.
- [ ] Kunci dari rahasia terpasang; cadangan kunci disimpan terpisah.
- [ ] Tidak ada nilai sensitif di log atau galat.
