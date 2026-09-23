# Plan Pengerjaan Sisa MVP — VMS

**Dibuat:** 2026-09-23  
**Status Saat Ini:** Backend Fase 1–3 ✅ · Backend Fase 4–7 (mekanisme) ✅ · UI semua fase ❌ · Arsitektur Backend belum sesuai standar `docs/12` ⚠️

> **Catatan penting:** Plan ini **tidak menimpa** aturan yang sudah ada di `.agy/rules/`. Setiap pekerjaan tetap wajib mengikuti:
> - `.agy/rules/changelog.md` — tulis CHANGELOG sebelum commit
> - `.agy/rules/git-flow.md` — branch `development`, PR ke `prod`
> - `.agy/rules/design-system.md` — semua UI pakai token VMS
> - `.agy/rules/tailwind-v4.md` — hanya Tailwind v4
> - `.agy/rules/ai-testing.md` — test lokal di `.local_tests/`

---

## Prioritas Eksekusi

```
[A] Refactor Arsitektur Backend  →  [B] QR & PDF  →  [C] UI Web  →  [D] Flutter Mobile  →  [E] Hardening
```

Prioritas **A** dikerjakan **paralel** dengan **B**, karena keduanya murni backend tanpa UI.

---

## [A] Refactor Arsitektur Backend — KRITIS
> **Mengapa perlu?** Semua endpoint saat ini ditulis langsung dalam router (raw SQL di dalam `@router.post`). Standar di `docs/12-STANDAR-BACKEND.md` mewajibkan lapisan: `router → controller → service → repository`. Tanpa ini, kode sulit diuji dan aturan bisnis tersebar.

### A-1 · Buat Struktur Folder yang Benar
**File yang dibuat:**
```
api/app/
├── services/           ← aturan bisnis
│   ├── auth_service.py
│   ├── plan_service.py
│   ├── attendance_service.py
│   ├── employee_service.py
│   ├── document_service.py   ← snapshot + SHA-256
│   ├── asset_service.py
│   └── hse_service.py
├── repositories/       ← semua query SQL
│   ├── plan_repo.py
│   ├── attendance_repo.py
│   ├── employee_repo.py
│   ├── asset_repo.py
│   └── base_repo.py
└── core/
    ├── errors.py       ← AppError standar
    ├── pagination.py   ← Cursor/offset pagination
    └── time.py         ← server time, bukan datetime.now()
```

**Aturan:**
- Router **hanya**: jalur, metode, status code, `response_model`, dependency injection — tidak ada `if` bisnis.
- Service menerima objek domain, bukan `AsyncSession` langsung.
- Repository adalah satu-satunya tempat SQL/ORM ditulis.
- `datetime.now()` **dilarang** — hanya `from app.core.time import utcnow`.

### A-2 · Refactor Modul Auth
**File:** `api/app/services/auth_service.py`, `api/app/repositories/user_repo.py`  
**Pindahkan** logika dari `api/app/api/auth.py`:
- `login()` — panggil `vms.issue_session`, cek lockout
- `refresh()` — panggil `vms.rotate_session`, cek `is_active`
- `logout()` — cabut sesi
- Router menjadi ≤ 15 baris per endpoint

### A-3 · Refactor Modul Plans
**File:** `api/app/services/plan_service.py`, `api/app/repositories/plan_repo.py`  
- Pindahkan logika transisi status dari `plan_transitions.py`
- Snapshot JSONB + SHA-256 dipindah ke `services/document_service.py`
- Optimistic lock handling → `AppError("CONFLICT", "Muat ulang dan coba lagi")`

### A-4 · Refactor Modul Attendance
**File:** `api/app/services/attendance_service.py`  
- Logika `is_late` dan `is_early_leave` menggunakan jam kerja dari konfigurasi organisasi, bukan hardcoded `>= 9`.
- Geofence calculation dipindah ke service, bukan di router.

### A-5 · Error Handling Terpusat
**File:** `api/app/core/errors.py`  
```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400): ...
```
Tambah exception handler di `main.py` yang mengubah `AppError` → JSON `{"code": "...", "message": "..."}` dengan bahasa Indonesia.

### A-6 · Pagination & Filter Standar
**File:** `api/app/core/pagination.py`  
- Cursor pagination untuk semua endpoint list
- Parameter standar: `?limit=20&cursor=...&sort=created_at:desc`

---

## [B] Tanda Tangan QR & PDF — Fase 6
> Backend `db/04_signature_auth.sql` sudah siap. Tinggal implementasi endpoint.

### B-1 · Document Service (Kanonisasi + Hashing)
**File:** `api/app/services/document_service.py`  
- Kanonisasi JSON via RFC 8785 (`canonicaljson` library)
- SHA-256 dari hasil kanonisasi (bukan `json.dumps` biasa — urutan key harus deterministik)
- `register_signature(plan_id, signer_employee_id, role)` → insert ke `vms.document_signature`
- `verify_by_token(token: str)` → panggil DB function `vms.verify_signature_qr()`

### B-2 · Penomoran Seri Otomatis
**File:** `api/app/services/document_service.py`  
- Panggil DB function `vms.next_signature_serial(org_id, prefix)` yang sudah ada di skema
- Format: `VTI/2026/000001`

### B-3 · Endpoint Tanda Tangan
**File:** `api/app/api/signatures.py`  
```
POST /plans/{id}/sign          — menandatangani SK (ISSUER/ACCEPTOR/WITNESS)
POST /plans/{id}/sign/revoke   — mencabut tanda tangan + alasan
GET  /verify/{token}           — verifikasi publik (tanpa auth), rate-limited 60/mnt
```

### B-4 · Render PDF
**File:** `api/app/services/pdf_service.py`, `api/app/templates/*.html.j2`  
Dependencies: `WeasyPrint` (sudah di requirements), `Jinja2`  
Template yang dibuat:
- `sk.html.j2` — Surat Keputusan
- `addendum.html.j2` — Adendum
- `final_report.html.j2` — Laporan Akhir
- `handover.html.j2` — Berita Acara Serah Terima Aset

**Endpoint:**
```
GET /plans/{id}/pdf          — unduh PDF SK + QR
GET /plans/{id}/report/pdf   — unduh PDF laporan akhir
GET /assets/returns/{id}/pdf — unduh PDF BAST
```

**Aturan rendering:**
- Logo perusahaan dari `file_object` (bukan path hardcoded)
- QR code digenerate via `qrcode` library, embed base64 ke HTML
- Font di-embed ke PDF (tidak bergantung sistem operasi server)

---

## [C] UI Web — React + shadcn/ui
> Semua komponen **wajib** pakai token sistem desain (`docs/18-SISTEM-DESAIN-UI.md`). Tidak ada warna hardcoded.

### C-1 · Setup & Konfigurasi Web
**File:** `web/src/styles/index.css` (ganti dengan `docs/design/web/theme.css`)  
- Install: `npm i tw-animate-css@^1.4.0 @fontsource-variable/plus-jakarta-sans@^5.3.0`
- Update `components.json`: `"style": "new-york"`, `"tailwind.baseColor": "neutral"`, `"cssVariables": true`
- Tambah shadcn components: `button input label card badge dialog sheet table tabs`
- Verifikasi `api/v1/` prefix di semua pemanggilan API dari web

### C-2 · Komponen Shared
**Folder:** `web/src/components/ui/shared/`  
| Komponen | Keterangan |
|---|---|
| `StatusBadge` | Badge warna otomatis dari status domain (`DRAFT` → neutral, `IN_PROGRESS` → brand, dll) |
| `PageHeader` | Judul halaman + breadcrumb + slot aksi kanan |
| `EmptyState` | Ilustrasi + pesan + tombol aksi |
| `DataTable` | Tabel shadcn dengan filter, sort, pagination cursor |
| `ConfirmDialog` | Dialog konfirmasi destruktif (tidak pakai `window.confirm`) |
| `FileUploader` | Upload file dengan progress, validasi tipe, preview |
| `AvatarName` | Avatar inisial + nama + jabatan |

### C-3 · Halaman Auth
**Folder:** `web/src/features/auth/`  
- `LoginPage` — form email + password, error state, loading state
- `MePage` — profil user (sudah ada, perlu selaraskan dengan `GET /auth/me`)

### C-4 · Halaman Karyawan & Dokumen (M2)
**Folder:** `web/src/features/employees/`  
| Halaman | Route | Peran |
|---|---|---|
| Daftar Karyawan | `/employees` | HR, OPS |
| Profil Karyawan | `/employees/:id` | HR, semua untuk diri sendiri |
| Form Tambah/Edit | `/employees/new`, `/employees/:id/edit` | HR |
| Dokumen Karyawan | `/employees/:id/documents` | HR, pemilik |
| Form Unggah Dokumen | dialog | HR, pemilik |

### C-5 · Halaman SK & Siklus (M3)
**Folder:** `web/src/features/plans/`  
| Halaman | Route | Peran |
|---|---|---|
| Daftar SK | `/plans` | PM, Leader, OPS |
| Detail SK + Rincian Hari | `/plans/:id` | PM, Leader, Member |
| Buat / Edit Draft | `/plans/new`, `/plans/:id/edit` | PM |
| Dialog Terbitkan SK | `/plans/:id` (dialog) | PM |
| Dialog Adendum | `/plans/:id` (dialog) | PM |
| Riwayat Versi Dokumen | `/plans/:id/history` | PM, OPS |
| Dialog Konflik Jadwal | saat assign personel | PM |

### C-6 · Halaman Absensi (M4)
**Folder:** `web/src/features/attendance/`  
| Halaman | Route | Peran |
|---|---|---|
| Daftar Absensi | `/attendance` | Finance, OPS |
| Panel Tinjauan Absensi | `/attendance/:id/review` | Finance |
| Ekspor CSV | tombol di daftar | Finance |

### C-7 · Halaman Laporan (M5)
**Folder:** `web/src/features/reports/`  
| Halaman | Route | Peran |
|---|---|---|
| Laporan Harian (per hari SK) | `/plans/:id/days/:dayId/report` | Leader, PM |
| Daftar Laporan Mingguan | `/plans/:id/reports/weekly` | PM |
| Laporan Akhir | `/plans/:id/reports/final` | PM, OPS |
| Mode Presentasi | `/plans/:id/presentation` | PM, OPS, semua |

### C-8 · Halaman Aset (M6)
**Folder:** `web/src/features/assets/`  
| Halaman | Route | Peran |
|---|---|---|
| Daftar Aset + Status | `/assets` | ASSET, OPS |
| Form Alokasi | dialog | ASSET |
| Form BAST Pengembalian | dialog | ASSET, Leader |

### C-9 · Halaman Insiden K3 & Lembur (M7, M8)
**Folder:** `web/src/features/hse/`, `web/src/features/overtime/`  
- Daftar insiden, form lapor, form selesaikan (tersaring per unit)
- Daftar lembur, form ajukan, tinjauan Finance

### C-10 · Halaman OPS Lini Masa (M11)
**Folder:** `web/src/features/ops/`  
- Lini masa **dikelompokkan per pekerjaan** (bukan daftar datar — lihat catatan prototipe)
- Rekap lintas pekerjaan, filter unit, filter tanggal

### C-11 · Halaman Admin & Pengaturan
**Folder:** `web/src/features/admin/`  
- Manajemen user & peran
- Pengaturan lokasi proyek (Sites)
- Log audit (`/audit`)

---

## [D] Flutter Mobile — Layar Lapangan
> Semua komponen **wajib** pakai `VmsTheme`, `VmsColors`, `VmsTextStyles`, `VmsSizes`.

### D-1 · Navigasi & Auth
**File:** `mobile/lib/shared/router.dart` (review), `mobile/lib/features/auth/`  
- Bottom navigation: Dashboard, SK Aktif, Absensi, Profil
- Login screen
- Splash screen dengan cek token

### D-2 · SK Aktif (M3 — Mobile)
**Folder:** `mobile/lib/features/plans/`  
- Daftar SK aktif milik user (sebagai Leader atau Member)
- Detail SK: info, anggota, hari kerja, progres tugas
- Terima SK (untuk Leader)

### D-3 · Absensi Lapangan (M4 — Mobile)
**Folder:** `mobile/lib/features/attendance/`  
- Layar Check-In:
  - Request izin lokasi + kamera
  - Tampilkan jarak ke site (realtime Haversine)
  - Tolak akurasi GPS > 100m
  - Ambil swafoto dengan watermark (tanggal + koordinat)
  - Kirim: `site_id`, `location`, `selfie_file_id`
- Layar Check-Out: konfirmasi, ambil lokasi akhir
- Riwayat absensi mingguan
- Form penjelasan untuk absensi `NEEDS_REVIEW`
- **Luring**: antrean aksi check-in/out saat tanpa sinyal

### D-4 · Laporan Harian (M5 — Mobile)
**Folder:** `mobile/lib/features/reports/`  
- Daftar hari kerja SK aktif
- Form laporan: centang tugas, teks pekerjaan, kendala, foto bukti
- Simpan draft luring, kirim saat daring
- Status laporan (DRAFT / SUBMITTED / APPROVED / REVISION)

### D-5 · Profil & Dokumen (M2 — Mobile)
**Folder:** `mobile/lib/features/profile/`  
- Profil karyawan diri sendiri
- Daftar dokumen: status, masa berlaku, peringatan kadaluarsa
- Upload dokumen dari galeri/kamera

### D-6 · Sinkronisasi Luring (M12)
**File:** `mobile/lib/core/connectivity_sync.dart` (sudah ada, review & lengkapi)  
- Antrean operasi: check-in, check-out, simpan laporan, upload foto
- Indikator status di AppBar: 🟢 Daring / 🔴 Luring / 🔄 Menyinkronkan
- Daftar "Perlu Perhatian" untuk aksi yang ditolak server

---

## [E] Hardening & Kualitas — Fase 9

### E-1 · Matriks RBAC Lengkap
**File:** `api/app/core/permissions.py`  
Buat tabel uji yang memastikan setiap endpoint dicek oleh tepat satu permission:
```
endpoint × peran → boleh/tolak
```
Jalankan sebagai test suite di `.local_tests/test_rbac_matrix.py`.

### E-2 · Test Suite Backend
**Folder:** `.local_tests/`  
| File | Isi |
|---|---|
| `test_auth_flow.py` | Login → refresh → logout, cek lockout, session reuse |
| `test_plan_transitions.py` | Semua transisi status, optimistic lock, snapshot SHA |
| `test_attendance.py` | Check-in dalam/luar radius, GPS palsu, face mismatch |
| `test_rbac_matrix.py` | Setiap endpoint × setiap peran |
| `test_document_integrity.py` | Hash berubah jika snapshot berubah |

### E-3 · Validasi Pesan Error
- Semua `AppError` menghasilkan pesan dalam **Bahasa Indonesia**
- Tidak ada stack trace yang bocor ke response body di production
- Field `"code"` selalu ada sehingga klien bisa handle programatik

### E-4 · Rate Limiting & Keamanan
**File:** `api/app/core/middleware.py`  
- Rate limit `POST /auth/login`: 5 kali per menit per IP
- Rate limit `GET /verify/{token}`: 60 per menit per IP
- CORS hanya dari domain yang dikonfigurasi di env

### E-5 · CI/CD yang Benar
**File:** `.github/workflows/`  
- `ci.yml`: `ruff check`, `mypy`, `pytest .local_tests/` (dengan PostgreSQL test container)
- `cd.yml`: deploy ke staging pada push `development`, deploy ke prod dengan approval manual

---

## Urutan Minggu

| Minggu | Fokus | Target Selesai |
|---|---|---|
| **W1** (sekarang) | A-1 s.d. A-6 (Refactor arsitektur) | Struktur folder baru, error handler, pagination |
| **W2** | B-1 s.d. B-4 (QR, PDF) | Endpoint sign, verify, unduh PDF |
| **W3** | C-1 s.d. C-3 (Setup web + Auth + Shared) | Web bisa login end-to-end |
| **W4** | C-4, C-5 (Karyawan + SK) | CRUD karyawan dan SK di web |
| **W5** | C-6, C-7 (Absensi + Laporan web) | Finance bisa review absensi |
| **W6** | C-8, C-9, C-10, C-11 (Aset, HSE, OPS, Admin) | Semua modul web tersedia |
| **W7** | D-1 s.d. D-4 (Flutter auth, SK, absensi, laporan) | Flutter bisa absensi end-to-end |
| **W8** | D-5, D-6 (Flutter profil + luring) | Flutter bisa kerja tanpa sinyal |
| **W9** | E-1 s.d. E-5 (Hardening) | CI hijau, RBAC teruji, pesan error Indonesia |
| **W10** | UAT staging + perbaikan | Satu tim nyata pakai selama seminggu |

---

## Catatan untuk AI yang Melanjutkan

1. **Baca file ini terlebih dahulu** sebelum mulai. Cek bagian mana yang sudah dikerjakan di `CHANGELOG.md`.
2. **Jangan hapus atau ubah** entri di `CHANGELOG.md` yang sudah ada.
3. Setiap pekerjaan dimulai dari **backend dulu** (unit A/B), lalu **web** (C), lalu **mobile** (D).
4. Refactor arsitektur (A) **tidak boleh mengubah perilaku API yang sudah ada** — hanya memindahkan kode ke tempat yang benar.
5. Saat membuat UI, selalu cek `docs/18-SISTEM-DESAIN-UI.md` dan `docs/design/tokens.json` untuk warna, ukuran, dan komponen.
6. Prototipe di `visiontech-V2/` adalah **acuan aturan bisnis** — jika ada keraguan tentang alur, lihat `js/domain.js` di sana.

---

*Dibuat: 2026-09-23 · Diperbarui oleh: Antigravity (Claude Sonnet 4.6)*
