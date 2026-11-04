# Runbook: beta aman (API tailnet saja, data beta sintetis)

Dibuat dari PR `fix/beta-aman`. Semua langkah dijalankan PEMILIK dari komputernya. Agen tidak mengakses server.
Pola perintah ke server: `ssh ageng@192.168.88.160 "bash -s" < deploy/...` (sama seperti `deploy/README.md`).

## Yang berubah di repo

| Berkas | Sebelum | Sesudah |
|---|---|---|
| `deploy/beta/pasang-beta.sh` (Tailscale) | Funnel `:10000` (publik) ke API beta | Funnel 10000 dimatikan; Serve `:10000` (tailnet saja) |
| `deploy/beta/pasang-beta.sh` (`data`) | `pg_dump` DB prod ke beta | Seed sintetis `db/07_master_seed_v2.sql` (hanya bila beta belum berisi karyawan) |
| `deploy/beta/pasang-beta.sh` (`berkas`) | Salin semua bucket MinIO prod ke beta | Dinonaktifkan (exit 2) |
| `deploy/compose.limits.yml` (face) | 768m | 1200m (nilai yang sudah terpasang) |
| `deploy/README.md`, `.claude/skills/vms-devops-infra/*` | dokumen tidak cocok dengan kode | diperbaiki |

Tidak berubah: `.github/workflows/*` (termasuk `apk.yml`), `autodeploy.sh`, `backup.sh`, skema dan migrasi.

## Dampak ke APK dan CI

- **APK beta** (`apk.yml:73`) memakai `https://visiontech-bar.tail827174.ts.net:10000`. URL ini TIDAK diubah, tetapi sekarang
  HANYA bisa dijangkau HP yang Tailscale-nya aktif dan sudah masuk tailnet (dan lolos ACL). HP beta di luar tailnet
  tidak bisa login, dan foto/tautan berkas beta (`MINIO_PUBLIC_URL`, `PUBLIC_VERIFY_URL` = URL yang sama) juga tidak terbuka.
  Harus dikomunikasikan ke penguji beta sebelum langkah 1.
- **APK prod** dan `portal.visiontechindo.com`: tidak terdampak.
- **CI**: tidak berubah. Tes arsitektur `api/tests/architecture/test_deploy_scripts.py` memeriksa `bash -n` semua `deploy/*.sh`.
- **Workflow yang sudah dibuat ulang**: tidak ada.

## Langkah pemilik (urutan)

### 0. Catat keadaan sekarang (read-only)

```bash
ssh ageng@192.168.88.160 "tailscale funnel status; echo ---; tailscale serve status"
```

Simpan keluarannya (tanpa rahasia). Bila `funnel status` memuat `:10000`, API beta sedang PUBLIK.

### 1. Matikan Funnel 10000 sekarang (mendesak, tidak menunggu merge)

Cek sintaks dulu, karena `off` belum diverifikasi di repo:

```bash
ssh ageng@192.168.88.160 "tailscale funnel --help | head -n 30"
ssh ageng@192.168.88.160 "sudo tailscale funnel --https=10000 off; tailscale funnel status"
```

Verifikasi dari HP atau jaringan di luar tailnet (data seluler, Tailscale MATI). Hasilnya harus GAGAL / timeout:

```bash
curl -sS -m 10 https://visiontech-bar.tail827174.ts.net:10000/health
```

Pastikan `tailscale funnel status` tidak menampilkan layanan apa pun.

### 2. Terapkan skrip baru (setelah PR masuk `beta` dan autodeploy beta berjalan)

Merge ke `beta` adalah keputusan pemilik. Setelah itu, jalankan skrip (idempoten; cron dan kredensial tidak ditimpa):

```bash
ssh ageng@192.168.88.160 "bash -s siapkan" < deploy/beta/pasang-beta.sh
```

Catatan: `siapkan` mengambil `src/` cabang `beta` terbaru dan menjalankan `up -d` untuk infra beta.

### 3. Verifikasi jalur tailnet

```bash
ssh ageng@192.168.88.160 "tailscale serve status; echo ---; tailscale funnel status"
```

- `serve status` memuat `:8444` (web beta) dan `:10000` (API beta) saja.
- `funnel status` kosong.
- Dari HP yang sudah di tailnet: `curl -sS https://visiontech-bar.tail827174.ts.net:10000/health` harus 200.

### 4. Periksa apakah beta pernah menerima data prod (WAJIB)

Skrip lama (`data` dan `berkas`) pernah menyalin dump prod dan berkas MinIO prod ke beta. Anggap data itu sudah ada di beta sampai dibuktikan sebaliknya.

```bash
ssh ageng@192.168.88.160 "docker exec vms_db_beta psql -U vms_app -d vms_beta -Atc 'select count(*) from employee'"
ssh ageng@192.168.88.160 "ls -la ~/deploy/vms-beta/backups/ | tail -n 25"
```

Jika jumlah karyawan > 0 dan data itu berasal dari prod, lanjut ke langkah 5 (pembersihan). Jangan memakai data itu untuk uji.

### 5. Pembersihan data prod di beta (keputusan pemilik; cadangkan dulu)

Pembersihan ini menghapus data beta, termasuk cadangan lama yang berisi data prod. Lakukan HANYA setelah pemilik setuju.

a. Cadangkan keadaan beta saat ini (untuk audit, lalu disimpan di luar server atau dihapus setelah pembersihan):
   `ssh ... "cd ~/deploy/vms-beta && ./backup.sh manual-sebelum-bersih"` (lihat `backup.sh` untuk argumen label yang dipakai).
b. Hentikan API dan web beta, kosongkan database beta, lalu pasang ulang dari sumber sintetis:
   ```bash
   ssh ageng@192.168.88.160 "cd ~/deploy/vms-beta && docker stop vms_beta_api vms_beta_web"
   ssh ageng@192.168.88.160 "docker exec vms_db_beta psql -U vms_app -d postgres -q -c 'DROP DATABASE vms_beta' -c 'CREATE DATABASE vms_beta'"
   ssh ageng@192.168.88.160 "bash -s siapkan" < deploy/beta/pasang-beta.sh   # skema 06 + 08 (tabel employee belum ada)
   ssh ageng@192.168.88.160 "cd ~/deploy/vms-beta && docker compose run --rm --no-deps api python -m alembic upgrade head"
   ssh ageng@192.168.88.160 "bash -s data" < deploy/beta/pasang-beta.sh      # seed 07 (sintetis), setelah migrasi
   ssh ageng@192.168.88.160 "cd ~/deploy/vms-beta && docker start vms_beta_api vms_beta_web"
   ```
   Urutan ini mengikuti CI (`06` → `08` → `alembic upgrade head`), lalu seed `07` di atas skema terbaru. JANGAN `stamp`:
   `alembic_version` hilang saat DB dibuat ulang, dan autodeploy berikutnya menjalankan `alembic upgrade head` (galat kode 15 bila
   tidak sinkron). Dengan urutan ini `alembic_version` terbentuk dari migrasi. Urutan `07` terhadap migrasi TIDAK DIVERIFIKASI
   (`db/README.md` menyebut 07 opsional; skill `vms-db` menulis 06, 08, 07, alembic). Jika seed gagal, perbaiki seed.
   PERHATIAN: akun beta hasil salinan prod memakai hash sandi prod. Setelah pembersihan, akun beta hanya dari seed.
c. Kosongkan bucket berkas beta `vms-files` dan `vms-bucket` di `vms_minio_beta` (salinan foto dan dokumen prod). Pemilik memilih
   cara (konsol MinIO lewat tailnet, atau klien MinIO dengan kredensial beta dari `infra.env`, tanpa mencetak nilainya).
d. Hapus dump beta lama di `~/deploy/vms-beta/backups/` dan bucket `vms-backups` di MinIO beta bila memuat data prod. Cadangan beta
   berikutnya hanya berisi data sintetis.

### 6. Verifikasi akhir

- `docker exec vms_db_beta psql -U vms_app -d vms_beta -Atc 'select count(*) from employee'` menghasilkan 9 (8 karyawan dan 1 karyawan offboarding, sesuai komentar `db/07`).
- `curl -sS https://visiontech-bar.tail827174.ts.net:10000/ready` dari tailnet: 200.
- Log: `~/deploy/vms-beta/logs/cron.log` dan `self-update.log` tidak menampilkan galat berulang.

## Rollback

- Mengembalikan jalur tailnet ke kondisi "tanpa Serve 10000": `sudo tailscale serve --https=10000 off`. API beta menjadi tidak terjangkau
  dari tailnet. Ini tidak membuka publik.
- Mengembalikan skrip ke versi sebelumnya: revert PR di `beta` (keputusan pemilik), lalu autodeploy beta mengambil skrip terbaru
  dan `self-update` menyimpan salinan lama di `~/deploy/vms-beta/autodeploy.sh.sebelum`.
- MEMBUKA KEMBALI Funnel (publik) TIDAK dianjurkan dan tidak ada langkah di runbook ini. Bila pemilik tetap memerlukannya,
  itu keputusan tertulis baru.
- Pembersihan langkah 5 tidak bisa dibatalkan kecuali ada cadangan dari langkah 5a.

## Pertanyaan untuk pemilik

1. Apakah HP beta (penguji) bisa memakai Tailscale? Bila tidak, perlu jalur lain. Jalur publik untuk beta tidak dibuat di PR ini.
2. Batas memori face: 1200m (sekarang) atau 768m. Pengukuran 482 MB (2026-10-28) belum mencakup beban puncak. Ukur `docker stats` dulu.
3. Apakah `api.env` beta (disalin dari templat prod, hanya kunci koneksi yang diganti) masih memuat kunci lain dari prod (mis. webhook, SMTP). Periksa nama variabelnya saja.
4. Akun seed `db/07` memakai `password_hash` yang sudah ada di repo. Pastikan hash itu bukan sandi yang dipakai di luar uji.
