# 12 · Standar Backend

Aturan mengikat untuk `api/`. Tumpukan: **FastAPI + SQLModel + asyncpg + Alembic**,
PostgreSQL 18 (PostGIS + pgvector), MinIO.

---

## 1. Struktur folder (WAJIB — keputusan pemilik 2026-09-29, dikoreksi 2026-09-30 R-30)

> **Kritis.** Struktur ini **persis** contoh yang diberikan pemilik (R-28). Versi 2026-09-29 di dokumen ini
> sempat menyimpang (`core/database.py`, `app/dependencies.py`) dan sudah dikoreksi (R-30). Kode lama
> dimigrasikan bertahap (`docs/26-PLAN-MIGRASI-STRUKTUR-API.md`); **berkas baru wajib** dibuat di tempat
> yang benar menurut struktur ini.

```
api/
├── alembic/                  migrasi database (Alembic)
├── app/                      kode sumber aplikasi
│   ├── api/                  endpoint API (routing)
│   │   ├── v1/
│   │   │   ├── endpoints/    satu berkas per modul: auth.py, work_plans.py, attendance.py, …
│   │   │   └── router.py     menggabungkan semua router v1
│   │   └── deps.py           dependency injection global: get_db, get_current_user, izin, penjaga akses,
│   │                         dan perakitan service (get_<nama>_service)
│   ├── core/                 konfigurasi inti dan keamanan
│   │   ├── config.py         pengaturan env via pydantic-settings — SATU-SATUNYA sumber rahasia
│   │   └── security.py       hashing password, JWT, identitas pengguna (CurrentUser)
│   ├── crud/                 operasi database — SATU-SATUNYA tempat ada kueri SQL
│   │   ├── crud_user.py      satu berkas per entitas: crud_<entitas>.py, kelas CRUD<Entitas>
│   │   └── …
│   ├── models/               model ORM (SQLModel) — satu berkas per entitas: user.py, work_plan.py, …
│   ├── schemas/              skema validasi & serialisasi (Pydantic) — satu berkas per entitas
│   ├── services/             logika bisnis (padanan prototype/js/domain.js), tanpa SQL
│   ├── db/                   koneksi dan sesi database
│   │   ├── base.py           basis deklaratif model (metadata untuk Alembic)
│   │   └── session.py        engine async, session maker, transaksi, konteks RLS (SET LOCAL app.*)
│   └── main.py               titik masuk aplikasi (instance FastAPI)
├── tests/                    pytest: conftest.py, test_<fitur>.py
├── .env                      variabel lingkungan lokal (tidak di-commit)
├── Dockerfile
├── requirements*.txt        dependensi (versi dikunci)
└── ruff.toml · mypy.ini      konfigurasi lint & tipe (§5)
```

Tambahan proyek yang dipertahankan (tidak ada di contoh, dibutuhkan produk): `app/core/` berisi juga
`errors.py`, `permissions.py`, `time.py`, `storage.py`, dsb. (fondasi tanpa domain); `app/templates/`
(Jinja2 untuk PDF); `app/cli.py` (seed, create-admin).

**Aturan penulisan**

| Lapisan | Boleh | Tidak boleh |
|---|---|---|
| `api/v1/endpoints/*` | `Depends(...)` dari `api/deps.py`, panggil **service**, kembalikan **schema** | SQL, `text()`, `db.execute`, aturan bisnis, `HTTPException` (pakai `AppError`) |
| `api/deps.py` | sesi DB, autentikasi, izin, penjaga akses, perakitan service | kueri di luar `crud` |
| `services/*` | aturan bisnis, memanggil **crud**, melempar `AppError` | SQL, objek `Request`/`Response`, impor `app.api` |
| `crud/*` | kueri SQL/SQLModel, mengembalikan baris/model | aturan bisnis, `AppError` bisnis |
| `models/*` / `schemas/*` | definisi bentuk data | logika |
| `db/*` | engine, sesi, transaksi, basis model | kueri domain |

- Nama berkas: endpoint = jamak modul (`work_plans.py`), crud = `crud_<entitas tunggal>.py`,
  service = `<entitas>_service.py`, schema/model = `<entitas>.py`.
- Satu arah impor: `endpoints → services → crud → models`; `core` dan `db` tidak mengimpor lapisan domain.
  Dijaga uji `tests/test_structure.py` (docs/26 M0).
- Tidak ada folder lain di `app/` (mis. `controllers/`, `repositories/`, `dependencies.py`).

---

## 2. Tanggung jawab tiap lapisan

Alur satu permintaan: **endpoint → service → crud**. Tidak ada lapisan lain (`routes/`, `controllers/`,
`repositories/` tidak ada — versi lama dokumen ini menyebutnya; dikoreksi 2026-10-07).

### Endpoint — `api/v1/endpoints/<modul>.py`
Tipis. Hanya: jalur, metode, status, `response_model`, dependency, lalu memanggil **service** dan
membentuk **schema** respons. Tidak ada aturan bisnis dan tidak menyentuh basis data
(dijaga `tests/test_router_layering.py`).

```python
router = APIRouter(prefix="/units", tags=["Units"])

@router.get("", response_model=list[UnitOut])
async def list_units(
    current_user: CurrentUser = Depends(get_current_user),
    unit_service: UnitService = Depends(get_unit_service),
) -> list[UnitOut]:
    """Unit milik organisasi pengguna saja (V-09)."""
    return [UnitOut(**r._mapping) for r in await unit_service.list_units(current_user.organization_id)]
```

### Perakitan — `api/deps.py`
Satu fungsi `get_<nama>_service` per service: membuka sesi ber-RLS (`get_db_with_user`) dan menyuntikkan crud.

```python
def get_unit_service(db: AsyncSession = Depends(get_db_with_user)) -> UnitService:
    return UnitService(CRUDUnit(db))
```

### Service — `services/<entitas>_service.py`
**Tempat aturan bisnis.** Nama metode = transaksi di `prototype/js/domain.js` (`publish`, `accept`, …).
Tidak menulis SQL, tidak tahu HTTP/JSON, melempar `AppError` berpesan Indonesia.

```python
class PlanTransitionService:
    async def publish(self, plan_id: UUID, actor: CurrentUser) -> Any:
        plan = await self.repo.get(plan_id)
        if plan.status != PlanStatus.DRAFT:
            raise InvalidStateError("SK ini sudah terbit, jadi tidak bisa diterbitkan lagi.")
        ...
```

### CRUD — `crud/crud_<entitas>.py`
**Satu-satunya tempat SQL.** Kelas `CRUD<Entitas>(CRUDBase)` dengan helper `execute`/`fetchone`/`fetchall`
dari `crud/base.py`; SQL mentah berparameter (`:nama`), tanpa `SELECT *` (dijaga `test_no_select_star.py`).

```python
class CRUDUnit(CRUDBase):
    async def list_for_org(self, org_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT id, code, name FROM vms.business_unit WHERE organization_id = :org ORDER BY name",
            {"org": org_id},
        ))
```

### Schema — `schemas/<entitas>.py`
Bentuk permintaan & respons (Pydantic). Aturan lengkap: §10. Baris DB / model **tidak pernah** menjadi
respons langsung — kolom baru (mis. `password_hash`, `embedding`) akan ikut terkirim tanpa disadari.

---

## 3. Aturan khusus SQLModel + async

### Tipe kolom khusus

```python
from geoalchemy2 import Geography
from pgvector.sqlalchemy import Vector

class Attendance(SQLModel, table=True):
    location: Any | None = Field(
        default=None, sa_column=Column(Geography("POINT", srid=4326)))

class FaceEnrollment(SQLModel, table=True):
    embedding: Any = Field(sa_column=Column(Vector(512)))
```

### Geografi tidak pernah keluar mentah

```python
# SALAH — WKB bocor ke JSON, dan React akan mogok (ini pernah terjadi)
return attendance

# BENAR
return AttendanceRead(
    ...,
    coordinates=Coordinates(lat=lat, lon=lon),
    distance_m=attendance.distance_m,
)
```

### Sesi dan RLS

```python
async def get_session(ctx: AuthContext) -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        async with session.begin():                       # satu transaksi
            await session.exec(text(
                "SELECT set_config('app.user_id', :uid, true), "
                "       set_config('app.organization_id', :org, true), "
                "       set_config('app.actor_label', :label, true)"
            ), {"uid": str(ctx.user_id), "org": str(ctx.org_id), "label": ctx.label})
            yield session
```

`true` pada `set_config` = setara `SET LOCAL`, hilang saat transaksi selesai.

**Aturan keras:**
- Satu permintaan = satu sesi = satu transaksi.
- Sesi **tidak pernah** dibagikan ke `asyncio.gather` atau task latar.
- Bila konteks gagal disetel → permintaan **ditolak**, bukan dilanjutkan. Tanpa konteks,
  RLS mengembalikan nol baris dan aplikasi akan tampak "kosong" alih-alih memberi tahu ada
  masalah.

### Engine

```python
engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://...
    pool_size=10, max_overflow=20, pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},   # wajib bila memakai PgBouncer
)
```

---

## 4. Penanganan galat

Satu kelas galat domain, satu tempat pemetaan ke HTTP:

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, *,
                 status: int = 400, details: dict | None = None): ...
```

Handler global mengubahnya menjadi bentuk baku di dokumen 05. Aturan:

- `message` **Bahasa Indonesia**, ditujukan kepada pengguna, bukan kepada programmer.
- Galat tak terduga → 500 dengan `request_id`, **tanpa** jejak tumpukan. Detailnya masuk log.
- Galat basis data diterjemahkan, tidak diteruskan mentah:
  - `40001` (row_version) → 409 "Data berubah di sesi lain. Muat ulang sebelum menyimpan."
  - pelanggaran exclusion aset → 409 "Aset ini sudah dipakai pekerjaan lain pada tanggal itu."
  - trigger dokumen tetap → 409 "Dokumen terbit tidak bisa diubah. Terbitkan versi baru."

---

## 5. Konvensi kode

| Hal | Aturan |
|---|---|
| Lint | `ruff check app tests` — set aturan di `api/ruff.toml` (`E,W,F,I,UP,B,RUF,DTZ,BLE,ASYNC,SIM,C4,PIE`), baris ≤ **120**. Mengubah set aturan = keputusan pemilik |
| Utang lint lama | `[lint.per-file-ignores]` di `ruff.toml` **hanya boleh menyusut**. Berkas baru tidak boleh masuk daftar; menyentuh berkas lama → rapikan baris panjangnya lalu hapus `E501`-nya |
| Tipe | `mypy` strict untuk seluruh `app/`; tidak ada `Any` tanpa alasan tertulis |
| Penamaan berkas | endpoint `<modul jamak>.py`, service `<entitas>_service.py`, crud `crud_<entitas>.py`, schema `<entitas>.py` |
| Penamaan fungsi servis | Sama dengan transaksi prototipe: `publish`, `accept`, `request_personnel_change` |
| Impor | Absolut (`app.services.x`); di dalam `crud/` boleh `from .base import CRUDBase` |
| Async | Semua I/O `async`; kerja CPU berat (kompresi gambar, render PDF) → `run_in_threadpool` |
| Rahasia | Hanya lewat `core/config.py`; tidak ada `os.getenv` tersebar |
| Waktu | Hanya lewat `core/time.py` (`utcnow`, `jakarta_now`) |
| Galat | `AppError` / turunan di `core/errors.py`; `raise … from e` di dalam `except` |
| Docstring & komentar | Bahasa Indonesia; menjelaskan **kenapa**, bukan **apa** |
| Ragu / ambigu | **Tanyakan pemilik dulu, jangan menebak** (§12) |

**Kerja berat tidak boleh memblokir event loop.** Kompresi gambar dan render PDF berjalan di
thread pool. Ini mudah terlewat dan akibatnya seluruh server tersendat saat satu orang
mengunggah foto besar.

---

## 6. DRY di backend

**Yang disatukan:**

| Hal | Di mana |
|---|---|
| Helper SQL dasar | `crud/base.py` (`CRUDBase`) |
| Pagination, penyaringan, pengurutan | `core/pagination.py` |
| Pemeriksaan izin | `core/permissions.py` + `require_permission` di `api/deps.py` — **tidak pernah** ditulis ulang di endpoint |
| Penjaga akses SK | `core/plan_auth.py` + `plan_access(...)` di `api/deps.py` |
| Pemetaan galat | `core/errors.py` |
| Kompresi gambar | `core/image.py` |
| Penyimpanan berkas | `core/storage.py` |
| Snapshot & hash dokumen | `services/document_service.py` |
| Waktu | `core/time.py` |

**Yang sengaja tidak dipaksakan sama:** aturan bisnis tiap modul. Absensi dan lembur
kebetulan sama-sama punya alur "ajukan → periksa", tetapi aturannya berbeda dan akan makin
berbeda. Menyatukannya menghasilkan satu fungsi dengan banyak percabangan yang tidak ada
yang berani ubah.

---

## 7. Migrasi

- Alembic mode async (`alembic init -t async`).
- Berkas `db/01`–`db/05` menjadi baseline `0001`.
- Fungsi PL/pgSQL, trigger, dan kebijakan RLS ikut diversikan lewat `op.execute()` — jangan
  pernah dijalankan manual di server, karena produksi dan pengembangan akan diam-diam
  berbeda.
- Satu migrasi per perubahan; **maju saja** di produksi.
- Kompatibel mundur satu versi: tambah kolom → isi → (rilis berikutnya) hapus yang lama.
- Setiap migrasi diuji pada basis data kosong **dan** pada salinan yang sudah berisi data.

---

## 8. Pengujian

| Jenis | Isi | Alat |
|---|---|---|
| Unit | Servis, dengan crud tiruan | pytest |
| Integrasi | CRUD, trigger, RLS, constraint | pytest + PostgreSQL nyata |
| API | Endpoint + matriks RBAC | `fastapi.testclient.TestClient` (`tests/conftest.py`) |

- **PostgreSQL sungguhan**, bukan SQLite: separuh aturan sistem ini hidup di trigger, RLS,
  dan exclusion constraint yang tidak dimiliki SQLite.
- Setiap uji berjalan dalam transaksi yang di-*rollback*, atau memakai basis data sekali
  pakai (`pytest-postgresql` / container).
- Waktu dibekukan lewat `core/time.py`.
- **Matriks RBAC dibangkitkan**: setiap endpoint × 8 peran. Endpoint baru tanpa baris di
  matriks → CI gagal.
- Target: 100% cabang pada `services/`; endpoint minimal jalur berhasil + jalur ditolak.

---

## 9. Keamanan pada tingkat kode

1. Tidak pernah mengembalikan objek model langsung (§2).
2. Tidak pernah membangun SQL dengan penggabungan string; pakai parameter.
3. Semua unggahan divalidasi *magic bytes*; gambar di-*re-encode* dan EXIF dibuang (dokumen 13).
4. Tidak ada rahasia di log; `password`, `token`, `embedding` masuk daftar penyaring log.
5. Berkas yang tidak berwenang → **404**, bukan 403.
6. Pembatasan laju di `/auth/login`, `/verify/{token}`, `/files`.
7. Peran dan izin selalu dibaca dari basis data, bukan dari klaim token.

---

## 10. Skema (Pydantic) — gaya wajib untuk kode baru

Kelas skema lama **tidak diganti namanya**: nama kelas menjadi nama komponen OpenAPI dan tipe TypeScript web
(`web/src/lib/api-types.ts`). Aturan di bawah berlaku untuk skema **baru** (keputusan pemilik 2026-10-07).

### Letak & penamaan

| Hal | Aturan | Contoh |
|---|---|---|
| Berkas | `app/schemas/<entitas>.py`, satu entitas/modul per berkas; docstring modul 1 baris | `schemas/app_release.py` |
| Masukan | `<Entitas>In` (buat), `<Entitas>Update` (ubah sebagian), `<Aksi>In` untuk aksi | `MemberReportIn`, `AmendmentReasonIn` |
| Keluaran | `<Entitas>Out`; daftar berhalaman `<Entitas>ListOut` (`items`, `total`, …) | `NotificationOut` |
| Bagian bersarang | kata benda tanpa akhiran In/Out bila dipakai dua arah | `GeoPoint`, `DayTaskOut` |
| Pilihan tetap | `Literal[...]` bernama di atas berkas, atau `StrEnum` di `core/enums.py` bila dipakai lintas modul | `PlanCategory = Literal[...]` |
| Nama field | `snake_case` Inggris singkat, sama dengan kolom DB/OpenAPI; jangan menerjemahkan | `work_date`, `row_version` |

### Isi kelas

```python
"""Skema rilis aplikasi Android (pembaruan otomatis, docs/32)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

UpdateStatus = Literal["UP_TO_DATE", "OPTIONAL", "REQUIRED"]


class ReleaseFileOut(BaseModel):
    """Satu berkas APK untuk satu arsitektur."""

    abi: str
    url: str                                   # jalur relatif ke API — klien tidak menerima host lain
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(gt=0)                    # bita


class AppUpdateOut(BaseModel):
    """Jawaban pemeriksaan pembaruan untuk satu HP."""

    status: UpdateStatus
    current_build: int
    latest_build: int | None = None
    notes: list[str] = []
    download: ReleaseFileOut | None = None
```

- Satu baris docstring Indonesia per kelas (apa artinya bagi pengguna/klien, bukan "Schema for …").
- Komentar per field **hanya** bila ada yang tidak jelas dari nama/tipe (satuan, rujukan aturan) — bukan
  mengulang nama field.
- Tipe tepat: `UUID`, `date`, `datetime` (ber-zona, dari `core/time.py`), `int | None`. Tidak ada `Any`,
  tidak ada `dict` bebas di respons kecuali `details` galat.
- Nilai opsional diberi bawaan eksplisit (`= None`, `= []`); field wajib tanpa bawaan.
- **Batas bentuk di skema** (`Field(min_length, max_length, ge, le, pattern)`), **aturan bisnis di service**
  dengan `AppError` berpesan Indonesia (urutan & kalimat galat harus sama dengan prototipe). Pesan Pydantic
  berbahasa Inggris tidak pernah sampai ke pengguna: `validation_error_handler` menggantinya dengan pesan
  baku + `details.fields`.
- Teks bebas dari pengguna: batasi `max_length`; pemangkasan spasi dilakukan service (agar terlihat di uji).
- Respons tulis mengembalikan data **sesudah** disimpan (dibaca ulang), bukan salinan masukan.
- Tidak ada logika di skema selain `field_validator` untuk normalisasi bentuk (mis. huruf besar kode);
  validator tidak memanggil DB.
- Koordinat keluar sebagai `lat`/`lng` angka, tidak pernah geometri mentah (§3).
- Kolom sensitif (`password_hash`, `embedding`, token) tidak pernah ada di skema keluaran.

### Perubahan skema = perubahan API
Setiap perubahan skema mengubah OpenAPI: jalankan `UPDATE_OPENAPI_SNAPSHOT=1 pytest tests/test_openapi_snapshot.py`,
tinjau diff-nya, lalu `npm run gen:api:export && npm run gen:api` di `web/` bila web memakai skema itu.

---

## 11. Templat fitur backend (salin untuk modul baru)

Urutan berkas untuk modul `<modul>` (entitas `<entitas>`):

1. `app/schemas/<entitas>.py` — `<Entitas>In` / `<Entitas>Out` (§10).
2. `app/crud/crud_<entitas>.py` — `class CRUD<Entitas>(CRUDBase)`, SQL berparameter, kolom disebut satu per satu.
3. `app/services/<entitas>_service.py` — `class <Entitas>Service`, konstruktor menerima crud, nama metode = transaksi
   `domain.js`, galat `AppError`.
4. `app/api/deps.py` — `def get_<entitas>_service(db = Depends(get_db_with_user)) -> <Entitas>Service`.
5. `app/api/v1/endpoints/<modul>.py` — `router = APIRouter(prefix="/<modul>", tags=["<Modul>"])`, tiap rute memakai
   `require_permission(...)`, penjaga SK, atau terdaftar di `SELF_SERVICE`/`PUBLIC_ROUTES` beserta alasannya.
6. `app/api/v1/router.py` — `api_router.include_router(...)` (urutan memengaruhi OpenAPI; tambahkan di akhir).
7. Uji: `tests/test_<fitur>.py` — jalur berhasil (tulis → baca ulang), jalur ditolak, peran lain; snapshot OpenAPI.
8. Skema DB berubah → migrasi Alembic baru **dan** `db/*.sql` disamakan di commit yang sama; migrasi yang sudah
   di produksi tidak pernah diubah.

Contoh lengkap yang kecil dan bersih untuk ditiru: `units` (`endpoints/units.py`, `services/unit_service.py`,
`crud/crud_unit.py`, `schemas/unit.py`).

---

## 12. Bila ragu: tanyakan, jangan menebak

Aturan untuk developer **dan** agen AI (keputusan pemilik 2026-10-07):

- Spesifikasi ambigu, dua pilihan sama masuk akal, atau keputusan menyangkut keamanan, privasi, data produksi,
  biaya, lisensi, atau perilaku yang terlihat pengguna → **tanyakan pemilik dulu** dengan pilihan + rekomendasi.
- Jangan mengisi celah dengan asumsi diam-diam. Jawaban pemilik dicatat di `docs/10-...md` Bagian C.
- Yang boleh diputuskan sendiri hanya hal teknis kecil yang punya satu jawaban jelas dari kode/standar ini
  (mis. mengikuti pola berkas tetangga) — sebutkan keputusannya di laporan.
