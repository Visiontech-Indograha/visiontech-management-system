# 26 · Plan Migrasi Struktur Folder API

**Dasar:** keputusan pemilik 2026-09-29 (R-28, **kritis**): `api/` wajib mengikuti struktur
`docs/12` §1 (`api/v1/endpoints`, `api/deps.py`, `core/`, `models/`, `schemas/`, `crud/`, `services/`,
`main.py`, `dependencies.py`), supaya mudah dibaca, di-debug, dan dirawat.
**Prinsip:**
- **Perilaku API tidak boleh berubah.** Pemindahan ≠ penulisan ulang.
- Satu langkah = satu commit = semua uji hijau, ditambah uji nyata singkat (aturan pemilik 2026-09-29).
- Gabungkan dengan R-25b (O-02 · SQL keluar dari router): setiap modul yang dipindah sekaligus dibersihkan.

---

## 0. Keadaan sekarang → tujuan

| Sekarang (`api/app/`) | Jumlah | Tujuan | Catatan |
|---|---|---|---|
| `api/<modul>.py` (router) | 25 | `api/v1/endpoints/<modul>.py` | nama jamak dipertahankan (`plans.py` → `work_plans.py`, lihat M2) |
| `api/deps.py` | 1 | `api/deps.py` | tetap |
| `api/guards.py` | 1 | `api/deps.py` | penjaga akses SK adalah `Depends`, dipindah ke `api/deps.py` (bagian "Penjaga akses") |
| rakitan `APIRouter` di `main.py` | — | `api/v1/router.py` | `main.py` hanya memasang satu router |
| `db/session.py`, `db/context.py`, `db/transaction.py` | 3 | `core/database.py` | satu berkas; `SEARCH_PATH`, `make_engine`, `AsyncSessionLocal`, `SET LOCAL`, transaksi |
| `repositories/*_repo.py` | 25 | `crud/crud_<entitas>.py` | `base_repo.py` → `crud/base.py`; kelas `XxxRepo` → `CRUDXxx` |
| `controllers/auth_controller.py` | 1 | `services/auth_service.py` | orkestrasi digabung; folder `controllers/` dihapus |
| pembuat service tersebar di router (`Service(Repo(db))`) | ±60 | `dependencies.py` | `get_<nama>_service(db=Depends(get_db_with_user))` |
| `schemas/*.py` | 9 | `schemas/<entitas>.py` | skema yang masih didefinisikan di router ikut dipindah (M2) |
| `models/` | 0 | `models/<entitas>.py` | dibuat bertahap. Sekarang kueri SQL mentah, jadi `models/` diisi saat sebuah modul memakai SQLModel (lihat §3 Keputusan) |
| `core/*` (13 berkas) | 13 | `core/*` | tetap; `core` tidak boleh mengimpor lapisan lain |
| `templates/`, `cli.py`, `main.py` | — | tetap | |
| `requirements*.txt`, `ruff.toml`, `mypy.ini` | 4 | `pyproject.toml` | M7; `requirements.txt` tetap dihasilkan untuk Docker bila perlu |

## 1. Urutan (rencana ringkas)

| Tahap | Isi | Risiko | Bukti selesai |
|---|---|---|---|
| **M0** | Penjaga struktur: `tests/test_structure.py` + snapshot OpenAPI | Rendah | uji baru hijau; snapshot tersimpan |
| **M1** | `db/*` → `core/database.py` | Rendah | suite hijau; OpenAPI identik |
| **M2** | Router → `api/v1/endpoints/` + `api/v1/router.py`; `guards.py` → `api/deps.py` | Sedang (impor banyak) | suite hijau; OpenAPI **identik byte-per-byte** |
| **M3** | `repositories/` → `crud/` (nama `crud_<entitas>.py`) | Sedang | suite hijau; tidak ada `repositories` tersisa |
| **M4** | `controllers/` → `services/` | Rendah | suite hijau |
| **M5** | `dependencies.py` (perakitan service) | Rendah | endpoint tidak lagi `Service(Repo(db))` |
| **M6** | Per modul: SQL keluar dari endpoint ke `crud`, `HTTPException` → `AppError` (= R-25b / O-02). Urutan: `plans` → `attendance` → `employees` → `assets` → `hse` → `files` → `sites` → `audit` → `expiry` | Sedang per modul | modul keluar dari daftar `LEGACY` di `test_router_layering.py` |
| **M7** | `pyproject.toml` | Rendah | CI & Docker tetap hijau |
| **M8** | Dokumen: `docs/12`, `PETA-KODE.md`, `CLAUDE.md`, docs/23 | — | tidak ada rujukan jalur lama |

M1–M5 bersifat **mekanis** (pindah + ganti impor), dikerjakan berurutan tanpa jeda fitur lain.
M6 bisa diselang dengan fitur, tetapi satu modul per commit.

## 2. Rencana rinci per tahap

### M0 · Penjaga struktur (dikerjakan pertama, uji ditulis dulu)
1. `tests/test_structure.py` (statis, AST, tanpa DB):
   - folder di bawah `app/` hanya: `api`, `core`, `models`, `schemas`, `crud`, `services`, `templates`,
     plus sementara `repositories`, `controllers`, `db` yang ditandai **LEGACY**. Daftar legacy hanya boleh
     menyusut; uji gagal bila ada berkas baru di folder legacy;
   - arah impor: `core` tidak mengimpor `api/services/crud`; `crud` tidak mengimpor `services/api`;
     `services` tidak mengimpor `api` (kecuali `api.deps.CurrentUser`, dicatat sebagai pengecualian yang
     dipindah ke `core/security.py` di M5);
   - `api/v1/endpoints/*` tidak mengimpor `crud` langsung (menyatu dengan `test_router_layering.py`).
2. **Snapshot OpenAPI**: `tests/snapshots/openapi.json` dari `app.openapi()`; uji membandingkan bahwa
   rute, metode, skema, dan status sama persis. Ini jaring pengaman utama bahwa pemindahan tidak mengubah API.
3. Commit: `test(R-28 M0): penjaga struktur folder API + snapshot OpenAPI`.

### M1 · `core/database.py`
1. Satukan `db/session.py`, `db/context.py`, dan `db/transaction.py` ke `core/database.py` (isi dipindah apa adanya).
2. Ganti semua `from app.db.session import …` / `app.db.context` / `app.db.transaction` →
   `from app.core.database import …`: `alembic/env.py`, `cli.py`, `tests/conftest.py`, `main.py`, `api/deps.py`.
3. Hapus folder `db/`; keluarkan dari daftar LEGACY.
4. Verifikasi: `ruff`, `mypy`, suite penuh (DB UJI), snapshot OpenAPI identik.

### M2 · `api/v1/endpoints` + `router.py`
1. `git mv app/api/<modul>.py app/api/v1/endpoints/<modul>.py` untuk 25 berkas.
   Ganti nama agar konsisten jamak & jelas:
   - `plans.py` → `work_plans.py`, `plan_days.py` → `work_plan_days.py`, dan seterusnya;
   - nama **rute** tidak berubah, hanya nama berkas.
2. `api/v1/router.py`: `api_router = APIRouter()` + `include_router` semua endpoint dengan prefix dan tag
   yang sama seperti sekarang di `main.py` (disalin, bukan ditulis ulang).
3. `main.py`: hanya `app.include_router(api_router, prefix=API_PREFIX)`. `/health` dan `/ready` tetap di akar.
4. `guards.py` → bagian "Penjaga akses" di `api/deps.py` (fungsi, nama, dan tanda tangan tetap).
5. Skema Pydantic yang didefinisikan di dalam berkas router (mis. `TeamRequest`, `AccountOut`) → `schemas/<entitas>.py`.
6. Ganti impor di `tests/` (`from app.api.plans import …` dsb.).
7. Verifikasi: suite penuh; **snapshot OpenAPI identik**; `test_route_smoke.py` hijau; `web` `npm run gen:api`
   tidak menghasilkan diff pada `web/src/lib/api-types.ts`.

### M3 · `repositories/` → `crud/`
1. `git mv repositories/<x>_repo.py crud/crud_<x>.py`, dan `base_repo.py` → `crud/base.py`.
2. Nama kelas: `PlanMemberRepo` → `CRUDPlanMember`, dan seterusnya (sed terkendali, satu pola per berkas; periksa
   `git diff --stat` agar tidak ada penggantian di luar impor/kelas).
3. Parameter konstruktor service yang bernama `repo` dibiarkan (hindari churn); hanya tipe/impor yang berubah.
4. Verifikasi: suite penuh; snapshot identik; `grep -r "repositories" app tests` kosong.

### M4 · `controllers/` → `services/`
1. `auth_controller.py`: logika orkestrasi → `services/auth_service.py` (atau `services/auth_flow.py` bila terlalu
   besar), dependency `get_auth_controller` → `dependencies.get_auth_service`.
2. Hapus `controllers/`.

### M5 · `dependencies.py`
1. Untuk setiap service: `def get_<nama>_service(db: AsyncSession = Depends(get_db_with_user)) -> <Nama>Service`.
2. Endpoint memakai `service: XService = Depends(get_x_service)` alih-alih merakit `XService(XRepo(db))`.
3. `CurrentUser` dipindah dari `api/deps.py` ke `core/security.py` (tipe data), dan `api/deps.py` mengekspor
   ulang. Dengan begitu `services` tidak mengimpor `api`.

### M6 · Per modul: SQL keluar dari endpoint (R-25b / O-02)
Untuk setiap modul, sesuai urutan di §1:
1. Uji yang ada untuk modul itu = jaring pengaman. Bila ada jalur tanpa uji, tulis uji dulu.
2. Pindahkan setiap `text("…")` / `db.execute` dari endpoint ke `crud_<entitas>.py`, dan aturan bisnis ke service.
3. `HTTPException` → `AppError` (kode & pesan Bahasa Indonesia). Bila bentuk galat berubah, catat di
   CHANGELOG dan periksa web/mobile yang membaca `detail` lama.
4. Hapus modul dari daftar `LEGACY` di `test_router_layering.py`.
5. Verifikasi: suite penuh, snapshot OpenAPI (hanya skema galat yang boleh berubah, dicatat), uji nyata singkat
   di web & HP untuk alur modul itu.

### M6b · Model untuk tabel sisa (K-1)
1. Ambil daftar tabel `vms` dari `information_schema.tables` di DB UJI, lalu kurangi tabel yang sudah punya model dari M6.
2. Buat `models/<entitas>.py` (SQLModel `table=True`) dengan nama dan tipe kolom sama dengan `db/01_schema.sql`.
   Jangan membuat tabel baru dan jangan pakai Alembic autogenerate. Uji `tests/test_models_match_schema.py`
   mencocokkan kolom model dengan skema DB.
3. Model tidak dipakai untuk menulis data sampai modulnya memakai SQLModel, sehingga RLS dan trigger tetap bekerja.

### M7 · `pyproject.toml`
Gabungkan `ruff.toml`, `mypy.ini`, konfigurasi pytest, dan dependensi (`requirements*.txt` tetap dibuat untuk
Docker/CI atau Docker pindah ke `pip install .`). Verifikasi: CI (`.github/workflows/ci.yml`) dan build
Docker server tetap hijau.

### M8 · Dokumen
`docs/12` §1 (tanpa label migrasi), `docs/PETA-KODE.md` (jalur baru), `CLAUDE.md`, `docs/23`, dan hapus
daftar LEGACY dari uji.

## 3. Keputusan & risiko

| # | Hal | Keputusan / mitigasi |
|---|---|---|
| K-1 | `models/` kosong karena kode memakai SQL mentah + fungsi/trigger DB | **Diputuskan pemilik 2026-09-30: bertahap, tetapi WAJIB selesai untuk semua tabel.** Setiap modul yang dipindah (M6) sekaligus mendapat model SQLModel untuk tabel-tabelnya. Tahap **M6b** memodelkan tabel sisa. Model tidak boleh mengubah perilaku RLS/trigger (uji yang ada tetap hijau) |
| K-2 | Contoh pemilik memakai `.env`, `docker-compose.yml` di akar `api/` | `.env` tetap git-ignored (`api/.env`, `api/.env.test`). `docker-compose.yml` lokal pemilik tidak di-commit; produksi memakai `~/deploy/vms-mvp/compose.yml` |
| K-3 | Banyak impor berubah sekaligus → konflik dengan branch lain | M1–M5 dikerjakan berurutan dan cepat, tanpa branch fitur paralel yang menyentuh `api/`; setiap langkah langsung di-push |
| K-4 | Server produksi & autodeploy | Struktur internal tidak memengaruhi Dockerfile (`app.main:app` tetap) dan `alembic` (env.py ikut diganti di M1). Deploy ke `prod` hanya setelah M1–M5 selesai dan pemilik setuju |
| K-5 | Uji harus di DB UJI (docs/24 A-00) | Semua verifikasi memakai `api/.env.test`; penjaga `tests/db_guard.py` aktif |

## 4. Definisi selesai

- `tests/test_structure.py` hijau **tanpa** daftar LEGACY.
- Tidak ada folder `repositories/`, `controllers/`, atau `db/` di `api/app/`.
- Setiap tabel skema `vms` punya model di `models/` (K-1), dan `test_models_match_schema.py` hijau.
- Snapshot OpenAPI identik dengan sebelum migrasi, kecuali perubahan galat M6 yang tercatat.
- Suite API penuh, web, dan mobile hijau; uji nyata singkat (login, buat/terbit SK, terima SK di HP, absen) lulus.
- `docs/12`, `PETA-KODE.md`, dan `CLAUDE.md` sesuai kode.
