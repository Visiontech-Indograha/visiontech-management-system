# 13 · Pengelolaan Berkas dan Kompresi

**Status: dikunci.** Angka dan aturan di sini adalah keputusan, bukan usulan.

Penyimpanan: **MinIO** (kompatibel S3). Basis data hanya menyimpan metadata dan
`storage_key` — isi berkas tidak pernah masuk basis data.

> **Yang dikompresi hanya FOTO/GAMBAR.** PDF, Word, PowerPoint, dan Excel disimpan apa
> adanya, tanpa diproses ulang. Alasannya di §5.

---

## 1. Kenapa foto wajib dikompresi

Foto dari kamera HP sekarang berukuran 3–8 MB. Pada 800 foto per hari itu berarti
**2–6 GB per hari**. Dua akibatnya, dan yang kedua lebih terasa daripada yang pertama:

1. Biaya penyimpanan naik terus dan tidak pernah turun.
2. **Unggahan dari lapangan gagal.** Dengan sinyal EDGE, mengunggah foto 6 MB butuh
   menit-menit dan sering putus di tengah. Foto 400 KB terkirim dalam hitungan detik.

Kompresi foto di sini bukan penghematan biaya; ini syarat agar aplikasi bisa dipakai di
lapangan.

---

## 2. Kompresi dua tahap

```
PERANGKAT (sebelum unggah)              SERVER (sebelum simpan)
├─ Android: flutter_image_compress      ├─ validasi magic bytes
├─ resize sisi terpanjang → 1600 px     ├─ buang EXIF (termasuk GPS)
├─ JPEG kualitas 75                     ├─ re-encode ke WebP
└─ hasil ± 300–600 KB                   ├─ buat 3 ukuran turunan
                                        └─ simpan ke MinIO
```

Kompresi di perangkat menyelamatkan kuota dan waktu pengguna. Kompresi di server menjamin
hasil akhirnya seragam apa pun perangkatnya — dan menjamin **EXIF benar-benar dibuang**,
karena perangkat tidak bisa dipercaya melakukannya.

---

## 3. Gambar (JPEG, PNG, HEIC, WebP)

**Pustaka:** Pillow (+ `pillow-heif` untuk HEIC dari iPhone).

**Tiga ukuran disimpan untuk setiap gambar:**

| Nama | Sisi terpanjang | Format | Kualitas | Perkiraan ukuran | Dipakai untuk |
|---|---|---|---|---|---|
| `thumb` | 320 px | WebP | 70 | 15–40 KB | Daftar, kartu, pratinjau |
| `view` | 1280 px | WebP | 80 | 120–300 KB | Tampilan layar penuh |
| `full` | 2048 px | WebP | 85 | 300–700 KB | Unduhan, cetak, bukti |

**Aturan:**

- Gambar asli **tidak disimpan**. `full` adalah versi arsipnya.
- Gambar yang lebih kecil dari ukuran target tidak diperbesar.
- PNG dengan transparansi tetap WebP (WebP mendukung transparansi).
- **Semua metadata dibuang** kecuali orientasi, yang diterapkan lalu dihapus. EXIF memuat
  koordinat GPS, merek perangkat, dan nomor seri kamera — data yang tidak kita minta dan
  tidak ingin kita simpan.
- Swafoto absensi: watermark (waktu, lokasi, nama) dibakar ke gambar **di perangkat**
  sebelum unggah, supaya melekat pada bukti.

**Penghematan nyata:** foto HP 5 MB → `full` ± 500 KB. **Sekitar 90%.**

---

## 4. Gambar yang gagal diproses

Bila kompresi gagal (berkas rusak, format aneh, HEIC dengan profil tidak lazim):

1. Berkas **disimpan apa adanya**, ditandai `compressed = false` di metadata.
2. Kegagalannya dicatat di log dan dihitung untuk pemantauan.
3. Unggahan **tidak pernah ditolak** hanya karena kompresinya gagal.

Kehilangan bukti pekerjaan karena pustaka gambar rewel adalah kerugian yang jauh lebih besar
daripada satu berkas yang kebesaran.

---

## 5. Dokumen (PDF, Word, PowerPoint, Excel) — **disimpan apa adanya**

**Dikunci: tidak ada kompresi untuk dokumen.** Diterima, divalidasi, disimpan utuh.

Alasannya:

1. **`.docx`, `.pptx`, `.xlsx` sudah terkompresi** — formatnya arsip ZIP. Mengompresi ulang
   hampir tidak menghasilkan apa pun pada dokumen berbasis teks.
2. **Risikonya tidak sepadan.** Menulis ulang isi berkas Office atau PDF berarti ada
   kemungkinan dokumen rusak atau berubah tampilannya. Untuk dokumen yang menjadi bukti
   kepegawaian dan bukti pekerjaan, itu risiko yang tidak layak diambil demi selisih ukuran.
3. **PDF bertanda tangan tidak boleh disentuh.** Mengompresi PDF yang memuat tanda tangan
   digital akan merusak tanda tangan itu — dan kerusakannya akan tampak seperti dokumen
   dipalsukan padahal tidak.
4. Volumenya kecil. Yang membanjiri penyimpanan adalah foto harian, bukan dokumen.

**Yang tetap dilakukan untuk dokumen:**

| Langkah | Isi |
|---|---|
| Validasi jenis | Magic bytes, bukan ekstensi nama berkas |
| Batas ukuran | 25 MB per berkas |
| Nama berkas | Disimpan sebagai metadata; kunci di MinIO tetap UUID |
| Hash | SHA-256 untuk deduplikasi dan pemeriksaan keutuhan |
| Akses | Sama ketatnya dengan berkas lain: URL bertanda tangan ≤ 5 menit |

Bila suatu saat dokumen benar-benar membanjiri penyimpanan, keputusan ini ditinjau ulang dan
dicatat di dokumen 10 Bagian D — bukan diubah diam-diam.

---

## 6. Batas ukuran dan jenis yang diterima

| Kategori | Jenis | Batas unggah | Perlakuan | Ukuran tersimpan |
|---|---|---|---|---|
| **Gambar** | jpg, jpeg, png, heic, webp | 15 MB | **Dikompresi** → 3 ukuran WebP | ± 700 KB |
| PDF | pdf | 25 MB | Disimpan apa adanya | sama dengan aslinya |
| Dokumen | docx, doc, pptx, ppt, xlsx, xls | 25 MB | Disimpan apa adanya | sama dengan aslinya |
| Lainnya | — | **ditolak** | — | — |

**Validasi memakai magic bytes, bukan ekstensi nama berkas.** Berkas bernama `foto.jpg`
yang isinya bukan gambar ditolak.

Nama berkas asli disimpan sebagai metadata untuk ditampilkan; nama di MinIO adalah UUID.
Nama asli tidak pernah dipakai sebagai kunci penyimpanan — nama dari perangkat bisa berisi
karakter yang merepotkan dan bisa membocorkan informasi.

---

## 7. Susunan di MinIO

```
vms-files/
├── attendance/{tahun}/{bulan}/{uuid}/{thumb|view|full}.webp
├── reports/{plan_id}/{report_id}/{uuid}/{thumb|view|full}.webp
├── documents/{employee_id}/{uuid}.{ext}          ← dokumen pribadi, paling ketat
├── plan-documents/{plan_id}/{document_id}.pdf    ← SK terbit, TIDAK PERNAH diubah
├── incidents/{incident_id}/{uuid}/...
└── temp/{uuid}                                   ← unggahan belum terpakai, hapus > 24 jam
```

**Aturan bucket:**

- Bucket **privat**. Tidak ada objek yang bisa diakses tanpa URL bertanda tangan.
- URL bertanda tangan berumur **≤ 5 menit**, dibuat hanya setelah otorisasi diperiksa.
- Versioning **aktif** pada `plan-documents/` — dokumen terbit tidak boleh hilang.
- Lifecycle: `temp/` dihapus otomatis setelah 24 jam.
- Berkas yatim (ada di MinIO, tidak ada barisnya di basis data) dibersihkan `cli
  cleanup-orphans` mingguan.

---

## 8. Alur unggah

```
1. Klien POST /files (multipart)
2. Server: periksa ukuran → magic bytes → jenis diterima?
3. Simpan sementara ke temp/
4. Gambar?  → kompresi di thread pool (jangan blokir event loop)
   Dokumen? → lanjut tanpa diproses
5. Hitung SHA-256 hasil akhir
6. Hash sudah ada untuk pemilik yang sama? → pakai berkas yang ada, jangan simpan dua kali
7. Pindahkan ke lokasi tetap
8. INSERT file_object (nama asli, jenis, ukuran asli, ukuran akhir, hash, storage_key,
   compressed)
9. Kembalikan file_id
```

Langkah 6 (deduplikasi) menghemat penyimpanan ketika foto atau dokumen yang sama dilampirkan
pada beberapa laporan — dan itu sering terjadi.

Langkah 4 berjalan di thread pool. Kompresi gambar adalah kerja CPU berat; menjalankannya di
event loop akan menyendatkan seluruh server saat satu orang mengunggah foto besar.

---

## 9. Retensi

| Jenis | Disimpan | Setelah itu |
|---|---|---|
| Swafoto absensi | 2 tahun | Hanya `thumb` disimpan, `view`/`full` dihapus |
| Bukti laporan | 5 tahun | Dipindahkan ke penyimpanan dingin |
| Dokumen pribadi | 2 tahun setelah karyawan keluar | Dihapus |
| SK dan dokumen terbit | **Permanen** | Tidak pernah dihapus |
| Embedding percobaan wajah | 30 hari | Dikosongkan `purge_face_probes()` |
| `temp/` | 24 jam | Dihapus |

Angka-angka ini dikunci. Dokumen terbit permanen karena ia bukti hukum; sisanya mengikuti
prinsip menyimpan secukupnya sesuai UU PDP.

---

## 10. Yang dipantau

| Metrik | Ambang |
|---|---|
| Rasio kompresi rata-rata gambar | < 70% → ada yang salah dengan alurnya |
| Kegagalan kompresi gambar | > 1% unggahan gambar |
| Waktu kompresi p95 | > 3 detik |
| Pertumbuhan bucket | > 20 GB/bulan |
| Berkas yatim | > 100 |
