---
name: vms-api
description: >-
  Pakai skill ini untuk setiap pekerjaan pada API FastAPI VMS (folder api/): membuat atau mengubah endpoint, route, controller, service, repository, schema Pydantic, daftar dengan ListParams/apply_list, pencarian q, paginasi, transaksi dan locking (FOR UPDATE, kondisi status pada UPDATE), Idempotency-Key, izin require_permission, cakupan divisi/tim, keamanan (Argon2id, JWT EdDSA, OWASP API Top 10, BOLA/IDOR), penanganan galat berbahasa Indonesia, log JSON dan correlation id, tes pytest (matriks peran, tes konkurensi), kontrak OpenAPI dan generator tipe web. Kata kunci: FastAPI, endpoint, API, router, service, repository, query, SQL, N+1, indeks, pagination, cursor, keyset, idempotency, race condition, transaksi, lock, otorisasi, IDOR, BOLA, rate limit, observability, Big O, performa, api, backend, uji API.
---

# vms-api · FastAPI berlapis VMS

Skill ini menjaga API VMS tetap sesuai aturan proyek, praktik produksi dari panduan PDF, dan temuan audit nyata. Basis: kode `api/` di repo ini (cabang `origin/beta`, diperiksa 2026-11-04). Target arsitektur mengikuti `vms-next/docs/01`, `06`, dan ADR 0001 (path lokal `C:\Users\ageng\visiontect-vms\vms-next\docs\`).

Aturan membedakan dua hal:
- **Kode saat ini**: apa yang benar-benar ada di `api/` sekarang. Dinyatakan dengan `(bukti: file:baris)`.
- **Target**: standar yang disepakati untuk perubahan baru, dari dokumen VMS Next dan panduan PDF. Dinyatakan dengan `Target:`.

Setiap klaim dari sumber luar memakai tautan dan tanggal akses 2026-11-04 (lihat `references/sumber-dan-tautan.md`).

## 1. Aturan keras (jangan dilanggar)

1. **Tanpa `LIKE '%…'` atau `ILIKE '%' || :q`** (wildcard di depan). Pencarian = awalan (`ILIKE :q || '%'`). Aturan R-31 di `api/tests/architecture/test_sql_rules.py`.
2. **Tanpa `OFFSET` baru.** Daftar baru memakai keyset/cursor `(created_at, id)`. Dilarang menambah baris `KNOWN` di `test_sql_rules.py`. Daftar `KNOWN` hanya boleh menyusut.
3. **Tanpa `SELECT *`**, `RETURNING *`, dan `NOT IN (SELECT …)`. Tulis nama kolom.
4. **Daftar API**: pakai `ListParams` (`?q=&page=&size=`) dan header `X-Total-Count`. Tanpa parameter = perilaku lama. APK lapangan lama harus tetap jalan.
5. **Validasi query** lewat `Query(max_length=…, ge=…, le=…)`, dan rentang tanggal lewat `check_date_range` (`api/app/core/list_params.py:20-25`). Batas input web dan mobile harus sama dengan batas API.
6. **Router tipis.** Router tidak menyentuh DB (`test_router_layering.py`: `LEGACY` kosong). SQL hanya di repository.
7. **Repository tidak commit.** Batas transaksi di service/controller.
8. **Setiap rute punya izin**: `require_permission` (`api/app/api/deps.py:176`) atau penjaga kepemilikan di handler yang didaftarkan di `test_route_guards.py` (V-09). Menambah pengecualian = keputusan keamanan.
9. **404, bukan 403**, untuk objek yang tidak boleh diketahui keberadaannya (Target: `docs/06` Otorisasi).
10. **Jangan kirim hash sandi, embedding wajah, token, NIK mentah, atau email di log/respons** (Target: `docs/06`, ADR 0001 keputusan 5 dan 10).
11. **Jangan `async def` untuk kode sinkron yang lama.** Argon2, builder dokumen, dan CPU berat dibungkus `asyncio.to_thread` atau dibuat `def` (FastAPI menjalankan `def` di threadpool, lihat `references/sumber-dan-tautan.md`).
12. **Tes DB hanya ke `vms_test`** (atau host lokal dengan nama `*_test`). Lihat `api/tests/db_guard.py:16-25`. Jangan pernah menjalankan tes ke DB dev atau produksi.
13. **Tes dan pytest hanya atas perintah user** (memori `defer-test-writing`). Tulis tes boleh; jalankan tidak sebelum diminta.

## 2. Peta kode (bukti)

| Lapis | Lokasi | Catatan |
|---|---|---|
| Aplikasi | `api/app/main.py` | `API_PREFIX="/api/v1"` (baris 26); `/health` (59), `/ready` (69), `/api/v1/version` (64) |
| Dependency izin | `api/app/api/deps.py` | `require_permission` (176), `require_any_permission` (193) |
| Daftar | `api/app/core/list_params.py` | `ListParams` (28-40), `apply_list` (49-68), `MAX_PAGE_SIZE=100` (16) |
| Cakupan & akses | `api/app/shared/access/access_service.py` | `require_daily_status` (65), `check_daily_access` (74), `ensure_same_org` (153) |
| Modul | `api/app/modules/<fitur>/` | `routes/`, `controllers/`, `services/`, `repositories/`, `schemas/`, `tests/` (ADR 0001 keputusan 13) |
| Sesi DB | `api/app/database/session.py` | pool (51-53), `set_config` konteks (107-112) |
| Logging | `api/app/core/logging_config.py` | `request_id_context` (19), `JSONFormatter` (22), `RequestIDMiddleware` (49) |
| Auth | `api/app/modules/auth/services/auth_service.py` | `ACCESS_TOKEN_TTL` 15 menit (25) |
| Keamanan | `api/app/core/security.py` | `_ALGORITHM="EdDSA"` (30); `hash_password` (46); `verify_password` (50, ada fallback bcrypt seed) |
| Unggahan | `api/app/modules/system/controllers/files_controller.py` | lihat `vms-storage-minio` |

Jumlah endpoint mutasi (dihitung dari `@router.<metode>(` di `api/app/modules`): POST 121, PUT 31, PATCH 5, DELETE 32 = **189**.

## 3. Alur kerja saat menambah atau mengubah endpoint

Ikuti urutan ini. Setiap langkah punya checklist di `references/`.

1. **Kontrak dulu**: tentukan path, metode, izin, schema input/output, status galat (422, 403/404, 409). Dokumentasikan di docstring route. Lihat `references/pengujian-kontrak-dan-galat.md`.
2. **Izin & cakupan**: pasang `require_permission`. Untuk objek, panggil pemeriksaan cakupan di service (`check_daily_access`, `ensure_same_org`). Lihat `references/keamanan-dan-otorisasi.md`.
3. **Query**: tulis SQL dengan kolom eksplisit, indeks yang dipakai, dan pagination SQL. Lihat `references/big-o-query-dan-pagination.md`.
4. **Transaksi**: bila ada transisi status, uang, stok, atau kuota, pakai `FOR UPDATE` atau `UPDATE … WHERE status = :expected` dan cek `rowcount`. Lihat `references/transaksi-locking-idempotensi.md`.
5. **Idempotensi**: endpoint tulis dari klien offline atau dari retry wajib `Idempotency-Key` (Target). Lihat referensi yang sama.
6. **Tes**: tulis tes peran × endpoint × ID lintas divisi, dan tes konkurensi untuk jalur kritis. Jangan jalankan sebelum diminta. Lihat `references/pengujian-kontrak-dan-galat.md`.
7. **Kontrak web/mobile**: ubah skema → `UPDATE_OPENAPI_SNAPSHOT=1 pytest` (atas perintah user), lalu `cd web && npm run gen:api:export && npm run gen:api`.
8. **Rilis**: perubahan kontrak mengikuti SemVer (`VERSION`, `CHANGELOG.md`, `scripts/versi.sh --tulis`). Breaking = MAJOR, fitur = MINOR, perbaikan = PATCH. Lihat `CLAUDE.md` proyek.

## 4. Big O dan kinerja API (ringkas)

Rincian dan contoh ada di `references/big-o-query-dan-pagination.md`.

- **Hash/set untuk pencarian kunci**: O(1). Sudah dipakai di `work_plans` (bukti: `survey_service.py:112-114`, `daily_plan_service.py:377-380`). Kelompokkan dengan `dict` dan jangan `in list` di dalam loop.
- **Indeks B-tree**: O(log n). Indeks komposit mengikuti leftmost prefix (PDF bagian 3.2, baris 215-219).
- **Masalah nyata: `apply_list` memuat seluruh tabel** lalu memfilter dan memotong di Python (bukti: `list_params.py:58` `rows = list(items)`, `:61-63` filter `_fold`, `:65-67` potong). Biaya O(n) per request, padahal pengguna meminta 20 baris. Target: `q`, `LIMIT/OFFSET` (atau keyset), dan `COUNT(*) OVER()` didorong ke SQL dengan kontrak yang sama.
- **N+1 nyata**: bulk jadwal memanggil `_bulk_cell_problem` dan `_cell_warnings` per sel (`daily_plan_service.py:303-311`, `:322-343`, `:347-359`). Batas 30 tim × 31 tanggal × 20 aset (`daily_plan_schema.py:119-129`) berarti kasus terburuk puluhan ribu kueri (perkiraan teoretis, bukan hasil profiling). Perbaikan: ambil data dalam satu kueri `IN (...)`/`unnest`, lalu insert batch.
- **Cursor pagination**: O(log n) untuk seek di B-tree, ditambah O(ukuran halaman). Bukan O(1) seperti tertulis di PDF baris 227-230 (koreksi riset 01 bagian 6).
- **Async vs sync**: `async def` hanya bila memanggil `await` I/O. Argon2 sinkron dipanggil di metode async: `auth_service.py:145`, `:314`, `:322`; `account_service.py:118`, `:169`. Builder dokumen sinkron: `export_service.py:148`, `:165`, `:313`, `:438` (bukti dari riset 01 F-17/F-18; verifikasi ulang sebelum diubah).
- **Cache dan Redis**: tidak ada Redis di compose. Rate limit dan idempotensi tidak punya penyimpanan cepat. Keputusan: tabel PostgreSQL sebagai sumber kebenaran; Redis hanya opsional (ADR 0001 keputusan 3 dan 7).

## 5. Transaksi, locking, dan idempotensi (ringkas)

- **Locking yang sudah dipakai**: `FOR UPDATE` di ±12 titik, misalnya `asset_repository.py:292`, `auth_session_repository.py:175` (rotasi refresh), `plan_item_repository.py:69` (rollover). Pola ini sudah dikenal tim.
- **Celah TOCTOU**: approve/submit jadwal membaca status lalu UPDATE tanpa kondisi status. `daily_plan_service.py:462-464` (`approve`) dan `daily_plan_repository.py:309-325` (`set_status`, UPDATE tanpa `AND status = …`). Perbaikan: `UPDATE … WHERE status = ANY(:allowed)`, cek `rowcount`; 0 baris = 409.
- **PM override status order** tanpa kondisi: `work_completion_core_repository.py` (`update_status`, riset F-13).
- **Idempotency**: hanya untuk sinkron offline lewat `client_op_id` (`attendance_offline_service.py:164-173`). Tidak ada `Idempotency-Key` pada endpoint online (0 kecocokan `idempotency` selain itu, sudah dihitung).
- **Target idempotensi** (ADR 0001 keputusan 7; `docs/06` Idempotensi): endpoint tulis terotentikasi wajib `Idempotency-Key`. Tabel `idempotency_keys` di PostgreSQL adalah sumber kebenaran, TTL 24 jam, disimpan dalam transaksi yang sama dengan aksinya. Redis `SET NX` hanya kunci cepat anti-balapan. Respons login dan refresh tidak disimpan. Key sama + body sama → kembalikan respons tersimpan (200), bukan 409 (koreksi riset 01 bagian 6). Key sama + body beda → 422. Permintaan masih berjalan → 409.

## 6. Keamanan dan otorisasi (ringkas)

Rincian di `references/keamanan-dan-otorisasi.md`.

- **Sudah sesuai**: Argon2id untuk hash baru (`security.py:46-54`); bcrypt hanya untuk hash seed (`security.py:51-54`); JWT EdDSA dan tolak HS256/`alg:none` (`security.py:7`, `:30`); access token 15 menit (`auth_service.py:25`); rotasi refresh dengan `FOR UPDATE OF s` (`auth_session_repository.py:175`); lockout login 15 menit (`auth_session_repository.py:30`).
- **Target** (`docs/06`): access token menyimpan `sid`, `roles`, `jti`, `typ`, `kid`; setiap request memeriksa sesi aktif, sehingga pencabutan langsung berlaku. Refresh token disimpan sebagai SHA-256 di `user_sessions`. Pemakaian ulang = cabut seluruh family (`reuse_detected`).
- **Belum ada**: rate limiter umum (hanya kode 429 di `core/errors.py:140`, riset 01 F-19); timeout dan circuit breaker untuk panggilan keluar (riset 01 T8).
- **Static mount `/uploads` masih aktif** di `api/app/main.py:54-57` pada `origin/beta` (HEAD `d1a3d4e5`). Perbaikannya ada di commit `0c0f98eb` pada cabang `hotfix/uploads-anonim`, dan belum menjadi leluhur `origin/beta` (diverifikasi `git merge-base --is-ancestor`). Jangan pernah menambah mount statis untuk unggahan. Akses file hanya lewat `/api/v1/files/{id}/url` (`files_route.py:60-79`), yang memeriksa akses per berkas.
- **Cakupan divisi**: ada di kode aplikasi (repositori menyebut `division_id`), tanpa helper terpusat dan tanpa RLS (lihat `vms-db`). Audit VMS lama mencatat 7 kebocoran lintas divisi (ADR 0001 keputusan 9, alasan).

## 7. Galat, log, dan observability (ringkas)

- **Galat berbahasa Indonesia**: `detail={"code": "...", "message": "..."}` (contoh `files_controller.py:59-62`, `:73-75`). Kode galat stabil; pesan untuk pengguna. Jangan bocorkan stack trace atau SQL.
- **Log JSON** dengan `request_id` sudah ada (`logging_config.py:19-62`). Yang belum ada menurut riset 01 T13: `duration_ms`, `http_path`, `status`, `user_id` konsisten. Target: `route` (template, bukan URL berisi ID), `status`, `duration_ms`, `X-Correlation-ID`, `traceparent` diterima (ADR 0001 keputusan 5). Metrik RED/USE dan OpenTelemetry belum ada (0 kecocokan `prometheus|opentelemetry|traceparent`).
- **Health**: `/health` liveness tanpa DB (`main.py:59`). `/ready` cek DB (`main.py:69-79`). Target `docs/06`: `GET /health/live` dan `GET /health/ready` di root, body hanya `{"status":"ok"}` atau `{"status":"degraded"}`; detail hanya untuk pemanggil terotentikasi. Migrasi nama endpoint perlu dikoordinasikan dengan `healthcheck.sh` dan compose.

## 8. Pengujian (ringkas)

Rincian di `references/pengujian-kontrak-dan-galat.md`.

- Piramida (PDF bab 11): static analysis wajib, unit banyak, integrasi ke PostgreSQL nyata, E2E sedikit.
- Tes arsitektur sudah ada: `test_sql_rules.py`, `test_route_guards.py`, `test_router_layering.py`, `test_alembic_v2.py` (head `v2_0019`, baris `assert scripts.get_heads()`), `test_no_select_star.py`, `test_openapi_snapshot.py`.
- **Celah yang terbaca dari kode (belum dijalankan)**: `work_order_repository.py:122-124` (3 kecocokan `ILIKE '%' || :q || '%'`) dan `project_repository.py:44-45` (2 kecocokan) tidak ada di `KNOWN` (`test_sql_rules.py:35-45`). Berdasarkan regex, `test_no_new_forbidden_sql` (`test_sql_rules.py:98`) akan merah. Ini belum diverifikasi dengan pytest.
- **Tes konkurensi belum ada** (0 kecocokan `gather|threading|concurren` di `api/tests`, riset 01 F-14). Tambah tiga tes: dua approve bersamaan, dua rollover bersamaan, dua serah terima aset bersamaan. Hanya satu boleh sukses.
- **Tes matriks peran**: target `docs/06` dan ADR 0001 kriteria: peran × endpoint × ID lintas divisi (404), daftar tidak membocorkan baris lain, dan query tanpa konteks RLS mengembalikan 0 baris.
- **CI**: `ci.yml:86-87` menjalankan `pytest` dan `ci.yml:77-84` menjalankan ruff dan mypy. Belum ada `--cov-fail-under` (riset F-22).

## 9. Kontrak OpenAPI dan generator tipe

- Sumber kebenaran kontrak: FastAPI OpenAPI. Snapshot ada di `api/tests/snapshots/` dan dicek oleh `api/tests/architecture/test_openapi_snapshot.py`. Perubahan kontrak: `UPDATE_OPENAPI_SNAPSHOT=1 pytest` atas perintah user, lalu `npm run gen:api:export` dan `npm run gen:api` di `web/`.
- Respons daftar: `items` dan `X-Total-Count` (header, bukan badan). Jangan mengubah bentuk ini tanpa catatan kompatibilitas.
- Deprecation (Target): header `Sunset: <HTTP-date>` (RFC 8594) dan `Deprecation: @<unix>` (RFC 9745). Format `Deprecation: true` dari PDF tidak dipakai (ADR 0002). Saat ini belum ada (0 kecocokan `sunset|deprecation`).

## 10. Anti-pola nyata (dari audit, dengan bukti)

| Anti-pola | Bukti | Perbaikan |
|---|---|---|
| Mount statis unggahan | `api/app/main.py:54-57` (aktif di beta) | Hapus mount. Akses lewat `/files/{id}/url` |
| Daftar memuat seluruh tabel | `list_params.py:58-67` | Pagination dan `q` di SQL |
| Daftar tanpa `LIMIT` | `project_repository.py:40-46`, `client_repository.py:19-25`, divisi, jabatan (riset F-06) | `LIMIT` maksimum 500 atau pagination; dropdown pakai endpoint opsi |
| Pencarian `%q%` | `work_order_repository.py:122-124`, `project_repository.py:44-45` | Awalan atau trigram/FTS dengan keputusan pemilik |
| UPDATE status tanpa kondisi | `daily_plan_repository.py:309-325` | `WHERE status = ANY(:allowed)` + `rowcount` |
| Pemeriksaan kepemilikan diulang di handler | pola dari `fastapi/full-stack-fastapi-template` (ditolak sebagai acuan, riset 02 §1.2) | Filter cakupan terpusat (service + RLS) |
| Argon2 di event loop | `auth_service.py:145,314,322` | `await asyncio.to_thread(...)` atau `def` |
| Idempotensi hanya offline | `attendance_offline_service.py:164-173` | `Idempotency-Key` pada endpoint tulis |
| Galat generik tanpa kode | sebagian router (riset 01 bagian 2 T25) | `{"code","message"}` seragam |

## 11. Checklist selesai

- [ ] Tidak ada `LIKE '%`, `OFFSET` baru, `SELECT *`, atau `NOT IN (SELECT`.
- [ ] Route punya `require_permission` atau penjaga yang terdaftar di `test_route_guards.py`.
- [ ] Objek lintas divisi dijawab 404; cakupan dicek di service.
- [ ] Daftar memakai `ListParams`; tanpa parameter tetap perilaku lama.
- [ ] Transisi status atau uang memakai `FOR UPDATE` atau `UPDATE … WHERE status` + `rowcount`.
- [ ] Endpoint tulis dari klien offline/retry punya `Idempotency-Key` (atau alasan tertulis).
- [ ] Panggilan sinkron berat dibungkus `to_thread`; panggilan keluar punya timeout.
- [ ] Log tanpa PII/token; `X-Correlation-ID` diteruskan.
- [ ] Galat `{"code","message"}` berbahasa Indonesia.
- [ ] Tes matriks peran dan tes konkurensi ditulis; belum dijalankan kecuali diperintah.
- [ ] `KNOWN` di `test_sql_rules.py` tidak bertambah; kontrak OpenAPI dan generator tipe diperbarui bila skema berubah.
- [ ] Perubahan kontrak: `VERSION` dan `CHANGELOG.md` diperbarui sesuai SemVer.

## 12. Skill global yang boleh dipanggil atau dilebur

Pakai skill ini untuk pekerjaan yang memerlukan keahlian khusus. Jangan menyalin isinya ke sini. Lebur hasilnya ke folder `api/`, `tests/`, dan dokumen proyek.

- **`postman:api-testing`**: menjalankan koleksi Postman terhadap endpoint yang diubah. Lengkapi dengan tes pytest; Postman tidak menggantikan tes arsitektur. Port lokal API 8000 (memori `vms-postman-port`).
- **`postman:api-documentation`**: membuat dokumentasi dari OpenAPI yang sudah ada. Lengkapi dengan kontrak `docs/`, bukan dokumen baru yang terpisah.
- **`postman:ci-integration`**: menambah langkah CI untuk tes API. Lengkapi `ci.yml` yang sudah ada; jangan membuat workflow kedua.
- **`postman:api-engineer`**: panduan desain endpoint. Lengkapi dengan bagian 3 skill ini sebagai urutan kerja.
- **`security-review`**: tinjau perubahan auth, izin, dan unggahan sebelum merge. Lengkapi dengan checklist bagian 6.
- **`simplify`**: merapikan kode yang baru ditulis. Jangan mengubah kontrak atau perilaku ListParams.
- **`code-review`**: tinjau diff sebelum commit. Pakai `--max-findings` sesuai kebutuhan; jangan `max` atau `ultra` kecuali diminta.

## 13. Berkas referensi

- `references/big-o-query-dan-pagination.md`: Big O, N+1, indeks, keyset, batching.
- `references/transaksi-locking-idempotensi.md`: transaksi, isolasi, FOR UPDATE, optimistic lock, TOCTOU, Idempotency-Key.
- `references/keamanan-dan-otorisasi.md`: Argon2id, JWT, refresh rotation, RBAC/ABAC, BOLA, OWASP API Top 10, rate limit.
- `references/pengujian-kontrak-dan-galat.md`: pytest, matriks peran, konkurensi, kontrak OpenAPI, galat.
- `references/sumber-dan-tautan.md`: semua tautan dan tanggal akses.
