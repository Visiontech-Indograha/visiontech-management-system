# Big O, query, dan pagination (API VMS)

Sumber: panduan PDF bagian 1 (baris 13-97), bagian 3.1-3.2 (baris 201-230), bagian 4.4 (baris 414-493). Bukti kode dari worktree `origin/beta` (2026-11-04).

## 1. Big O yang dipakai di API

| Notasi | Contoh di VMS | Catatan |
|---|---|---|
| O(1) | Lookup `dict`/`set` untuk kelompok tim/sel | `survey_service.py:112-114`, `daily_plan_service.py:377-380` |
| O(log n) | Index seek B-tree | `idx_work_plan_daily_team` (db/06) |
| O(n) | Sequential scan; `apply_list` memuat semua | `list_params.py:58` |
| O(n·k) | Filter `_fold` per kolom di Python | `list_params.py:61-63` |
| O(n) kueri | N+1 per baris | `daily_plan_service.py:137-147` (`check_daily_access` per baris) |

Aturan praktis: hitung jumlah kueri dan baris yang disentuh, bukan hanya jumlah baris kode. Satu kueri per item di dalam loop adalah N+1, walau kodenya terlihat rapi.

## 2. N+1 dan batching

Anti-pola nyata:
- `daily_plan_service.py:322-343`: loop tim × tanggal. Tiap sel memanggil `_bulk_cell_problem` (`:303-311`, 3 kueri), `_cell_warnings` (`:347-359`, 1 kueri per aset). Batas input 30 tim × 31 tanggal × 20 aset (`daily_plan_schema.py:119-129`).
- `sync_service.py` (riset F-08): tiga round trip per operasi offline (enqueue, savepoint, mark).

Perbaikan:
- Ambil data sekaligus: `WHERE team_id = ANY(:ids)` atau `IN (...)`/`unnest` untuk tim, jadwal, cuti, dan bentrok aset.
- Insert batch: `INSERT ... SELECT` atau `executemany`.
- Pertahankan urutan dan aturan `SKIPPED` dan `warnings` persis seperti sebelumnya. Uji dengan data campuran.
- Batasi kombinasi sel per permintaan (mis. 200). Lebih dari itu → 422.

Eager loading di SQLAlchemy 2.0: `selectinload` untuk koleksi, `joinedload` untuk satu relasi (PDF 4.4, baris 454-456). Repositori VMS memakai SQL mentah (`text()`), jadi pola ini berlaku untuk ORM baru saja.

## 3. Pagination

### 3.1 Yang ada sekarang
- `ListParams`: `q` (maks 100 karakter), `page` (1..100000), `size` (1..100, bawaan 20). Salah satu `page` atau `size` mengaktifkan paginasi. Tanpa keduanya = semua baris (bukti: `list_params.py:28-40`).
- `apply_list`: filter di Python, lalu potong (`list_params.py:49-68`). Biaya O(n) per request.
- `OFFSET` masih ada di empat kueri lama (`audit_repository.py:84`, `attendance_session_repository.py:953`, `employee_repository.py:86`, `work_completion_core_repository.py:243`). Semuanya tercatat di `KNOWN` dan hanya boleh berkurang.

### 3.2 Target
- **Keyset/cursor** untuk daftar besar (audit, absensi, notifikasi):
  ```sql
  SELECT id, created_at, ...
  FROM app_activity_logs
  WHERE (created_at, id) < (:cursor_created_at, :cursor_id)
  ORDER BY created_at DESC, id DESC
  LIMIT :size
  ```
  Indeks pendukung: `(created_at DESC, id DESC)` pada partisi. Biaya: O(log n) seek + O(ukuran halaman). Koreksi: PDF menulis O(1) (baris 227-230), padahal seek B-tree itu O(log n).
- **Kontrak**: cursor opsional di `ListParams` (mis. `after=<base64(created_at,id)>`); tanpa parameter = perilaku lama. Respons pakai `X-Next-Cursor`. `X-Total-Count` tidak dihitung untuk keyset (mahal); tampilkan "perkiraan" bila perlu.
- **Total**: `COUNT(*) OVER()` dalam satu kueri untuk daftar kecil. Untuk log besar, pakai estimasi `pg_class.reltuples` atau batas rentang tanggal default (riset F-10).
- **Batas**: setiap daftar punya `LIMIT` maksimum (`MAX_PAGE_SIZE=100` untuk paginasi; ≤ 500 untuk daftar referensi tanpa paginasi).
- **Urutan logis SQL** (PDF 3.1, baris 211-213): FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT. Alias di SELECT tidak bisa dipakai di WHERE.

## 4. Indeks yang harus ditinjau saat menulis kueri

Catat pola kueri, lalu cocokkan dengan indeks (lihat `vms-db`):
- Filter kesamaan + urutan waktu: indeks komposit `(kolom_filter, created_at DESC, id)`.
- Leftmost prefix: `INDEX(user_id, status)` tidak dipakai untuk `WHERE status = ...` saja (PDF 3.2).
- Kolom filter tanpa indeks yang cocok: `attendance_date = :d` tanpa `employee_id` (riset F-11), `refresh_token_hash` (riset F-04).
- Verifikasi dengan `EXPLAIN (ANALYZE, BUFFERS)` di `vms_test` atas perintah user. Jangan jalankan `ANALYZE` pada data produksi.

## 5. Async vs sync

- `async def` hanya bila memanggil `await` (asyncpg, httpx.AsyncClient). Jika memanggil pustaka blocking, pakai `def` (FastAPI menjalankannya di threadpool) atau `await asyncio.to_thread(fn, ...)`. (FastAPI docs, https://fastapi.tiangolo.com/async/, akses 2026-11-04.)
- Yang harus dibungkus di VMS:
  - Argon2: `auth_service.py:145` (`verify_password`), `:314`, `:322` (`hash_password`); `account_service.py:118`, `:169`.
  - Builder dokumen dan slide: `export_service.py:148`, `:165`, `:313`, `:438` (riset F-18). Pemanggilan yang sudah benar: `:220`, `:238`, `:452`, `:479`.
- Objek ORM atau session DB tidak boleh dipakai dari thread lain. Ambil data dulu di async, lalu serahkan data biasa (dict, bytes) ke thread.

## 6. Caching dan memoization

- Tidak ada Redis di compose. Cache HTTP ada di `teams/routes/team_route.py:177` (`private, no-cache`) dan `system/routes/media_stream_route.py:74`.
- Memoization untuk data referensi kecil yang sering dibaca (mis. daftar peran) boleh dengan `functools.lru_cache` jika datanya tidak berubah per request. Invalidasi harus eksplisit.
- Cache-aside (PDF 8.2) baru dipertimbangkan bila pengukuran menunjukkan perlu. Cache stampede dicegah dengan jitter TTL atau mutex (PDF 3.3, baris 272-275).

## 7. Checklist kueri

- [ ] Kolom eksplisit, bukan `*`.
- [ ] Filter `delete_at IS NULL` dan indeks parsial yang cocok.
- [ ] Pencarian awalan, bukan `%q%`.
- [ ] `LIMIT` ada; tanpa `OFFSET` baru.
- [ ] Tidak ada query di dalam loop; data dibatch.
- [ ] Indeks baru dibuat dengan `CONCURRENTLY` di migrasi baru (lihat `vms-db`).
- [ ] Urutan hasil stabil (`ORDER BY ... , id`).
