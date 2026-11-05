# Pengujian, kontrak, dan galat (API VMS)

Sumber: PDF bagian 11 (baris 1482-1609), bagian 16.1 (baris 1929-1951), ADR 0001 kriteria A-E, `vms-next/docs/01` (Tes), `docs/06`. Bukti: worktree `origin/beta`. Aturan proyek: tes hanya atas perintah user (memori `defer-test-writing`).

## 1. Piramida tes

| Lapis | Proporsi (PDF) | Di VMS |
|---|---|---|
| Static analysis | 100% | `ruff check --isolated --select E9,F63,F7,F82`, `ruff check app tests` (baseline), `mypy` (`ci.yml:77-84`) |
| Unit | 50-60% | Fungsi murni: kalkulasi, validasi, mapping |
| Integrasi | 30-40% | pytest ke PostgreSQL nyata (`ci.yml:86-87`) |
| E2E | 5-10% | Smoke: login akun uji dan satu GET terotentikasi (`docs/06` rilis langkah f) |

Tes arsitektur yang sudah ada di `api/tests/architecture/`:
- `test_sql_rules.py`: R-31 (SQL, KNOWN hanya menyusut).
- `test_route_guards.py`: V-09, setiap rute punya izin atau penjaga terdaftar.
- `test_router_layering.py`: router tidak menyentuh DB (`LEGACY` kosong).
- `test_alembic_v2.py`: rantai migrasi dan head `v2_0019`.
- `test_no_select_star.py`, `test_openapi_snapshot.py`, `test_route_smoke.py`, `test_structure.py`, `test_api_prefix.py`, `test_deploy_scripts.py`, `test_no_dead_modules.py`, `test_versi.py`, `test_sql_matches_schema.py`.

Tes yang dibutuhkan tetapi belum ada (riset 01 F-14, T14):
- Konkurensi: `asyncio.gather` pada approve, rollover, dan serah terima aset.
- Matriks peran × endpoint × ID lintas divisi (ADR 0001 kriteria, `docs/06` Otorisasi).
- Query tanpa konteks RLS mengembalikan 0 baris (`vms-db`).
- Cakupan: `pytest --cov=app --cov-fail-under=<angka awal terukur>`. Jangan langsung 80%; ukur dulu (riset 01 F-22).

## 2. Lokasi dan konvensi

- Tes sejajar modul: `modules/<fitur>/tests/` (ADR 0001 keputusan 13). Berkas tes yang sudah ada berada di `api/tests/modules/`, `api/tests/core/`, `api/tests/shared/`, `api/tests/integration/`, dan `api/tests/beban/`.
- Basis data: `conftest.py` memakai `TEST_DATABASE_URL` (`db_guard.py:38-51`). `_UNSAFE` menolak DB non-lokal yang tidak bernama `*_test`/`test_*` (`db_guard.py:16-25`). Setup data memakai `TEST_SETUP_DATABASE_URL` (`conftest.py:43`).
- **Peringatan**: `ci.yml:31` memakai `postgres:postgres@.../visiontech_db` (superuser). Superuser melewati RLS; tes RLS wajib memakai peran aplikasi non-superuser (ADR 0001 keputusan 9e, `vms-db`).
- Lokal: DB uji `vms_test` saja. Jangan memakai `vms-dev-db` atau DB produksi untuk tes (memori `vms-master-local-test-db`).

## 3. Matriks peran × endpoint

Template tes (pseudo-kode, jangan dijalankan sebelum diminta):
```python
@pytest.mark.parametrize("peran,status_harap", [
    ("EMPLOYEE", 403),
    ("TEAM_LEADER", 200),
    ("PROJECT_MANAGER", 200),
])
async def test_daftar_jadwal_per_peran(client, token_untuk, peran, status_harap):
    r = await client.get("/api/v1/daily-plans", headers=token_untuk(peran))
    assert r.status_code == status_harap

async def test_id_lintas_divisi_dijawab_404(client, token_pm_divisi_a, jadwal_divisi_b):
    r = await client.get(f"/api/v1/daily-plans/{jadwal_divisi_b}", headers=token_pm_divisi_a)
    assert r.status_code == 404
    assert "divisi" not in r.text.lower()  # jangan bocorkan keberadaan
```
Aturan:
- Setiap endpoint yang baru punya minimal satu baris matriks untuk peran yang diizinkan, satu untuk yang tidak, dan satu ID lintas cakupan.
- Daftar tidak membocorkan baris lain: tes bahwa `items` dan `X-Total-Count` hanya berisi milik cakupan.

## 4. Konkurensi

Pola dan contoh ada di `transaksi-locking-idempotensi.md` bagian 6. Ringkasnya:
- Gunakan `asyncio.gather` dengan barrier agar benar-benar bersamaan.
- Assertion: tepat satu sukses (200), sisanya 409.
- Hindari flaky: pengulangan terbatas dan tanpa `sleep` tebakan.
- Catatan PDF: test 11.1 mengharapkan 4×409 untuk duplikat identik. Desain Target memakai 200 untuk respons tersimpan (`transaksi` bagian 4.3).

## 5. Kontrak OpenAPI dan generator tipe

- Snapshot: `api/tests/snapshots/` dan `test_openapi_snapshot.py`. Perubahan skema yang disengaja:
  ```
  cd api && UPDATE_OPENAPI_SNAPSHOT=1 pytest   # atas perintah user
  cd web && npm run gen:api:export && npm run gen:api
  ```
- Batas input web dan mobile harus sama dengan skema API (aturan proyek).
- Perubahan kontrak tanpa kompatibilitas mundur = MAJOR. Penambahan field opsional = MINOR. Lihat `CLAUDE.md` (rilis).
- Referensi: FastAPI menghasilkan OpenAPI dari route dan Pydantic (fastapi.tiangolo.com, akses 2026-11-04). Full-stack template resmi memakai `items` + `count` (`github.com/fastapi/full-stack-fastapi-template`, akses 2026-11-04). VMS memakai header `X-Total-Count`.

## 6. Galat (kontrak respons)

Bentuk seragam untuk galat bisnis:
```json
{"detail": {"code": "FILE_TOO_LARGE", "message": "Ukuran berkas melebihi batas 10MB."}}
```
Bukti pola: `files_controller.py:59-62`, `:73-75`, `:84-87`.

| Status | Kapan | Contoh kode |
|---|---|---|
| 400 | Permintaan rusak secara umum | `FILE_EMPTY` |
| 401 | Tidak terotentikasi / token tidak sah | `TOKEN_INVALID` |
| 403 | Terotentikasi tapi tidak boleh (peran) | `PERMISSION_DENIED` |
| 404 | Objek tidak ada atau di luar cakupan | `NOT_FOUND` |
| 409 | Konflik status / sedang diproses | `STATUS_CHANGED`, `IDEMPOTENCY_IN_PROGRESS` |
| 413 | Ukuran terlalu besar | `FILE_TOO_LARGE` |
| 415 | Tipe tidak didukung | `INVALID_FILE_TYPE` |
| 422 | Validasi input atau aturan bisnis | `DATE_RANGE_INVALID` (`check_date_range`, `list_params.py:25`) |
| 423 | Akun terkunci | (perlu cek kode yang dipakai login) |
| 429 | Batas laju | `RATE_LIMITED` (dengan `Retry-After`) |
| 503 | Layanan belum siap | `/ready` (`main.py:78`) |

Aturan:
- Pesan untuk pengguna berbahasa Indonesia sederhana. Kode stabil dalam bahasa Inggris dan huruf besar.
- Galat validasi Pydantic (422 dari FastAPI) dipetakan ke `applyFieldErrors` di web (`web/src/lib/errors.ts`, aturan proyek).
- Jangan bocorkan stack trace, SQL, nama tabel, atau keberadaan objek.

## 7. Observability dalam tes

- Tes yang memeriksa log: pastikan tidak ada email, NIK, token pada keluaran log (`caplog`).
- Tes header: `X-Correlation-ID` diteruskan ke respons.

## 8. Checklist tes

- [ ] Ada tes untuk jalur sukses, galat validasi, dan galat izin untuk endpoint baru.
- [ ] Matriks peran × ID lintas cakupan (404) ada.
- [ ] Transisi yang diubah punya tes konkurensi.
- [ ] Tidak ada tes yang menulis ke DB non-`*_test`.
- [ ] Snapshot OpenAPI diperbarui hanya bila kontrak berubah dan disetujui.
- [ ] Tes dijalankan hanya atas perintah user.
