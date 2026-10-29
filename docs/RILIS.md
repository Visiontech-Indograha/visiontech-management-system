# Rilis dan Semantic Versioning

Versi tunggal ada di berkas `VERSION` (root repo), format `X.Y.Z` (SemVer).
API, web, dan mobile mengikutinya lewat `bash scripts/versi.sh --tulis`; `bash scripts/verify.sh` dan tes arsitektur
`api/tests/architecture/test_versi.py` gagal bila tidak konsisten.

## Aturan kenaikan
- **MAJOR** (X): perubahan skema API yang merusak (rute/field dihapus atau berubah arti).
- **MINOR** (Y): fitur baru yang kompatibel.
- **PATCH** (Z): perbaikan yang kompatibel.
- Build number mobile (`+N`) naik otomatis: `versi.sh --tulis` menulisnya dari jumlah commit.

## Urutan menaikkan versi
1. Di cabang kerja, ubah `VERSION` lalu jalankan `bash scripts/versi.sh --tulis`.
2. Tambahkan bagian `## [X.Y.Z] - YYYY-MM-DD` di `CHANGELOG.md` (format Keep a Changelog; isi dari `[Unreleased]`).
3. Jalankan `bash scripts/verify.sh all`, lalu buka PR ke `development`.
4. Setelah PR beruntun ke `prod` digabung, workflow `.github/workflows/rilis.yml` membuat tag `vX.Y.Z` dan
   GitHub Release dengan catatan bagian tersebut.

Catatan: push ke `prod` tanpa kenaikan `VERSION` membuat workflow gagal dengan sengaja (tag sudah ada).
