## Ringkasan
<!-- Apa yang berubah dan kenapa (1–3 kalimat). -->

## Keputusan pemilik / pertanyaan terbuka
<!-- Keputusan yang dipakai PR ini (dicatat di docs/10 Bagian C), atau pertanyaan yang belum dijawab. -->

## Bukti
<!-- Perintah yang dijalankan + hasilnya (n lulus), tangkapan layar uji nyata web/HP. -->

## Checklist (docs/CHECKLIST-PR.md)
- [ ] Lint & tipe bersih (ruff/mypy · eslint/tsc · flutter analyze)
- [ ] Uji hijau (pytest dengan DB nyata · npm test · flutter test)
- [ ] OpenAPI / migrasi / `db/*.sql` disamakan (bila berubah)
- [ ] Rute publik/izin baru beralasan
- [ ] Tidak ada rahasia; CHANGELOG diperbarui
- [ ] Langkah server/APK untuk pemilik ditulis (bila ada)
