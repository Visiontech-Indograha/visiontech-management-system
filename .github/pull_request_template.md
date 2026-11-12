## Ringkasan
<!-- Apa yang berubah dan kenapa (1–3 kalimat). -->

## Keputusan pemilik / pertanyaan terbuka
<!-- Keputusan yang dipakai PR ini (dicatat di deskripsi PR), atau pertanyaan yang belum dijawab. -->

## Bukti
<!-- Perintah yang dijalankan + hasilnya (n lulus), tangkapan layar uji nyata web/HP. -->

## Checklist
- [ ] Lint & tipe bersih (ruff/mypy · eslint/tsc · flutter analyze)
- [ ] Uji hijau (pytest dengan DB nyata · npm test · flutter test)
- [ ] OpenAPI / migrasi / `db/*.sql` disamakan (bila berubah)
- [ ] Rute publik/izin baru beralasan
- [ ] Tidak ada rahasia
- [ ] Langkah server/APK untuk pemilik ditulis (bila ada)

## Checklist web (hanya butir yang relevan; aturan lengkap: `docs/ATURAN-DESAIN-WEB.md`)
- [ ] Tombol kirim tidak bisa diklik ganda dan berlabel proses (R1)
- [ ] Aksi hapus/merusak lewat `ConfirmDialog` bernama objek dan akibat (R2)
- [ ] Setiap `catch` memakai `errorMessage(err, "apa-mengapa-solusi")` (R3)
- [ ] Validasi di kolom dengan `Field`; toast hanya untuk hasil aksi (R4)
- [ ] Halaman dan daftar lewat `QueryState`; unggahan lewat komponen unggah (R5)
- [ ] Teks sesuai glosarium dan sentence case (R6, R7)
- [ ] Tanggal, angka, uang lewat `lib/format.ts` (R8)
- [ ] Simpan kanan, Batal kiri; satu aksi utama; tombol ikon ber-`aria-label` (R9)
- [ ] Petunjuk di bawah label, bukan placeholder (R10)
- [ ] Tangkapan 375/768/1280; teks 120 huruf tidak meluap; `bash scripts/verify.sh web` hijau
