# 03 · Cakupan Produk

Cakupan ini **dikunci** pada apa yang sudah ada di prototipe V2. Segala sesuatu di luar
daftar ini masuk "fase lanjutan" dan tidak boleh menyela pekerjaan berjalan.

---

## 1. Peran dan batasnya

| Peran | Siapa | Lingkup data | Yang boleh dilakukan |
|---|---|---|---|
| **PM** | Manajer proyek per unit bisnis | Hanya pekerjaan di unitnya | Membuat & menerbitkan SK, revisi, adendum, menilai laporan, menyetujui penyelesaian |
| **LEADER** | Ketua tim **menurut SK yang berlaku** | Pekerjaan tempat ia ditugaskan | Menerima/mengajukan banding SK, laporan harian & mingguan, insiden, lembur, pinjam & kembalikan aset |
| **MEMBER** | Anggota tim menurut SK | Pekerjaan tempat ia terdaftar | Absensi, lihat tugas, bantu isi bukti, ajukan dokumen pribadi |
| **FINANCE** | Akuntansi | Seluruh unit | Memeriksa absensi bertanda, menyetujui lembur, rekap |
| **HR** | Pengelola SDM | Seluruh karyawan | Verifikasi dokumen pribadi, promosi, offboarding |
| **ASSET** | Logistik | Seluruh aset | Melepas aset, memeriksa pengembalian, kondisi aset |
| **OPS** | Manajer operasional | Seluruh unit (baca) | Lini masa, rekap lintas pekerjaan, pemantauan |

**Aturan inti yang membedakan sistem ini:** peran LEADER dan MEMBER **bukan label pada
akun**. Keduanya berasal dari penugasan pada SK yang sedang berlaku. Ketua yang diganti lewat
adendum kehilangan kewenangan ketua pada hari adendum berlaku, tetapi tetap punya hak anggota
bila namanya masih terdaftar. Ini sudah diterapkan di prototipe dan di `db/` lewat
`is_plan_leader()` / `is_plan_member()`.

**Pemisahan unit itu nyata.** PM CCTV tidak boleh melihat insiden, lembur, atau pekerjaan
unit Wall Display. Ini pernah bocor di prototipe dan sudah diperbaiki — uji regresinya wajib
ikut dibawa.

---

## 2. Modul

### M1 · Identitas, akun, dan peran
Login, sesi, ganti kata sandi, pencabutan sesi, peran global per unit, jejak audit.
Kewenangan per pekerjaan dihitung dari SK, bukan disimpan di akun.

### M2 · Karyawan dan dokumen pribadi
Direktori karyawan, riwayat jabatan/penempatan, unggah dokumen pribadi (KTP, SIM, sertifikat,
MCU), verifikasi HR, masa berlaku dan peringatan ≤ 30 hari, pengajuan perpanjangan dari
halaman profil, promosi, offboarding dan pemulihan.

**Aturan:** nomor dokumen asli tidak disimpan — hanya bentuk tersamar + hash untuk deteksi
duplikat. Berkasnya hanya bisa dilihat pemilik dan HR.

### M3 · Surat Keputusan (SK) dan siklus pekerjaan
Inti produk.

```
DRAFT ──PUBLISH──> PUBLISHED ──ACCEPT──> ACCEPTED ──START──> IN_PROGRESS
                       │                                          │
                       └──APPEAL──> APPEALED ──REVISE──> PUBLISHED │
                                                                   ▼
                              COMPLETED <──APPROVE_COMPLETE── COMPLETION_REVIEW
```

- SK, revisi, adendum perpanjangan, dan **adendum personel** masing-masing menjadi dokumen
  dengan nomor dan snapshot sendiri.
- Dokumen terbit **tidak pernah diubah**. Versi lama otomatis terkunci saat versi baru terbit.
- Adendum personel berjalan penuh: usulan PM → penerimaan ketua masuk → penarikan oleh PM
  bila belum diterima → berlaku. Bentrok jadwal personel ditandai sebelum diajukan.
- Pembatalan dan pemulihan pekerjaan.

### M4 · Absensi lapangan
Masuk dan pulang, dengan:
- **Geofence** — jarak dihitung server terhadap titik lokasi proyek (radius bawaan 100 m,
  dapat ditimpa per lokasi). Di luar radius tetap boleh, tetapi ditandai dan wajib swafoto.
- **Swafoto** dengan watermark waktu dan lokasi.
- **Penanda terlambat / pulang cepat** dibanding jam kerja organisasi (08.00–17.00).
- Penjelasan dari karyawan (`EXPLAIN_ATTENDANCE`) dan pemeriksaan Finance
  (`REVIEW_ATTENDANCE`). Absensi yang ditolak boleh diajukan ulang di hari yang sama;
  catatan lama tetap tersimpan sebagai riwayat.

### M5 · Laporan pekerjaan
- **Harian**: tugas per hari (centang), teks pekerjaan, kendala, bukti foto → diajukan →
  dinilai PM (setuju / minta perbaikan).
- **Mingguan**: rekap, diajukan, dinilai.
- **Akhir**: permintaan penyelesaian oleh ketua → PM menyetujui → pekerjaan Selesai.
- **Mode presentasi** untuk pekerjaan yang sudah selesai.
- Laporan tidak boleh dibuat untuk tanggal yang belum tiba.

### M6 · Aset
Pesan (`RESERVE`) → dilepas Aset (`RELEASE`) → dipakai → dikembalikan ketua (`RETURN`) →
diperiksa Aset (`VERIFY_RETURN`). Kendaraan menampilkan pengemudi dan memeriksa masa berlaku
SIM. Satu aset tidak bisa dipakai dua pekerjaan pada rentang yang beririsan — ditegakkan
basis data, bukan hanya UI.

### M7 · Insiden K3
Kategori `K3_RINGAN`, `K3_BERAT`, `K3_LINGKUNGAN`, `K3_HAMPIR`, `ASET`; tingkat keparahan;
kronologi; bukti; penyelesaian. Muncul di laporan akhir dan mode presentasi.
**Tersaring per unit.**

### M8 · Lembur
Pengajuan oleh ketua, pemeriksaan Finance, rekap per periode. **Tersaring per unit.**

### M9 · Tanda tangan digital ber-QR
Penerbitan tanda tangan pada dokumen, nomor seri berurutan, QR tercetak, halaman verifikasi
publik. Memindai QR menampilkan: status, nomor seri, nama + jabatan + unit penandatangan,
nomor & judul dokumen, waktu. Dokumen yang diubah setelah ditandatangani terdeteksi
(`DOCUMENT_CHANGED`).

### M10 · Pengenalan wajah untuk absensi *(fase 8)*
Pendaftaran wajah dengan persetujuan tertulis, verifikasi 1:1 saat absensi, hasil tidak cocok
→ masuk antrean pemeriksaan manusia. Persetujuan bisa ditarik kapan saja.

### M11 · Lini masa, rekap, dan pemantauan (OPS)
Lini masa **dikelompokkan per pekerjaan** (bukan daftar datar — ini keluhan yang sudah Anda
sampaikan dan sudah diperbaiki di prototipe), rekap lembur, filter absensi, daftar aset.

### M12 · Kerja luring (Android)
Antrean aksi saat tanpa sinyal, indikator status, sinkronisasi otomatis saat daring, daftar
"perlu perhatian" untuk aksi yang ditolak server.

---

## 3. Yang masuk MVP dan yang ditunda

**MVP (fase 0–7, ± 17 minggu)** — M1, M2, M3, M4, M5, M6, M7, M8, M9, M11, M12.
Artinya: seluruh isi prototipe kecuali pengenalan wajah.

**Setelah MVP** — M10 (wajah, fase 8), lalu daftar di bawah.

**Fase lanjutan (belum dijadwalkan, butuh keputusan terpisah):**

| Ide | Kenapa menarik | Kenapa ditunda |
|---|---|---|
| Notifikasi push | Persetujuan sering tertahan karena tidak ada yang tahu | Butuh Firebase + kebijakan; nilainya baru terasa saat sistem dipakai |
| Input laporan dengan suara | Mengetik di lapangan itu menyiksa (`vti_frontend` sudah pernah mencobanya) | Perlu uji akurasi Bahasa Indonesia di lapangan berisik |
| Tanda tangan elektronik tersertifikasi (PSrE) | Kekuatan hukum penuh | Butuh vendor resmi & biaya; rancangan sekarang sudah siap disambungkan |
| iOS | Sebagian staf mungkin memakai iPhone | Tambah biaya & perangkat uji; belum ada permintaan nyata |
| Dasbor analitik / gudang data | Pertanyaan manajemen | Perlu data historis dulu |
| Integrasi mesin absensi kantor | Menyatukan dua sumber | Skema sudah menyiapkan `attendance_source = MACHINE` |

---

## 4. Yang **tidak** termasuk

Supaya tidak ada salah paham di kemudian hari:

- **Cuti dan izin** — ada di percobaan lama, tidak ada di prototipe V2.
- **Penggajian** — VMS menyediakan rekap absensi dan lembur; perhitungan upah di luar sistem.
- **Stok dan pembelian** — aset dicatat perpindahannya, bukan stoknya.
- **Portofolio, pengalaman perusahaan, indikator HES** — dari percobaan lama, di luar cakupan.
- **Servis kendaraan dan surat dinas** — di luar cakupan.

Bila salah satu dari ini ternyata Anda butuhkan, katakan sekarang: menambahkannya di awal
jauh lebih murah daripada di bulan keempat.

---

## 5. Ukuran dan target kinerja

| Parameter | Nilai rencana |
|---|---|
| Pengguna terdaftar | ≤ 200 |
| Pengguna bersamaan | ≤ 60 |
| Pekerjaan aktif bersamaan | ≤ 50 |
| Absensi per hari | ≤ 400 baris |
| Foto per hari | ≤ 800 (± 400 MB/bulan setelah re-encode) |
| Waktu muat halaman web | < 2 detik pada koneksi kantor |
| Waktu simpan absensi (daring) | < 3 detik termasuk unggah swafoto |
| Waktu verifikasi QR | < 1 detik |
| Waktu pencocokan wajah | < 2 detik |
| Ketersediaan | jam kerja 07.00–19.00 WIB; pemeliharaan di luar jam itu |

Angka-angka ini menentukan spesifikasi server di dokumen 09. Bila perkiraan jumlah pengguna
Anda berbeda jauh, beri tahu — itu mengubah rencana infrastruktur, bukan rencana kode.
