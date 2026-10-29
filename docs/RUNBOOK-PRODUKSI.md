# Runbook produksi VMS

Server: `ssh visiontech` (192.168.88.160, Tailscale 100.117.92.14). Folder: `~/deploy/vms-mvp` (prod), `~/deploy/vms-beta` (beta).
Alur deploy lengkap ada di [`deploy/README.md`](../deploy/README.md).

## 1. Cek status (2 menit)
```bash
ssh visiontech 'bash -s -- --cetak' < deploy/healthcheck.sh     # SEHAT / daftar masalah, tanpa mengubah apa pun
ssh visiontech 'docker ps -a --format "{{.Names}}\t{{.Status}}" | sort'
ssh visiontech 'cd ~/deploy/vms-mvp && ls -t logs/deploy-* | head -3'   # deploy terakhir; >1 per 10 menit = loop
ssh visiontech 'cd ~/deploy/vms-mvp && cat .last-deployed .last-failed 2>/dev/null'
```
Normal: `/health` dan `/ready` 200, `localhost:8080/api/v1/auth/me` 401, semua kontainer berkebijakan restart berstatus *Up*.

## 2. Gejala → tindakan
| Gejala | Penyebab umum | Tindakan |
|---|---|---|
| Deploy berulang tiap menit | Tahap gagal (MinIO/DB) sebelum `.last-deployed` tertulis | Baca log deploy terakhir; perbaiki penyebab. `autodeploy.sh` terbaru memberi jeda 15 menit (`.last-failed`) |
| "Tunggu API tersambung ke MinIO" gagal | `vms_minio_prod` mati / tidak terhubung ke jaringan `visiontech_vms_network` | `docker start vms_minio_prod`; bila `docker inspect -f '{{json .NetworkSettings.Networks}}'` kosong: `docker network connect --alias minio visiontech_vms_network vms_minio_prod` |
| `/ready` 503 | DB mati / kredensial | `docker logs vms_db_prod`, `docker logs vms_api` |
| Disk ≥ 80% | Citra/log menumpuk | `docker image prune -f`, `docker builder prune -f`, periksa `logs/` dan `backups/` |
| RAM tipis / swap tinggi | Terlalu banyak layanan (face beta, DB/MinIO uji) | Beta tanpa wajah: `bash scripts/saklar-wajah.sh off ~/deploy/vms-beta/api.env`, restart `vms_beta_api`, lalu `docker stop vms_beta_face` (hemat ±260 MB; nyalakan lagi bila menguji wajah). Hentikan `vms_db_test` / `vms_minio_test` bila tak dipakai. Pasang batas memori: `deploy/compose.limits.yml` |

## 3. Rollback
`autodeploy.sh` mengambil `origin/prod`. Untuk kembali ke versi sebelumnya: di GitHub **revert** merge PR bermasalah pada `prod` (PR baru `prod`), tunggu deploy otomatis. Jangan `git reset` di `src/` server.
Pulihkan DB: `deploy/uji-pulih-cadangan.sh` (latihan, tidak menyentuh prod) lalu ikuti perintah `pg_restore` yang dicetaknya terhadap salinan terbaru di `backups/` atau salinan luar-server.

## 4. Backup
- Harian 01:30: `backup.sh` → `backups/*.dump` (7 terakhir) + unggah MinIO `vms-backups`.
- Luar-server: `deploy/backup-offsite.sh` (rsync via Tailscale; konfigurasi `offsite.env`, lihat komentar di skrip). Tanpa ini tidak ada salinan di luar server.
  Pasang dua fase: `bash siapkan-offsite.sh siapkan <user@host> <folder>` (buat kunci + `offsite.env`, cetak baris kunci untuk mesin tujuan), lalu `bash siapkan-offsite.sh pasang` (uji kering, salin nyata, cron 01:45).
- `healthcheck.sh` memberi alert Discord bila backup lokal/luar-server > 26 jam.

## 5. Pemeliharaan rutin
- **Mingguan:** tinjau PR dependabot; `docker image prune -f`; jalankan `deploy/uji-pulih-cadangan.sh`.
- **Bulanan:** tinjau `~/.ssh/authorized_keys` (cabut yang tak dikenal), `sudo bash deploy/hardening-server.sh --cek`, ukuran `backups/` dan disk, pembaruan keamanan OS (`unattended-upgrades`).
- **Kuartalan:** latihan pulih penuh ke mesin kosong; rotasi kunci deploy dan kredensial MinIO/DB.

## 6. Kontak/rujukan
Webhook Discord ada di `notify.env` (`DISCORD_WEBHOOK_DEPLOY`, opsional `DISCORD_WEBHOOK_ALERT` untuk healthcheck). Rahasia (`*.env`) berizin 600 dan tidak di Git.

## 7. Menutup port DB ke localhost
`bash ~/deploy/vms-mvp/src/deploy/tutup-port-db.sh --cek` lalu `--ya` (jam sepi; DB restart beberapa detik). Mengikat `5433` ke `127.0.0.1`; aplikasi, backup, dan deploy tidak terpengaruh. Pulihkan dengan berkas `docker-compose.prod.yml.bak-*` yang dicetak skrip.

## 8. Menutup port API dan MinIO ke localhost
`bash ~/deploy/vms-mvp/src/deploy/tutup-port-layanan.sh --cek` lalu `--ya` (jam sepi). Dasar keamanannya: Cloudflare Tunnel hanya ke `localhost:8080`; Tailscale Serve/Funnel hanya ke `127.0.0.1`. API tetap terikat ke gerbang Docker agar monitor Kuma (`host.docker.internal`) hijau.
