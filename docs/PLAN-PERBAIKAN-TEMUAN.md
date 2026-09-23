# Plan Perbaikan Temuan — VMS

**Dibuat:** 2026-09-23 · **Metode:** pemecahan masalah 7 segmen · **Berlaku untuk:** manusia & agen AI
**Hubungan dengan plan lain:** dikerjakan **sebelum** melanjutkan `PLAN-SISA-MVP.md` blok A-3 dst.
Tanpa perbaikan ini, setiap fitur baru dibangun di atas fondasi yang tidak bisa menyimpan data.

Setiap task di Bagian 8 tetap tunduk pada `.agy/rules/*` dan `CLAUDE.md`: uji dulu, satu task =
satu commit, CHANGELOG, pemeriksaan rahasia, push.

---

## Segmen 1 · Definisi masalah

> **Backend VMS tampak "Fase 1–7 selesai" di CHANGELOG, tetapi pada 2026-09-23 tidak satu pun
> endpoint selain `/auth/*` dapat menyimpan data atau bahkan dipanggil dengan benar di basis data
> sungguhan.** Masalahnya bukan satu bug, melainkan tidak adanya umpan balik: kode ditulis dan
> di-commit tanpa pernah dijalankan terhadap PostgreSQL.

**Bukti** (probe `.local_tests/probe_endpoints.py`, token ADMIN sah):

| Panggilan | Hasil | Seharusnya |
|---|---|---|
| `GET /auth/me` | `role: ADMIN`, `permissions: []` | ADMIN punya seluruh izin |
| `GET /audit-events`, `/employees`, `/plans` | 403 `Not enough permissions` | 200 |
| `GET /sites`, `/assets` | 500 `BAD_REQUEST` "Internal server error" | 200 |
| Semua `POST/PUT/PATCH` di 13 router | Tidak pernah `commit` → di-rollback diam-diam | Tersimpan |
| Web `POST /api/v1/auth/login` | 404 (API tidak berawalan `/api/v1`) | 200 |

**Kriteria selesai (terukur):**
1. Setiap endpoint API dapat dipanggil peran yang berwenang tanpa 500 — dibuktikan uji otomatis.
2. Setiap endpoint tulis benar-benar menyimpan data — dibuktikan uji integrasi PostgreSQL.
3. Matriks izin 8 peran sesuai dok 03 §1 — dibuktikan uji parametrik.
4. CI menjalankan lint, tipe, dan uji terhadap PostgreSQL nyata pada setiap push — merah bila gagal.
5. Aturan AI mencegah pola "klaim selesai tanpa bukti uji" terulang.

**Di luar cakupan plan ini:** fitur baru, UI web/mobile (Blok C/D), refactor lapisan modul SK
dan absensi (A-3/A-4) — kecuali sejauh diperlukan agar endpoint tidak rusak.

---

## Segmen 2 · Pemecahan masalah (pohon isu, MECE)

```
Endpoint tidak bisa menyimpan / dipanggil
├── A. Lapisan basis data
│   ├── A1 Sesi tidak pernah commit ................................. F-01
│   ├── A2 Konteks RLS (SET LOCAL) gagal dieksekusi ................. F-02
│   ├── A3 Skema DB ≠ skema repo (new_id rusak, search_path) ........ F-15 (sudah diperbaiki)
│   └── A4 RLS tidak berlaku: vms_app superuser + BYPASSRLS ......... F-11
├── B. Identitas & izin
│   ├── B1 Kode peran DB (UPPER) ≠ peta izin (lower) ................ F-03
│   ├── B2 Peta izin tidak mengikuti 8 peran dok 03 ................. F-04
│   ├── B3 Peran dibawa di token, bukan dibaca dari DB (dok 05 §4) .. F-04
│   ├── B4 `create-admin` menyisipkan 'admin' → enum galat .......... F-05
│   └── B5 JWT HS256 + rahasia bawaan, bukan EdDSA (K-20) ........... F-12
├── C. Kontrak HTTP
│   ├── C1 Tanpa awalan /api/v1 (dok 05) ............................ F-07
│   ├── C2 500 berlabel BAD_REQUEST; pesan Inggris .................. F-06
│   └── C3 Web memanggil rute & izin dari percobaan lama ............ F-08
├── D. Kode yang belum terverifikasi
│   ├── D1 services/ & repositories/ (plan, attendance, document, pdf) belum pernah dipakai/diuji .. F-09
│   └── D2 attendance_cron memakai setelan yang tidak ada ........... F-10
└── E. Proses (akar dari semua di atas)
    ├── E1 CI hanya `echo` → tidak ada gerbang otomatis ............. F-13
    ├── E2 Tidak ada uji endpoint/RBAC terhadap DB nyata ............ F-14
    └── E3 Agen AI menandai "selesai" tanpa menjalankan kode ........ F-17
```

---

## Segmen 3 · Prioritas

Skor: **Dampak** (1–5) × **Kemungkinan terjadi di produksi** (1–5); **Biaya** S/M/L.
Urutan akhir juga mengikuti ketergantungan: yang memblokir banyak hal dikerjakan dulu.

| Temuan | Dampak | Kemungkinan | Skor | Biaya | Memblokir | Urutan |
|---|---|---|---|---|---|---|
| F-02 SET LOCAL gagal | 5 | 5 | 25 | S | semua endpoint terlindungi | **1** |
| F-01 tidak commit | 5 | 5 | 25 | S | semua endpoint tulis | **2** |
| F-03/F-04 peran ↔ izin | 5 | 5 | 25 | M | semua endpoint ber-izin | **3** |
| F-05 create-admin | 4 | 5 | 20 | S | onboarding pertama | **4** |
| F-06 galat 500 & pesan | 3 | 5 | 15 | S | UX, prinsip 5 | **5** |
| F-07 /api/v1 | 4 | 5 | 20 | S | web ↔ API | **6** |
| F-10 cron | 3 | 5 | 15 | S | peringatan bisnis | **7** |
| F-14 uji asap semua rute | 5 | 4 | 20 | M | pencegahan | **8** |
| F-13 CI nyata | 5 | 4 | 20 | M | pencegahan | **9** |
| F-17 aturan AI | 4 | 4 | 16 | S | pencegahan | **10** |
| F-11 RLS efektif | 5 | 2 | 10 | M | butuh akses admin server | 11 (keputusan pemilik) |
| F-12 JWT EdDSA | 4 | 2 | 8 | M | P1-1 | 12 |
| F-09 servis belum terverifikasi | 3 | 3 | 9 | L | A-3/A-4 | dikerjakan saat A-3/A-4 |
| F-08 web lama | 4 | 3 | 12 | L | Blok C | dikerjakan saat Blok C |

---

## Segmen 4 · Rencana kerja

| Gelombang | Isi | Keluaran yang bisa diperiksa |
|---|---|---|
| **G1 · Fondasi DB** | T-01, T-02 | Endpoint terlindungi tidak 500; data tulis tersimpan |
| **G2 · Identitas** | T-03, T-04, T-05 | ADMIN & 7 peran lain mendapat izin sesuai dok 03; `create-admin` jalan |
| **G3 · Kontrak HTTP** | T-06, T-07, T-08 | Galat baku berbahasa Indonesia; semua rute di `/api/v1`; cron tidak crash |
| **G4 · Jaring pengaman** | T-09, T-10, T-11 | Uji asap semua rute; CI hijau/merah sungguhan; aturan AI diperketat |
| **G5 · Keputusan pemilik** | T-12, T-13 | Role DB non-superuser; JWT EdDSA |

Setiap task berdiri sendiri, ber-uji, dan di-push. Bila satu task gagal, task berikutnya tidak
dimulai sebelum penyebabnya dicatat.

---

## Segmen 5 · Analisis akar masalah (5 × mengapa)

**F-01 — data tidak tersimpan**
1. Mengapa tidak tersimpan? `AsyncSession` ditutup tanpa `commit()`.
2. Mengapa tidak ada commit? `get_db` hanya `yield session`; tidak ada batas transaksi.
3. Mengapa tidak ada batas transaksi? Lapisan controller (dok 12 §2) belum dibuat; router ditulis langsung.
4. Mengapa tidak terdeteksi? Tidak ada uji yang membaca ulang data setelah endpoint tulis.
5. Mengapa tidak ada uji itu? CI kosong dan aturan AI tidak mensyaratkan uji integrasi per endpoint.
→ **Akar:** tidak ada batas transaksi baku + tidak ada uji "tulis lalu baca ulang".

**F-02 — SET LOCAL gagal**
1. Mengapa 500? asyncpg menolak `SET LOCAL a = $1; SET LOCAL b = $2; …` — `SET` tidak menerima parameter bind dan prepared statement tidak boleh berisi banyak perintah.
2. Mengapa ditulis begitu? Pola disalin dari psycopg (sinkron) yang mengirim string mentah.
3. Mengapa lolos? Tidak ada endpoint terlindungi yang pernah dipanggil dalam uji.
→ **Akar:** asumsi pustaka tidak diverifikasi + nihil uji. Perbaikan baku: `SELECT set_config(key, value, true)`.

**F-03/F-04 — ADMIN tanpa izin**
1. Mengapa kosong? `ROLE_PERMISSIONS` berkunci `admin`, DB mengirim `ADMIN`.
2. Mengapa beda? Peta izin ditulis dari model peran percobaan lama (`hr/pm/field`), bukan enum `role_code`.
3. Mengapa tidak ketahuan? Tidak ada uji yang membandingkan kode peran Python dengan `pg_enum`.
→ **Akar:** dua sumber kebenaran untuk satu daftar. Perbaikan: satu `Enum` Python + uji kesetaraan dengan DB.

**F-07 — /api/v1**: dok 05 menetapkan basis, router ditulis tanpa awalan, web mengikuti dok.
→ **Akar:** kontrak tidak diuji dari sisi klien. Perbaikan: awalan di satu tempat (`main.py`) + uji rute.

**F-13/F-17 — proses**
1. Mengapa semua bug di atas bisa masuk? Tidak ada gerbang otomatis.
2. Mengapa CI kosong? P0-11 ditandai selesai dengan kerangka `echo`.
3. Mengapa ditandai selesai? DoD fase tidak diperiksa; agen menilai "selesai" dari keberadaan berkas.
→ **Akar:** definisi "selesai" = berkas ada, bukan = terbukti jalan.

---

## Segmen 6 · Sintesis

1. **Satu pola gagal, banyak gejala.** Hampir semua temuan adalah kode yang *tidak pernah
   dijalankan*. Memperbaiki gejala satu per satu tidak cukup — yang harus berubah adalah syarat
   "selesai".
2. **Sumber kebenaran ganda selalu menyimpang.** Peran (DB vs Python), skema (repo vs server),
   jalur API (dok vs router). Setiap daftar yang hidup di dua tempat butuh **uji kesetaraan**.
3. **Batas transaksi harus bawaan, bukan pilihan.** Endpoint baru tidak boleh bisa "lupa commit".
4. **Keamanan lapis kedua (RLS) saat ini mati** karena peran DB superuser; lapis pertama (izin di
   aplikasi) baru saja diperbaiki. Sampai F-11 selesai, aplikasi adalah satu-satunya pagar.

---

## Segmen 7 · Rekomendasi & pencegahan agar tidak terulang

| # | Pencegahan | Bentuk konkret | Task |
|---|---|---|---|
| P-1 | Batas transaksi otomatis | Dependency DB default commit di akhir permintaan sukses, rollback saat galat; controller baru memakai `unit_of_work` | T-02 |
| P-2 | Konteks RLS dengan cara yang benar | `set_config(..., true)` dalam satu `SELECT`, diuji | T-01 |
| P-3 | Satu sumber daftar peran | `RoleCode` Python + uji kesetaraan dengan `pg_enum` | T-03 |
| P-4 | Uji asap seluruh rute | Uji yang **menginventaris `app.routes` otomatis**: rute baru tanpa uji/izin → gagal | T-09 |
| P-5 | Gerbang CI sungguhan | PostgreSQL+PostGIS+pgvector di CI, pasang `db/*.sql` + Alembic, jalankan ruff/mypy/pytest | T-10 |
| P-6 | Definisi "selesai" baru untuk AI | Aturan: endpoint baru wajib uji integrasi tulis-lalu-baca; klaim selesai wajib menyertakan keluaran uji; dilarang menandai task selesai berdasarkan keberadaan berkas | T-11 |
| P-7 | Rahasia tidak masuk Git | Sudah: pemindaian sebelum push (git-flow butir 8). Tambahan: `gitleaks` di CI | T-10 |
| P-8 | Skema server = skema repo | CI membangun DB dari `db/*.sql` + migrasi; perubahan skema hanya lewat Alembic | T-10, aturan |

**Komunikasi:** setiap task selesai dicatat di `CHANGELOG.md` dan dicentang di Bagian 8.
Keputusan yang diambil sendiri dicatat di dok 10 Bagian C.

---

## Bagian 8 · Plan turunan (antrean eksekusi)

Format tiap task: **Masalah → Uji dulu → Perubahan → DoD**. Centang hanya setelah commit di-push.

### G1 · Fondasi DB

- [x] **T-01 · Konteks RLS dengan `set_config`** (F-02)
  - Uji: `tests/test_db_context.py` — dependency menyetel `app.user_id`, `app.organization_id`,
    `app.actor_label`; `current_user_id()`/`current_org_id()` di DB mengembalikan nilai itu; nilai
    hilang setelah transaksi (tidak bocor ke permintaan lain).
  - Perubahan: `api/app/api/deps.py::get_db_with_user` → satu `SELECT set_config(...), set_config(...), set_config(...)`.
  - DoD: `GET /sites` dengan token sah → bukan 500.

- [x] **T-02 · Batas transaksi bawaan** (F-01)
  - Uji: endpoint tulis sungguhan (`POST /sites`) lalu baca ulang lewat koneksi terpisah → baris ada;
    endpoint yang melempar galat → tidak ada baris tersisa.
  - Perubahan: dependency sesi (`get_db`/`get_db_with_user`) commit setelah handler sukses,
    rollback bila galat; `AppError(persist=True)` tetap di-commit. Pastikan commit terjadi
    **sebelum** respons dikirim (uji: galat commit → klien menerima 500, bukan 200).
  - DoD: uji tulis-lalu-baca hijau; auth tetap hijau.

### G2 · Identitas & izin

- [x] **T-03 · Satu sumber peran + peta izin 8 peran** (F-03, F-04)
  - Uji: `RoleCode` Python == `enum_range(NULL::vms.role_code)`; parametrik 8 peran × izin sesuai dok 03 §1;
    ADMIN mendapat semua izin; peran tak dikenal → tanpa izin.
  - Perubahan: `core/permissions.py` berkunci `RoleCode`; `require_permission` tanpa perbandingan string `"admin"`.
  - DoD: probe ADMIN → `/audit-events`, `/employees`, `/plans` 200.

- [x] **T-04 · Peran dibaca dari DB tiap permintaan** (F-04, dok 05 §4)
  - Uji: cabut peran di DB → permintaan berikutnya dengan token lama ditolak 403; akun nonaktif → 401.
  - Perubahan: `get_current_user` memuat peran & `is_active` dari DB; token hanya identitas (`sub`, `org`, `jti`).

- [x] **T-05 · `create-admin` memakai `ADMIN`** (F-05)
  - Uji: jalankan fungsi `create_admin` ke organisasi uji → pengguna + peran `ADMIN` tersimpan; login berhasil.

### G3 · Kontrak HTTP

- [x] **T-06 · Galat baku & Bahasa Indonesia** (F-06)
  - Uji: 401/403/404/405/500 menghasilkan kode yang benar (`UNAUTHENTICATED`/`FORBIDDEN`/`NOT_FOUND`/`METHOD_NOT_ALLOWED`/`INTERNAL_ERROR`) dan pesan Indonesia; tidak ada jejak tumpukan.
- [x] **T-07 · Awalan `/api/v1`** (F-07)
  - Uji: `/api/v1/auth/login` 200; `/auth/login` 404; `/health` & `/ready` tetap di akar (Caddy).
- [x] **T-08 · `attendance_cron` memakai setelan yang ada** (F-10)
  - Uji: impor modul & panggil fungsi peringatan tanpa webhook → tidak crash.
- [x] **T-15 · Wajah tidak cocok benar-benar masuk NEEDS_REVIEW** (F-19, ditemukan saat T-08)
  - Masalah: trigger BEFORE dijalankan menurut urutan nama; `attendance_face_flag` jalan sebelum
    `attendance_geofence` yang lalu menyetel ulang status → `NO_MATCH`/`LOW_QUALITY` selalu tersimpan
    `AUTO_VALID`. Melanggar aturan inti "wajah tidak cocok → diperiksa manusia" (K-10, R-02).
  - Uji: `tests/test_attendance_triggers.py` — NO_MATCH/LOW_QUALITY → NEEDS_REVIEW; MATCH/NOT_ENROLLED/
    SKIPPED/tanpa wajah → AUTO_VALID; urutan trigger dijaga.
  - Perubahan: migrasi `0003` mengganti nama trigger menjadi `attendance_post_geofence_face_flag`;
    `db/05_face.sql` disamakan.
- [ ] **T-16 · Python lokal = Python produksi (3.12)** (F-21, ditemukan saat T-09)
  - Masalah: venv lokal memakai Python 3.14 (anotasi malas, PEP 649), Dockerfile & tumpukan terkunci
    3.12. `employees.py` memakai `date` tanpa impor — lolos di 3.14, **gagal saat impor di 3.12** →
    API tidak bisa start di container. Bug semacam ini tak terlihat selama uji jalan di 3.14.
  - Perubahan: venv `api/.venv` dibuat ulang dengan CPython 3.12 (tersedia lewat uv); CI (T-10)
    memakai 3.12; `ruff --select F821` (nama tak terdefinisi) masuk gerbang CI.
  - Uji: seluruh suite hijau di 3.12; `python -c "import app.main"` di 3.12.
- [ ] **T-14 · MinIO tidak disentuh saat impor** (F-18, ditemukan saat T-02)
  - Masalah: `core/storage.py` memanggil `ensure_bucket()` di tingkat modul → setiap impor aplikasi
    (termasuk uji dan `alembic`) mencoba menyambung ke MinIO dan mengulang ±10 detik bila mati.
    Melanggar prinsip 3 (komponen pendukung mati → pekerjaan tetap bisa dilakukan).
  - Uji: impor `app.main` dengan MinIO tak terjangkau selesai < 1 detik tanpa percobaan koneksi;
    `/ready` melaporkan status MinIO.
  - Perubahan: klien & bucket dibuat malas (saat pertama dipakai) atau di `lifespan`, dengan batas waktu.

### G4 · Jaring pengaman

- [x] **T-09 · Uji asap seluruh rute** (F-14, P-4)
  - Uji menginventaris `app.routes`: setiap rute non-publik tanpa token → 401; dengan ADMIN → bukan 500.
    Rute publik harus terdaftar eksplisit.
- [ ] **T-10 · CI sungguhan** (F-13, P-5, P-7, P-8)
  - `ci.yml`: service PostGIS+pgvector, pasang `db/01–05`, `alembic upgrade head`, `ruff`, `mypy`
    (modul yang sudah bersih), `pytest`; `gitleaks`; notifikasi Discord tetap.
- [ ] **T-11 · Aturan AI: definisi selesai** (F-17, P-6)
  - `.agy/rules/ai-testing.md` + `CLAUDE.md`: syarat bukti uji, uji tulis-lalu-baca per endpoint,
    larangan menandai selesai tanpa menjalankan kode, perubahan skema hanya lewat Alembic.

### G5 · Butuh keputusan pemilik produk

- [ ] **T-12 · RLS efektif** (F-11) — buat peran DB aplikasi non-superuser tanpa `BYPASSRLS`;
  butuh akses admin server. Rencana dan skrip disiapkan, eksekusi menunggu persetujuan.
- [ ] **T-13 · JWT EdDSA** (F-12, K-20) — kunci Ed25519 dari env/berkas, `kid`, uji verifikasi.

### Dikerjakan bersama plan lain
- F-09 → diverifikasi terhadap skema saat A-3 (SK) dan A-4 (absensi), dengan pola A-2.
- F-08 → Blok C (web) dimulai dengan menyelaraskan `web/` ke kontrak dok 05 dan peran dok 03.
