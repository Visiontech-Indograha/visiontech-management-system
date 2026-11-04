# Migrasi Alembic: expand, migrate, contract (vms-db)

Sumber: PDF 13.2 (baris 1747-1757), ADR 0001 keputusan 2, `docs/03` (Migrasi), `docs/06` (Rilis langkah 4-5), riset 01 T26, riset 02 §2.3. Dokumentasi: Alembic `autocommit_block` (https://alembic.sqlalchemy.org/en/latest/api/runtime.html, akses 2026-11-04). pgroll (https://github.com/xataio/pgroll, akses 2026-11-04). squawk (https://github.com/sbdchd/squawk, dirujuk ADR 0003 R8). strong_migrations (https://github.com/ankane/strong_migrations, daftar aturan, ADR 0003 R7).

## 1. Kondisi sekarang (bukti)

- `api/alembic_v2/versions/`: 19 migrasi `v2_0001` … `v2_0019` (head `v2_0019`, `test_alembic_v2.py`).
- Semua migrasi punya `downgrade()` (riset 01 F-35). `DROP COLUMN` hanya di `downgrade()`, misalnya `v2_0008_mess_master_requests.py:83-86`.
- Tidak ada `CONCURRENTLY` (0 kecocokan). `autocommit_block` hanya 2 kali.
- `v2_0003_performance_composite_indexes.py:21-31`: `CREATE INDEX IF NOT EXISTS` biasa. Ini baseline; jangan diubah. Migrasi baru wajib berbeda.
- DDL startup `migration_v3.py:83-117` dan `lifespan.py:24-33`: partisi dibuat di luar Alembic. Pindahkan.
- Tes `test_sql_rules.py` memindai `ROOT/app` saja (`:67`), tidak memindai migrasi. Aturan `CREATE INDEX` tanpa `CONCURRENTLY` (R-31) belum ditegakkan untuk migrasi (riset 01 F-34).
- `env.py:17`: `MIGRATION_DATABASE_URL` dipakai bila ada, lalu `DATABASE_URL`. Ini bagus: peran migrasi bisa dibedakan. Pastikan produksi memakai peran migrasi terpisah (`vms_migrator`).

## 2. Aturan migrasi baru

1. **Tiga fase, dalam rilis berbeda bila perlu:**
   - *Expand*: tambah kolom `NULL` (tanpa default berat), tambah tabel, tambah indeks `CONCURRENTLY`. Kode baru menulis ke kolom lama dan baru bila perlu.
   - *Migrate*: backfill dalam batch (mis. 1.000-5.000 baris per transaksi) dengan skrip atau job. Ubah kode baca ke kolom baru.
   - *Contract*: `SET NOT NULL`, `DROP` kolom lama, hanya setelah tidak ada versi lama yang berjalan (`docs/06`: kolom lama dihapus rilis N+1 atau sesudahnya).
2. **Constraint NOT NULL pada tabel besar**: `ADD CONSTRAINT ck_… CHECK (kolom IS NOT NULL) NOT VALID;` lalu `VALIDATE CONSTRAINT ck_…;` lalu `ALTER COLUMN … SET NOT NULL;` (PG 12+ melewati scan bila CHECK valid).
3. **Foreign key**: `ADD CONSTRAINT … NOT VALID`, lalu `VALIDATE CONSTRAINT`.
4. **Indeks**: `CREATE INDEX CONCURRENTLY` di luar transaksi. Gagal di tengah bisa meninggalkan indeks `INVALID`; cek dengan `pg_index.indisvalid` dan hapus dengan `DROP INDEX CONCURRENTLY`.
5. **Tanpa `ALTER COLUMN … TYPE`** pada tabel besar; buat kolom baru dan migrasikan.
6. **Tanpa `DROP` dan penambahan dalam migrasi yang sama.**
7. **Tiap migrasi mendukung `downgrade()`** bila memungkinkan. Bila tidak, tulis alasan di docstring dan tandai "tidak dapat dibalik" (`docs/06` Rilis langkah 5).
8. **Migrasi statis**: tanpa data dinamis dari aplikasi atau waktu sekarang di dalam migrasi (riset 02 §2.3, ide dari `zhanymkanov`).

## 3. Contoh (pola, jangan dijalankan)

### 3.1 Indeks unik parsial untuk refresh token (riset 01 F-04)
```python
"""Tambah indeks refresh_token_hash (expand, tanpa kunci tabel)."""
from alembic import op

revision = "v2_0020"
down_revision = "v2_0019"

def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_user_sessions_refresh_hash "
            "ON user_sessions (refresh_token_hash) WHERE delete_at IS NULL"
        )

def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ux_user_sessions_refresh_hash")
```
Catatan: nama revisi `v2_0020` hanya contoh. Ikuti penomoran yang berlaku di repo. `CONCURRENTLY` tidak bisa di dalam transaksi Alembic; blok `autocommit_block` menyelesaikannya. Lihat juga peringatan dokumentasi bahwa transaksi sebelum blok di-commit tanpa syarat (sebaiknya `transaction_per_migration` di `env.py`).

### 3.2 Kolom baru NOT NULL dengan backfill bertahap
```python
def upgrade() -> None:
    op.add_column("attendance", sa.Column("evidence_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    # backfill dilakukan di job terpisah, dibatch; migrasi ini tidak mengisi data
```
Pengetatan `NOT NULL` dibuat di rilis berikutnya setelah backfill selesai.

### 3.3 Partisi bulanan dari Alembic (menggantikan DDL startup)
- Buat migrasi yang membuat partisi 2 bulan ke depan.
- Job terjadwal (cron di container DB atau task aplikasi) membuat partisi bulan berikutnya dan mengarsipkan partisi lama. Retensi default 24 bulan (riset 02 B-2, usulan).
- Partisi default tetap dipantau.

## 4. Lint migrasi (Target)

- squawk (`https://github.com/sbdchd/squawk`) memeriksa SQL migrasi: `CREATE INDEX` tanpa `CONCURRENTLY`, `ADD COLUMN ... NOT NULL` tanpa default, `ALTER TYPE`, dan lainnya. Pasang sebagai langkah CI yang membaca file baru di `alembic_v2/versions/`. Status: direncanakan (ADR 0003 A4, belum dipasang).
- Tes ringan (riset 02 B-3): tes Python yang memindai migrasi baru untuk pola terlarang, mirip `test_sql_rules.py`, dengan daftar `KNOWN` hanya untuk baseline `v2_0001`-`v2_0019`.

## 5. Rollback dan rilis

- Rollback aplikasi cukup bila migrasi kompatibel mundur (`docs/06` Rilis langkah 5). Skema tidak di-downgrade otomatis.
- Sebelum migrasi: `pg_dump` berlabel versi (`docs/06` langkah 3a).
- Deploy memastikan `alembic current` sama dengan head rilis (`docs/06` Versi).
- Uji migrasi di DB uji `vms_test`: `alembic upgrade head` dari kosong, lalu `downgrade -1` bila dapat dibalik. Jalankan hanya atas perintah user.

## 6. pgroll (alternatif, belum dipakai)

- pgroll membuat versioned schema (view) dan menjalankan `start`, `complete`, `rollback`. Versi lama dan baru dapat berjalan bersamaan. Syarat PostgreSQL 14+ (dokumentasi pgroll, akses 2026-11-04).
- Klien memilih versi lewat `search_path`. APK lapangan lama memakai jalur yang sama; perlu uji dulu sebelum dipakai.
- Keputusan: disiplin expand-contract dengan Alembic cukup untuk sekarang (riset 02 §2.3).

## 7. Checklist migrasi

- [ ] Revisi baru berantai dari head (`down_revision` benar); `test_alembic_v2.py` diperbarui bila head berubah.
- [ ] Indeks `CONCURRENTLY` di `autocommit_block`.
- [ ] `NOT NULL` lewat `NOT VALID` lalu `VALIDATE`.
- [ ] Tidak ada `DROP`/`RENAME`/`ALTER TYPE` di migrasi yang menambah sesuatu.
- [ ] `downgrade()` ada atau alasan tertulis.
- [ ] Backfill di batch dan di job terpisah.
- [ ] Uji di `vms_test` atas perintah user.
- [ ] `pg_dump` sebelum rilis.
