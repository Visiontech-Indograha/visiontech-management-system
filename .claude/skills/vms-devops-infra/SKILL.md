---
name: vms-devops-infra
description: Infrastruktur VMS: tata letak server prod dan beta (kontainer, port, Tailscale), alur autodeploy dan rollback, Dockerfile/image, Docker Compose (batas memori 4 GB, healthcheck, restart), rahasia dan rotasinya, cadangan DB dan uji pemulihan, monitoring (healthcheck, Uptime Kuma), pemeliharaan, runbook insiden, runner self-hosted dan workflow GitHub yang dimatikan, serta keamanan jaringan. Pakai saat menyentuh deploy/, docker-compose*.yml, Dockerfile, .github/workflows, cadangan, Tailscale, atau saat server bermasalah.
---

# vms-devops-infra - infrastruktur, deploy, cadangan, dan insiden VMS

Skill ini melengkapi `vms-cicd-versioning` (cabang, gerbang CI, versi, APK) dan `vms-system-design` (kapasitas 4 GB, prinsip). Skill ini TIDAK mengulang keduanya: rujuk saja.

Sumber fakta: `deploy/`, `.github/workflows/`, `scripts/`, `api/Dockerfile`, `face-service/Dockerfile`, `db/Dockerfile`, `docker-compose*.yml`, `VERSION`, `docs/PANDUAN-AGENTIK.md`, dan dokumen di `vms-next/docs/08-KEADAAN-VMS-SAAT-INI.md` (bagian Server). Status repo: cabang `docs/skills-agentik`, dibaca 2026-11-04. Setiap klaim bertanda `(bukti: berkas:baris)`. Yang tidak bisa dipastikan bertanda TIDAK YAKIN atau TIDAK DIVERIFIKASI.

## 0. Aturan keras (wajib)

- Sesi agen TIDAK SSH ke server, TIDAK menjalankan `docker compose`, `docker`, atau `crontab` di server, dan TIDAK membaca isi berkas rahasia. Perintah ke server hanya dijalankan pemilik, dari komputernya.
- Perubahan infrastruktur lewat brief arsitek, di cabang dan worktree sendiri. Commit hanya bila pemilik meminta. Dilarang `git add -A` dan `git stash` (aturan `devops-engineer.md`).
- Dilarang mematikan workflow, menghapus langkah, atau menambah `continue-on-error` demi lolos (`devops-engineer.md`).
- Dilarang menaruh rahasia di workflow, skrip, Dockerfile, compose, atau Git. Rahasia hanya `${{ secrets.* }}` atau berkas server chmod 600.
- Setiap perubahan skrip di `deploy/` wajib `bash -n <skrip>` sebelum commit.
- Tes DB hanya atas perintah pemilik (`docs/PANDUAN-AGENTIK.md`, memori).
- Output perintah dibatasi (`| tail -n 25`).

## 1. Tata letak server (ringkas; detail di `references/01-server-dan-jaringan.md`)

Server `visiontech-bar`, Tailscale 100.117.92.14, RAM 4 GB (`docs/08` baris 32).

| Lingkungan | Folder | Cabang sumber | Kontainer utama | Port host |
|---|---|---|---|---|
| Prod | `~/deploy/vms-mvp` | `prod` | `vms_api`, `vms_web`, `vms_face`, `vms_db_prod`, `vms_minio_prod` | API 8000, web 8080, DB 5433, MinIO 9000/9001 |
| Beta | `~/deploy/vms-beta` | `beta` | `vms_beta_api`, `vms_beta_web`, `vms_beta_face`, `vms_db_beta`, `vms_minio_beta` | API 8001, web 8081, DB 127.0.0.1:5435, MinIO 127.0.0.1:9002/9003 |
| Monitor | - | - | `vms_uptime_kuma` | 100.117.92.14:3001 |

Sumber: `docs/08` baris 35-38; `deploy/autodeploy.sh:10-16`; `deploy/beta/compose.yml`; `deploy/beta/compose.infra.yml`; `deploy/uptime-kuma.compose.yml:17`.

Jalur publik yang sudah ada (inventaris, perlu dicek pemilik): Cloudflare Tunnel ke web prod (`deploy/tutup-port-layanan.sh:3`); Tailscale Funnel API beta publik di :10000 (`deploy/beta/pasang-beta.sh:92-93`). Detail di `references/01`.

## 2. Alur autodeploy (ringkas; detail di `references/02-autodeploy-dan-ci.md`)

Cron server tiap menit (beta: `deploy/beta/pasang-beta.sh:95`; prod: tidak ada di repo, TIDAK YAKIN isinya). Skrip `deploy/autodeploy.sh`:

1. `flock` agar tidak ada dua deploy sekaligus (`:23`).
2. `git fetch origin <cabang>`; skrip memperbarui dirinya dari origin (`:40-50`).
3. Commit baru? Jika sama dengan `.last-deployed`, berhenti (`:74`). Commit yang baru gagal ditahan 900 dtk (`:76-83`).
4. Checkout, simpan image lama sebagai tag `:rollback`, build, backup DB pra-deploy, `alembic upgrade head`, `up -d --force-recreate`.
5. Tunggu API tersambung DB dan MinIO. Cek siap pakai 3x berturut-turut (`/health`, `/ready`, web, `/api/v1/auth/me` 401, kontainer running).
6. Gagal dengan kode 14, 16, 17, atau 18: rollback image ke tag `:rollback`. Migrasi TIDAK dibalik. Kode 11, 12, 13, 15 tidak rollback.
7. Lapor ke Discord (mulai, siap, gagal). Log lengkap dilampirkan.

Cara membaca hasil: kode keluar di pesan Discord, lalu log di `~/deploy/vms-mvp/logs/deploy-*.log`. Urutan debug dan tabel kode keluar ada di `references/02` (2.1 dan 2.3). Rollback manual ada di 2.4.

## 3. Dockerfile dan image (ringkas; detail di `references/03-image-compose-rahasia.md`)

Checklist untuk setiap Dockerfile baru atau diubah:
- [ ] Multi-stage bila ada alat build (pip, npm). Runtime tidak membawa compiler atau cache.
- [ ] `USER` non-root dengan UID tetap (contoh 10001). Folder tulis (`uploads/`, LibreOffice) bisa ditulis UID itu.
- [ ] `.dockerignore` ada di folder konteks, minimal mengabaikan `.env`, `.env.*`, `!.env.example`, `.git/`, `tests/`, cache, dan folder data. Mencontoh `web/.dockerignore` dan `face-service/.dockerignore`.
- [ ] `HEALTHCHECK` ke endpoint hidup (`/health`). Contoh ada di `face-service/Dockerfile:32-33`.
- [ ] Base image dipin ke digest atau versi tetap. Tag `latest` dilarang. Dependabot `docker` untuk pembaruan terkontrol.
- [ ] Label `org.opencontainers.image.revision`, `vms.layanan`, `vms.lingkungan` (dibaca `deploy/status-layanan.sh`; contoh di `api/Dockerfile:29-32`).
- [ ] Tidak ada rahasia di layer: tidak ada `ENV` dengan nilai rahasia, tidak `COPY` berkas `.env`.
- [ ] `docker build` lokal lalu `docker run --rm <image> ls /app/.env` harus gagal (pemilik atau devops).

## 4. Compose (ringkas)

- [ ] Batas memori (`mem_limit`) untuk setiap layanan. Total harus muat 4 GB dengan swap yang aman. Ukur dulu dengan `docker stats --no-stream`.
- [ ] `restart: unless-stopped` (atau `always` untuk DB dan MinIO, seperti di `deploy/beta/compose.infra.yml`). Restart policy diperiksa `healthcheck.sh:24`.
- [ ] `healthcheck` untuk DB (contoh `docker-compose.yml:37-41`) dan layanan lain. `depends_on` dengan `condition: service_healthy` bila perlu.
- [ ] Port diikat ke `127.0.0.1` atau IP Tailscale: `ports: ["127.0.0.1:5435:5432"]`. Port tanpa ikatan lolos ufw (`deploy/hardening-server.sh:6`).
- [ ] Jaringan terpisah per lingkungan (`vms_beta_net`, `deploy/beta/compose.yml:2-3`).
- [ ] Rahasia lewat `env_file` (berkas server) atau `${VAR:?pesan}` (bukan nilai di file). Contoh: `docker-compose.yml:10`.
- [ ] Log dibatasi `json-file` 10m x 3 (`deploy/compose.limits.yml:13-15`).
- [ ] Volume bernama. Ganti versi mayor Postgres = volume baru + dump/restore (komentar `docker-compose.yml:35`).
- [ ] `docker compose config >/dev/null` lolos sebelum `up -d` (dipakai di skrip `compose.limits.yml:7`).

## 5. Rahasia (ringkas; detail di `references/03` 3.5)

- Rahasia server: `api.env`, `notify.env`, `infra.env`, `face.env`, `offsite.env`, deploy key, kunci SSH offsite. Semua chmod 600, tidak di Git (`.gitignore` baris 2-4).
- GitHub secrets: keystore APK dan `DISCORD_WEBHOOK_CI` (`apk.yml`, `ci.yml`).
- Pagar yang ada: `.githooks/pre-commit:13-18` menolak berkas rahasia di-stage; gitleaks 8.30.1 di CI dengan checksum (`ci.yml` sekitar 127-131); `.gitleaksignore` 12 baris pengecualian (isi tidak dikutip; setiap baris perlu alasan).
- Rotasi: lihat `references/03` 3.5 (buat nilai baru, simpan di server atau GitHub secrets, recreate kontainer, verifikasi `/ready`, catat tanggal tanpa nilai).
- Jangan pernah mencetak nilai rahasia di chat, log, atau skill. Pesan galat di `deploy/backup.sh` menunjuk berkas server lama; jangan ikuti nilainya.
- Utang: `JWT_KID=jwt-dev-1` di produksi (`docs/08` baris 48). Rotasi kunci JWT mengeluarkan semua sesi; jadwalkan dengan pemilik.

## 6. Cadangan dan pemulihan (ringkas; detail di `references/04-cadangan-monitoring-insiden.md`)

- DB prod: `deploy/backup.sh` (pg_dump `-Fc` di kontainer), cron 01:30 (dokumen), disimpan 7 dump lokal dan 30 hari di MinIO bucket `vms-backups` (`backup.sh:18`). Beta: cron 01:45 (`pasang-beta.sh:97`).
- Luar-server: `deploy/backup-offsite.sh` (rsync SSH, verifikasi ukuran), cron 01:45 bila dipasang (`siapkan-offsite.sh:7`). Status di server TIDAK DIKETAHUI.
- Uji pulih: `deploy/uji-pulih-cadangan.sh`, dijalankan pemilik tiap bulan dan setelah perubahan skema besar (`deploy/README.md`). Hasil terakhir TIDAK ADA di repo.
- Pemulihan: selalu ke database sementara dulu, baru ke prod dengan persetujuan tertulis pemilik (`references/04` 4.3).
- RPO dan RTO belum tertulis di repo (riset F-30). Usulan belum disetujui: RPO 24 jam, RTO diukur.
- Keterbatasan yang tercatat: dump di server yang sama dengan DB; berkas MinIO (foto, dokumen, PDF) belum ikut dicadangkan (`deploy/README.md`).

## 7. Monitoring dan pemeliharaan (ringkas)

- `deploy/healthcheck.sh` cron 5 menit, alarm Discord hanya saat berubah: kontainer mati, restart > 3, endpoint, MinIO, disk >= 80%, RAM < 400 MB, swap >= 60%, umur backup > 26 jam (`healthcheck.sh:24-64`).
- Uptime Kuma (`deploy/uptime-kuma.compose.yml`), hanya tailnet. Monitor yang disarankan ada di komentar file itu.
- Belum ada metrik RED, duration, atau tracing (riset F-20; `docs/PANDUAN-AGENTIK.md` 4.6). Usulan bertahap: log akses tanpa PII, lalu metrik bila anggaran RAM cukup, lalu tracing (perlu ADR).
- Pemeliharaan: `docker image prune -f` aman (sudah dipakai `autodeploy.sh`). LARANG tanpa perintah pemilik: `docker system prune -a`, `docker volume prune`, `docker volume rm`, `docker compose down -v`.
- Pembaruan OS dan SSH: `deploy/hardening-server.sh --cek` lalu `--ya` (pemilik; sudo; buka sesi SSH kedua dulu).

## 8. Runner dan workflow GitHub (ringkas; detail di `references/02` 2.6-2.8)

- Hampir semua workflow jalan di runner self-hosted `[self-hosted, linux, vms]` (`ci.yml:27`). Kecuali `apk.yml` (`ubuntu-24.04`, `apk.yml:33`).
- Pemeriksaan read-only (2026-11-04): satu runner `vms-pc` online. Nama itu menunjukkan PC pengembang, bukan server. TIDAK YAKIN. Jika mesin itu mati, CI berhenti diam-diam.
- Daftar workflow (dari `gh workflow list -a`): APK, CD, CI, Images, Rilis, Dependabot, Dependency Graph, CodeQL, CodeQL Code Quality. Semua `active` pada 2026-11-04.
- Workflow yang dimatikan manual tidak memicu apa pun. Cek setelah setiap perubahan CI: `gh workflow list -R Visiontech-Indograha/visiontech-management-system -a`. Hidupkan lagi: `gh workflow enable "<nama>" -R ...` (pemilik).
- Pelajaran: CI sempat bergantung pada GitHub Actions minutes (habis 2026-10-30, `f4d74746`); gitleaks-action gagal lisensi 2026-10-02 (komentar `ci.yml`). Pakai CLI yang dikunci versi dan checksum.
- Branch `prod` tidak diproteksi (`gh api .../branches/prod/protection` mengembalikan 404). Sesuai `docs/08` tabel tenggat utang (baris Branch protection).
- `sha_pinning_required: false` pada pengaturan Actions (`gh api .../actions/permissions`).

## 9. Keamanan infrastruktur (ringkas; detail di `references/01` 1.3-1.5)

- Port publik: hanya yang disengaja (Cloudflare Tunnel ke 8080; Funnel 10000). Semua lain diikat ke localhost atau IP tailnet.
- Tailscale: Serve untuk tailnet, Funnel untuk publik, satu port hanya salah satu (Tailscale KB, https://tailscale.com/kb/1312/serve, diakses 2026-11-04). ACL belum diperiksa dari repo; daftarnya ada di `references/01` 1.4.
- Firewall: ufw menolak masuk kecuali SSH, web, dan `tailscale0` (`hardening-server.sh:61,69`). Status penerapan TIDAK DIKETAHUI.
- SSH: kunci saja, root login mati (`hardening-server.sh:14-16`). Terapkan dengan `--ya` oleh pemilik.

## 10. Checklist definisi selesai (perubahan infrastruktur)

Sebuah perubahan di `deploy/`, `.github/`, `scripts/`, Dockerfile, atau compose dianggap selesai bila semua ini terpenuhi (atau alasannya ditulis):
- [ ] `bash -n` lolos untuk setiap skrip shell yang berubah. `docker compose config -q` lolos untuk compose yang berubah.
- [ ] `ci.yml` tetap hijau; tidak ada `continue-on-error` baru; tidak ada workflow yang dimatikan.
- [ ] Tidak ada rahasia baru di Git (gitleaks dan hook pre-commit lolos).
- [ ] Tidak ada port baru yang tidak diikat. Ada catatan bila ada jalur publik.
- [ ] Batas memori baru diukur atau diberi tanda "perlu ukur".
- [ ] Perubahan autodeploy: salinan di server dicatat dan langkah salin manual disebut bila perlu (`references/02` 2.5).
- [ ] Perubahan migrasi: kompatibel mundur (tambah dulu, pakai, baru hapus). Diuji di beta sebelum prod.
- [ ] Perubahan cadangan: uji pulih dijadwalkan atau dijalankan, dan hasilnya dicatat.
- [ ] Dokumen diperbarui: `deploy/README.md`, `docs/PANDUAN-AGENTIK.md` (bagian lokasi dan peran), dan skill ini bila aturan berubah. Riwayat skill ditambah.
- [ ] Langkah manual untuk pemilik ditulis jelas (perintah, tempat dijalankan, cara batal).
- [ ] Laporan memakai format `devops-engineer.md` (maks 15 baris).

## 11. Anti-pola nyata dari repo (bukti berkas:baris)

| No | Anti-pola | Bukti | Status (2026-11-04) |
|---|---|---|---|
| A-1 | API berjalan root, tanpa HEALTHCHECK, satu tahap | `api/Dockerfile:1`, tanpa `USER`, tanpa `HEALTHCHECK`, `:34` CMD | Terbuka (riset F-02) |
| A-2 | Konteks build API tanpa `.dockerignore`; `COPY . .` | `api/Dockerfile:27`; `api/.dockerignore` tidak ada (dicek). Web dan face sudah punya. | Terbuka (riset F-01, bagian `api/.env` tidak terbukti di worktree ini) |
| A-3 | Port DB dev tidak diikat ke localhost | `docker-compose.yml:33` `"5433:5432"` | Terbuka (dev laptop); beta sudah benar (`compose.infra.yml:12`) |
| A-4 | Tag tidak dipin, termasuk `latest` | `api/Dockerfile:1`, `db/Dockerfile:10`, `deploy/beta/compose.infra.yml:22` (`minio:latest`), `deploy/uptime-kuma.compose.yml:13` (`:1`) | Terbuka |
| A-5 | Batas memori face berbeda antar dokumen | `deploy/compose.limits.yml:21` (768m) vs `deploy/pasang-face-service.sh:57` dan `deploy/beta/compose.yml:33` (1200m) | Perlu keputusan pemilik |
| A-6 | Dokumen tidak sama dengan kode | `deploy/README.md` (salin manual) vs `autodeploy.sh:40-50` (self-update, commit `47895c20`); README "14 dump" vs `backup.sh:18` (7) | Perbaiki dokumen |
| A-7 | Beta menyalin dump DB prod | `deploy/beta/pasang-beta.sh:104-110` (`pg_dump` prod ke `sumber_v1` beta) | TIDAK YAKIN isi beta; perlu kebijakan data dari pemilik |
| A-8 | API beta publik lewat Funnel | `deploy/beta/pasang-beta.sh:92-93` (:10000 -> 8001) | Disengaja (komentar); catat di ADR, batasi bila perlu |
| A-9 | Seluruh CI bergantung pada satu runner | `gh api .../actions/runners` (satu runner `vms-pc`); `ci.yml:27` | Titik tunggal gagal |
| A-10 | Branch prod tanpa proteksi | `gh api .../branches/prod/protection` (404); `docs/08` tabel tenggat utang (baris Branch protection) | Terbuka (pemilik) |
| A-11 | Lokasi compose prod tidak konsisten di dokumen | `deploy/README.md` (`vms-mvp/compose.yml`) vs `deploy/tutup-port-db.sh:6` (`~/deploy/visiontech/`) | TIDAK YAKIN, verifikasi di server |
| A-12 | Tidak ada pindai image, gerbang cakupan, atau tanda tangan image | `ci.yml` (0 kecocokan Trivy, cov-fail-under) | Terbuka (riset F-22) |
| A-13 | Cadangan DB di server yang sama; berkas MinIO tidak dicadangkan | `deploy/README.md` (bagian uji pulih) | Terbuka; offsite perlu dicek |
| A-14 | RPO dan RTO tidak tertulis | riset `01` F-30 (baris 585-588) | Terbuka |
| A-15 | Runbook yang dirujuk tidak ada | `deploy/README.md` dan `ci.yml` merujuk `docs/RUNBOOK-PRODUKSI.md`, `docs/RUNBOOK-CI.md`; `ls docs` hanya `PANDUAN-AGENTIK.md` | Terbuka |
| A-16 | `version:` usang di compose dev | `docker-compose.yml:1` | Kecil |
| A-17 | Pesan galat backup menyebut berkas server lama | `deploy/backup.sh` (pesan MinIO, sekitar baris 30-40) | Kecil; jangan ikuti nilainya |

Catatan status temuan riset (`riset-best-practice/01-PDF-DAN-AUDIT-VMS.md`):
- F-01 (rahasia di image): sebagian. `api/.env` tidak ada di worktree ini, tetapi `api/.dockerignore` tetap tidak ada. Terbuka.
- F-02 (root, tanpa HEALTHCHECK): terbuka (A-1).
- F-20 (metrik): terbuka.
- F-22 (gitleaks, Trivy, cov): gitleaks sudah ada; Trivy dan cov belum.
- F-30 (cadangan): sebagian. Jadwal dan skrip sudah ada di `deploy/` (riset menyebut tidak ada). RPO/RTO belum.

## 12. Skill global yang boleh dipanggil atau dilebur

Skill global tidak disalin ke repo. Pakai bila tugasnya cocok. Yang dilebur hanya rujukan dan kebiasaan kerjanya, bukan isinya.

| Skill global | Kapan dipakai untuk infra VMS | Catatan |
|---|---|---|
| `postman:ci-integration` | menambah uji API atau lint kontrak ke `ci.yml` (perubahan CI, atas persetujuan arsitek) | Mengikuti aturan: validasi terpisah dari publikasi ke workspace. Jangan ubah gerbang yang ada untuk lolos. |
| `postman:api-monitoring` | pemantauan sintetis berkala terhadap `/health`, `/ready`, dan jalur web (sebagai pelengkap Uptime Kuma). Pemantau Postman yang menjangkau API privat butuh runner self-hosted. | Usulan, bukan wajib. Kebutuhan 4 GB RAM dan jalur publik harus dinilai dulu. |
| `postman:api-testing` | uji smoke endpoint setelah deploy beta (GET saja) | Gunakan Postman CLI terpasang (`CLAUDE.md`). |
| `security-review` | tinjauan keamanan perubahan infrastruktur sebelum PR ke `prod` | Dipakai arsitek atau pemilik. |
| `update-config` | mengubah `settings.json` (izin, hook). BUKAN untuk server. | Bukan untuk konfigurasi server. |
| `run` | menjalankan stack dev lokal (`docker-compose.yml`) untuk melihat perubahan | Hanya dev laptop. |
| `code-review` | tinjauan kebenaran diff skrip deploy dan workflow | Mode `max` atau `ultra` hanya bila pemilik meminta. |
| `simplify` | merapikan skrip yang sudah berubah | Setelah tes, bukan sebelum. |
| `anthropic-skills:skill-creator` | memperbaiki deskripsi skill ini | - |

Yang TIDAK dipakai untuk infra VMS: `claude-api`, `plugin-authoring`, `init` (tanpa perintah), `dataviz`.

## 13. Pemeliharaan skill ini

- Perbarui saat: `deploy/`, workflow, Dockerfile, atau compose berubah; saat daftar workflow atau runner berubah; saat keputusan pemilik soal port publik, batas memori, atau RPO/RTO keluar; setelah insiden.
- Tinjau tiap kuartal bersama `vms-cicd-versioning` dan `vms-system-design`.
- Jangan simpan rahasia, IP tambahan, atau nilai dari berkas server di skill ini.

## 14. Sumber luar (diakses 2026-11-04)

- Docker, Dockerfile best practices: https://docs.docker.com/build/building/best-practices/ (pin digest, `.dockerignore`, non-root, multi-stage).
- Docker, Compose services reference: https://docs.docker.com/reference/compose-file/services/ (`mem_limit`, `restart`, `healthcheck`).
- GitHub Docs, hardening GitHub Actions: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions (permissions, pin SHA, self-hosted runner, OIDC).
- Tailscale KB, Serve dan Funnel: https://tailscale.com/kb/1312/serve. Sintaks `--tcp` dan `--https` TIDAK ditemukan di halaman itu; TIDAK YAKIN.
- PostgreSQL, pg_dump: https://www.postgresql.org/docs/current/app-pgdump.html (format custom, konsistensi, bukan PITR).
- Uptime Kuma: https://github.com/louislam/uptime-kuma/wiki/How-to-Install. Halaman yang terbuka hanya berisi daftar judul; detail tag v1 dan v2 TIDAK DIVERIFIKASI.
- Panduan internal: `vms-next/docs/panduan/panduan-fullstack.txt` baris 1610-1627 (observability), 1686-1757 (Docker, health, expand-contract), 2031-2062 (CI/CD). Riset audit: `riset-best-practice/01-PDF-DAN-AUDIT-VMS.md`.

## Tanda yang perlu dikonfirmasi pemilik

1. Runner `vms-pc`: apakah ini PC pengembang, dan apa rencana bila mati.
2. Lokasi compose prod (A-11) dan isi crontab prod.
3. Funnel :10000 untuk API beta, dan kebijakan data beta (A-7, A-8).
4. Batas memori face: 768m atau 1200m (A-5).
5. Status offsite, uji pulih terakhir, dan status ufw serta ACL Tailscale di server.
6. RPO dan RTO yang disetujui.
7. Lokasi `docs/RUNBOOK-*.md` (A-15).

## Riwayat

- v0.1 - 2026-11-04 - Awal. Disusun dari `deploy/`, workflow, Dockerfile, compose, `docs/08` bagian Server, riset audit DevOps, dan panduan internal. Pemeriksaan GitHub read-only (`gh`). Tidak ada akses SSH ke server.
