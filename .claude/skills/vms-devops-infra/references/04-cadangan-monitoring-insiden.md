# 04 · Cadangan, pemulihan, monitoring, pemeliharaan, dan runbook insiden

Sumber: `deploy/backup.sh`, `deploy/backup-offsite.sh`, `deploy/siapkan-offsite.sh`, `deploy/uji-pulih-cadangan.sh`, `deploy/healthcheck.sh`, `deploy/uptime-kuma.compose.yml`, `deploy/hardening-server.sh`, `deploy/README.md`, `deploy/beta/pasang-beta.sh`, `docs/PANDUAN-AGENTIK.md` bagian 6.2. Praktik resmi PostgreSQL pg_dump (https://www.postgresql.org/docs/current/app-pgdump.html, diakses 2026-11-04): `-Fc` menghasilkan arsip biner untuk `pg_restore`, dump konsisten walau database dipakai, tetapi bukan PITR. Untuk PITR perlu base backup plus arsip WAL (halaman continuous archiving, belum dibuka di sesi ini; TIDAK YAKIN detailnya).

## 4.1 Cadangan (apa yang ada)

| Jenis | Cara | Jadwal | Tujuan | Retensi | Sumber |
|---|---|---|---|---|---|
| DB prod | `pg_dump -Fc` di dalam `vms_db_prod` lalu unggah ke MinIO | cron 01:30 (dokumen); autodeploy juga memanggil `backup.sh pra-deploy-<sha>` | `backups/*.dump` di server + bucket `vms-backups` | lokal 7 berkas (`backup.sh:18`); MinIO 30 hari (baris ~60, `cut`) | `deploy/backup.sh`, `docs/PANDUAN-AGENTIK.md` 6.2 |
| DB beta | sama, label `harian` | cron 01:45 (`deploy/beta/pasang-beta.sh:97`) | sama, di `~/deploy/vms-beta` | sama | sama |
| Salinan luar-server | `rsync` berkas `.dump` ke mesin tujuan lewat SSH kunci khusus; verifikasi ukuran | cron 01:45 (`deploy/siapkan-offsite.sh:7`) | `OFFSITE_HOST:OFFSITE_DIR` | `OFFSITE_KEEP_DAYS` (bawaan 30) | `deploy/backup-offsite.sh` |

Catatan penting:
- Konflik angka retensi: `deploy/README.md` menulis "14 terakhir disimpan di `backups/`", sedangkan kode `backup.sh:18` menyimpan 7. Kode yang berlaku. Perbaiki dokumen (anomali A-6).
- Dump dibuat di server yang sama dengan DB. Cadangan luar-server hanya ada bila `offsite.env` sudah dipasang. Status di server TIDAK DIKETAHUI dari repo (pemilik cek `logs/offsite.log` dan `.offsite.ok`).
- Berkas di MinIO (foto, dokumen, PDF) belum ikut dicadangkan (`deploy/README.md`, bagian uji pulih cadangan).
- Cadangan MinIO itu sendiri: TIDAK ADA. Bucket `vms-backups` berisi dump, bukan salinan `vms-*` lainnya.
- Retensi walau unggah gagal: `trap retention EXIT` (`backup.sh:21`). Pelajaran insiden 2026-10-13: 12 dump @1,9 MB dalam 12 menit sebelum trap ditambahkan (komentar `backup.sh:12-14`).

## 4.2 Uji pemulihan (sudah ada, dijalankan pemilik)

`deploy/uji-pulih-cadangan.sh` (dijalankan dari komputer pemilik: `ssh ageng@<ip> "bash -s" < deploy/uji-pulih-cadangan.sh`):
1. Buat cadangan baru lewat `backup.sh` (label `uji-pulih`).
2. Unduh salinan MinIO, cocokkan SHA-256.
3. Nyalakan Postgres sementara (citra sama, tanpa jaringan, tanpa port, tanpa volume tetap).
4. `pg_restore` ke database kosong. Galat harus 0.
5. Bandingkan dengan prod: jumlah baris per tabel, versi alembic, tabel ber-RLS, fungsi SECURITY DEFINER.
6. Hapus kontainer sementara walau gagal.

Jadwal yang tertulis: tiap bulan dan setelah perubahan skema besar (`deploy/README.md`). Catat hasil (tanggal, lama pulih, hasil perbandingan) di runbook. Hasil uji terakhir TIDAK ADA di repo; TIDAK YAKIN apakah pernah dijalankan.

## 4.3 Runbook pemulihan DB (urutan aman)

Jangan pernah memulihkan langsung ke `vms_v2` (prod). Selalu ke database sementara dulu.
1. Pemilik memastikan penyebab (lihat 4.6) dan membuat cadangan baru lewat `backup.sh pra-pemulihan` bila DB masih hidup.
2. Pilih berkas: `ls -1t backups/*.dump` (atau unduh dari MinIO bucket `vms-backups`).
3. Nyalakan Postgres sementara dari citra `vms-db:18` tanpa jaringan dan tanpa port (seperti `uji-pulih-cadangan.sh`).
4. `pg_restore --no-owner --no-acl -d <db_sementara> <berkas.dump>`. Periksa galat.
5. Bandingkan jumlah baris per tabel dan versi alembic dengan prod.
6. Hanya dengan persetujuan tertulis pemilik: hentikan API prod, pulihkan ke database yang dipakai, nyalakan lagi, lalu cek `/ready`.
7. Catat waktu mulai, waktu selesai, dan RPO yang tercapai (selisih waktu cadangan terakhir).

RPO dan RTO belum tertulis di repo (riset F-30, `riset-best-practice/01-PDF-DAN-AUDIT-VMS.md` baris 585-588). Usulan (belum disetujui): RPO = 24 jam (dump harian; PITR belum ada), RTO = ukur di uji pulih lalu tetapkan. Tanyakan pemilik.

## 4.4 Monitoring (yang sudah berjalan)

`deploy/healthcheck.sh` (cron tiap 5 menit, di prod; alert Discord hanya saat keadaan berubah):
- Kontainer dengan restart `always` / `unless-stopped` harus berjalan; `RestartCount` > 3 dicatat sebagai masalah (`healthcheck.sh:24-33`).
- Endpoint: API `/health` 200, `/ready` 200, web 200, `/api/v1/auth/me` 401 (`:37-40`).
- API bisa menjangkau MinIO (`:43`).
- Disk `/` >= 80% (`:49`). RAM tersedia < 400 MB (`:51`). Swap terpakai >= 60% (`:55-56`).
- Umur backup lokal dan offsite < 26 jam (`:62-64`).
- Kontainer yang sengaja mati: masukkan namanya di `healthcheck.skip` (`:6`).

Uptime Kuma (`deploy/uptime-kuma.compose.yml`): hanya dapat dibuka dari server atau Tailscale (`100.117.92.14:3001`). Monitor yang disarankan di komentar (interval 60 dtk): `/health`, `/ready`, web `:8080/`, `:8080/api/v1/auth/me` (401). Image `louislam/uptime-kuma:1`. Status monitor yang aktif TIDAK DIKETAHUI dari repo.

Log:
- Log deploy: `~/deploy/vms-mvp/logs/deploy-*.log`, `cron.log`, `healthcheck.log`, `backup.log`, `offsite.log` (`deploy/README.md`, `deploy/beta/pasang-beta.sh:97`, `deploy/healthcheck.sh:4`).
- Log kontainer: driver `json-file`, 10 MB x 3 file (`deploy/compose.limits.yml:13-15`). Tanpa rotasi, log menghabiskan disk.
- Log JSON dan request ID di API: menurut riset `01` (baris 681) ada di `api/app/core/logging_config.py`. TIDAK DIVERIFIKASI di sesi ini (tidak dibaca).

Yang belum ada (riset F-20, `docs/PANDUAN-AGENTIK.md` 4.6):
- `duration_ms` dan metrik RED/USE. Target bertahap yang disepakati dokumen: log akses lengkap tanpa data pribadi -> metrik RED bila anggaran memungkinkan -> tracing (perlu ADR; ditunda).
- Panduan (`vms-next/docs/panduan/panduan-fullstack.txt` baris 1610-1627) menyarankan JSON log dengan trace_id, metrik RED (Prometheus/Grafana), dan jangan mencatat PII/token. Di 4 GB RAM, Prometheus + Grafana + Loki bersama aplikasi tidak realistis tanpa ukuran. Usulan: mulai dari log dan Uptime Kuma. Keputusan pemilik.

## 4.5 Pemeliharaan

- Pembaruan OS: `deploy/hardening-server.sh` mengatur pembaruan otomatis (perlu sudo; dijalankan pemilik). Status di server: TIDAK DIKETAHUI.
- Docker prune. Yang AMAN: `docker image prune -f` (hanya image dangling; dipakai autodeploy, `autodeploy.sh` sekitar baris 281). Image dengan tag `:rollback` bukan dangling, jadi aman.
- Yang DILARANG tanpa perintah pemilik: `docker system prune -a` (menghapus image tanpa kontainer, termasuk tag rollback), `docker volume prune` dan `docker volume rm` (menghapus data DB atau MinIO), `docker compose down -v`.
- Disk: `df -h /` dan `du -sh ~/deploy/*/backups`. Ambang alarm 80% (`healthcheck.sh:49`). Log json-file sudah dibatasi.
- Pembaruan image dasar: pin digest lalu perbarui lewat Dependabot `package-ecosystem: docker` (rekomendasi Docker Build best practices). Belum ada `dependabot.yml` untuk docker: periksa `.github/dependabot.yml` (TIDAK DIVERIFIKASI).
- Setiap kuartal: tinjau daftar workflow (`gh workflow list -a`), ACL Tailscale, daftar Funnel, dan isi `healthcheck.skip`.

## 4.6 Runbook insiden (cepat)

Prinsip: lihat dulu, ubah belakangan. Jangan menjalankan perintah yang mengubah server tanpa perintah pemilik (`devops-engineer.md`). Semua langkah di bawah dijalankan pemilik di server.

| Gejala | Langkah pertama | Lanjut | Jangan |
|---|---|---|---|
| Deploy GAGAL (Discord merah) | Baca kode keluar dan log (`02-autodeploy-dan-ci.md` 2.3). | Perbaiki penyebab, tunggu deploy berikutnya atau hapus `.last-deployed`. | Hapus volume; mengabaikan kode 15 (migrasi) dengan menjalankan ulang tanpa cek. |
| Prod down (`/ready` 503 atau 000) | `docker ps -a --filter name=vms`, `docker logs vms_api --tail 100`. | Bila DB: cek `vms_db_prod` health; bila MinIO: lihat di bawah. Rollback manual bila perlu (2.4). | Restart DB berkali-kali tanpa membaca log. |
| DB penuh / disk penuh | `df -h /`, ukuran volume DB, jumlah `backups/*.dump`. | Hapus dump lokal lama yang sudah ada di MinIO dan offsite (oleh pemilik). Kurangi log. | `volume prune`; hapus volume DB. |
| MinIO mati | `healthcheck` akan melapor "API tidak bisa menjangkau MinIO". Cek `vms_minio_prod`. | Pulihkan kontainer (`restart: always`). Deploy akan gagal kode 18 dan rollback otomatis bila kontainer baru gagal. | Biarkan autodeploy berulang: insiden 2026-10-23..28, ±650 deploy per hari saat MinIO mati (`autodeploy.sh:76-77`). Anti-loop `.last-failed` sudah dipasang; pastikan jalan. |
| Swap tinggi (>= 60%) | `docker stats --no-stream`, `free -m`. | Batasi beta dulu: hentikan `vms_beta_face` bila tidak dipakai, dan catat namanya di `healthcheck.skip` agar tidak memicu alarm. Lalu cek batas di `compose.limits.yml`. | Restart prod serampangan; menaikkan batas tanpa mengukur. |
| Tailscale Funnel tak sengaja aktif | `tailscale funnel status`. | Matikan layanan publik yang tidak diinginkan (perintah `off` pada port itu; sintaks dicek ke `tailscale funnel --help` dulu, TIDAK DIVERIFIKASI). | Mengubah ACL tanpa catatan. |
| Backup gagal | Baca `logs/backup.log` dan petunjuk kredensial MinIO dari `backup.sh`. | Perbaiki `api.env` (nama variabel saja), `up -d --force-recreate api`, lalu `./backup.sh uji`. | Mencetak nilai kredensial ke chat. |
| Uptime Kuma tidak bisa dibuka | `docker ps` untuk `vms_uptime_kuma`; cek `100.117.92.14` dari tailnet. | Nyalakan ulang kontainer. | Membuka port baru. |

Setelah insiden: catat di runbook (tanggal, gejala, sebab, langkah, siapa), dan usulkan perubahan skill bila aturan ternyata kurang (`.claude/skills/README.md` bagian 6).

## 4.7 Runbook yang belum ada di repo

Repo merujuk `docs/RUNBOOK-PRODUKSI.md` dan `docs/RUNBOOK-CI.md`, tetapi berkasnya TIDAK ADA di `docs/` (hanya `PANDUAN-AGENTIK.md`, dicek `ls docs`). Sumber alternatifnya `vms-next/docs/` (TIDAK DIPERIKSA di sesi ini). Jangan mengarang isi runbook itu; tanyakan pemilik lokasinya.
