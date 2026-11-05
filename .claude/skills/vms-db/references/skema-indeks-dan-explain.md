# Skema, indeks, dan EXPLAIN (vms-db)

Sumber: PDF bagian 3.1-3.2 (baris 201-230), bagian 8.2 (baris 912-921), bagian 19 (baris 2192-2208). Dokumentasi resmi: PostgreSQL 18 `functions-uuid` (https://www.postgresql.org/docs/18/functions-uuid.html, akses 2026-11-04). pev2 (https://github.com/dalibo/pev2, akses 2026-11-04 melalui riset 02).

## 1. Tipe data

| Kebutuhan | Standar | Bukti/catatan |
|---|---|---|
| Uang | `NUMERIC(12,2)` | Ada: `06:87-88`, `:572`; `08:77`. Riset 01 T2 |
| Waktu | `TIMESTAMPTZ` | Ada: `06:558`, `:144` |
| ID | `uuid`; `uuidv7()` untuk tabel baru | Sekarang `gen_random_uuid()` (`06:77`, dst.) |
| Status | `TEXT` + `CHECK` | Target `docs/03` |
| Biometrik | Terenkripsi (Target) | `06:109` JSONB teks biasa |

Hitungan kapasitas (PDF 8.2, dicek ulang di riset 01 bagian 1): 1 hari ≈ 86.400 detik; 10 juta DAU × 20 baca = 2.000 QPS baca rata-rata, 6.000 puncak; 200 TPS tulis. Untuk VMS (ratusan karyawan, satu server 4 GB) angka ini jauh di bawah kapasitas; gunakan hanya untuk memahami pola, bukan untuk merancang sharding.

## 2. UUIDv7

- PostgreSQL 18 menyediakan `uuidv7()` dan `uuidv7(shift interval)`. Timestamp 48-bit milidetik, urut waktu, sehingga indeks B-tree lebih rapat (dokumentasi PG18, akses 2026-11-04).
- Pola: `id uuid PRIMARY KEY DEFAULT uuidv7()` untuk tabel baru. Tabel lama tidak diubah.
- Campuran UUIDv4 dan v7 pada FK tidak masalah. Jangan menebak urutan dari UUIDv4.
- Untuk ID yang dibuat di aplikasi (sebelum INSERT), gunakan library UUID7 Python. Pastikan library memakai layanan yang sama dengan `uuidv7()` agar tidak ada konflik format.

## 3. Indeks

### 3.1 Jenis dan kapan dipakai

| Jenis | Kapan | Contoh VMS |
|---|---|---|
| B-tree | kesamaan, rentang, urutan | `idx_work_plan_daily_team` (`db/06:771`) |
| Komposit | filter beberapa kolom; urutan kolom mengikuti kueri | `attendance(employee_id, attendance_date)` (`v2_0003:21`) |
| Parsial | hanya baris aktif (`delete_at IS NULL`) atau kondisi status | `ix_notification_user_created` (`06:513`) |
| Unik parsial | invariant bisnis | `uq_work_plan_daily_team_day` (`06:773`) |
| Covering (`INCLUDE`) | menghindari heap fetch | Pakai bila EXPLAIN menunjukkan heap fetch |
| GIN/trigram (`pg_trgm`) | pencarian mengandung kata | Belum; keputusan pemilik (R-31) |
| GiST | geografi, rentang waktu | Belum; PostGIS ada di image |
| HNSW (pgvector) | pencarian vektor | Belum; tidak dipakai |

### 3.2 Aturan leftmost prefix (PDF 3.2)
`INDEX(user_id, status)`:
- dipakai: `WHERE user_id = 10`, `WHERE user_id = 10 AND status = 'PAID'`.
- tidak dipakai: `WHERE status = 'PAID'` saja.

Pada VMS: `attendance_date = :d` tanpa `employee_id` (monitor harian) tidak memakai indeks komposit (riset 01 F-11). Tambahkan indeks `(attendance_date)` parsial bila pola ini sering.

### 3.3 Kekurangan yang tercatat
- `user_sessions.refresh_token_hash` tanpa indeks (`db/06:139`). Setiap refresh melakukan sequential scan. Perbaikan: unique parsial `CONCURRENTLY` (lihat `migrasi-expand-contract.md`, contoh).
- `app_activity_logs`: indeks hanya `idx_activity_logs_entity (entity_table, entity_id)` (riset 01 F-10). Pola `ORDER BY created_at DESC` butuh indeks `(created_at DESC, id DESC)` per partisi.
- Foreign key tanpa indeks: periksa FK di `06` dan `08` satu per satu sebelum menambah tabel baru. ADR 0003 A5: indeks penuh pada setiap kolom FK.

### 3.4 Aturan membuat indeks
- Buat dengan `CONCURRENTLY` di migrasi baru (`autocommit_block()`). Tanpa `CONCURRENTLY`, tabel terkunci untuk tulis selama pembuatan.
- Jangan buat indeks tanpa kueri yang memakainya. Catat kueri di komentar migrasi.
- Nama: `ix_<tabel>_<kolom>` (Target) atau nama sejenis yang konsisten.

## 4. EXPLAIN ANALYZE

Membaca rencana (PDF 3.2 baris 220-222):
- `Index Scan` atau `Index Only Scan`: O(log n) + baris yang diambil.
- `Seq Scan` pada tabel besar: O(n). Sah untuk tabel kecil.
- `Bitmap Heap Scan`: banyak baris, indeks dipakai lalu heap diambil.
- `Rows Removed by Filter` besar: indeks belum mencakup filter.
- Estimasi baris (`rows=`) jauh dari `actual rows=`: jalankan `ANALYZE` pada tabel (statistik basi).

Perintah:
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, created_at FROM app_activity_logs
WHERE entity_table = 'attendance'
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
Simpan hasil JSON dan buka di pev2. Jalankan hanya di `vms_test` dan atas perintah user. `ANALYZE` pada data produksi membebani RAM (riset 02 B-4).

## 5. Partisi

- Tabel `app_activity_logs` dipartisi `RANGE (created_at)` (`06:667-685`). Partisi bulan berjalan dan bulan depan dibuat saat startup (`migration_v3.py:83-117`).
- Pindahkan pembuatan partisi ke Alembic atau job terjadwal (lihat `migrasi-expand-contract.md`).
- Retensi: `ALTER TABLE ... DETACH PARTITION ...` lalu arsip (`pg_dump` atau `COPY`), lalu `DROP`. Jangan `DELETE` massal.
- Partisi default (`app_activity_logs_default`, `migration_v3.py:99`) menampung baris di luar rentang. Pantau agar tidak membesar.

## 6. Normalisasi dan desain

- 3NF untuk data transaksi (PDF 3.1). Denormalisasi hanya untuk pembacaan yang terukur.
- Relasi tanpa FK hanya dengan alasan tertulis.
- Enum sebagai `TEXT` + `CHECK` (`docs/03`).
- Soft delete: jangan membuat `UNIQUE` biasa yang bentrok dengan baris terhapus. Gunakan unik parsial `WHERE delete_at IS NULL`.
- Kolom audit: `created_at`, `updated_at` (Target), dan `delete_at`/`deleted_at`. Campuran `create_at`/`update_at` dan `created_at` di log (riset 01 T25) dirapikan saat menyentuh tabel.

## 7. Urutan eksekusi SQL (untuk optimasi)

FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT/OFFSET (PDF 3.1). Akibatnya:
- Alias kolom dari SELECT tidak bisa dipakai di WHERE.
- Filter di WHERE sebelum join menghemat baris.
- `LIMIT` berlaku setelah sort; sort besar tanpa indeks tetap O(n log n).

## 8. Checklist (skema dan indeks)

- [ ] Uang `NUMERIC(12,2)`, waktu `TIMESTAMPTZ`.
- [ ] PK `uuidv7()` untuk tabel baru.
- [ ] Setiap FK punya indeks.
- [ ] Indeks parsial untuk baris aktif bila tabel sering dibaca dengan soft delete.
- [ ] Indeks baru punya kueri pendukung dan `CONCURRENTLY`.
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` dicatat (di `vms_test`, atas perintah).
