# 12 · Standar Backend

Aturan mengikat untuk `api/`. Tumpukan: **FastAPI + SQLModel + asyncpg + Alembic**,
PostgreSQL 18 (PostGIS + pgvector), MinIO.

---

## 1. Struktur folder (WAJIB — keputusan pemilik 2026-09-29)

> **Kritis.** Struktur di bawah menggantikan versi sebelumnya dari bagian ini. Kode lama sedang
> dimigrasikan bertahap (`docs/26-PLAN-MIGRASI-STRUKTUR-API.md`). **Berkas baru wajib** dibuat di
> tempat yang benar menurut struktur ini, walau modul lamanya belum dipindah. Tujuannya: mudah dibaca,
> mudah di-debug, mudah dirawat — satu jenis tanggung jawab = satu folder, satu entitas = satu berkas.

```
api/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/          satu berkas per modul: rute HTTP saja (validasi masukan, panggil service, bentuk respons)
│   │   │   │   ├── auth.py
│   │   │   │   ├── work_plans.py
│   │   │   │   ├── attendance.py
│   │   │   │   └── ...
│   │   │   └── router.py           menggabungkan semua endpoint di bawah /api/v1
│   │   └── deps.py                 Depends FastAPI: pengguna aktif, izin, penjaga akses SK, sesi DB per permintaan
│   ├── core/                       fondasi, tidak tahu soal domain
│   │   ├── config.py               pydantic-settings — SATU-SATUNYA sumber rahasia/env
│   │   ├── database.py             engine async, session maker, SET LOCAL app.*, transaksi
│   │   ├── security.py · permissions.py · errors.py · time.py · storage.py · …
│   ├── models/                     bentuk tabel (SQLModel) — satu berkas per entitas
│   ├── schemas/                    bentuk permintaan & respons (Pydantic) — satu berkas per entitas
│   ├── crud/                       akses data — SATU-SATUNYA tempat ada kueri SQL
│   │   ├── base.py                 kelas dasar (fetchone/fetchall/execute)
│   │   ├── crud_work_plan.py
│   │   ├── crud_user.py
│   │   └── ...
│   ├── services/                   aturan bisnis — padanan prototype/js/domain.js, tanpa SQL
│   ├── templates/                  Jinja2 untuk PDF (WeasyPrint)
│   ├── main.py                     app factory: middleware, handler galat, pasang api/v1/router.py
│   ├── dependencies.py             perakitan objek: get_<nama>_service(db) → service + crud-nya
│   └── cli.py                      seed, create-admin, cleanup
├── alembic/                        migrasi skema
├── tests/
├── Dockerfile
└── pyproject.toml                  dependensi + konfigurasi ruff/mypy/pytest
```

**Aturan penulisan**

| Lapisan | Boleh | Tidak boleh |
|---|---|---|
| `api/v1/endpoints/*` | `Depends(...)` dari `api/deps.py` & `dependencies.py`, panggil **service**, kembalikan **schema** | SQL, `text()`, `db.execute`, aturan bisnis, `HTTPException` (pakai `AppError`) |
| `services/*` | aturan bisnis, memanggil **crud**, melempar `AppError` | SQL, objek `Request`/`Response` |
| `crud/*` | kueri SQL/SQLModel, mengembalikan baris/model | aturan bisnis, `AppError` bisnis |
| `models/*` / `schemas/*` | definisi bentuk data | logika |
| `api/deps.py` | autentikasi, izin, penjaga akses, sesi DB | kueri di luar `crud` |

- Nama berkas: endpoint = jamak modul (`work_plans.py`), crud = `crud_<entitas tunggal>.py`,
  service = `<entitas>_service.py`, schema/model = `<entitas>.py`.
- Satu arah impor: `endpoints → services → crud → models`; `core` boleh diimpor siapa saja, tetapi `core`
  tidak mengimpor lapisan lain. Dijaga uji `tests/test_structure.py` (docs/26 M0).
- Folder `controllers/`, `repositories/`, dan `db/` **tidak boleh** mendapat berkas baru; isinya dipindah ke
  `services/`, `crud/`, dan `core/database.py` (docs/26).

---

## 2. Tanggung jawab tiap lapisan

### Router — `api/v1/routes/`
Tipis. Hanya: jalur, metode, status, model respons, dependency. **Tidak ada `if` aturan
bisnis dan tidak pernah menyentuh basis data.**

```python
@router.post("/{plan_id}/publish", response_model=WorkPlanRead, status_code=200)
async def publish_work_plan(
    plan_id: UUID,
    payload: PublishRequest,
    ctx: RequestContext = Depends(get_context),
    controller: WorkPlanController = Depends(get_work_plan_controller),
):
    return await controller.publish(plan_id, payload, ctx)
```

### Controller — `controllers/`
Satu kasus pakai. Membuka transaksi, memanggil satu atau beberapa servis, mengubah hasil
menjadi skema respons. Di sinilah beberapa langkah digabung: mis. "terbitkan SK" =
terbitkan dokumen + tanda tangani + catat audit + kirim notifikasi.

### Service — `services/`
**Tempat aturan bisnis berada.** Padanan langsung `transition()` di prototipe.

```python
class WorkPlanService:
    async def publish(self, plan: WorkPlan, actor: Actor) -> WorkPlan:
        if plan.status != PlanStatus.DRAFT:
            raise AppError("PLAN_NOT_DRAFT",
                           "Pekerjaan ini sudah terbit, jadi tidak bisa diterbitkan lagi.")
        if not plan.leader_employee_id:
            raise AppError("PLAN_NO_LEADER",
                           "Tentukan ketua tim sebelum menerbitkan SK.")
        ...
```

Aturan: servis **tidak** menulis SQL, **tidak** tahu HTTP, dan **tidak** tahu bentuk JSON.
Servis menerima dan mengembalikan objek domain.

### Repository — `repositories/`
Satu-satunya tempat kueri ditulis. Semua pemuatan relasi eksplisit (`selectinload`), karena
lazy loading tidak bekerja di async.

```python
async def get_with_members(self, plan_id: UUID) -> WorkPlan | None:
    stmt = (select(WorkPlan)
            .where(WorkPlan.id == plan_id)
            .options(selectinload(WorkPlan.members),
                     selectinload(WorkPlan.days)))
    return (await self.session.exec(stmt)).first()
```

### Model vs Schema
- **Model** (`models/`) = bentuk tabel, `table=True`, tidak pernah dikembalikan langsung ke
  klien.
- **Schema** (`schemas/`) = bentuk permintaan & respons.

**Model tidak pernah menjadi respons API.** Ini penting dan mudah dilanggar karena SQLModel
membuatnya tampak praktis: mengembalikan model berarti kolom baru — termasuk yang sensitif
seperti `password_hash` atau `embedding` — otomatis ikut terkirim begitu ditambahkan.

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
| Format & lint | `ruff` (format + lint), `mypy` mode strict |
| Penamaan berkas | `snake_case`, akhiran jelas: `_service`, `_repo`, `_controller` |
| Penamaan fungsi servis | Sama dengan transaksi prototipe: `publish`, `accept`, `request_personnel_change` |
| Tipe | Anotasi penuh; tidak ada `Any` tanpa alasan tertulis |
| Impor | Absolut (`app.services.x`), bukan relatif berantai |
| Async | Semua I/O `async`; kerja CPU berat (kompresi gambar, render PDF) → `run_in_threadpool` |
| Rahasia | Hanya lewat `core/config.py`; tidak ada `os.getenv` tersebar |
| Waktu | Hanya lewat `core/time.py` |
| Komentar | Menjelaskan **kenapa**, bukan **apa** |

**Kerja berat tidak boleh memblokir event loop.** Kompresi gambar dan render PDF berjalan di
thread pool. Ini mudah terlewat dan akibatnya seluruh server tersendat saat satu orang
mengunggah foto besar.

---

## 6. DRY di backend

**Yang disatukan:**

| Hal | Di mana |
|---|---|
| CRUD dasar | `repositories/base.py` generik |
| Pagination, penyaringan, pengurutan | `core/pagination.py` |
| Pemeriksaan izin | `core/permissions.py` — **tidak pernah** ditulis ulang di router |
| Pemetaan galat | `core/errors.py` |
| Kompresi gambar | `storage/image_compressor.py` |
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
| Unit | Servis, dengan repository tiruan | pytest |
| Integrasi | Repository, trigger, RLS, constraint | pytest + PostgreSQL nyata |
| API | Endpoint + matriks RBAC | httpx AsyncClient |

- **PostgreSQL sungguhan**, bukan SQLite: separuh aturan sistem ini hidup di trigger, RLS,
  dan exclusion constraint yang tidak dimiliki SQLite.
- Setiap uji berjalan dalam transaksi yang di-*rollback*, atau memakai basis data sekali
  pakai (`pytest-postgresql` / container).
- Waktu dibekukan lewat `core/time.py`.
- **Matriks RBAC dibangkitkan**: setiap endpoint × 7 peran. Endpoint baru tanpa baris di
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
