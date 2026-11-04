# Contoh rencana uji dan laporan QA

## A. Rencana uji (satu fitur)

```
Fitur: <nama> (PR #<n>, cabang <beta>, versi <X.Y.Z>)
Tujuan uji: memastikan <peran> dapat <tujuan> tanpa bantuan, dan <peran lain> tidak dapat melihat data divisi lain.
Lingkungan: web http://localhost:5173 | API http://127.0.0.1:8000 | APK beta di emulator/HP uji
Akun: <peran> = <akun dari scripts/akun-uji-lokal.txt>; jangan sebut sandi di laporan.
Data uji: <daftar ID buatan QA>; dihapus setelah uji (tanggal).

Skenario (urut prioritas):
  S1 (P1) Peran utama - alur bahagia: langkah 1..n. Harapan: ...
  S2 (P1) Peran lain - tidak berhak: langkah ... Harapan: 403 atau tidak terlihat (404).
  S3 (P2) Galat input: isi kosong, panjang melebihi batas, tanggal terbalik. Harapan: pesan Bahasa Indonesia, tanda di kolom yang salah (422 -> applyFieldErrors).
  S4 (P2) Kondisi layar: kosong, galat jaringan (matikan koneksi sebentar), sebagian.
  S5 (P3) Mode gelap dan fokus keyboard.
  S6 (P1, HP) Offline: buat data tanpa sinyal, lalu sambung; data terkirim sekali (tanpa duplikat).

Kriteria lulus: S1-S3 dan S6 lulus; tidak ada P1 terbuka.
Kriteria tahan rilis: ada P1 terbuka, atau kebocoran lintas divisi.
```

## B. Contoh laporan ringkas (untuk arsitek dan pemilik)

Contoh ini FIKTIF, hanya untuk bentuk format. Jangan dikutip sebagai hasil uji.

```
Laporan QA - beta <X.Y.Z>, tanggal <YYYY-MM-DD>, penguji: QA (sub-agen)

Ringkasan: 22 lulus, 3 gagal, 1 dilewati (DB uji tidak diminta).
Rekomendasi: TAHAN (1 P1 terbuka).

P1 (wajib sebelum rilis)
  QA-AUD-004 | PM divisi A | GET /api/v1/work-orders | respons memuat 2 pekerjaan divisi B | bukti: scratchpad/.../qa-004.json | BARU

P2
  QA-UX-011 | HR | Tambah karyawan | galat "NIK tidak valid" tanpa penanda kolom | bukti: .../qa-011.png | BARU

P3
  QA-UX-015 | OM | Judul halaman memakai jargon "rollover" | BARU

Catatan: uji offline HP (S6) belum dijalankan; HP uji belum terpasang APK beta.
```

## C. Contoh matriks peran x endpoint (potongan)

| Endpoint (GET) | SUPER_ADMIN | OM | PM div A | PM div B | TEAM_LEADER | HR | FINANCE | EMPLOYEE |
|---|---|---|---|---|---|---|---|---|
| /api/v1/employees | 200 semua | 200 | 200 divisi A | 200 divisi B | ... | 200 | ... | 403 |

Isi sel diisi dari hasil uji nyata. Jangan mengisi dari dugaan. Sel tanpa uji diberi `-`.
