# E2E Playwright (lokal)

Hanya untuk lingkungan lokal. `e2e/env.ts` menolak host non-lokal (bukan localhost, 127.0.0.1, 10.x, 192.168.x).
CI tidak menjalankan E2E (job web terpisah dari API+Postgres); jalankan di mesin sendiri.

## Prinsip
Semua data uji (karyawan, akun, cuti, dll.) dibuat dan dihapus lewat UI dengan akun admin. Tes tidak memakai
API langsung, SQL, localStorage/cookie, atau intersep jaringan. Bila suatu langkah belum punya jalur UI, tes
itu ditandai `test.fixme` dengan alasan "jalur UI belum ada: ..." (bukan dikerjakan lewat jalan pintas).

## Menjalankan
1. Hidupkan DB uji pribadi dan API (port 8010) yang menunjuk ke DB itu.
2. Web dev dengan proxy ke API itu:
   `cd web && DEV_API_PROXY_TARGET=http://localhost:8010 npm run dev -- --host localhost --port 5173`
3. Pasang peramban sekali: `npx playwright install chromium`.
4. Isi kredensial lewat env (jangan di-commit), lalu `npm run e2e`:
   - `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD` (SUPER_ADMIN, login lewat /admin-login)
   - Opsional: `E2E_BASE_URL` (default http://localhost:5173), `E2E_API_URL`

Tes tanpa kredensial yang dibutuhkan dilewati (skipped).

## Prasyarat lingkungan (bukan data uji)
Server uji lokal itu sendiri: DB uji pribadi (dibuat dari template `vms_test`, tanpa Super Admin aktif) dan proses
API/web. API uji diberi `SETUP_TOKEN` (minimal 24 karakter). Admin awal dibuat lewat halaman `/setup` oleh
`00-setup.spec.ts`; kredensialnya masukan lingkungan: `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD` (12-128 karakter)
dan `E2E_SETUP_TOKEN` (sama dengan `SETUP_TOKEN` server uji). Bila DB sudah punya admin, tes penyiapan dilewati
(skipped) dan tes lain memakai kredensial yang sama.

Peran kantor untuk tes (HR/GA) diberikan admin lewat Direktori > Akun login > Peran utama (dengan konfirmasi), lalu
sandi direset agar akun wajib ganti sandi saat masuk pertama.

## Tes yang ditunda (`test.fixme`)
Tidak ada. Pemeriksa kedua cuti (persetujuan oleh orang lain) belum dicakup: tes cuti hanya mengajukan lalu
membatalkan pengajuan yang menunggu.

## Data uji
Awalan `QA-E2E-`. Tes membersihkan datanya lewat UI (blok `finally`). Sandi salah hanya dicoba satu kali.

## Catatan
- Setiap login membuka satu perangkat (batas 4 per akun); fixture di `fixtures.ts` mengeluarkan sesi tiap tes.
  Keluar dilakukan lewat UI (Keluar di sidebar + konfirmasi).
- Jangan menjalankan dua `npm run e2e` bersamaan.
