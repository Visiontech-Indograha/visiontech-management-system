# 02 · Autodeploy, rollback, dan CI (membaca dan men-debug)

Sumber: `deploy/autodeploy.sh` (489 baris), `deploy/README.md`, `.github/workflows/*.yml`. Nomor baris di bawah perkiraan dari `grep -n` pada cabang `docs/skills-agentik`; cocokkan dulu sebelum mengutip.

## 2.1 Alur autodeploy (cron tiap menit, server)

Cron: `* * * * *` untuk beta (`deploy/beta/pasang-beta.sh:95`). Prod: cron tidak ada di repo; dokumen menyebut tiap menit (`deploy/README.md:13`). TIDAK YAKIN isi crontab prod.

Urutan di `autodeploy.sh` (nomor baris perkiraan):

| Langkah | Baris | Gagal -> kode keluar | Catatan |
|---|---|---|---|
| Kunci `flock -n` | 23 | exit 0 (tidak error) | Deploy lain masih jalan. |
| `git fetch origin $BRANCH` | 38 | exit 1 | |
| Perbarui diri sendiri dari `origin/$BRANCH` | 40-50 | - | Salinan lama disimpan `autodeploy.sh.sebelum`. Lihat anomali A-6. |
| Pasang APK (dari branch `rilis-apk-<env>`) | 55-72 | - | Dipasang dulu, `latest.json` terakhir. |
| Bandingkan commit baru vs `.last-deployed` | 74 | exit 0 bila sama | |
| Anti-loop `.last-failed` | 76-83 | exit 0 | Jeda `VMS_DEPLOY_RETRY_AFTER` (bawaan 900 dtk). |
| Checkout paksa, salin `api web face` | 240 | 11 | `git -C src checkout --force`, lalu `rm -rf api web face` dan `cp -a`. |
| Tandai image lama `:rollback` | 242-244 | - | Dasar rollback. |
| `docker compose build` (flock antrean build) | 246-250 | 12 | Build prod dan beta tidak boleh bersamaan (commit 9f31dbb9). |
| Backup DB pra-deploy | 251-252 | 13 | `backup.sh pra-deploy-<sha>`. |
| `alembic upgrade head` | 254 | 15 | Di kontainer baru sekali pakai. Tidak ada rollback kode untuk 15. |
| `up -d --force-recreate` | 257 | 14 | Memicu rollback image. |
| Tunggu API tersambung DB, lalu MinIO | 259-261 | 17 / 18 | Pesan perbaikan dari `db_hint`, `minio_hint`. |
| Cek siap pakai 3x berturut-turut | 262-276 | 16 | Maks 24 x 5 dtk. Cek: /health 200, /ready 200, web 200, /api/v1/auth/me 401, kontainer running. |
| Image yang berjalan = image hasil build | 277-279 | 16 | Membandingkan image ID. |
| Sukses: tulis `.last-deployed`, hapus `.last-failed` | 312-316 | - | Discord "Siap dipakai". |

Rollback otomatis (`rollback_images`, sekitar 286-296): hanya untuk kode keluar 14, 16, 17, 18. Mengembalikan tag `:rollback` ke `:latest` lalu `up -d --force-recreate --no-build`. Migrasi DB TIDAK dibalik. Karena itu migrasi harus kompatibel mundur (tambah dulu, pakai, baru hapus). Sumber: `deploy/README.md` dan `docs/PANDUAN-AGENTIK.md` bagian 6.4.

## 2.2 Membaca hasil deploy

- Discord `#vms-deploy` (webhook di `notify.env`, nama variabel saja): mulai (biru), siap dipakai (hijau), GAGAL (merah) dengan 20 baris log terakhir. Log lengkap terlampir.
- Log di server: `~/deploy/vms-mvp/logs/deploy-*.log`, `logs/cron.log` (`deploy/README.md:64`).
- Ringkasan kontainer dan versi: `bash deploy/status-layanan.sh` (membaca label image `vms.lingkungan`, `org.opencontainers.image.revision`). Hanya dijalankan pemilik di server.
- Status kunci dan penanda: `.autodeploy.lock`, `.last-deployed`, `.last-failed`, `.last-apk`, `.healthcheck.state`, `.offsite.ok` di `~/deploy/vms-mvp`.

## 2.3 Urutan debug (deploy GAGAL)

1. Baca kode keluar di pesan Discord (tabel 2.1). Kode yang menentukan arah:
   - 11 checkout: cek cabang di GitHub, izin deploy key.
   - 12 build: baca `$LOG` tahap build, biasanya Dockerfile atau dependensi (`api/requirements.txt`).
   - 13 backup: lihat `04-cadangan-monitoring-insiden.md` (kredensial MinIO atau DB).
   - 15 migrasi: baca error alembic. Jangan memaksa lanjut. Lihat runbook "deploy gagal" di `04-cadangan-monitoring-insiden.md`.
   - 14/16: kontainer tidak sehat. Cek `docker logs vms_api --tail 100`, lalu `/ready`.
   - 17: API tidak bisa ke DB. `db_hint` menunjuk nilai `DATABASE_URL` di `api.env`.
   - 18: API tidak bisa ke MinIO. `minio_hint` menunjuk `MINIO_ENDPOINT`.
2. Setelah perbaikan, tunggu deploy berikutnya (<= 1 menit), atau paksa dengan `rm ~/deploy/vms-mvp/.last-deployed` (`deploy/README.md:66`). Anti-loop hanya menahan commit yang sama.
3. Jika tidak ada deploy sama sekali: cek `flock` (proses lama masih jalan), `git -C src log -1`, dan cron.
4. Jika kontainer sehat tetapi versi salah: `status-layanan.sh`, lalu bandingkan image ID (langkah 277-279).

## 2.4 Rollback manual (pemilik, di server)

Kondisi: deploy sukses tetapi perilaku buruk, atau rollback otomatis tidak menyala (misalnya kode keluar 15).
1. Hentikan deploy otomatis dulu. Anti-loop `.last-failed` hanya menahan commit yang sama selama 900 dtk, jadi tidak cukup. Pemilik menonaktifkan baris cron prod sementara (`crontab -e`, beri `#`), dan mencatat waktunya. Cron prod tidak ada di repo (lihat 2.1).
2. Cek tag rollback: `docker image inspect vms-mvp-api-api:rollback` (nama image mengikuti `VMS_IMAGE_PREFIX`, bawaan `vms-mvp`; nama pasti TIDAK YAKIN, cek `docker images`).
3. Kembalikan: `docker tag <img>:rollback <img>:latest`, lalu `docker compose up -d --force-recreate --no-build api web`.
4. Jika migrasi sudah jalan dan kode lama tidak cocok skema baru: JANGAN balik migrasi tanpa runbook. Pulihkan DB dari backup pra-deploy (lihat 04-...), dengan persetujuan pemilik.
5. Setelah stabil, nyalakan cron lagi. Catat di CHANGELOG atau runbook.

## 2.5 Cara menyalin perubahan skrip deploy ke server

`autodeploy.sh` sekarang memperbarui dirinya sendiri (`autodeploy.sh:40-50`, commit 47895c20). `deploy/README.md` (bagian "Memasang perubahan skrip ini ke server") masih menulis salin manual. Ikuti dua-duanya sampai README diperbarui:
```
cd ~/deploy/vms-mvp && cp autodeploy.sh autodeploy.sh.bak-$(date +%Y%m%d) && cp src/deploy/autodeploy.sh . && bash -n autodeploy.sh
```
Skrip lain (`backup.sh`, `healthcheck.sh`) disalin manual: tidak ada mekanisme self-update.

## 2.6 Workflow GitHub Actions (inventaris)

Diperiksa pada 2026-11-04 dengan `gh workflow list -a` (read-only). Semua berstatus `active`.

| Workflow (nama) | Berkas | Pemicu | Runner | Izin | Catatan |
|---|---|---|---|---|---|
| CI | `ci.yml` | PR ke `prod`, `development`; manual | self-hosted `[self-hosted, linux, vms]` | `contents: read` | Job: gitleaks (`secrets`), api, web, mobile, notify. Tidak ada Trivy, tidak ada gerbang cakupan (dicek: 0 kecocokan). |
| CD · Production source guard | `cd.yml` | push `prod`; manual | self-hosted | `contents: read` | Hanya memastikan HEAD = `origin/prod`. Deploy nyata tetap di cron server. |
| Images · GHCR | `images.yml` | push `prod`; manual | self-hosted | `contents: read`, `packages: write` | Dorong image ke GHCR. Server BELUM memakainya (`deploy/README.md`, bagian Citra via GHCR). |
| Rilis | `rilis.yml` | push `prod` | self-hosted | `contents: write` | Tag dan GitHub Release. Gagal bila tag sudah ada. |
| APK | `apk.yml` | push `beta`/`prod` bila `mobile/**`; manual (pilih env) | `ubuntu-24.04` (hosted) | default | Sertifikat dicek ke `deploy/android-release-cert.sha256`. |
| Dependabot Updates, Dependency Graph | (bawaan GitHub) | - | - | - | Ada di daftar. |
| CodeQL, CodeQL - Code Quality | (bawaan / setelan repo) | - | - | - | Ada di daftar. |

Sumber: `.github/workflows/*.yml` (baris `on:`, `runs-on:`, `permissions:`); `gh workflow list`.

Pagar GitHub yang sudah diperiksa (read-only, 2026-11-04):
- Runner: `vms-pc` online, label `self-hosted, Linux, X64, vms`. Nama "vms-pc" menunjukkan mesin pengembang, BUKAN server. TIDAK YAKIN. Jika runner ada di PC yang mati, semua CI berhenti diam-diam. Pemilik perlu konfirmasi.
- Branch `prod`: `Branch not protected` (HTTP 404). Konsisten dengan `docs/08` baris 99 (branch protection belum aktif).
- Actions: `allowed_actions: all`, `sha_pinning_required: false`. Artinya action pihak ketiga boleh tag biasa. Workflow sudah memakai SHA (`@3d3c42e5...`), tetapi tidak dipaksa.

## 2.7 Workflow yang bisa dimatikan manual (daftar dan cara hidupkan lagi)

Pelajaran dari repo: `docs/PANDUAN-AGENTIK.md:568` mencatat "Workflow bisa dimatikan manual, dan CI lama bisa rusak diam-diam".

Cek setelah setiap perubahan CI atau sebelum merge ke `prod`:
```
gh workflow list -R Visiontech-Indograha/visiontech-management-system -a
```
Kolom kedua harus `active`. Untuk menghidupkan lagi (pemilik, izin repo admin):
```
gh workflow enable "<nama atau id>" -R Visiontech-Indograha/visiontech-management-system
```
Catat: nama workflow dan id (`392879337` APK, `368924632` CD, `367918818` CI, `400058605` Images, `401561117` Rilis, pada 2026-11-04). Id bisa berubah bila berkas dibuat ulang.

Pelajaran CI yang diam-diam rusak (bukti di riwayat git dan komentar kode):
- `ci.yml` memakai `gitleaks-action@v3` sampai gagal 2026-10-02 karena lisensi organisasi. Sekarang CLI gitleaks 8.30.1 dengan checksum (`ci.yml` baris sekitar 127-131). Pelajaran: versi action pihak ketiga bisa berubah syaratnya; pakai CLI yang dikunci.
- Menit GitHub Actions habis: semua CI dipindah ke runner self-hosted (commit `f4d74746`, 2026-10-30; `ba01d829` memindah cd, images, rilis).
- Runner ubuntu-24.04 dikunci (commit `ae6bf7c1`). APK tetap di hosted karena runner belum punya Android SDK (`apk.yml:30`).
- Perubahan `ci.yml` memicu semua job bila diff kosong (`ci.yml` bagian "Bagian yang berubah": "menjalankan semua job demi keamanan").

Aturan agen (dari `devops-engineer.md`): dilarang mematikan workflow atau menambah `continue-on-error` demi lolos. Bila tak terhindarkan, minta persetujuan pemilik lewat arsitek.

## 2.8 Gerbang CI yang belum ada

- Trivy (pindai image): tidak ada di `ci.yml` (dicek 0 kecocokan).
- Gerbang cakupan (`--cov-fail-under`): tidak ada (0 kecocokan). `api/.coveragerc` ada.
- Cosign / tanda tangan image: tidak ada. Dokumen panduan menyebut ini sebagai tahap 3 (`vms-next/docs/panduan/panduan-fullstack.txt` baris 2037-2062).
- Canary / feature flag: tidak ada. Untuk satu server, cukup env var (riset `01` T23).
- Pemeriksaan migrasi expand-contract di `upgrade()`: belum diverifikasi penuh (riset `01` T23).
