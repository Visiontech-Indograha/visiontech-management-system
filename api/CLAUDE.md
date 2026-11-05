# API VMS (FastAPI) · aturan untuk agen

Dibaca otomatis saat bekerja di `api/`. Aturan lengkap di `CLAUDE.md` root dan skill `vms-api`.

## Aturan inti
- Tanpa `LIKE '%…'` / `ILIKE '%' || :q` (cari = awalan). Tanpa `OFFSET` baru (pakai keyset). Tanpa `SELECT *`. `KNOWN` di `tests/architecture/test_sql_rules.py` hanya boleh menyusut.
- Keputusan pemilik (5 Nov 2026): pencarian `q` pada daftar LAMA tetap "mengandung kata" (tercatat di `KNOWN`); daftar BARU wajib awalan. `OFFSET` baru dilarang: daftar baru memakai keyset `(created_at, id)`.
- Daftar pakai `ListParams`/`apply_list` dan `X-Total-Count`. Tanpa parameter = perilaku lama.
- Router tipis; SQL hanya di `repositories/`; repository tidak commit; transaksi di service.
- Setiap rute punya `require_permission` atau penjaga terdaftar di `test_route_guards.py`. Objek di luar cakupan → 404.
- Transisi status/uang: `FOR UPDATE` atau `UPDATE … WHERE status = …` lalu cek `rowcount`.
- Jangan tambah mount statis (`/uploads`). Berkas lewat `/api/v1/files/{id}/url`.
- Argon2 dan kode sinkron berat dibungkus `asyncio.to_thread`.
- Log dan respons tanpa PII, hash sandi, token, embedding wajah.

## Skill
- `vms-api`: endpoint, Big O, transaksi, keamanan, pengujian, kontrak.
- `vms-db`: skema, migrasi, RLS, enkripsi.
- `vms-storage-minio`: unggahan, validasi, bucket.

## Perintah (jalankan dari `api/`)
- Lint dan tipe: `ruff check app tests`, `python -m mypy`.
- Tes (atas perintah user saja): `TEST_DATABASE_URL=postgresql+asyncpg://<peran>@localhost:<port>/vms_test python -m pytest -q -p no:warnings`
- Migrasi: `python -m alembic upgrade head` (di DB `vms_test`); `python -m alembic current`.
- Kontrak OpenAPI (atas perintah user): `UPDATE_OPENAPI_SNAPSHOT=1 python -m pytest tests/architecture/test_openapi_snapshot.py`, lalu `cd ../web && npm run gen:api:export && npm run gen:api`.

## Larangan
- Jangan pakai DB dev atau produksi untuk tes (`tests/db_guard.py` menolak nama non-`*_test`).
- Jangan mengubah migrasi lama di `alembic_v2/versions/`; migrasi baru saja.
- Jangan commit tanpa perintah user; jangan `git add -A`.
