# Aturan desain web (R1-R15)

Wajib untuk kode web baru dan yang disentuh. Sumber lengkap dan alasannya: `docs/rencana/struktur-dan-kualitas-kode-v2.md` bagian 5 dan `docs/rencana/audit-usability-web.md`. Teks UI Bahasa Indonesia sederhana.

| No | Aturan singkat | Penegak sekarang |
|---|---|---|
| R1 | Tombol kirim nonaktif dan berlabel proses ("Menyimpan...") saat `pending`; tombol nonaktif karena izin atau syarat punya alasan terlihat; isian salah diberi pesan di kolom | Tes statis (`disabled={x.isPending}` manual tidak boleh bertambah); prop `pending` di `Button` menyusul (G2) |
| R2 | Aksi merusak lewat `ConfirmDialog` yang menyebut nama objek dan akibat, tombol bernama aksi; permanen: ketik "HAPUS"; tanpa `window.confirm` | Tes statis (berkas yang memanggil hapus/nonaktifkan wajib memakai konfirmasi; daftar lama sebagai baseline) |
| R3 | Pesan galat apa-mengapa-solusi, tanpa kode galat; pesan server menang atas cadangan; isian pengguna tidak dihapus | Tes statis (`catch` tanpa variabel, `toast.error(String(err))`/kode mentah); `errorMessage(err, cadangan)` |
| R4 | Validasi di kolom (Zod + `Field`), bukan toast; toast hanya hasil aksi | Tes statis (`toast.error("...")` berliteral tidak boleh bertambah) |
| R5 | Lima kondisi layar lewat `QueryState`; unggahan lewat `UploadField` dengan persen | Tes statis (`type="file"` langsung tidak boleh bertambah) |
| R6 | Bahasa sederhana sesuai glosarium | Daftar periksa PR (tes glosarium menyusul di G3/G6) |
| R7 | Sentence case untuk label, judul, tombol; judul halaman = label menu | Tes statis (Title Case pada `label=`, `placeholder=`, `title=`) |
| R8 | Tanggal, angka, uang, jarak hanya lewat `lib/format.ts` | Tes statis (`toLocale*String` di luar `format.ts`, literal `Rp ${`) |
| R9 | Simpan kanan, Batal kiri; satu aksi utama; target 44 px; tombol ikon ber-`aria-label` | Tes `h-8/h-9` yang ada; sisanya daftar periksa PR |
| R10 | Label di atas kolom, petunjuk di bawah (bukan placeholder), "(opsional)", pilihan "Pilih ..." tanpa "--" | Tes statis (teks berawalan `--`) |
| R11 | Pengguna tahu lokasinya: judul = menu, breadcrumb di halaman detail, konfirmasi keluar dari form kotor | Daftar periksa PR |
| R12 | Daftar: cari awalan, urut, filter terlihat, total (`X-Total-Count`) | Daftar periksa PR |
| R13 | Bantuan dalam konteks, keadaan kosong yang mengajak bertindak | Daftar periksa PR |
| R14 | Sesi: peringatan sebelum habis, kembali ke halaman semula, banner offline | Daftar periksa PR |
| R15 | Status penting lewat `role="status"`/`role="alert"`/`aria-live`; skeleton berlabel | Daftar periksa PR |

## Cara kerja tes penegak
Berkas: `web/src/lib/aturanDesain.test.ts`. Tes hanya membaca teks sumber, tidak mengubah perilaku. Setiap aturan punya baseline per berkas (jumlah pelanggaran lama):
- Pelanggaran baru atau bertambah: tes gagal. Perbaiki kodenya, jangan menaikkan baseline.
- Pelanggaran berkurang: tes juga gagal sampai angka baseline di berkas itu diturunkan atau barisnya dihapus (baseline hanya boleh menyusut).
- Aturan yang belum bisa dicek otomatis tertulis di daftar periksa PR (`.github/pull_request_template.md`).

## Kebijakan R1 (saran (a) di rencana v2, bagian 7)
Tombol Simpan abu-abu hanya saat sedang diproses atau tidak berizin; isian yang salah diberi pesan di kolomnya.
