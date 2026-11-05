# 03 · Image Docker, Compose, dan rahasia

Sumber: `api/Dockerfile`, `face-service/Dockerfile`, `db/Dockerfile`, `web/.dockerignore`, `face-service/.dockerignore`, `docker-compose.yml`, `deploy/compose.limits.yml`, `deploy/beta/compose*.yml`, `deploy/uptime-kuma.compose.yml`, `deploy/pasang-face-service.sh`, `.gitleaksignore`, `.githooks/pre-commit`. Praktik resmi: Docker Build best practices (https://docs.docker.com/build/building/best-practices/, diakses 2026-11-04); Compose services (https://docs.docker.com/reference/compose-file/services/, diakses 2026-11-04). Ringkasan pin digest dan .dockerignore dari halaman pertama.

## 3.1 Status image per layanan (diperiksa dari repo, 2026-11-04)

| Hal | `api/Dockerfile` | `face-service/Dockerfile` | `db/Dockerfile` | `web/Dockerfile` |
|---|---|---|---|---|
| Base image | `python:3.12-slim` (baris 1), tag saja, tanpa digest | sama (baris 2) | `postgis/postgis:18-3.6` (baris 10), tag saja | ada, belum diperiksa rinci |
| Multi-stage | TIDAK (satu tahap) | TIDAK | - | belum diperiksa |
| Non-root (`USER`) | TIDAK ada | ADA: `USER face` (baris 24) | - | belum diperiksa |
| HEALTHCHECK | TIDAK ada | ADA (baris 32-33) | - | belum diperiksa |
| `.dockerignore` | TIDAK ada di `api/` (dicek dengan test -f) | ADA (`face-service/.dockerignore`) | - | ADA (`web/.dockerignore`, memuat `.env`, `.env.*`, `!.env.example`) |
| Salin seluruh konteks | `COPY . .` (baris 27) | salin file tertentu | - | - |
| Metadata label | ADA (baris 29-32) | ADA | - | - |

Konsekuensi untuk `api`:
- Tanpa `.dockerignore`, `COPY . .` ikut menyalin apa pun di folder `api/` yang tidak diabaikan Git. `.gitignore` TIDAK dipakai Docker. Riset F-01 (`riset-best-practice/01-PDF-DAN-AUDIT-VMS.md` baris 385-394) menyebut `api/.env` dan `api/uploads/` (364 berkas, sekitar 234 MB). Pada worktree ini `api/.env` TIDAK ADA (dicek nama saja), dan `api/uploads/` hanya berisi `.gitkeep` (`git ls-files`). Jadi temuan F-01 untuk `.env` sudah tidak terbukti di worktree ini; TIDAK YAKIN untuk checkout lokal pemilik, karena riset dibuat dari sana.
- Tanpa USER, proses berjalan root di dalam kontainer (F-02, riset baris 396-399). Belum diperbaiki.
- Tanpa HEALTHCHECK, Docker tidak tahu kontainer sehat. Pemeriksaan sebenarnya ada di `autodeploy.sh` dan `healthcheck.sh`. Compose healthcheck untuk API tidak ada di `docker-compose.yml` (hanya untuk db).
- Image API memasang LibreOffice dan font (`api/Dockerfile` baris 13-20) untuk pratinjau laporan. Ukurannya besar. Pertimbangkan pemisahan tahap (builder untuk pip, runtime untuk LibreOffice tetap ada), dan uji dulu karena pratinjau memakainya.

## 3.2 Rekomendasi (belum diterapkan; ubah lewat brief arsitek)

Bentuk yang disarankan untuk `api` (contoh, bukan perintah):
```
FROM python:3.12-slim@sha256:<digest> AS base   # pin digest; perbarui lewat Dependabot docker
# ... paket apt (LibreOffice, font, libpango) ...
RUN groupadd -g 10001 app && useradd -u 10001 -g app -s /usr/sbin/nologin -M app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER 10001:10001
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Syarat sebelum diterapkan:
- `uploads/` dan path tulis LibreOffice harus bisa ditulis UID 10001. Uji di beta dulu.
- `.dockerignore` untuk `api/`, mencontoh `web/.dockerignore`: `.env`, `.env.*`, `!.env.example`, `uploads/`, `backups/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `tests/`, `.git/`. Pastikan `app/shared/documents/templates/` (template .docx) tidak ikut terabaikan (riset baris 394).
- Tes: `docker build` lalu `docker run --rm <image> ls /app/.env` harus gagal (riset baris 392). Tes ini dijalankan pemilik atau devops; tes DB hanya atas perintah pemilik (tidak relevan di sini).
- Pin tag lain: `postgis/postgis:18-3.6`, `louislam/uptime-kuma:1`, `quay.io/minio/minio:latest` (`deploy/beta/compose.infra.yml:22`, tidak dipin). Pakai digest atau versi tetap; `latest` tidak boleh.

## 3.3 Compose

Berkas di repo:
- `docker-compose.yml`: dev laptop. Baris 1 `version: '3.8'` sudah usang (Compose mengabaikannya; TIDAK YAKIN apakah masih memberi peringatan di versi Compose yang dipakai). Port DB `5433:5432` (baris 33) TIDAK diikat ke `127.0.0.1`. Pola yang benar sudah ada di `deploy/beta/compose.infra.yml:12`: `127.0.0.1:5435:5432`. `${POSTGRES_PASSWORD:?...}` (baris 10, 30) menghentikan compose bila variabel kosong. Pola ini bagus, pertahankan.
- `deploy/compose.limits.yml`: batas memori dan log. Nilai: `api` 768m (baris 11), `web` 128m (17), `face` 768m (21). Log `json-file` max 10m x 3 file. Berkas ini disalin manual ke `compose.override.yml` di server (instruksi di baris 4-7).
- Konflik batas face: `deploy/pasang-face-service.sh:57` memakai `mem_limit: 1200m`, dan `deploy/beta/compose.yml:33` juga 1200m. `compose.limits.yml` 768m. Pemilik perlu memutuskan; catat sebagai anomali A-5.
- Restart: `unless-stopped` di compose limits dan beta. Dokumen Compose: `unless-stopped` tidak menyalakan ulang bila kontainer dihentikan manual (https://docs.docker.com/reference/compose-file/services/#restart, diakses 2026-11-04). Akibatnya setelah reboot host, kontainer yang dihentikan manual tidak naik lagi. Wajar, tetapi catat saat insiden.
- `mem_limit` didokumentasikan sebagai setara dengan `deploy.resources.limits.memory`; keduanya tidak boleh berbeda (Compose services reference, diakses 2026-11-04).

Batas memori untuk 4 GB (`docs/08` baris 47 dan utang tenggat baris 110: "container beta tanpa batas memori"):
- Jumlah batas yang ada di compose limits: api 768m + web 128m + face 768m = 1664m untuk prod. Beta: `api` dan `web` belum punya batas, `face` 1200m (`deploy/beta/compose.yml:33`), `db` dan `minio` tidak punya batas di mana pun dalam repo.
- Pengukuran terakhir di dokumen: face prod 482 MB, beta 259 MB, swap 561 MB (`deploy/compose.limits.yml:2`, tanggal 2026-10-28). Swap pernah 86-92% (`docs/08` baris 47).
- Usulan (perlu diukur dulu dengan `docker stats --no-stream` dan dicatat): tambah `mem_limit` untuk `db`, `minio`, dan semua layanan beta. Jangan menurunkan batas sebelum mengukur.

## 3.4 Volume, jaringan, dan port

- Volume bernama yang dipakai: `vms_pgdata18_beta`, `vms_minio_data_beta`, `uptime_kuma_data` (`deploy/beta/compose.infra.yml:33-35`, `deploy/uptime-kuma.compose.yml:27`). Data DB prod tidak ada di repo (volume prod di server). TIDAK YAKIN namanya.
- Volume `postgres18_data` di dev (`docker-compose.yml:44`). Komentar baris 35 menjelaskan volume baru agar data PG16 lama tidak tertimpa. Pelajaran: ganti versi mayor Postgres = volume baru + dump/restore, bukan ganti image di volume lama.
- Jaringan beta: `vms_beta_net` WAJIB terpisah dari prod (`deploy/beta/compose.yml:2-3`). Nama layanan (`api`, `db`, `minio`) bentrok bila jaringan sama.
- Port: `ports:` memublikasikan ke semua antarmuka kecuali diikat. Docker melewati ufw (`deploy/hardening-server.sh:6`). Selalu ikat ke `127.0.0.1` atau ke IP Tailscale.

## 3.5 Rahasia

Daftar tempat rahasia (nama berkas saja; nilai JANGAN ditulis atau dicetak):

| Berkas / tempat | Isi (nama) | Lokasi | Aturan |
|---|---|---|---|
| `api.env` | DATABASE_URL, MIGRATION_DATABASE_URL, MINIO_*, JWT_*, DOC_SIGNING_*, FACE_SERVICE_TOKEN, PUBLIC_VERIFY_URL, MINIO_PUBLIC_URL | server `~/deploy/vms-*` | chmod 600, tidak di Git. Ada di `.gitignore`. |
| `notify.env` | DISCORD_WEBHOOK_DEPLOY, DISCORD_WEBHOOK_BUILD, DISCORD_WEBHOOK_ALERT | server | Webhook = rahasia. Rotasi bila bocor. |
| `infra.env` | POSTGRES_*, MINIO_ROOT_* (beta) | server beta | Dibuat `pasang-beta.sh`. |
| `face.env` | token face-service | server | Dibuat `pasang-face-service.sh`. |
| `offsite.env`, `~/.ssh/vms_offsite` | host dan kunci SSH cadangan luar-server | server | chmod 600; kunci khusus hanya untuk rsync. |
| `~/.ssh/vms_deploy` | deploy key baca-saja ke GitHub | server | Hanya baca. |
| GitHub secrets | `ANDROID_KEYSTORE_B64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `DISCORD_WEBHOOK_CI` | repo settings | Dipakai `apk.yml` dan `ci.yml`. |
| `scripts/akun-uji-lokal.txt` | akun uji | laptop | Tidak ditemukan di `scripts/` pada worktree ini (`docs/PANDUAN-AGENTIK.md` baris 226). Jangan dibaca. |

Catatan: pesan galat di `deploy/backup.sh` (sekitar baris 30-40) menyebut berkas `/home/ageng/deploy/visiontech/.env` sebagai sumber kredensial. Itu jejak dari server lama. Jangan salin nilainya ke mana pun.

Pengamanan yang sudah ada:
- `.gitignore` baris 2-4 mengabaikan `.env`, `.env.*`, dan mengecualikan `.env.example`.
- `.githooks/pre-commit` menolak berkas rahasia yang di-stage (`.githooks/pre-commit:13-18`). Pasang: `bash scripts/pasang-hook.sh`.
- Gitleaks di CI: CLI 8.30.1 dengan checksum (`ci.yml`, sekitar baris 127-131), pindaian commit baru. Berkas pengecualian `.gitleaksignore` berisi 12 baris. Isinya tidak dikutip di sini. Setiap baris pengecualian harus punya alasan dan pemilik. Periksa berkala.

Rotasi rahasia (urutan minimum):
1. Buat nilai baru di luar Git. Jangan di chat atau log.
2. Simpan di berkas server (chmod 600) atau GitHub secrets.
3. Restart layanan yang memakainya (`docker compose up -d --force-recreate api`).
4. Verifikasi dengan `/ready` dan login.
5. Catat tanggal rotasi (bukan nilainya) di runbook.
6. Anggap rahasia bocor bila pernah ada di image yang didorong ke registry (riset F-01 baris 387).

Utang yang sudah tercatat: `JWT_KID=jwt-dev-1` dipakai di produksi (label saja, `docs/08` baris 48 dan 104; usulan tenggat 2026-11-30). Itu rotasi kunci JWT: efeknya semua sesi keluar. Jadwalkan dengan pemilik.

## 3.6 GitHub Actions: rahasia dan izin

Dari GitHub Docs (https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions, diakses 2026-11-04):
- `permissions:` minimal. Di repo: semua workflow sudah `contents: read` di level workflow. `rilis.yml` menaikkan izin ke `contents: write` hanya di job `rilis`; `images.yml` menambah `packages: write` di level workflow (bisa dipersempit ke job push).
- Pin action ke SHA: sudah dilakukan di workflow repo. `sha_pinning_required` masih `false` (cek `gh api .../actions/permissions`). Pertimbangkan mengaktifkan.
- Self-hosted runner: dokumen GitHub memperingatkan agar tidak dipakai di repo publik, dan mesin runner tidak boleh menyimpan kredensial sensitif. Runner di repo ini (`vms-pc`) menjalankan CI untuk PR. Repo privat, tetapi pastikan PR dari fork tidak bisa memicu job di runner ini. TIDAK YAKIN pengaturan "fork pull request" di repo; cek di pengaturan Actions.
- `pull_request_target` dan `workflow_run` tidak dipakai di workflow repo (dicek grep: 0 kecocokan di 5 berkas). Pertahankan.
- OIDC belum dipakai (tidak ada akses cloud). Tidak perlu sekarang.
