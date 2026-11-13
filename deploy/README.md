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
`alembic upgrade head` (Master Schema V2) → `up -d --force-recreate` → **cek siap pakai**. Backup DB menyimpan 7 dump terakhir (`backup.sh`, `retention`). `--force-recreate`
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
| `localhost:8000/ready` (API berhasil terhubung ke DB) | 200, bukan 503 |
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

`autodeploy.sh` di server **memperbarui dirinya sendiri** dari `origin/$BRANCH` (bagian "Perbarui diri sendiri"
di skrip, pada setiap jalannya bila isinya berbeda dan sintaksnya valid). Versi sebelumnya disimpan di
`$BASE/autodeploy.sh.sebelum`, dan catatannya di `logs/self-update.log`. Jadi perubahan `autodeploy.sh` di branch
deploy ikut berlaku otomatis.

Salin manual hanya bila self-update tidak bisa jalan (misalnya `src/` belum ada atau sintaks salah). Sebelum itu,
cadangkan dulu:

```bash
cd ~/deploy/vms-mvp && cp autodeploy.sh autodeploy.sh.bak-$(date +%Y%m%d) && cp src/deploy/autodeploy.sh . && bash -n autodeploy.sh
```

Skrip lain di `deploy/` (`pasang-*.sh`, `pakai-peran-runtime.sh`, dan seterusnya) TIDAK diperbarui otomatis. Jalankan
ulang dari komputer pemilik bila diperlukan.

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

## Cadangan terpisah per lingkungan (opsional)
`VMS_BACKUP_DIR` (folder) dan `VMS_BACKUP_NAME` (awalan nama berkas) di `deploy.env` memisahkan cadangan prod dan beta;
tanpa keduanya perilaku lama (`backups/`, nama DB, 7 berkas). Langkah aman: `deploy/PANDUAN-PISAH-CADANGAN.md`.
Tes logika: `bash scripts/uji-backup-retensi.sh`.

## Uji pulih cadangan (P9-5)
`ssh ageng@192.168.88.160 "bash -s" < deploy/uji-pulih-cadangan.sh` — membuat cadangan baru lewat `backup.sh`,
mengunduh salinan MinIO-nya (SHA-256 harus sama), memulihkannya ke Postgres SEMENTARA (citra sama, tanpa jaringan),
lalu membandingkan jumlah baris per tabel, versi alembic, tabel ber-RLS, dan fungsi dengan prod. Prod hanya dibaca;
kontainer sementara selalu dihapus; keluaran hanya nama tabel & angka. Jalankan tiap bulan dan setelah perubahan
besar skema. Catatan: berkas di MinIO (foto/dokumen/PDF) belum ikut dicadangkan, dan cadangan DB masih di server
yang sama (lihat docs/06 P9-5).

## Alur pengembangan beta → produksi (ringkas)

`feature/*` → PR ke `development` (CI api/web/mobile + gitleaks wajib hijau) → merge ke `beta` (server beta deploy otomatis;
uji nyata web + APK beta dari `apk.yml`) → PR `beta` → `prod` (satu persetujuan, CI hijau) → server prod deploy
(backup → migrasi → cek siap pakai → Discord). Hotfix: `hotfix/*` dari `prod`, PR langsung ke `prod`, lalu back-merge ke
`beta`/`development`. Migrasi DB selalu kompatibel mundur (tambah dulu, pakai, baru hapus) dan diuji di beta sebelum prod.

## Pemantauan dan pemeliharaan

- `deploy/healthcheck.sh` (cron 5 menit; alert Discord hanya saat berubah): kontainer berkebijakan restart yang mati,
  /health /ready web proxy, jangkauan API→MinIO, disk/RAM/swap, umur backup lokal dan luar-server.
- `deploy/uptime-kuma.compose.yml`: pemantau ketersediaan (hanya Tailscale/lokal).
- `deploy/backup-offsite.sh`: salinan backup ke mesin lain via rsync + SSH (butuh `offsite.env`).
- `deploy/hardening-server.sh --cek|--ya`: SSH, firewall, fail2ban, pembaruan otomatis (perlu sudo, dijalankan pemilik).
- Anti-loop: deploy yang gagal untuk commit yang sama baru dicoba lagi setelah `VMS_DEPLOY_RETRY_AFTER` detik (bawaan 900);
  penanda `.last-failed`. Self-update `autodeploy.sh` lihat bagian "Memasang perubahan skrip".
- Beta (`deploy/beta/`): API dan web beta HANYA tailnet (Tailscale Serve, bukan Funnel). Data beta berasal dari
  `db/07_master_seed_v2.sql` (sintetis), bukan dari prod. Langkah pemilik dan rollback: `deploy/RUNBOOK-beta-aman.md`.
- Panduan operasional harian: [`docs/RUNBOOK-PRODUKSI.md`](../docs/RUNBOOK-PRODUKSI.md) (berkas ini belum ada di repo).

## Citra via GHCR (opsional, mengurangi beban build di server)
Workflow `.github/workflows/images.yml` membangun `api` dan `web` di runner GitHub saat `prod` berubah dan mendorongnya ke
`ghcr.io/visiontech-indograha/vms-{api,web}:<sha>` (+ `latest`). Server belum memakainya. Untuk beralih (tindakan pemilik server):
buat token `read:packages`, `docker login ghcr.io` di server, ubah `compose.yml` server ke `image: ghcr.io/...:${TAG}` dan ganti
`docker compose build` di `autodeploy.sh` dengan `docker compose pull`. Uji dulu di beta.

## Cadangan berkas MinIO dan uji pulih

- `deploy/backup-minio.sh [label]`: `mc mirror` satu arah semua bucket (kecuali `vms-backups`) ke `$VMS_BACKUP_DIR/<NAME>-berkas/` plus manifest hitungan objek. Mematuhi retensi UU PDP: berkas terhapus maksimal **35 hari** (30 hari retensi DB/MinIO + maks 5 hari cadangan). Bawaan mengaktifkan `--remove` (`VMS_MINIO_REMOVE=1`). Kontainer MinIO: `VMS_MINIO_CT` (bawaan `${VMS_CONTAINER_PREFIX:-vms}_minio`). Pin citra mc lewat `VMS_MC_IMAGE`.
- Integrasi opsional: `VMS_BACKUP_MINIO=1 ./backup.sh` (bawaan mati). Cron terpisah juga boleh.
- `deploy/uji-pulih.sh`: pulihkan dump terbaru ke Postgres sementara (tanpa jaringan) dan cocokkan hitungan berkas dengan manifest. Hanya membaca cadangan.
- Rencana pengganti MinIO: `docs/RENCANA-KELUAR-MINIO.md`.

## Cadangan terenkripsi age, kepatuhan PDP, dan pemulihan (LANGKAH PEMILIK)

> [!IMPORTANT]
> **EKSEKUSI SERVER ADALAH LANGKAH PEMILIK:** Seluruh perintah pemulihan, penjadwalan cron, atau pengubahan konfigurasi di server produksi Linux dan mesin Windows adalah kewenangan manual pemilik. Agen AI dilarang menjalankan perintah langsung di server.

1. **Enkripsi Cadangan age (`deploy/backup-terenkripsi.sh`, `deploy/backup-offsite.sh`)**:
   - Seluruh cadangan yang keluar dari server Linux wajib terenkripsi `age` menggunakan kunci publik dari `age-recipients.txt`. Kunci privat hanya disimpan offline dan di mesin Windows penarik (`pobonguar`).
   - `backup-offsite.sh` secara otomatis mengenkripsi dump dengan `age` sebelum rsync ke server cadangan lain dan menolak pengiriman dump polos tanpa enkripsi.
2. **Perlindungan Biometrik PDP (UU PDP No. 27/2022)**:
   - Kolom `face_embedding` pada tabel `employee` adalah Data Pribadi Spesifik.
   - Opsi `VMS_BACKUP_EXCLUDE_BIOMETRIC=1` pada `backup.sh` dan `backup-terenkripsi.sh` mengecualikan data biometrik mentah dari dump.
   - Untuk lingkungan pengujian / non-produksi, gunakan skrip `deploy/sanitasi-dump-biometrik.sh` (`--db` atau `--berkas`) untuk membersihkan `face_embedding` menjadi `NULL`.
3. **Panduan Lengkap Tarik & Pemulihan Cadangan**:
   - Rincian konfigurasi Windows Task Scheduler, SFTP baca-saja, BitLocker, VSS, dan langkah pemulihan bencana (DR) terdokumentasi di [`docs/CADANGAN-WINDOWS.md`](../docs/CADANGAN-WINDOWS.md).
4. **Penanganan Insiden PDP**:
   - Bila terjadi insiden kebocoran data pribadi (kredensial, biometrik, berkas, atau database), ikuti prosedur wajib notifikasi tertulis **3x24 jam (72 jam)** sesuai [`docs/RUNBOOK-INSIDEN-PDP.md`](../docs/RUNBOOK-INSIDEN-PDP.md).
