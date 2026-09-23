# 01 · Inventaris Aset

Apa yang **sudah ada** di komputer ini, dan vonis pakai-ulangnya. Semua angka di bawah
berasal dari pemindaian nyata pada 23 September 2026, bukan perkiraan.

Vonis yang saya pakai: **PAKAI** (jadi fondasi) · **AMBIL** (salin bagian tertentu) ·
**RUJUK** (baca, jangan salin) · **PENSIUN** (jangan disentuh lagi).

---

## 1. Ringkasan

| Aset | Lokasi | Isi | Vonis |
|---|---|---|---|
| Prototipe V2 | `visiontech-V2/` | HTML/CSS/JS polos, 162 layar, 49 transaksi | **PAKAI** — spesifikasi produk |
| Skema basis data | `visiontech-V2/db/` | 5 berkas SQL, 30+ tabel | **PAKAI** — fondasi data |
| Dokumen VMS lama | `visiontech/docs/` | 10 dokumen, 1.667 baris (BRD/SRS/FRD/dll.) | **RUJUK** |
| Backend VMS lama | `visiontech/backend/` | FastAPI, 67 berkas Python | **AMBIL** sebagian |
| Web VMS lama | `visiontech/web/` | React + Vite, 51 berkas TS/TSX | **AMBIL** sebagian |
| Mobile VMS lama | `visiontech/mobile/` | Flutter, 38 berkas Dart | **AMBIL** — paling berharga |
| API percobaan | `vti_api/` | FastAPI, 45 berkas Python | **PENSIUN** |
| Web percobaan | `vti_frontend/` | React 19 + MUI + Tailwind | **PENSIUN** |
| Layanan wajah | `face_api_service/` | FastAPI + pgvector, 3 berkas | **AMBIL** — hemat waktu besar |
| PostgreSQL 18 + PostGIS | terpasang di Windows | layanan `postgresql-x64-18` berjalan | **PAKAI** |

---

## 2. Prototipe V2 — **PAKAI**

`visiontech-V2/index.html`, `js/`, `css/`, `tests/`

Ini bukan mockup. Ini definisi produk yang sudah melewati puluhan putaran QA:

- **`js/domain.js`** memuat mesin transisi murni `transition(state, actor, type, payload)`
  dengan **49 jenis transaksi**: `CREATE_PLAN`, `PUBLISH`, `ACCEPT`, `APPEAL`, `REVISE`,
  `REQUEST_CHANGE`, `REQUEST_PERSONNEL_CHANGE`, `ACCEPT_CHANGE`, `WITHDRAW_CHANGE`,
  `CHECK_IN`, `CHECK_OUT`, `REVIEW_ATTENDANCE`, `EXPLAIN_ATTENDANCE`, `SAVE_REPORT`,
  `SUBMIT_REPORT`, `REVIEW_REPORT`, `SAVE_WEEKLY`, `SUBMIT_WEEKLY`, `REVIEW_WEEKLY`,
  `REQUEST_COMPLETE`, `APPROVE_COMPLETE`, `RESERVE_ASSET`, `RELEASE_ASSET`, `RETURN_ASSET`,
  `VERIFY_RETURN`, `CHECK_ASSET`, `REPORT_INCIDENT`, `RESOLVE_INCIDENT`, `REPORT_OVERTIME`,
  `REVIEW_OVERTIME`, `UPLOAD_DOCUMENT`, `VERIFY_DOCUMENT`, `PROMOTE`, `OFFBOARD`, dan lainnya.
- **7 peran**: PM (per unit bisnis), LEADER, MEMBER, FINANCE, HR, ASSET, OPS.
  5 unit: CCTV_ACS, WALL_DISPLAY, FINANCE_ACCOUNTING, OPERATIONS, BIZDEV_COMMERCIAL.
- **Pengujian**: `node --test tests/domain.test.cjs` (19 uji), `tests/browser.mjs`
  (162 layar, Playwright), `tests/offline_geo.mjs` (antrean luring + geofence).

**Cara memakainya:** setiap aturan di `domain.js` diterjemahkan menjadi satu fungsi servis
di backend, **satu per satu, dengan uji yang setara**. Bila aplikasi sungguhan berbeda
perilakunya dari prototipe, yang salah adalah aplikasi sungguhan.

> Prototipe tetap hidup selama pembangunan sebagai **alat banding**. Jangan dihapus dan
> jangan diubah kecuali aturannya memang berubah atas keputusan Anda.

---

## 3. Skema basis data `db/` — **PAKAI**

| Berkas | Isi |
|---|---|
| `01_schema.sql` | Ekstensi, 20 enum, 28 tabel inti, indeks, batasan |
| `02_functions.sql` | Trigger aturan bisnis, geofence, bentrok personel, view rekap |
| `03_policies.sql` | Peran DB (`vms_app`, `vms_readonly`, `vms_migrator`), hak akses, RLS |
| `04_signature_auth.sql` | Tanda tangan digital ber-QR, `signing_key`, sesi JWT, lockout |
| `05_face.sql` | `face_enrollment` (vector 512), persetujuan biometrik, retensi |

**Status jujur:** belum pernah dijalankan. `psql` ada, PostgreSQL 18 berjalan — jadi
pengujian pertamanya bisa dilakukan kapan saja Anda izinkan.

**Satu penyesuaian yang sudah pasti perlu:** skema memakai pembungkus `new_id()` yang kini
mengembalikan `gen_random_uuid()`. Karena server Anda **PostgreSQL 18**, ganti isinya
menjadi `uuidv7()` — nilainya urut waktu, indeks lebih padat, tanpa mengubah satu pun
definisi tabel. Ini keuntungan gratis; ambil.

---

## 4. `visiontech/` — percobaan VMS sebelumnya

Ini yang paling perlu dibahas hati-hati, karena isinya banyak dan terlihat siap pakai.

### 4.1 Dokumen (`visiontech/docs/`) — **RUJUK**

Sepuluh dokumen lengkap (Proposal, BRD, SRS, FRD, Data Model, API Spec, UI/UX,
Implementation Plan, Decisions, Gap Analysis). Kualitasnya bagus dan **30 keputusan (D-01
… D-30)** di dalamnya layak dibaca.

**Tetapi produknya berbeda dari yang Anda setujui sekarang.** Perbedaan mendasar:

| Hal | Dokumen `visiontech/` | Prototipe V2 (yang berlaku) |
|---|---|---|
| Model peran | `super_admin, admin, team_leader, finance, hes, user` | PM per unit, LEADER/MEMBER **mengikuti SK** |
| Sumber kewenangan | Role statis pada akun | Penugasan pada SK yang berlaku |
| Absensi | Khusus dinas luar kota, geofence poligon Kota Pekanbaru | Per lokasi proyek + radius, semua pekerjaan |
| Geospasial | D-30: **tanpa PostGIS**, pakai shapely | PostGIS, jarak dihitung di basis data |
| Dokumen SK | tidak ada konsep SK/adendum/penerimaan | inti produk |
| Tanda tangan QR | tidak ada | inti produk |
| Wajah | tidak ada | fase 8 |
| Cuti, portofolio, HES indikator | ada | tidak ada |

Artinya: **jangan menjadikan dokumen itu spesifikasi.** Bacalah untuk tiga hal yang tetap
berlaku dan sayang kalau disusun ulang: format error API, struktur dokumen kebutuhan, dan
daftar pertanyaan operasional (hosting, distribusi APK, retensi).

### 4.2 Backend (`visiontech/backend/`, 67 berkas Python) — **AMBIL sebagian**

FastAPI + SQLAlchemy async + Alembic + MinIO + geoalchemy2.

**Yang layak diambil** (pola, bukan salin mentah):
- `core/` — konfigurasi `pydantic-settings`, logging JSON + `request_id`, format error seragam.
- `storage/` — abstraksi penyimpanan berkas + validasi gambar (magic bytes, re-encode Pillow).
- `cli.py` — pola perintah administratif (`seed`, `create-superadmin`, `cleanup-orphans`).
- `alembic/` — konfigurasi migrasi, bukan isi migrasinya.
- `tests/conftest.py` — pola uji dengan PostgreSQL nyata, bukan SQLite.

**Yang tidak diambil:** seluruh `models/`, `routers/`, `services/`. Model identitasnya
(`user_app` 1:1 `employees`, enum peran `ADMIN/FIELD_STAFF/PM/OM/...`) bertabrakan langsung
dengan model "kewenangan mengikuti SK". Memaksakannya berarti menulis ulang hampir semua
endpoint sambil membawa asumsi lama — lebih lambat daripada menulis baru di atas skema `db/`.

Gap Analysis milik mereka sendiri sudah mengakui ini: 13 dari 14 baris "fondasi" berstatus
**Beda (besar)** atau **Belum ada**.

### 4.3 Web (`visiontech/web/`, 51 berkas) — **AMBIL sebagian**

React + Vite + TypeScript + Caddy. Yang diambil: `Caddyfile` (header keamanan + proxy),
`vite.config.ts`, konfigurasi TS strict, skrip `gen:api` dari `openapi.json`, dan pola
komponen `DataTable` + `FormDialog`. Halaman-halamannya dibangun ulang mengikuti 162 layar
prototipe.

### 4.4 Mobile (`visiontech/mobile/`, 38 berkas Dart) — **AMBIL, ini yang paling berharga**

Flutter dengan fitur `attendance/` (termasuk `geofence_confirm` dan `watermark_camera`),
`auth/`, `fieldwork/`, `logbook/`, `sync/`, `notifications/`, `profile/`.

Kamera berwatermark, konfirmasi geofence, dan kerangka sinkronisasi adalah bagian yang
paling mahal dan paling banyak jebakannya di Android. Kode ini menghemat perkiraan
**2–3 minggu**. Yang perlu diganti: lapisan data/API (menyesuaikan kontrak baru) dan
fitur `leave/` (cuti tidak ada di produk ini).

---

## 5. `vti_api/` dan `vti_frontend/` — **PENSIUN**

- `vti_api/` (45 berkas): FastAPI dengan `bcrypt`, `psycopg2`, `geopy`, dan — perlu
  dicatat — dependensi `openai`. Strukturnya (`app/agent`, `app/mobile`, `app/web`)
  berbeda arah dari yang dibutuhkan. Tidak ada bagian yang cukup unik untuk diselamatkan.
- `vti_frontend/`: React 19 + Vite, tetapi memakai **tiga sistem styling sekaligus**
  (Tailwind, MUI/Emotion, styled-components) dan validasi `yup` + `react-hook-form`.
  Campuran itu mahal dirawat. Satu hal yang menarik untuk ditiru: `react-speech-recognition`
  — bila Anda memang ingin input suara untuk laporan lapangan, itu ide bagus dan saya
  catat sebagai kandidat fase lanjutan.

Saran: jangan dihapus, cukup diamkan. Biayanya nol dan sewaktu-waktu bisa dilihat lagi.

---

## 6. `face_api_service/` — **AMBIL**

Tiga berkas (`main.py`, `face_utils.py`, `database.py`): FastAPI + `pgvector.psycopg2`,
endpoint `/register` yang menyimpan embedding dengan upsert per `karyawan_id`.

Ini persis bentuk layanan yang dibutuhkan skema `db/05_face.sql`. Yang perlu disesuaikan:

1. Tabelnya sekarang `face_encodings` sederhana → ganti ke `face_enrollment` + `face_check`
   milik skema baru, dengan persetujuan biometrik dan retensi.
2. Belum ada deteksi keaslian wajah (*liveness*) — **ini wajib ditambah**, tanpa itu foto
   dari galeri bisa menembus pencocokan.
3. Pastikan dimensi embedding model yang dipakai = 512 (ArcFace/InsightFace). Bila berbeda,
   ubah `vector(512)` di skema.

---

## 7. Lingkungan mesin ini

| Komponen | Status | Catatan |
|---|---|---|
| PostgreSQL 18 | **terpasang, layanan berjalan** (`postgresql-x64-18`) | `psql.exe` tersedia |
| PostGIS 3.6 | **tersedia** | `postgis.control` ada di `share/extension` |
| pgcrypto, btree_gist, pg_trgm, citext | tersedia | semua yang dipakai skema `01`–`04` |
| **pgvector** | **BELUM ADA** | tidak ada `vector.control` — dibutuhkan `05_face.sql` |
| Docker Desktop | terpasang, mesin mati | tidak wajib karena PG18 sudah ada |
| Git | repo ini **belum** di bawah Git | perlu diinisialisasi sebelum fase 0 |

**Konsekuensi langsung:** `db/01`–`db/04` bisa diuji sekarang juga di PostgreSQL 18 lokal.
`db/05_face.sql` baru bisa diuji setelah pgvector dipasang. Karena pengenalan wajah ada di
fase 8, ini tidak menghambat apa pun — cukup dicatat.

---

## 8. Kesimpulan

Yang dipakai ulang menghemat perkiraan **4–6 minggu**: Flutter (2–3 minggu), layanan wajah
(1–1,5 minggu), fondasi backend dan web (1–1,5 minggu).

Yang sengaja tidak dipakai ulang — model data dan endpoint lama — bukan karena kualitasnya
buruk, melainkan karena menjawab pertanyaan produk yang berbeda. Membawanya ikut berarti
membawa asumsi lama ke sistem baru, dan asumsi itulah yang paling sulit dicabut belakangan.
