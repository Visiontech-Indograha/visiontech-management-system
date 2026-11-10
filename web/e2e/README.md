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
Server uji lokal itu sendiri: DB uji pribadi dan proses API/web. Akun admin awal adalah masukan lingkungan
(kredensial `E2E_ADMIN_*`); ia ada karena DB tidak punya jalur UI untuk akun pertama. Jalur UI yang dibutuhkan:
halaman penyiapan awal yang hanya muncul bila belum ada admin (peran: pemilik/operator server).

## Tes yang ditunda (`test.fixme`)
| Langkah | Layar yang dibutuhkan | Peran |
|---|---|---|
| Memberi peran kantor ke akun baru (tes menu STAFF) | Direktori > Akun login > Peran, dengan peran kantor tersedia tanpa flag server `ROLE_ASSIGNMENT_ENABLED` | SUPER_ADMIN |
| Cuti: pemeriksa kedua (pemohon tak boleh menyetujui cuti sendiri) dan hapus/batalkan pengajuan yang masih menunggu | Cuti dan Izin (tombol batal untuk pengajuan menunggu) + peran kantor seperti di atas | SUPER_ADMIN |

## Data uji
Awalan `QA-E2E-`. Tes membersihkan datanya lewat UI (blok `finally`). Sandi salah hanya dicoba satu kali.

## Catatan
- Setiap login membuka satu perangkat (batas 4 per akun); fixture di `fixtures.ts` mengeluarkan sesi tiap tes.
  Itu pemanggilan keluar (logout) milik aplikasi, bukan penyuntikan data.
- Jangan menjalankan dua `npm run e2e` bersamaan.
