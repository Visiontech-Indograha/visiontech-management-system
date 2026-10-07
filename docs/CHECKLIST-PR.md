# Checklist sebelum commit & Pull Request

Dipakai developer **dan** agen AI (keputusan pemilik 2026-10-07). Centang yang relevan di deskripsi PR
(templat `.github/pull_request_template.md`). Ragu pada butir mana pun → **tanyakan pemilik, jangan menebak**
(`docs/12` §12).

## Sebelum mulai
- [ ] Branch baru dari `origin/development` (`feature/…`, `fix/…`, `chore/…`, `test/…`, `docs/…`), di worktree sendiri.
- [ ] Standar terkait sudah dibaca (`CLAUDE.md` → tabel "Sebelum menulis kode").
- [ ] Hal yang ambigu sudah ditanyakan dan jawabannya dicatat di `docs/10` Bagian C.

## Sebelum commit
- [ ] Satu commit per bagian pekerjaan (bukan satu commit raksasa); pesan `jenis(area): ringkasan` Bahasa Indonesia.
- [ ] Hook `pre-commit` aktif (`bash scripts/pasang-hook.sh`) — ruff · dart analyze · eslint · cegah berkas rahasia.
- [ ] Tidak ada rahasia/berkas lokal: `.env`, `key.properties`, `*.jks`, `.local_tests/`, data karyawan asli.
- [ ] `CHANGELOG.md` diperbarui (bagian `[Unreleased]`).

## Pemeriksaan per area (dijalankan, hasilnya dilaporkan)
**API** (`cd api`)
- [ ] `ruff check app tests` bersih; garis dasar `ruff.toml` tidak bertambah.
- [ ] `python -m mypy` bersih.
- [ ] `VMS_REQUIRE_DB=1 python -m pytest -q` hijau terhadap PostgreSQL nyata (Docker menyala — tanpa itu uji DB dilewati diam-diam).
- [ ] Rute baru: punya izin/penjaga, atau terdaftar di `SELF_SERVICE` / `PUBLIC_ROUTES` beserta alasannya.
- [ ] API berubah → snapshot OpenAPI diperbarui (`UPDATE_OPENAPI_SNAPSHOT=1`) dan diff-nya ditinjau.
- [ ] Skema DB berubah → migrasi Alembic baru + `db/*.sql` disamakan; migrasi yang sudah di prod tidak diubah.
- [ ] Skema baru mengikuti `docs/12` §10 (`<Entitas>In/Out`).

**Web** (`cd web`)
- [ ] `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` hijau.
- [ ] Empat keadaan layar; 360 px tanpa gulir mendatar (`docs/11` §10).

**Mobile** (`cd mobile`)
- [ ] `flutter analyze` bersih, `flutter test` hijau.
- [ ] Perubahan perilaku HP → APK baru perlu dibangun & dipasang (sebut di PR).

**Server / deploy**
- [ ] Skrip `deploy/*.sh` lolos `bash -n` dan pagar `api/tests/test_deploy_scripts.py`.
- [ ] Langkah yang harus dijalankan pemilik di server ditulis jelas (perintah CMD siap salin).

## Uji nyata (aturan pemilik)
- [ ] Alur diuji end-to-end di web dan HP/emulator; tangkapan layar bukti dilampirkan.
- [ ] Suite regresi baru ditulis **setelah** pemilik menyetujui alurnya.

## Pull Request
- [ ] PR ke `development`; ke `prod` hanya lewat PR `development → prod` bila pemilik meminta.
- [ ] CI hijau (API, Web, Mobile, gitleaks).
- [ ] Setelah merge: hapus branch lokal & remote; matikan server/emulator yang dinyalakan sendiri.
