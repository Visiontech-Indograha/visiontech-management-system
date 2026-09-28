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
`up -d` → `alembic upgrade head` → **cek siap pakai**.

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
- Berkas rahasia di server (tidak di Git, chmod 600): `api.env`, `notify.env` (`DISCORD_WEBHOOK_DEPLOY`).

## Memasang perubahan skrip ini ke server

`autodeploy.sh` di server adalah **salinan**, dan tidak ikut ter-update oleh deploy. Setelah skrip
ini berubah di `prod`, salin manual lalu buat cadangan lebih dulu:

```bash
cd ~/deploy/vms-mvp && cp autodeploy.sh autodeploy.sh.bak-$(date +%Y%m%d) && cp src/deploy/autodeploy.sh . && bash -n autodeploy.sh
```

## Lain-lain

- Log: `~/deploy/vms-mvp/logs/deploy-*.log`, `logs/cron.log`.
- Memaksa deploy ulang versi yang sama: `rm ~/deploy/vms-mvp/.last-deployed` (deploy berikutnya ≤ 1 menit).
