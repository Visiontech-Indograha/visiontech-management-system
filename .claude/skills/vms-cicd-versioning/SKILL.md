---
name: vms-cicd-versioning
description: Alur cabang, workflow GitHub Actions, gerbang kualitas per tahap, deploy dan rollback server, build APK per lingkungan, rahasia, versi SemVer, rilis, dan perbaikan CI yang rusak untuk VMS. Pakai saat membuat PR, merge ke beta atau prod, menaikkan versi, menyiapkan rilis, membangun APK, atau memperbaiki CI yang gagal.
---

# vms-cicd-versioning - CI/CD, rilis, dan versi VMS

Sumber fakta: `.github/workflows/*.yml`, `deploy/autodeploy.sh`, `deploy/README.md`, `scripts/versi.sh`, `scripts/rilis-apk.sh`, `.githooks/pre-commit`, `CHANGELOG.md`. Repo sumber: `integrasi/uji-ulang` (HEAD d8a12df5). Isi workflow identik di cabang `beta` (d1a3d4e5).

## 1. Cabang

```
feature/<nama> ──PR──▶ development ──merge──▶ beta ──PR (CI)──▶ prod
                                                     │             │
                                    server beta deploy otomatis    server prod deploy otomatis (cron 1 menit)
hotfix/<nama> (dari prod) ──PR langsung──▶ prod ──back-merge──▶ beta, development
```

- Jangan hapus `beta`, `development`, `rilis-apk-beta`, `rilis-apk-prod` (sumber: `KONTEKS-AGEN.md`, dan `vms-next/docs/08`).
- Merge ke `prod` = deploy produksi. Merge ke `beta` = deploy beta (server beta menarik `beta`, `deploy/beta/pasang-beta.sh`).
- Sumber: `KONTEKS-AGEN.md` dan `deploy/README.md` ("Alur pengembangan beta -> produksi").

## 2. Workflow: apa memicu apa

| Workflow (berkas) | Pemicu | Yang dilakukan | Catatan |
|---|---|---|---|
| CI (`ci.yml`) | PR ke `prod` atau `development`; manual | gitleaks; api (ruff, mypy, pytest dengan PostgreSQL, uji face-service); web (lint, typecheck, test, build); mobile (flutter analyze, test); lapor Discord `#vms-ci` | Api/web/mobile hanya jalan bila bagiannya berubah. PR ke `beta` TIDAK memicu CI. Merge ke `prod` tidak memicu ulang. |
| CD guard (`cd.yml`) | push `prod`; manual | pastikan HEAD = `origin/prod`; cek sintaks skrip deploy | Bukan deploy. Deploy dijalankan server. |
| Rilis (`rilis.yml`) | push `prod` | validasi `VERSION` (SemVer); gagal bila tag `vX.Y.Z` sudah ada; buat tag + GitHub Release (catatan dari `CHANGELOG.md`, bila kosong dibuat dari PR) | Gagal bila `VERSION` belum naik. |
| Images (`images.yml`) | push `prod`; manual | build dan dorong image `api` dan `web` ke GHCR (tag SHA + `latest`) | Tahap 1: hanya menerbitkan image. Server belum memakai pull. |
| APK (`apk.yml`) | push `beta` atau `prod` bila `mobile/**` berubah; manual (pilih env, opsi wajib) | build APK ditandatangani; cek sertifikat = `deploy/android-release-cert.sha256`; tulis `latest.json`; push ke cabang `rilis-apk-<env>` (ditimpa) | Server mengambil APK dari `rilis-apk-<env>` tiap menit. |
| Autodeploy (cron server, `deploy/autodeploy.sh`) | tiap menit | cek `origin/$BRANCH`; pasang APK terbaru; build, backup DB, migrasi, `up -d`, cek siap; rollback bila gagal | Prod: `BRANCH=prod`. Beta: `VMS_DEPLOY_BRANCH=beta`. |
| Healthcheck (cron 5 menit) | jadwal | kontainer mati, `/health` `/ready`, disk, RAM, umur cadangan; alarm Discord hanya saat berubah | `deploy/healthcheck.sh` |
| Cadangan (cron) | 01:30 prod, 01:45 beta | `pg_dump` ke MinIO `vms-backups` dan `~/deploy/*/backups` | Sumber: `vms-next/docs/08`. |

Runner: self-hosted `[self-hosted, linux, vms]`; APK di `ubuntu-24.04` (sumber: `apk.yml`, komentar).

## 3. Gerbang kualitas per tahap

| Tahap | Gerbang yang harus hijau | Siapa memeriksa |
|---|---|---|
| Sebelum commit | pre-commit: berkas rahasia ditolak (`*.env`, `key.properties`, `*.jks`, `.local_tests/*`); ruff pada `api/`; dart analyze pada `mobile/`; eslint pada `web/src/` | `.githooks/pre-commit` (pasang: `bash scripts/pasang-hook.sh`) |
| PR ke `development` | CI: gitleaks + api/web/mobile sesuai bagian yang berubah | `ci.yml` |
| `development` -> `beta` | TIDAK ada CI otomatis. Jalankan `bash scripts/verify-branch.sh development web` atau `api`. Uji nyata web dan APK beta. | Arsitek (perintah) + QA |
| PR `beta` -> `prod` | CI penuh (`ci.yml`), satu persetujuan | `ci.yml` + pemilik |
| Setelah merge ke `prod` | cd guard, rilis (tag), images, APK prod; server: build, backup, migrasi, cek siap (3 kali berturut-turut) | workflow + `autodeploy.sh` |

Cek siap (sumber: `deploy/README.md`): `localhost:8000/health` 200; `/ready` 200 (bukan 503); web `localhost:8080/` 200; `localhost:8080/api/v1/auth/me` 401; kontainer `vms_api` dan `vms_web` berjalan; image yang berjalan = image hasil build ini.

## 4. Deploy dan rollback

Urutan `autodeploy.sh` (ringkas): kunci `flock` -> checkout `origin/$BRANCH` -> simpan image lama sebagai `:rollback` -> `docker compose build` -> `backup.sh` -> `alembic upgrade head` -> `up -d --force-recreate` -> cek siap -> lapor Discord.

- Rollback otomatis: bila kontainer baru gagal sehat (kode keluar 14, 16, 17, 18), image `:rollback` dikembalikan sebagai `:latest` dan kontainer dinyalakan ulang tanpa build (fungsi `rollback_images`).
- Migrasi DB maju-saja. Karena itu migrasi WAJIB kompatibel mundur: tambah dulu (kolom NULLABLE, tabel baru), pakai, baru hapus pada rilis berikutnya (sumber: `vms-next/docs/06`, butir 4-5).
- Anti-loop: commit yang sama yang gagal dicoba lagi setelah `VMS_DEPLOY_RETRY_AFTER` detik (bawaan 900). Penanda `.last-failed`.
- Memaksa deploy ulang versi yang sama: hapus `~/deploy/vms-mvp/.last-deployed` (sumber: `deploy/README.md`).
- Skrip deploy di server adalah salinan. Perubahan `autodeploy.sh` harus disalin manual dan dicadangkan dulu (`deploy/README.md`, bagian "Memasang perubahan skrip ini ke server"). Baca bagian itu sebelum mengubah skrip.
- Rollback manual aplikasi: `docker tag <img>:rollback <img>:latest` lalu `docker compose up -d --force-recreate --no-build` (pola dari `rollback_images`). Rollback skema tidak otomatis.
- Uji pulih cadangan: `deploy/uji-pulih-cadangan.sh`, tiap bulan dan setelah perubahan skema besar. Berkas di MinIO belum ikut dicadangkan (`deploy/README.md`).

Pemberitahuan: Discord `#vms-deploy` (mulai, berhasil, gagal dengan 20 baris log). Pesan "Siap dipakai" hanya setelah cek siap lolos.

## 5. Versi

- SemVer `MAJOR.MINOR.PATCH` di berkas `VERSION` (sekarang `1.5.0`; tag `v1.5.0`).
- Aturan kenaikan (sumber: `CLAUDE.md`): perubahan API yang tidak kompatibel = MAJOR; fitur baru = MINOR; perbaikan = PATCH.
- Langkah rilis:
  1. Naikkan `VERSION` di PR ke `development`.
  2. `bash scripts/versi.sh --tulis` (menulis `api/VERSION`, `web/package.json` + lock, dan `mobile/pubspec.yaml` menjadi `X.Y.Z+BUILD`; BUILD = `git rev-list --count HEAD`).
  3. `bash scripts/versi.sh` (tanpa argumen) = cek konsistensi; keluarannya `LULUS` atau `GAGAL`.
  4. Tulis bagian `## [X.Y.Z] - YYYY-MM-DD` di `CHANGELOG.md` (format Keep a Changelog; isi `[Unreleased]` dipindah). `rilis.yml` mengambil catatan dari bagian ini.
  5. Merge ke `prod` -> `rilis.yml` membuat tag dan Release.
- Versi mobile: `version: x.y.z+N` di `mobile/pubspec.yaml`; `N` naik tiap build dan dipakai sebagai versionCode.
- Versi minimum APK: `latest.json` memuat `min_build`. Bawaan `1` (semua build boleh jalan). Dengan opsi `wajib` pada `apk.yml` (atau `rilis-apk.sh wajib`), `min_build` = build ini dan aplikasi lama wajib diperbarui.
- Versi API: path `/api/v1`. Perubahan tidak kompatibel = `/api/v2` (sumber: `vms-next/docs/06`, "Versi"). Untuk VMS lama, cek dampak ke APK lapangan lama sebelum mengubah daftar API (CLAUDE.md, "Daftar API": tanpa parameter = perilaku lama).
- Versi skema DB: revisi Alembic head, bukan SemVer.

## 6. Build APK per lingkungan

| Lingkungan | Perintah / sumber | Hasil |
|---|---|---|
| dev (uji lokal) | `VMS_DEVELOPMENT=1 flutter build apk --release --dart-define=API_BASE_URL=http://<ip-lan>:8000` (CLAUDE.md) | APK dev; jangan dikirim ke HP produksi |
| uji lokal ke emulator | `bash scripts/rilis-apk.sh bangun --uji-lokal --build N` (`scripts/rilis-apk.sh`) | APK ke `mobile/build/rilis-uji/N`; tidak pernah dikirim ke server |
| beta | `apk.yml` env beta: `VMS_BETA=1`, `--dart-define=VMS_BETA=true --dart-define=UPDATE_CHANNEL=beta`, `API_BASE_URL` tailnet | paket `com.visiontech.vms_mobile.beta`; kanal beta |
| prod | `apk.yml` env prod: `API_BASE_URL=https://portal.visiontechindo.com` | paket `com.visiontech.vms_mobile`; kanal stable |
| kirim manual | `scripts/rilis-apk.sh kirim` dari laptop pemilik (keystore tidak pernah ke server) | folder `rilis/android` di server |

Dasar: `apk.yml` (CI), `deploy/README.md` (pasang APK), `scripts/rilis-apk.sh`. Sertifikat harus cocok dengan `deploy/android-release-cert.sha256`; bila tidak, build dibatalkan.

## 7. Rahasia

- GitHub (secret repo): `ANDROID_KEYSTORE_B64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `DISCORD_WEBHOOK_CI`.
- Server (tidak di Git, chmod 600): `api.env`, `notify.env` (`DISCORD_WEBHOOK_DEPLOY`, `DISCORD_WEBHOOK_BUILD`), deploy key `~/.ssh/vms_deploy` (hanya baca).
- Laptop pemilik: keystore `.jks` dan `key.properties` (diblokir pre-commit; jangan di-stage).
- Jangan mencetak nilai rahasia di log. Workflow hanya memakai `${{ secrets.* }}` di env.

## 8. Konvensi commit dan PR

- Pola judul mengikuti riwayat repo: `fix(db): ...`, `feat(web): ...`, `fix(mobile): ...` (sumber: `git log`).
- Commit TANPA trailer AI dan tanpa `Co-authored-by` (aturan pemilik, CLAUDE.md dan memori "Commit VMS").
- Stage per path: `git add <berkas>`. Dilarang `git add -A`, `git stash` bersama, dan `git stash pop` dari sesi lain (aturan worktree).
- Isi PR memakai `.github/pull_request_template.md` (Ringkasan, Keputusan pemilik, Bukti, Checklist).
- Merge `beta` -> `prod` memerlukan persetujuan pemilik. Agen tidak merge ke `beta` atau `prod`.

## 9. Perbaikan CI yang rusak (playbook)

1. Baca run yang gagal: Discord `#vms-ci` atau log GitHub. Catat job: `secrets`, `api`, `web`, atau `mobile`.
2. Reproduksi lokal dengan salinan bersih: `bash scripts/verify-branch.sh <cabang> api|web` (log di `.local_tests/`). Untuk API, tes DB hanya atas perintah pemilik.
3. Periksa urutan skema di CI: `ci.yml` memasang `db/06_master_schema_v2.sql` lalu `db/08_master_v2_tambahan.sql`, lalu `alembic upgrade head`. Contoh nyata: commit `d8a12df5` memindahkan tabel `client_sites`..`work_order_bom` ke `08` agar dibuat setelah tabel `client` (CI gagal pasang skema).
4. Jangan mematikan job, menghapus langkah, atau menambah `continue-on-error` demi lolos. Bila tak terhindarkan: PR khusus, alasan tertulis, batas waktu, dan persetujuan pemilik.
5. Pantau workflow yang aktif: `gh workflow list` (bila CLI gh terpasang dan sudah login; jika tidak, lihat tab Actions di GitHub). Workflow yang dinonaktifkan manual bisa membuat CI tampak hijau padahal tidak jalan. Periksa setelah tiap perubahan CI.
6. Ulangi job yang gagal karena jaringan atau runner hanya bila log menunjukkan galat sementara.

## 10. Checklist rilis (ringkas)

- [ ] Semua PR fitur di `beta` sudah lolos QA (lihat `vms-qa`).
- [ ] `VERSION` naik; `versi.sh` = LULUS; `CHANGELOG.md` punya bagian versi.
- [ ] Migrasi kompatibel mundur; langkah server untuk pemilik ditulis.
- [ ] APK beta sudah diuji nyata; `min_build` sudah diputuskan (WAJIB atau tidak).
- [ ] PR `beta` -> `prod` hijau; pemilik menyetujui.
- [ ] Pantau Discord `#vms-deploy`; bila gagal, periksa `logs/deploy-*.log` dan rollback otomatis.

## Referensi

- `references/peta-workflow.md` - peta berkas dan perintah.
- `.claude/agents/devops-engineer.md` - definisi sub-agen DevOps.
- Tautan resmi (belum dibuka di sesi ini): GitHub Actions workflow syntax; Semantic Versioning 2.0.0 (semver.org); Keep a Changelog; Conventional Commits.

## Riwayat

- v0.1 - 2026-11-04 - Awal. Disusun dari sumber di repo dan folder riset (lihat docs/PANDUAN-AGENTIK.md bagian 14).
