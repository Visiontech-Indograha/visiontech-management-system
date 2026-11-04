# Glosarium bahasa sederhana untuk layar VMS

Aturan: teks yang dilihat pengguna (web dan HP) memakai bahasa sehari-hari. Nama teknis boleh di kode, API, dan nama berkas, tetapi tidak di layar. Sumber aturan: memori proyek `vms-bahasa-sederhana` (pemilik menegur 22-10-2026: "BAST apa itu?").

## 1. Padanan baku (dari memori proyek)

| Istilah di kode atau dokumen | Tampilkan di layar sebagai |
|---|---|
| BAST, Berita Acara | Serah terima pekerjaan |
| BoM, Bill of Material | Daftar material |
| BoQ, Bill of Quantity | Rekap material |
| rollover, geser | Pindah hari |
| prasyarat | Harus selesai dulu |
| realisasi | Hasil kerja |
| order klien | Pekerjaan klien |
| terbitkan jadwal | Kirim ke tim |
| luring | offline |
| daring | online |

Catatan: "daring" tidak dipakai di kode (bukti: 0 berkas). "luring" ditemukan di 2 berkas sumber (bukti: grep). Pemilik meminta istilah "offline" dan "online" (memori `vms-offline-first`).

## 2. Istilah yang perlu konfirmasi pemilik

Disebut dalam permintaan kerja, tetapi padanan belum tercatat di memori proyek:

| Istilah | Usulan | Status |
|---|---|---|
| Work Order (WO) | Pekerjaan | Belum dikonfirmasi. Perhatikan konflik dengan "Pekerjaan klien". Pastikan dua istilah tidak tertukar. |
| PM (Project Manager) | Atasan proyek | Belum dikonfirmasi. Tanyakan pemilik apakah "PM" dipakai sebagai peran di layar. |

Sebelum memakai usulan, minta konfirmasi dan catat keputusan di memori proyek.

## 3. Bukti pemakaian istilah di kode (hitung grep, sesi ini)

Angka ini menghitung berkas sumber (termasuk komentar kode, nama komponen, dan nama API). Belum tentu muncul di layar. Perlu cek layar langsung.

| Istilah | Berkas web dan mobile (tanpa tes) |
|---|---|
| BAST | 10 |
| BoM | 6 |
| BoQ | 1 |
| rollover | 3 |
| prasyarat | 1 |
| realisasi | 4 |
| luring | 2 |
| Work Order | 3 |

Contoh label yang sudah memakai padanan baku: "Daftar material" (`web/src/components/organisms/surveys/SurveyBomPanel.tsx:166`, `SurveyTabs.tsx:17`), "Serah terima aset" (komentar `AssetLendDialog.tsx:14`).

## 4. Aturan menulis teks

- Kalimat pendek, satu ide. Kata kerja aktif: "Kirim", "Simpan", "Ajukan".
- Tanpa singkatan kecuali yang sudah umum bagi pengguna (misalnya "HP", "K3" bila memang dipakai tim). Tulis dulu kepanjangannya di bantuan.
- Angka dan satuan jelas: "3 foto", "50 detik".
- Tombol: kata kerja, bukan kata benda. "Simpan perubahan", bukan "Penyimpanan".
- Galat: sebab, dan apa yang bisa dilakukan. Tanpa kode teknis.
- Tanggal: "4 Nov 2026" atau "Rabu, 4 November 2026". Konsisten.
- Jangan pakai bahasa Inggris di layar, kecuali nama merek atau singkatan yang sudah dikenal.

## 5. Contoh ubah kalimat

| Sebelum | Sesudah |
|---|---|
| "Gagal memuat data (HTTP 500)" | "Data belum bisa dibuka. Coba lagi beberapa saat lagi." |
| "Rollover jadwal gagal: prasyarat belum terpenuhi" | "Jadwal belum bisa dipindah. Selesaikan pekerjaan sebelumnya dulu." |
| "BAST belum ditandatangani" | "Serah terima pekerjaan belum ditandatangani." |
| "Offline: data akan disinkronkan" | "Anda sedang offline. Data tersimpan di HP dan akan dikirim saat online." |
| "Validation error: field required" | "Nama wajib diisi." |
| "Invalid input" | "Isian belum benar. Periksa tanggal dan jumlahnya." |

## 6. Cara mengecek di repo

```
grep -rn "BAST\|BoM\|BoQ\|rollover\|prasyarat\|realisasi\|luring" web/src mobile/lib --include=*.tsx --include=*.dart
```

Periksa hasilnya satu per satu:
- Di kode, komentar, dan nama API: boleh.
- Di teks yang tampil (JSX text, `Text(...)`, label, judul, tooltip, pesan galat): ganti sesuai tabel.

Ingat: API dan kode tidak diganti. Hanya layar.
