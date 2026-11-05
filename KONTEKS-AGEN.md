# Konteks untuk agen AI

Repo ini adalah **VMS lama (v1.5.0, masih produksi)**. Aturan kerja, perintah, dan alur ada di `CLAUDE.md` (lokal) dan `README`. CHANGELOG.md bersifat lokal dan tidak di-commit; catatan rilis dibuat otomatis dari judul/deskripsi PR (rilis.yml --generate-notes).

## Gambaran singkat
- API FastAPI (`api/`, struktur berlapis), web React+Vite+TS (`web/`), mobile Flutter (`mobile/`), layanan wajah (`face-service/`), DB PostgreSQL 18 (`db/06–08`, Alembic `api/alembic_v2/`), deploy (`deploy/`, `scripts/`).
- Cabang: `development` → `beta` → `prod`. Merge ke `prod` = deploy produksi. Jangan hapus `beta`, `development`, `rilis-apk-*`.
- Tes: `bash scripts/verify.sh [api|web|mobile|all]`.

## Proyek pembangunan ulang
**VMS Next** ada di repo privat `Visiontech-Indograha/vms-next`. Di sana tersedia:
- `docs/08-KEADAAN-VMS-SAAT-INI.md` — keadaan proyek ini secara rinci (stack, server, utang teknis).
- `docs/09-STATUS-VMS-NEXT.md` — status dan langkah berikutnya proyek baru.
- `docs/sumber-lama/` — diagram alur, matriks peran, skema, token desain dari proyek ini.
Perubahan perilaku bisnis di sini harus dicerminkan ke `vms-next/docs/00-KONTEKS-DOMAIN.md`.

## Catatan
Folder `docs/` repo ini sudah dihapus; komentar kode yang menyebut `docs/NN-…` merujuk ke `vms-next/docs/sumber-lama/`.
Riwayat git ditulis ulang pada 2026-11-04; clone lama harus di-clone ulang.
