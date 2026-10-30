# Runbook CI — runner self-hosted (PC Windows 11)

Latar: akun GitHub gagal membayar menit runner tersedia (2026-10), sehingga job `ubuntu-latest` tidak
berjalan. Job CI (`.github/workflows/ci.yml`) kini memakai runner di PC ini dengan label
`self-hosted, linux, vms`.

## Arsitektur

- Runner berjalan sebagai container Docker `vms-runner` (image `vms-runner:2.338.2`, dibangun dari
  `C:/actions-runner/Dockerfile`: Ubuntu 24.04 + runner resmi `actions/runner` v2.338.2, SHA-256 dicek).
- Nama runner di GitHub: `vms-pc`. Label: `self-hosted,linux,vms`.
- Socket Docker Desktop dipasang (`/var/run/docker.sock`) agar job bisa `docker build`/`docker run`
  (service PostgreSQL CI, container `vms-db`, port 5432).
- `--network host`: `localhost:5432` dari job menjangkau container DB yang dipublikasikan.
- `--restart unless-stopped`: container otomatis hidup lagi setelah Docker Desktop berjalan.
- Container berjalan sebagai root (`RUNNER_ALLOW_RUNASROOT=1`) karena akses ke socket Docker. Ini setara
  hak admin atas Docker Desktop di PC ini — pertahankan repo PRIVAT dan jangan izinkan workflow dari fork.

Pembatasan: satu runner = satu job sekaligus (antre). Ini aman untuk port 5432 dan nama container
`vms-db`. Tes lokal memakai `vms-test-db` (:55432) dan `vms-dev-db` (:55433), tidak bentrok.

## Setelah reboot PC

1. Pastikan Docker Desktop berjalan (opsi "Start Docker Desktop when you sign in" aktif).
2. Periksa: `docker ps --filter name=vms-runner` — status `Up`.
3. Bila tidak jalan: `docker start vms-runner`.
4. Periksa di GitHub: `gh api repos/Visiontech-Indograha/visiontech-management-system/actions/runners --jq '.runners[].status'` → `online`.

Tidak perlu Task Scheduler; restart policy Docker sudah menangani.

## Bila container hilang (`docker rm`, image diganti, atau runner dihapus di GitHub)

Pendaftaran ulang memakai token sekali pakai (kedaluwarsa 1 jam). Jangan cetak token ke log:

```bash
S=<folder-sementara-aman>   # bukan folder repo
umask 077
gh api -X POST repos/Visiontech-Indograha/visiontech-management-system/actions/runners/registration-token \
  --jq '"RUNNER_TOKEN=" + .token' > "$S/runner.env"
docker rm -f vms-runner 2>/dev/null
docker run -d --name vms-runner --restart unless-stopped --network host \
  -v //var/run/docker.sock:/var/run/docker.sock --env-file "$S/runner.env" vms-runner:2.338.2
rm -f "$S/runner.env"
```

Bila image belum ada: `cd C:/actions-runner && docker build -t vms-runner:2.338.2 .`

## Memperbarui runner

Ubah `RUNNER_VERSION` dan `RUNNER_SHA256` di `C:/actions-runner/Dockerfile` (ambil digest dari rilis
resmi `actions/runner`), bangun ulang image, lalu daftarkan ulang seperti di atas.

## Memeriksa / menghentikan

- Log: `docker logs --tail 50 vms-runner`
- Berhenti sementara: `docker stop vms-runner` (job CI antre sampai dijalankan lagi).
- Pembersihan sisa DB: `docker rm -f vms-db` (job juga melakukannya di awal dan akhir).

## Di luar cakupan

Workflow rilis/deploy (`apk.yml`, `cd.yml`, `images.yml`, `rilis.yml`) masih `ubuntu-latest` dan
belum dipindah ke runner ini.
