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
2. Judul PR sebaiknya memakai Conventional Commits (`feat:`, `fix:`, `chore:`, dan seterusnya); catatan rilis dibuat dari judul dan daftar PR.
3. CHANGELOG.md lokal bersifat opsional. Bila bagian `## [X.Y.Z]` ada di berkas itu, isinya dipakai sebagai catatan rilis; bila tidak, catatan dibuat otomatis.
4. Jalankan `bash scripts/verify.sh all`, lalu buka PR ke `development`.
5. Setelah PR beruntun ke `prod` digabung, workflow `.github/workflows/rilis.yml` membuat tag `vX.Y.Z` dan GitHub Release.

Catatan: push ke `prod` tanpa kenaikan `VERSION` membuat workflow gagal dengan sengaja (tag sudah ada).
