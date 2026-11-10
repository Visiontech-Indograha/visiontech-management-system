# Peran runtime `vms_api` (non-superuser) - langkah pemilik

Tujuan: API terhubung sebagai `vms_api` (bukan superuser, tanpa BYPASSRLS) dengan hak minimal. Ini prasyarat RLS
(belum ada `CREATE POLICY` di PR ini; perilaku aplikasi tidak berubah). Migrasi/DDL tetap memakai peran pemilik lewat
`MIGRATION_DATABASE_URL`.

Fakta prod (10 Nov 2026): peran ada `vms_migrator`, `vms_readonly`, `vms_api` (belum dipakai), `vms_app` (SUPERUSER+BYPASSRLS,
kemungkinan dipakai API sekarang), `pg_policies` = 0. Skrip `cek` memastikan.

Berkas: `deploy/peran-runtime.sql` (idempoten, sandi dari env `VMS_API_PASSWORD`, tidak ada di repo) dan
`deploy/pakai-peran-runtime.sh` (mode `cek`, `terapkan`, `kembalikan`; tidak pernah mencetak sandi).

Urutan: BETA dulu, lulus uji manual, baru PROD. Ganti `vms_db_prod`/`vms_api`/port bila beta
(`VMS_DIR`, `VMS_DB_CONTAINER`, `VMS_API_CONTAINER`, `VMS_PORT` mis. beta: `~/deploy/vms-beta`, `vms_db_beta`, `vms_beta_api`, `8001`).

## 1. Cek (hanya baca)
```
scp deploy/peran-runtime.sql ageng@192.168.88.160:~/deploy/vms-mvp/peran-runtime.sql
ssh ageng@192.168.88.160 "bash -s -- cek" < deploy/pakai-peran-runtime.sh
```
Keluaran: peran DATABASE_URL sekarang, atribut peran, jumlah policy, revisi Alembic. Tidak ada perubahan.

## 2. Cadangan (wajib sebelum terapkan)
```
ssh ageng@192.168.88.160 "cd ~/deploy/vms-mvp && ./backup.sh"   # atau deploy/backup.sh; pastikan berkas dump baru ada
ssh ageng@192.168.88.160 "cd ~/deploy/vms-mvp && cp -p api.env api.env.cadangan-manual && chmod 600 api.env.cadangan-manual"
```

## 3. Terapkan
```
ssh ageng@192.168.88.160 "bash -s -- terapkan" < deploy/pakai-peran-runtime.sh
```
Skrip: membuat/menyelaraskan `vms_api` + GRANT (SELECT/INSERT/UPDATE/DELETE tabel, USAGE/SELECT sequence di schema `public`
dan `vms`, default privileges untuk tabel baru milik `vms_migrator` dan `vms_app`), menyimpan `api.env.sebelum-vms_api.<waktu>`,
mengganti `DATABASE_URL` ke `vms_api`, `MIGRATION_DATABASE_URL` ke pemilik lama, membuat ulang `api`, lalu memeriksa `/ready` = 200
dan koneksi `vms_api False False`. Gagal di titik mana pun = rollback otomatis.

Uji manual setelahnya (lewat UI): login web, login HP, absen, buka daftar karyawan, unggah foto, satu tulis data.
Bila ada galat `permission denied`, catat tabel/fungsi-nya dan jalankan rollback.

## 4. Rollback
```
ssh ageng@192.168.88.160 "bash -s -- kembalikan" < deploy/pakai-peran-runtime.sh
```
Mengembalikan `api.env` terbaru dari `api.env.sebelum-vms_api.*` dan membuat ulang `api`. Peran `vms_api` dan GRANT dibiarkan
(tidak berbahaya). Pemulihan penuh dari dump hanya bila data rusak (tidak diharapkan: skrip tidak mengubah data).
Mencabut peran sepenuhnya: `REASSIGN OWNED BY vms_api TO vms_migrator; DROP OWNED BY vms_api; DROP ROLE vms_api;` (jarang perlu).

## 5. Migrasi ke depan
Tabel baru dari Alembic otomatis dapat hak ke `vms_api` lewat default privileges (hanya untuk pemilik yang tercantum di `VMS_OWNERS`;
bila pemilik migrasi berbeda, jalankan ulang `peran-runtime.sql` dengan `-v owners=...`). Fungsi baru: tetap `SECURITY DEFINER SET search_path`.

## CI dan tes
CI memasang skema sebagai `postgres`, menjalankan `peran-runtime.sql`, lalu pytest dengan `DATABASE_URL` = `vms_api` dan
`TEST_SETUP_DATABASE_URL` = pemilik. Lokal: buat DB dari template, jalankan `peran-runtime.sql`, set `TEST_DATABASE_URL` (vms_api) dan
`TEST_SETUP_DATABASE_URL` (superuser).
