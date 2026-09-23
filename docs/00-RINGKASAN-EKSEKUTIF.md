# 00 · Ringkasan Eksekutif

**Visiontech Management System (VMS)** · 23 September 2026 · Untuk dibaca pemilik produk

---

## 1. Apa yang akan dibangun

Aplikasi manajemen pekerjaan lapangan untuk Visiontech, menggantikan prototipe yang sudah
Anda setujui. Tiga permukaan:

| Permukaan | Untuk siapa | Fungsi utama |
|---|---|---|
| **Web (desktop)** | PM, HR, Finance, Aset, OPS | Menerbitkan SK, memeriksa laporan, rekap, dokumen, aset |
| **Android (Flutter)** | Ketua tim & anggota di lapangan | Absensi ber-GPS + wajah, laporan harian, insiden, lembur — **bisa luring** |
| **Halaman verifikasi publik** | Siapa saja yang memegang dokumen | Memindai QR pada SK untuk memastikan tanda tangannya asli |

Dasar fungsionalnya bukan karangan baru: **49 jenis transaksi bisnis** dan **162 layar**
yang sudah ada, teruji, dan Anda setujui di prototipe.

## 2. Tiga hal yang membedakan VMS dari aplikasi absensi biasa

1. **Kewenangan mengikuti SK, bukan jabatan.** Siapa yang jadi ketua pada satu pekerjaan
   ditentukan surat keputusan yang berlaku. Ganti ketua lewat adendum, kewenangannya ikut
   berpindah hari itu juga — dan ketua lama otomatis kehilangan haknya.
2. **Dokumen terbit tidak bisa diubah.** SK, revisi, dan adendum punya snapshot sendiri.
   QR di dokumen bukan hiasan: dipindai, ia menyebut nama penandatangan, jabatan, nomor
   seri, nomor dokumen, waktu — dan langsung memberi tahu bila isi dokumen diubah setelah
   ditandatangani.
3. **Absensi tidak mempercayai perangkat.** Jarak ke lokasi dihitung ulang di server, bukan
   dikirim HP. Wajah dicocokkan sebagai bukti pendukung — tidak cocok berarti **diperiksa
   manusia**, bukan ditolak diam-diam.

## 3. Berapa lama

**20–24 minggu** (± 5–6 bulan) untuk 1 developer penuh waktu yang dibantu AI, sampai rilis
produksi. Rinciannya di dokumen 06.

| Tonggak | Minggu ke- | Yang bisa Anda lihat |
|---|---|---|
| Fondasi berjalan | 2 | Login, peran, audit — di web |
| SK dan tim | 6 | PM menerbitkan SK, ketua menerima, adendum personel jalan |
| Absensi lapangan | 10 | Absen dari Android di lokasi proyek, Finance bisa rekap |
| Laporan & dokumen | 14 | Laporan harian/mingguan/akhir + PDF bertanda tangan QR |
| Aset, insiden, lembur | 17 | Seluruh modul prototipe tersedia |
| Pengenalan wajah | 19 | Absensi dengan verifikasi wajah |
| Uji terima & rilis | 22–24 | Dipakai satu tim sungguhan, lalu seluruh perusahaan |

**Jalur tercepat kalau Anda ingin cepat terasa manfaatnya:** hentikan di minggu ke-10.
Absensi lapangan + SK sudah cukup untuk dipakai satu tim nyata sambil sisanya dikerjakan.

## 4. Berapa biaya (perkiraan, di luar gaji developer)

| Pos | Perkiraan per bulan | Catatan |
|---|---|---|
| VPS aplikasi + basis data | Rp 400 rb – 1,2 jt | 4 vCPU / 8 GB cukup untuk ≤ 200 pengguna |
| Penyimpanan berkas (MinIO) | Rp 100 – 300 rb | Foto absensi (dikompresi ± 90%) dan dokumen |
| Layanan kunci (KMS) | Rp 0 – 200 rb | Bisa ditunda; lihat dokumen 08 |
| Domain + sertifikat | Rp 20 rb | Sertifikat gratis lewat Caddy |
| Cadangan luar-server | Rp 100 rb | Wajib, jangan dihemat |
| CI/CD + notifikasi | Rp 0 | GitHub Actions kuota gratis + webhook Discord |
| **Total berjalan** | **± Rp 700 rb – 1,8 jt** | |

Biaya sekali: server pengenalan wajah butuh RAM lebih besar (+2–4 GB) atau instans terpisah,
± Rp 300–500 rb/bulan bila dipisah. Play Store (opsional) USD 25 sekali seumur hidup.

## 5. Yang sudah siap dan yang belum

**Sudah siap dipakai:**
- Aturan bisnis lengkap dan teruji (prototipe, 19 uji domain + 162 layar).
- Skema basis data lengkap: 5 berkas SQL, 30+ tabel, RLS, tanda tangan digital, wajah.
- PostgreSQL 18 + PostGIS **sudah terpasang dan berjalan** di komputer ini.
- **Tailscale sudah terpasang di server** — dipakai untuk SSH, psql, konsol MinIO, dan staging.
- Kode percobaan sebelumnya (FastAPI, React, Flutter, layanan wajah) sebagai bahan rujukan.

**Belum ada:**
- **pgvector belum terpasang** di PostgreSQL 18 Anda — dibutuhkan untuk pengenalan wajah.
- Skema SQL belum pernah dijalankan sekali pun.
- Belum ada repositori Git untuk aplikasi sungguhan (prototipe ini bahkan belum di-Git).
- Belum ada server, domain, atau akun penyimpanan.

## 6. Tiga risiko terbesar

| Risiko | Kenapa serius | Penanganan |
|---|---|---|
| **Pengenalan wajah salah tolak orang yang benar** | Orang tidak bisa absen, upah terancam, kepercayaan hilang | Wajah hanya bukti pendukung; tidak cocok → diperiksa manusia, bukan ditolak. Ambang batas dikalibrasi dengan data nyata sebelum dipakai |
| **Data biometrik bocor** | Wajah tidak bisa diganti seperti kata sandi; pelanggaran UU PDP | Yang disimpan embedding, bukan foto; akses hanya HR dan pemilik; persetujuan tertulis yang bisa ditarik |
| **Ruang lingkup melebar di tengah jalan** | Penyebab paling umum proyek seperti ini mangkrak | Cakupan dikunci pada apa yang ada di prototipe; tambahan apa pun masuk daftar fase lanjutan, tidak menyela |

Daftar lengkap 18 risiko ada di dokumen 10 Bagian E.

## 7. Keputusan pokok yang sudah dikunci

1. **Backend dan web dibangun ulang** di atas skema `db/`, dengan prototipe sebagai
   spesifikasi. `vti_api` dan `visiontech/backend` tidak dilanjutkan — model identitas dan
   perannya berbeda mendasar dari model "kewenangan mengikuti SK", dan memaksakannya lebih
   lambat daripada menulis baru.
2. **Kode Flutter dan layanan wajah diambil** dari percobaan lama — dua bagian itu paling
   mahal dibuat dan paling sedikit bergantung pada model peran.
3. **Urutan fase mengikat.** Absensi lapangan di fase 4, bukan terakhir, karena paling
   berisiko dan paling menentukan apakah orang mau memakai aplikasinya.
4. **Pengenalan wajah di fase 8.** Sistem harus sudah dipercaya orang sebelum kita
   menambahkan hal yang bisa menolak mereka.
5. **Cakupan MVP = isi prototipe.** Fitur lanjutan sudah didaftar di dokumen 10 Bagian F dan
   tidak menyela pekerjaan berjalan.

Seluruh keputusan terkunci ada di **dokumen 10 Bagian A** (25 butir).

## 8. Langkah berikutnya

```
1. Buat folder vms/ + git init
2. Salin bahan (skema db/, prototipe, rencana ini, Flutter, layanan wajah)
3. Jalankan db/01–04 di PostgreSQL 18 yang sudah ada, perbaiki galat
4. Jadikan baseline Alembic 0001
5. Mulai fase 0
```

Langkah 3 adalah pekerjaan pertama yang benar-benar bernilai: sampai skema berjalan di basis
data sungguhan, seluruh isi `db/` masih berstatus dugaan. Perkiraan setengah hari kerja.

Rincian langkah dan lokasi setiap bahan ada di **MULAI-DI-SINI.md**.
