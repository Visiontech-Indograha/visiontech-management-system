# Deploy otomatis ke server (R-20)

Alur: kerjakan di `development` → Pull Request `development` → `prod` → setelah merge, dalam ±1 menit
server membangun & memasang versi baru, lalu melapor ke Discord `#vms-deploy`:
🚀 mulai (commit, pengubah, daftar perubahan) · ✅ berhasil (durasi, migrasi, versi DB, kesehatan, backup)
· 🔴 gagal (tahap yang gagal + 25 baris akhir log). Log build **lengkap** selalu terlampir.

Server (`~/deploy/vms-mvp`): `autodeploy.sh` dijalankan cron tiap menit (dengan kunci `flock`).
Urutan: checkout → `docker compose build` → backup DB (14 terakhir disimpan di `backups/`) →
`up -d` → `alembic upgrade head` → cek `/health` (api) dan `/` (web).

Berkas rahasia di server (tidak di Git, chmod 600): `api.env`, `notify.env` (`DISCORD_WEBHOOK_DEPLOY`).
Akses baca repo: deploy key `~/.ssh/vms_deploy` (alias SSH `github-vms`), hanya-baca.

Log: `~/deploy/vms-mvp/logs/deploy-*.log`, `logs/cron.log`.
Memaksa deploy ulang versi yang sama: `rm ~/deploy/vms-mvp/.last-deployed` (deploy berikutnya ≤ 1 menit).
