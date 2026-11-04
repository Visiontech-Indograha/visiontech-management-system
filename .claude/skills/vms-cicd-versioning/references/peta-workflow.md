# Peta berkas dan perintah CI/rilis

## Berkas

| Berkas | Fungsi |
|---|---|
| `.github/workflows/ci.yml` | gerbang PR (gitleaks, api, web, mobile, notify) |
| `.github/workflows/cd.yml` | penjaga sumber prod |
| `.github/workflows/rilis.yml` | tag + GitHub Release dari `VERSION` |
| `.github/workflows/images.yml` | image api/web ke GHCR |
| `.github/workflows/apk.yml` | APK bertanda tangan ke `rilis-apk-<env>` |
| `.github/pull_request_template.md` | isi PR |
| `.githooks/pre-commit` | pemeriksaan sebelum commit |
| `scripts/pasang-hook.sh` | memasang hook (`core.hooksPath`) |
| `scripts/verify.sh` | verifikasi cepat di disk kerja |
| `scripts/verify-branch.sh` | verifikasi dari salinan bersih (`git archive`) |
| `scripts/versi.sh` | cek dan sinkron versi (`--tulis`) |
| `scripts/rilis-apk.sh` / `rilis-apk.bat` | build dan kirim APK dari laptop |
| `deploy/autodeploy.sh` | deploy otomatis di server (cron 1 menit) |
| `deploy/healthcheck.sh` | pemantauan (cron 5 menit) |
| `deploy/backup.sh`, `backup-offsite.sh` | cadangan DB |
| `deploy/uji-pulih-cadangan.sh` | uji pulih |
| `deploy/beta/pasang-beta.sh`, `compose.yml`, `compose.infra.yml` | lingkungan beta |
| `deploy/compose.limits.yml` | batas memori: api 768m, web 128m, face 768m |
| `deploy/android-release-cert.sha256` | sidik sertifikat rilis Android |
| `deploy/README.md` | penjelasan deploy, cek siap, rahasia server |

## Perintah

```
bash scripts/verify.sh [api|web|mobile|all]          # cepat, di disk kerja
bash scripts/verify-branch.sh <cabang> web            # npm ci, lint, typecheck, test (salinan bersih)
bash scripts/verify-branch.sh <cabang> api [uji...]   # ruff, mypy, pytest (tes DB hanya atas perintah)
bash scripts/versi.sh                                 # cek versi konsisten
bash scripts/versi.sh --tulis                         # sinkronkan versi
bash scripts/pasang-hook.sh                           # pasang pre-commit
bash scripts/rilis-apk.sh bangun [--wajib] [--catatan "..."]
bash scripts/rilis-apk.sh kirim [BUILD]
bash scripts/rilis-apk.sh status
```

## Rujukan tambahan

- `deploy/README.md` bagian "Alur pengembangan beta -> produksi" dan "Cek siap pakai".
- `vms-next/docs/06-KEAMANAN-DAN-OPERASI.md` bagian "CI/CD" dan "Rilis dan lingkungan produksi" (rencana untuk VMS Next).
- `vms-next/docs/adr/0002-jawaban-pemilik-dan-mekanisme-rilis.md` keputusan 4, 6, 7, 11 (rencana VMS Next).
