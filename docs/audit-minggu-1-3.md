# Audit Minggu 1-3 (5 November 2026)

Untuk pemilik. Bahasa sederhana. Dasar audit: cabang `integrasi/uji-ulang`, versi `029c9c46` (VERSION 1.5.0). Audit dilakukan arsitek dan QA secara terpisah.

## 1. Ringkasan keputusan

Hasil: **boleh lanjut, setelah perbaikan**. Isi kerja minggu 1-3 sesuai klaim, dan pemeriksaan otomatis (CI) hijau. Audit menemukan 2 hal berat dan beberapa hal sedang. Semuanya sudah dibuatkan perbaikan (PR #319-#326, belum digabung) atau dicatat sebagai utang minggu 4.

Dua hal berat:
1. **Server uji (beta) ikut menyalin kunci tanda tangan dokumen milik produksi.** Artinya beta bisa membuat dokumen yang dianggap sah oleh produksi. Perbaikan: PR #320.
2. **Aturan perpindahan status order (#312) sudah aktif padahal masih "usulan".** Sudah Anda setujui, dan kini tercatat resmi (PR #319).

Bukti uji (dijalankan QA sendiri):
- Pemeriksaan GET pada 110 endpoint x 6 peran: **tidak ada** kebocoran sandi/hash, data wajah, token, NIK, atau rekening. Tidak ada galat server (5xx).
- Tes baru terbukti **gagal di kode lama** dan lulus di kode baru: perbaikan `6d09759d` (3 gagal), `c7e8f96e` (8 gagal), `4058538e` (4 gagal). Jadi tes itu memang menjaga perbaikannya.
- Seluruh tes API dari database kosong: 1615 lulus.
- Web: 448 tes lulus. HP: 265 tes lulus.
- Database uji `vms_test` sudah dinaikkan ke versi terbaru (v2_0027). Database `perf_tests_test` sudah dihapus. Worktree lama sudah dirapikan.

## 2. Temuan per PR

Arti: OK = sesuai. RISIKO = jalan, tapi ada yang perlu dijaga. MASALAH = perlu diperbaiki.

| PR | Isi singkat | Hasil | Berat | Saran | Status perbaikan |
|---|---|---|---|---|---|
| #301 | Image Docker tidak jalan sebagai root | OK / RISIKO | Rendah | PR ini tertulis "ditutup" walau isinya sudah masuk. Catat di CHANGELOG | Hanya kerapian, belum dikerjakan |
| #302 | Server beta aman | **MASALAH** | **Tinggi** | Kunci tanda tangan produksi tersalin ke beta. Ganti ke daftar putih, buat kunci beta baru | Diperbaiki di #320 |
| #302 | Port beta | RISIKO | Sedang | Port beta terbuka ke jaringan. Ikat ke 127.0.0.1 | Diperbaiki di #320 |
| #303 | Jadwal harian tidak bisa dua kali setuju | OK | - | Tes terbukti gagal di kode lama | Tidak perlu |
| #304 | Indeks database (v2_0024) | OK | - | Lihat risiko indeks rusak di bagian 3 | Runbook di #320 |
| #305 | CI pindah ke ubuntu-24.04 | OK | - | CI hijau | Tidak perlu |
| #307 | Hash sandi tidak memblokir server, rate limit | OK / RISIKO | Rendah | Pembatas permintaan masih "catat saja" dan hitungannya per proses | Keputusan pemilik: tetap catat-saja sampai tinjau Desember 2026 |
| #308 | Cegah dua orang mengubah status bersamaan | OK | - | Tes terbukti gagal di kode lama | Tes tidak stabil diperbaiki di #326 |
| #309 | Kunci anti-ganda (Idempotency-Key) | OK / RISIKO | Sedang | Ternyata 7 endpoint, bukan 6. POST `/mess` dan `/assets/loans` belum dijaga | Dijaga di #322 (jadi 8 endpoint) |
| #310 | Web kirim kunci anti-ganda | **MASALAH** | Sedang | Web belum mengirim kunci untuk pengajuan mess dan pinjam aset | Diperbaiki di #324 |
| #311 | HP kirim kunci anti-ganda | RISIKO | Rendah | PR tertulis "ditutup" walau isinya masuk. Kunci hanya di memori | Kerapian saja |
| #312 | Aturan perpindahan status order | **MASALAH** | **Tinggi** (tata kelola) | Sudah aktif tapi masih "usulan" | Anda setujui; dicatat di ADR (#319) |
| #313 | Lembur di web | OK | - | Batas 1000 huruf sama dengan API | Batas jam di OpenAPI: #323 |
| #314 | Lembur di HP | OK / RISIKO | Rendah | Alasan HP maksimal 500, API 1000. Pesan jam kurang pas | Diperbaiki di #325 |
| #315 | Utang kecil | OK / RISIKO | Rendah | Dua baris di skill vms-api sudah usang | Masuk utang |
| #316 | Batas 5000 baris untuk daftar tanpa halaman | RISIKO | Sedang | Daftar terpotong diam-diam | Header `X-Result-Truncated` di #321 |
| #317 | Indeks partisi dan pembuat dokumen di thread terpisah | OK / RISIKO | Rendah | Keterangan "Revises" salah. Semafor memblokir thread. PDF dibangun 2 kali | Masuk utang |
| #318 | Kueri bulk lebih sedikit (N+1) | OK | - | Tes terbukti gagal di kode lama | Tidak perlu |

## 3. Temuan lain

- **Indeks yang gagal setengah jalan** (migrasi v2_0024-0027): bila pembuatan indeks terhenti, indeks rusak bisa tertinggal diam-diam. Sudah ada runbook pemeriksaan `indisvalid` dan cron `cleanup-idempotency` (PR #320).
- **Tes tidak stabil** saat jalan paralel: dua tes (tutup jadwal tertahan, dan pencarian tim). Penyebab: database uji dipakai bersama antar-pekerja. Diperbaiki di #326.
- **Keamanan tambahan** (pengetatan): `/audit-events` kini khusus peran tertentu. HR/GA tidak lagi melihat detail rencana kerja. Foto aset dan foto profil dibatasi per peran. Peran lain hanya perlu dicek di tampilan web.
- **Bukti hotfix**: `/uploads/` tanpa login kini 404 (hotfix #299 terbukti).
- **Hal yang sama sekali tidak ada masalah**: tidak ada literal rahasia di perubahan; tidak ada `LIKE '%…'` atau `OFFSET` baru; tidak ada trailer AI di commit minggu 1-3.

## 4. Utang (masuk minggu 4)

Belum diperbaiki dan sengaja ditunda. Rendah sampai sedang karena sebagian sudah dilindungi kunci baris (FOR UPDATE) di service.

1. `UPDATE` status tanpa syarat status (perlu `AND status IN (...)` dan cek jumlah baris):
   - `document_repository:124`
   - `offboarding_repository:118, 202, 205`
   - `daily_correction_repository:94`
   - `daily_plan_repository:336`
   - `work_completion_revision:57`
   - `asset_repository:299, 562`
   - `plan_item_repository:291, 301, 311`
   - `leave_repository:201, 217` (review dan batal cuti)
2. Tabel `hse_campaign_views` tidak dipakai kode (`db/06:827`): hapus atau pakai.
3. Paginasi keyset untuk audit, absensi, lembur (sekarang masih OFFSET lama).
4. Semafor `to_thread` diganti `asyncio.Semaphore`, dan PDF dibangun dua kali (#317, rendah).
5. Dokumen dan skill usang (misalnya `vms-system-design:70` yang masih menyuruh OFFSET).
6. Kerapian: PR #301 dan #311 berstatus CLOSED walau isinya masuk; keterangan `Revises: v2_0025` di v2_0027 keliru (seharusnya v2_0026).

Belum teruji karena data kosong di salinan uji: `/overtime`, jadwal bulk, monitor harian, foto aset, batas 5000. Uji ulang saat ada data.

## 5. Keputusan pemilik

Sudah diputuskan:
- Aturan perpindahan status order #312 **disetujui**, termasuk "Selesai tidak bisa Dibatalkan". Tercatat di ADR (#319).
- `/divisions` dan `/offices` terbuka untuk semua peran: **disengaja** (data pilihan dropdown, tanpa data pribadi).
- Pencarian `q`: daftar lama tetap "mengandung kata", daftar baru "awalan". `OFFSET` baru dilarang, pakai keyset `(created_at, id)`. Teks sudah ditambahkan ke `api/CLAUDE.md`.
- Pembatas permintaan (rate limiter) tetap mode catat-saja sampai tinjau awal Desember 2026.
- Batas 200 sel untuk jadwal bulk **tidak diterapkan**.
- `vms-next` proyek lain, tidak dirujuk.

Masih menunggu Anda:
- Server beta lama sudah terpasang dengan kunci produksi. Setelah #320 digabung, **ganti kunci tanda tangan beta** dan jalankan ulang pemasangan. Pemasangan di server hanya dijalankan Anda.
- Pastikan data lama order berstatus DRAFT/PLANNED/IN_PROGRESS dicek di beta/prod sebelum rilis (status ini tidak punya jalur keluar di aturan baru).

## 6. Perbaikan hasil audit (PR #319-#326)

Semua ke `integrasi/uji-ulang`, **belum digabung**.

| PR | Perbaikan |
|---|---|
| #319 | ADR peta perpindahan status order (disetujui pemilik 5 Nov 2026) |
| #320 | Beta aman: daftar putih `api.env`, port 127.0.0.1, runbook `indisvalid`, cron `cleanup-idempotency`. Fungsi `periksa_kunci_beda` terbukti memberi kode 3 (kunci sama), 0 (beda), 3 (kosong) |
| #321 | Header `X-Result-Truncated` bila daftar terpotong di 5000 baris |
| #322 | `idempotency_guard` di POST `/mess` dan `/assets/loans` (total 8 endpoint) |
| #323 | Batas `hours` lembur tampil di OpenAPI |
| #324 | Web mengirim Idempotency-Key untuk mess dan pinjam aset |
| #325 | Batas lembur HP disamakan (alasan 1000, pesan jam diperbaiki) |
| #326 | Perbaikan 2 tes tidak stabil saat paralel (xdist) |

Langkah berikut: tinjau dan gabung #319-#326, jalankan CI, lalu uji ulang area data kosong.
