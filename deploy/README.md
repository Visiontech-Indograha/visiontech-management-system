# Deploy otomatis ke server (R-20)

Alur: kerjakan di `development` → Pull Request `development` → `prod` → setelah merge, dalam ±1 menit
server membangun & memasang versi baru, lalu melapor ke Discord `#vms-deploy`:

- 🚀 **Deploy dimulai**: commit (tautan GitHub), pengubah, daftar perubahan.
- ✅ **Siap dipakai**: dikirim **hanya setelah** cek siap pakai lolos (lihat di bawah). Isinya total
  waktu, kesehatan, migrasi dan versi DB, backup, serta durasi per tahap.
- 🔴 **Deploy GAGAL**: tahap yang gagal, 20 baris akhir log, dan durasi per tahap.

Log build **lengkap** selalu terlampir. Pesan memakai embed Discord (kolom, tautan commit, stempel waktu).

Server (`~/deploy/vms-mvp`): `autodeploy.sh` dijalankan cron tiap menit (dengan kunci `flock`).
Urutan: checkout → `docker compose build` → backup DB (14 terakhir disimpan di `backups/`) →
`up -d --force-recreate` → `alembic upgrade head` → **cek siap pakai**. `--force-recreate`
memastikan kontainer memakai ID image hasil build terbaru meskipun commit hanya mengubah dokumentasi.

Sumber build dikunci ke branch **`prod`**, bukan `main` dan bukan tag:

- `deploy/autodeploy.sh` memakai `BRANCH="${VMS_DEPLOY_BRANCH:-prod}"` lalu mengambil `origin/$BRANCH`.
- `.github/workflows/cd.yml` hanya berjalan pada push `prod` (atau manual dengan checkout tetap `prod`)
  dan memverifikasi bahwa commit yang diperiksa sama dengan `origin/prod`.
- Workflow GitHub tidak melakukan deploy kedua. Build produksi yang nyata tetap dilakukan di server agar
  backup, migrasi, dan pemeriksaan readiness berada dalam satu alur yang sama.

## Cek siap pakai (2026-09-28)

Cek ini diulang tiap 5 detik, maksimal ±2 menit. Semua syarat berikut harus lolos **3× berturut-turut**:

| Cek | Harus |
|---|---|
| `localhost:8000/health` | 200 |
| `localhost:8000/ready` (API benar-benar terhubung ke DB, skema `vms` ada) | 200, bukan 503 |
| `localhost:8080/` (web) | 200 |
| `localhost:8080/api/v1/auth/me` (jalur proxy web → API) | 401 |
| Kontainer `vms_api` dan `vms_web` | berjalan |

Terakhir, kontainer yang berjalan harus memakai image hasil build ini. Jika salah satu syarat gagal,
yang terkirim adalah 🔴 "cek siap pakai", bukan ✅.

Durasi deploy yang singkat (±25 dtk) itu wajar bila lapisan Docker ter-cache (hanya kode yang berubah).
Rinciannya ada di kolom **Tahapan** pada pesan ✅.

## Repo & akses

- Repo: `Visiontech-Indograha/visiontech-management-system` (pindah dari `consep33t/…` pada 2026-09-28).
  - Remote di server (`src/`) dan nilai bawaan `REPO` di `autodeploy.sh` sudah diganti.
  - Bisa ditimpa lewat env `VMS_DEPLOY_REPO`, `VMS_GITHUB_URL`, `VMS_PUBLIC_URL`.
- Akses baca repo: deploy key `~/.ssh/vms_deploy` (alias SSH `github-vms`), hanya-baca.
  - Terdaftar di repo baru sebagai `vms-server-deploy`.
- Berkas rahasia di server (tidak di Git, chmod 600): `api.env`, `notify.env` (`DISCORD_WEBHOOK_DEPLOY`, `DISCORD_WEBHOOK_BUILD` untuk webhook ke-4).

## Memasang perubahan skrip ini ke server

`autodeploy.sh` di server adalah **salinan**, dan tidak ikut ter-update oleh deploy. Setelah skrip
ini berubah di `prod`, salin manual lalu buat cadangan lebih dulu:

```bash
cd ~/deploy/vms-mvp && cp autodeploy.sh autodeploy.sh.bak-$(date +%Y%m%d) && cp src/deploy/autodeploy.sh . && bash -n autodeploy.sh
```

## Lain-lain

- Log: `~/deploy/vms-mvp/logs/deploy-*.log`, `logs/cron.log`.
- Memaksa deploy ulang versi yang sama: `rm ~/deploy/vms-mvp/.last-deployed` (deploy berikutnya ≤ 1 menit).

## Layanan wajah (face-service)
Dipasang sekali dengan `deploy/pasang-face-service.sh` (idempoten): menambah service `face` ke `compose.yml` (jaringan internal,
tanpa port, `mem_limit` 1200m), membuat `face.env` (token acak), mengisi `FACE_SERVICE_URL`/`FACE_SERVICE_TOKEN` di `api.env`, dan
mengubah `autodeploy.sh` agar menyalin `src/face-service` → `face` (pembaruan berikutnya otomatis). Jalankan dari komputer pemilik:
`ssh ageng@192.168.88.160 "bash -s" < deploy\pasang-face-service.sh`; tambah `WAJIB_DAFTAR=ya` untuk mewajibkan pendaftaran wajah setelah login.
Lisensi model InsightFace non-komersial: putuskan lisensi komersial sebelum dipakai penuh.


## Rilis aplikasi HP (pembaruan otomatis, docs/32)
Dipasang sekali dengan `deploy/pasang-rilis-apk.sh` (idempoten), **setelah** rilis API yang memuat `/api/v1/app/android/*`
ter-deploy: membuat `~/deploy/vms-mvp/rilis/android/` dan `compose.override.yml` yang me-mount folder itu **read-only**
ke `vms_api` (`/srv/rilis`, `APP_RELEASE_DIR`). `compose.yml` dan `api.env` tidak disentuh; autodeploy membaca override
secara otomatis. Jalankan dari komputer pemilik: `ssh ageng@192.168.88.160 "bash -s" < deploy\pasang-rilis-apk.sh`.
APK + `latest.json` dikirim dari laptop dengan `scripts\rilis-apk.bat kirim` (keystore tidak pernah ke server).
Mematikan fitur: hapus `compose.override.yml` lalu `docker compose up -d --force-recreate api` (API menjawab UP_TO_DATE).

## Peran runtime API `vms_api` (RLS, P9-2)
Sebelum 2026-10-08 API tersambung sebagai `vms_app` = superuser + pemilik tabel, sehingga RLS terlewati. Migrasi
`0024_runtime_role` (jalan otomatis saat autodeploy, tanpa perubahan perilaku) membuat peran `vms_api`. Setelah rilis
itu ter-deploy, pemilik menjalankan dari komputernya (bash UCRT64, di folder repo):
`ssh ageng@192.168.88.160 "bash -s" < deploy/pakai-peran-runtime.sh`. Skrip memeriksa peran & revisi alembic,
menyalin `api.env` ke `api.env.sebelum-vms_api.<waktu>`, menyetel sandi acak `vms_api` (tidak pernah dicetak),
menulis `DATABASE_URL` = `vms_api` dan `MIGRATION_DATABASE_URL` = URL lama (alembic & CLI tetap pemilik), membuat ulang
`api`, lalu memastikan `/ready` 200 dan API tersambung sebagai `vms_api` — gagal → rollback otomatis.
Rollback manual: `ssh ageng@192.168.88.160 "bash -s -- kembalikan" < deploy/pakai-peran-runtime.sh`.
Tabel baru di migrasi berikutnya wajib `GRANT` ke `vms_api` dan fungsi baru wajib `SECURITY DEFINER SET search_path`
(dijaga `api/tests/test_rls_app_role.py`).

## Alamat publik QR & berkas (`PUBLIC_VERIFY_URL`, `MINIO_PUBLIC_URL`)
QR pada SK/laporan berisi `<PUBLIC_VERIFY_URL>/<token>`; pratinjau & unduhan berkas memakai URL presigned dengan host
`MINIO_PUBLIC_URL` (Caddy meneruskan `/vms-files/*` ke MinIO). Keduanya harus domain publik — `https://portal.visiontechindo.com/verify`
dan `https://portal.visiontechindo.com` — bukan alamat Tailscale, agar terbuka dari HP/browser mana pun. Setel dengan
`ssh ageng@192.168.88.160 "bash -s" < deploy/setel-url-verifikasi.sh` (salinan api.env dibuat; salinan rollback
`api.env.sebelum-vms_api.*` ikut disamakan). Keduanya dibuat ulang setiap dokumen dibuka.

## Uji pulih cadangan (P9-5)
`ssh ageng@192.168.88.160 "bash -s" < deploy/uji-pulih-cadangan.sh` — membuat cadangan baru lewat `backup.sh`,
mengunduh salinan MinIO-nya (SHA-256 harus sama), memulihkannya ke Postgres SEMENTARA (citra sama, tanpa jaringan),
lalu membandingkan jumlah baris per tabel, versi alembic, tabel ber-RLS, dan fungsi dengan prod. Prod hanya dibaca;
kontainer sementara selalu dihapus; keluaran hanya nama tabel & angka. Jalankan tiap bulan dan setelah perubahan
besar skema. Catatan: berkas di MinIO (foto/dokumen/PDF) belum ikut dicadangkan, dan cadangan DB masih di server
yang sama (lihat docs/06 P9-5).

