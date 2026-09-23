# AGENTS.md — Frontend (VMS)

Berlaku bersama aturan umum di `../AGENTS.md`.

---

## Ruang Lingkup

Web dashboard untuk role: **OM, PM, Finance, HES/HR**.
(Bukan untuk teknisi lapangan — mereka pakai mobile app Flutter di luar repo ini.)

**UI/UX & Direktori:** Seluruh pengembangan UI (React) WAJIB mengikuti SOP struktur folder `src/pages/` dan pembagian fungsionalitas yang tercantum dalam cetak biru `docs/VMS_MASTER_REFERENCE.md`. Rujuk pada referensi wireframe (seperti pembagian halaman HES/HR, Finance, Project Manager) saat membangun dashboard.

---

## Status Implementasi Frontend (per 2026-09-10, hasil audit menyeluruh)

| Item | Status |
|---|---|
| Scaffold Vite + React + TypeScript + Tailwind | ✅ Selesai |
| ESLint bersih (0 errors, 0 warnings) | ✅ Selesai — tapi cek dulu `npm run lint` benar-benar jalan (lihat catatan TypeScript di bawah, sempat rusak total tanpa terdeteksi) |
| Routing dasar (`react-router`) + RBAC per-route (`ProtectedRoute`/`RoleRoute`, ada test) | ✅ Selesai |
| Vitest setup | ✅ Selesai — tapi cakupan test masih tipis (smoke test App + route guards saja, hook/page belum ada test) |
| Halaman/komponen per role (Auth, Dashboard, Attendance, HR, OM, PM, HES, Finance, Export) | ✅ Semua halaman utama sudah dibangun dan terhubung ke backend nyata |
| Reusable UI (`components/ui/`) | ✅ Card, Table, Button, Input/TextArea/Select, Modal/ModalFooter, QueryState — sebagian halaman (EmployeeListPage, LogbookPage, WorkPlanPage, PortofolioPage, InternalDocumentPage) masih pakai markup modal/form inline lama, belum dimigrasikan |
| API integration (TanStack Query) | ✅ Selesai (Axios interceptor + QueryClient, token di memory + refresh via httpOnly cookie) |

> ⚠️ **PENTING:** `typescript` sempat ter-upgrade ke `7.0.2`, yang membuat `typescript-eslint`
> gagal total ("does not support TS 7.0") — `npm run lint` crash instead of reporting errors,
> jadi CI/dev tidak pernah benar-benar melihat hasil lint selama itu. Sudah diturunkan ke `6.0.3`
> (versi stabil terbaru yang didukung `typescript-eslint`). SELALU jalankan `npm run lint` dan
> pastikan ia benar-benar selesai dengan laporan errors/warnings (bukan crash) sebelum percaya
> klaim "lint bersih" di dokumen manapun.

---

## Stack Teknologi (Final)

| Komponen | Pilihan |
|---|---|
| Build tool | Vite |
| Framework | React 19 (TypeScript, target 6.0.x — lihat catatan status di atas) |
| Styling | TailwindCSS |
| Routing | React Router |
| Data fetching | TanStack Query (React Query) |
| Form | React Hook Form + Zod |
| HTTP client | axios (interceptor JWT terpusat di `src/lib/api.ts`) |
| Testing | Vitest |

---

## Aturan Frontend

1. **JANGAN hardcode base URL API** — wajib pakai `VITE_API_BASE_URL`.
2. **JANGAN duplikasi tipe data manual, dan JANGAN menebak nama field.** Definisikan di
   `src/types/` mengikuti skema respons backend nyata — cek OpenAPI docs backend (`/docs`)
   atau `backend/app/schemas/`, BUKAN dari asumsi. Kejadian nyata (2026-09-10): tipe
   `AbsenceResponse`, `VehicleBookingLogResponse`, `LogbookToolResponse`, `Vehicle`, `Item`,
   `WorkPlanStatus`, dan `ReportType` di frontend SEMUANYA punya field/enum yang tidak cocok
   dengan backend (nama field karangan seperti `tool_id`/`borrow_time`/`plate_number`, enum
   value yang tidak pernah ada di backend seperti `PUBLISHED`/`IN_PROGRESS`/`DAILY_ACTIVITY`).
   Ini menutupi bug nyata dengan `as any` alih-alih memperbaiki tipe-nya — salah satu form
   (peminjaman alat di LogbookPage) bahkan diam-diam membuang input pengguna karena field
   yang dikirim tidak ada di schema backend.
3. **Struktur folder per role:** `src/pages/{auth,dashboard,pm,finance,hes,om}/`
4. **Reusable UI** (button, card, modal, tabel) di `src/components/ui/`.
5. Sebelum membangun halaman/role baru, cek `docs/requirements/` untuk daftar fitur role.
6. **Cek backend routes nyata** sebelum menulis axios/fetch call — lihat
   `backend/AGENTS.md` bagian "Peta URL Endpoint Aktual" untuk daftar URL yang valid.
7. **Mobile First & Dynamic Nav (WAJIB):** Setiap membuat tampilan atau komponen antarmuka, UTAMAKAN pendekatan *mobile-first* (menggunakan kelas-kelas Tailwind dasar untuk mobile, lalu ditingkatkan ke `sm:`, `md:`, `lg:`). Navigasi (Sidebar/Navbar) harus dinamis: mampu membedakan *active states*, merespons *role* pengguna dengan menyembunyikan menu yang tidak relevan, serta dapat *collapse* (tutup/buka) dengan mulus pada layar kecil agar pengalaman pengguna optimal.

---

## Pengecekan Tambahan di Awal Sesi (selain protokol umum di root)

```bash
# 1. Pastikan build terakhir masih sukses
npm run build

# 2. Pastikan test masih hijau
npm run test

# 3. Pastikan linting bersih
npm run lint
```

---

## Environment Variable Frontend

| Variable | Keterangan |
|---|---|
| `VITE_API_BASE_URL` | Base URL backend API (mis: `http://localhost:8000`) |

Lihat `web/.env.example` untuk daftar lengkap.

## Security Frontend (Koreksi dari Rencana Awal)
Rencana awal menyebut "axios interceptor JWT" tanpa menentukan tempat
penyimpanan token — untuk skala enterprise ini WAJIB diperjelas:
1. **JANGAN simpan access token di `localStorage`/`sessionStorage`** —
   rentan dicuri lewat XSS. Simpan access token HANYA di memory (state
   React, hilang saat refresh halaman), dan refresh token di **httpOnly
   secure cookie** yang tidak bisa diakses JavaScript.
2. **CSRF protection** wajib aktif kalau memakai cookie untuk autentikasi
   (double-submit cookie token atau header kustom yang divalidasi backend).
3. **Sanitasi output**: JANGAN pernah pakai `dangerouslySetInnerHTML`
   dengan data dari user/API tanpa sanitasi (pakai library seperti DOMPurify
   kalau memang butuh render HTML dinamis).
4. **Content Security Policy**: koordinasi dengan backend untuk header CSP
   yang membatasi sumber script/style yang boleh dimuat.
5. **Dependency scanning**: jalankan `npm audit` di CI, build gagal kalau
   ada vulnerability severity tinggi — tambahkan ke `frontend-ci.yml`.
6. Jangan tampilkan pesan error API mentah ke pengguna (bisa membocorkan
   detail sistem) — mapping ke pesan yang ramah pengguna di UI.
