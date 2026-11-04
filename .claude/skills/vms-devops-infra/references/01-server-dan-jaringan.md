# 01 · Server, tata letak, dan jaringan

Sumber utama: `deploy/README.md`, `deploy/tutup-port-*.sh`, `deploy/beta/pasang-beta.sh`, `deploy/hardening-server.sh`, `docs/08` bagian Server (`vms-next/docs/08-KEADAAN-VMS-SAAT-INI.md`, baris 32-37). Status per 2026-11-04. Akses server TIDAK dilakukan dari sesi ini; semua fakta di bawah dari repo dan dokumen.

## 1.1 Tata letak

| Hal | Prod | Beta | Sumber |
|---|---|---|---|
| Folder kerja di server | `~/deploy/vms-mvp` | `~/deploy/vms-beta` | `deploy/autodeploy.sh:10` (`VMS_DEPLOY_DIR`), `deploy/beta/pasang-beta.sh` |
| Cabang sumber | `prod` | `beta` | `deploy/autodeploy.sh:11` (`BRANCH`, bawaan `prod`) |
| Klon repo | `<base>/src/` | sama | `deploy/autodeploy.sh:32-35` |
| Kontainer API / web | `vms_api` :8000 / `vms_web` :8080 | `vms_beta_api` :8001 / `vms_beta_web` :8081 | `docs/08` baris 35; `deploy/beta/compose.yml:10,22` |
| Face | `vms_face` (tanpa port publik) | `vms_beta_face` (`mem_limit` 1200m) | `docs/08`; `deploy/beta/compose.yml:31,33` |
| DB | `vms_db_prod` (host :5433) | `vms_db_beta` (127.0.0.1:5435) | `docs/08`; `deploy/beta/compose.infra.yml:7,12` |
| MinIO | `vms_minio_prod` (:9000/9001) | `vms_minio_beta` (127.0.0.1:9002/9003) | `deploy/beta/compose.infra.yml:23,29` |
| Monitor | `vms_uptime_kuma` (100.117.92.14:3001) | - | `deploy/uptime-kuma.compose.yml:14,17` |
| Database yang dipakai API | `vms_v2` | `vms_beta` | `docs/08` baris 38 |
| Role aplikasi | Target `vms_api` (migrasi `0024_runtime_role`); pemindahan dilakukan pemilik lewat `deploy/pakai-peran-runtime.sh`. TIDAK YAKIN sudah dijalankan. | `vms_app` (tidak diketahui) | `deploy/README.md` bagian "Peran runtime"; `docs/08` baris 38 menulis `vms_app` |

Catatan:
- Server disebut `visiontech-bar`, Tailscale 100.117.92.14, RAM 4 GB, 2 CPU (`docs/08` baris 32; `deploy/compose.limits.yml:2`). Tidak yakin apakah 2 CPU masih berlaku.
- Compose prod TIDAK ada di repo. `deploy/README.md` menyebut `~/deploy/vms-mvp/compose.yml`, tetapi `deploy/tutup-port-db.sh:6` menyebut `~/deploy/visiontech/docker-compose.prod.yml`. TIDAK YAKIN lokasi mana yang benar. Verifikasi sendiri di server (pemilik).

## 1.2 Siapa boleh menyentuh server

- Sesi agen TIDAK SSH ke server. Perintah ke server hanya dijalankan pemilik, dari komputernya (pola: `ssh ageng@<ip> "bash -s" < deploy/<skrip>.sh`, lihat `deploy/README.md`).
- Alamat LAN yang tertulis di repo: `192.168.88.160` (`deploy/README.md`). Tidak perlu disalin ke tempat lain.
- Deploy key baca-saja: `~/.ssh/vms_deploy` (alias `github-vms`), sudah terdaftar di repo sebagai `vms-server-deploy` (`deploy/README.md` "Repo & akses").

## 1.3 Jalur akses publik (inventaris, bukan daftar setuju)

| Jalur | Apa | Bukti | Status |
|---|---|---|---|
| Cloudflare Tunnel | web prod ke `localhost:8080`; domain `portal.visiontechindo.com` | `deploy/tutup-port-layanan.sh:3`; `deploy/README.md:98` | Publik. TIDAK YAKIN konfigurasi tunnel (tidak ada di repo). |
| Tailscale Serve | web beta khusus tailnet `:8444` -> `127.0.0.1:8081` | `deploy/beta/pasang-beta.sh:89-91` | Hanya tailnet (ACL berlaku). |
| Tailscale Funnel | API beta publik `:10000` -> `127.0.0.1:8001` | `deploy/beta/pasang-beta.sh:92-93` (komentar: "API beta publik untuk HP") | PUBLIK, disengaja untuk HP beta. Perlu dicatat di ADR. |
| Tailscale Serve TCP | DB dan MinIO ke tailnet (5433, 5435, 9000, 9002, 9003) | `docs/08` baris 36 | Hanya tailnet menurut dokumen. Perintah `--tcp` TIDAK ada di repo; TIDAK YAKIN. |
| Docker publish | `docker-compose.yml:33` memublikasikan `5433:5432` tanpa `127.0.0.1` | file itu (dev) | Lihat anti-pola A-3. |

Aturan yang dipakai di repo: API diikat ke `127.0.0.1` dan gerbang Docker `172.17.0.1` agar Uptime Kuma tetap bisa menjangkau (`deploy/tutup-port-layanan.sh:2-5`). DB ke `127.0.0.1` (`deploy/tutup-port-db.sh:2`).

## 1.4 Tailscale: ACL yang masih perlu dicek

Dokumen Tailscale: Serve hanya tailnet, Funnel publik, dan satu port tidak bisa dipakai keduanya sekaligus (lihat Tailscale KB, diakses 2026-11-04, https://tailscale.com/kb/1312/serve). Akses dibatasi lewat ACL (https://tailscale.com/kb/1018/acls, belum dibuka di sesi ini).

Daftar yang perlu diperiksa pemilik di konsol Tailscale (tidak bisa dilihat dari repo):
1. ACL: siapa boleh menjangkau port DB (5433, 5435), MinIO (9000, 9002, 9003), dan Uptime Kuma (3001). Perangkat mana saja yang ada di tailnet.
2. Funnel: daftar layanan publik yang aktif (`tailscale funnel status`). Pastikan hanya 10000 (beta API) yang publik.
3. Tag perangkat server, dan kunci perangkat yang tidak dipakai dihapus.
4. `hardening-server.sh:69` mengizinkan SEMUA lalu lintas dari `tailscale0`. Itu berarti ACL tailnet adalah satu-satunya pagar untuk layanan tailnet.

## 1.5 Firewall dan SSH

- `deploy/hardening-server.sh` (jalan dengan sudo, dijalankan pemilik): mode `--cek` (aman) dan `--ya` (menerapkan). Mengatur sshd drop-in `/etc/ssh/sshd_config.d/99-vms-hardening.conf` (PermitRootLogin no, PasswordAuthentication no, `hardening-server.sh:14-16`).
- Aturan ufw: tolak masuk kecuali SSH, web, dan Tailscale (`hardening-server.sh:61`, `:69`).
- Peringatan dari skrip sendiri: port yang dipublikasikan Docker (`-p`) MELEWATI ufw. Ikat ke `127.0.0.1` di compose (`hardening-server.sh:6`).
- Sebelum `--ya`: buka sesi SSH kedua dan jangan tutup sebelum login kunci dari sesi baru berhasil (`hardening-server.sh:5`).
- Status penerapan di server TIDAK DIKETAHUI dari repo. Jalankan `--cek` oleh pemilik dan catat hasilnya di runbook.
