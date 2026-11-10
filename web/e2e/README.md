# E2E Playwright (lokal)

Hanya untuk lingkungan lokal. `e2e/env.ts` menolak host non-lokal (bukan localhost, 127.0.0.1, 10.x, 192.168.x).
CI tidak menjalankan E2E (job web terpisah dari API+Postgres); jalankan di mesin sendiri.

## Menjalankan
1. Hidupkan DB dev dan API: `bash scripts/api-lokal.sh` (port 8010).
2. Web dev dengan proxy ke API itu:
   `cd web && DEV_API_PROXY_TARGET=http://localhost:8010 npm run dev -- --host localhost --port 5173`
3. Pasang peramban sekali: `npx playwright install chromium`.
4. Isi kredensial lewat env (jangan di-commit), lalu `npm run e2e`:
   - `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD` (HR/admin kantor, login lewat /admin-login)
   - `E2E_STAFF_EMAIL`, `E2E_STAFF_PASSWORD` (karyawan kantor biasa)
   - Opsional: `E2E_BASE_URL` (default http://localhost:5173), `E2E_API_URL` (default `<BASE_URL>/api/v1`)

Tes tanpa kredensial yang dibutuhkan dilewati (skipped).

## Data uji
Semua data buatan tes berawalan `QA-E2E-` dan dihapus/dibatalkan oleh tes itu sendiri (blok `finally`).
Sandi salah hanya dicoba satu kali agar akun tidak terkunci.

## Catatan
- Setiap login membuka satu perangkat (batas 4 per akun); fixture di `fixtures.ts` mengeluarkan sesi tiap tes.
- Akun STAFF harus peran kantor (mis. Finance); akun lapangan ditolak di web.
- Jangan menjalankan dua `npm run e2e` bersamaan (data dan sesi bersama).
