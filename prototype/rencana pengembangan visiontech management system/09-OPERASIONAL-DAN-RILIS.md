# 09 · Operasional dan Rilis

---

## 1. Spesifikasi server

Dihitung dari target di dokumen 03 (≤ 200 pengguna, ≤ 60 bersamaan, ≤ 400 absensi/hari).

| Lingkungan | Spesifikasi | Perkiraan biaya/bulan |
|---|---|---|
| **Produksi** | 4 vCPU · 8 GB RAM · 160 GB SSD NVMe | Rp 400 rb – 1,2 jt |
| **Staging** | 2 vCPU · 4 GB RAM · 60 GB | Rp 150 – 400 rb (bisa dimatikan di luar jam uji) |
| **face-service** (fase 8) | +2–4 GB RAM, atau instans terpisah 2 vCPU · 4 GB | Rp 0 (menumpang) – 500 rb (terpisah) |

**Dikunci:** satu VPS produksi menampung semuanya. face-service dipisah **hanya bila**
pemantauan membuktikan ia mengganggu. Memisahkan lebih awal menambah biaya dan kerumitan
tanpa bukti bahwa itu perlu.

**Lokasi server:** Indonesia (Jakarta). Dua alasan: latensi ke pengguna lapangan, dan data
pribadi karyawan Indonesia lebih sederhana urusannya bila tidak melintasi batas negara.

---

## 1b. Jaringan dan akses: Tailscale

Server sudah memakai **Tailscale**, dan itu dikunci sebagai satu-satunya jalur administratif.

### Aturan firewall produksi

```
ufw default deny incoming
ufw allow 80/tcp          # hanya untuk pengalihan ke 443
ufw allow 443/tcp         # web, API, halaman verifikasi QR
ufw allow in on tailscale0
# port 22 TIDAK dibuka ke internet
```

### Yang hanya bisa diakses lewat tailnet

| Layanan | Kenapa tidak publik |
|---|---|
| SSH | Menghapus seluruh serangan tebak-kata-sandi SSH |
| PostgreSQL 5432 | Tidak ada alasan basis data terlihat dari internet |
| Konsol MinIO | Antarmuka admin penyimpanan |
| Uptime Kuma / pemantauan | Memuat informasi topologi sistem |
| Staging | Tidak boleh diindeks mesin pencari atau dibuka orang luar |
| face-service | Hanya dipanggil API, tidak pernah oleh klien |

### ACL dan tag

Perangkat diberi tag dan aturannya ditulis di berkas ACL Tailscale, tidak diingat-ingat:

| Tag | Untuk | Boleh mengakses |
|---|---|---|
| `tag:server` | VPS produksi & staging | — |
| `tag:admin` | Laptop pengelola | SSH, psql, konsol MinIO, pemantauan |
| `tag:dev` | Laptop developer | staging saja, **bukan** basis data produksi |
| `tag:ci` | Runner CI (auth key ephemeral) | deploy ke staging |

**Dikunci:** developer tidak diberi akses langsung ke basis data produksi. Bila perlu
memeriksa data produksi, lewat salinan yang sudah disamarkan — bukan dengan psql ke
produksi. Ini juga yang mencegah "sedikit perbaikan manual" yang tidak tercatat di migrasi.

### Batas yang harus disadari

**Tailscale bukan pengganti autentikasi aplikasi.** Berada di dalam tailnet tidak membuat
seseorang berwenang. Login, peran, dan RLS tetap berlaku penuh, termasuk untuk permintaan
yang datang dari alamat tailnet.

**Tailscale menjadi titik gagal untuk administrasi.** Bila tailnet bermasalah, akses SSH
ikut hilang. Karena itu: aktifkan akses konsol/VNC darurat dari panel penyedia VPS, dan
catat prosedurnya di runbook. Jangan menunggu keadaan darurat untuk mencari tahu caranya.

**Yang tidak dipakai:** Tailscale Funnel untuk produksi. Web produksi diakses lewat domain
perusahaan dengan sertifikat Caddy biasa.

---

## 2. Susunan layanan

```
docker compose (produksi)
├── caddy         443/80 → satu-satunya yang terbuka ke internet
├── api           FastAPI + uvicorn (2–4 worker)
├── web           berkas statis hasil build, disajikan Caddy
├── db            PostgreSQL 18 + PostGIS + pgvector
├── minio         penyimpanan berkas
└── face-service  fase 8, jaringan internal saja
```

**Basis data tidak dijalankan dalam container di produksi.** Dikunci: PostgreSQL berjalan
**di luar** container — langsung di host atau layanan terkelola. Basis data dalam
container bukan tidak bisa, tetapi menambah satu lapisan yang harus dipahami benar saat
pemulihan darurat, dan pemulihan darurat bukan saat yang tepat untuk belajar.

---

## 3. Konfigurasi dan rahasia

- Seluruh konfigurasi lewat variabel lingkungan; `.env.example` menjadi dokumentasinya.
- **Tidak ada rahasia di Git.** Tidak sekarang, tidak "sementara".
- Rahasia produksi disimpan di pengelola rahasia server (atau minimal berkas `.env` dengan
  izin 600 yang dicadangkan terpisah dan terenkripsi).
- Kunci penandatangan **tidak** disimpan sebagai variabel lingkungan — hanya rujukan KMS.

---

## 4. Alur rilis

```
commit → CI (lint, tipe, uji) → build image → deploy staging → uji asap → deploy produksi
```

Pipeline lengkap, isi setiap langkah, dan bentuk laporannya di Discord ada di **dokumen 17**.

- **Migrasi dijalankan terpisah dari start aplikasi**, sebelum versi baru dinyalakan.
- Migrasi harus **kompatibel mundur** satu versi: tambahkan kolom dulu, isi, baru hapus yang
  lama pada rilis berikutnya. Dengan begitu rollback tidak berarti kehilangan data.
- Versi aplikasi ditampilkan di layar (pojok pengaturan) supaya laporan bug bisa dikaitkan
  dengan versi.
- **Jendela rilis:** di luar 07.00–19.00 WIB. Rilis saat orang sedang absen adalah cara
  tercepat kehilangan kepercayaan.

---

## 5. Cadangan dan pemulihan

| Apa | Cara | Frekuensi | Disimpan |
|---|---|---|---|
| Basis data | `pg_dump` terkompresi | Harian 02.00 WIB | 30 hari |
| Basis data | WAL archiving (PITR) | Terus-menerus | 7 hari |
| Berkas MinIO | Sinkronisasi ke penyimpanan objek lain | Harian | 30 hari |
| Konfigurasi & rahasia | Terenkripsi, manual | Setiap berubah | Permanen |

**Aturan yang tidak boleh dilanggar:** cadangan disimpan **di luar server aplikasi**.
Cadangan yang ada di mesin yang sama tidak menolong saat mesin itu yang bermasalah.

**Pemulihan wajib diuji** — minimal sekali di fase 9 dan sekali setiap 6 bulan sesudahnya.
Target: RPO ≤ 1 jam (kehilangan data maksimal), RTO ≤ 4 jam (waktu pulih maksimal).

Cadangan yang belum pernah dipulihkan bukan cadangan; itu harapan.

---

## 6. Pemantauan

| Yang dipantau | Ambang peringatan |
|---|---|
| API hidup (`/health`) | Gagal 2 kali berturut-turut |
| Waktu respons p95 | > 2 detik selama 5 menit |
| Galat 5xx | > 1% permintaan |
| Ruang disk | < 20% tersisa |
| Cadangan terakhir | > 26 jam yang lalu |
| Sesi gagal login | Lonjakan tidak wajar |
| Antrean luring yang macet | Ada operasi `PENDING` > 24 jam |
| Absensi `NEEDS_REVIEW` | Melonjak dibanding rata-rata |

Seluruh peringatan dikirim ke **Discord** — kanal, format pesan, dan aturan anti-banjir ada
di dokumen 17. Peringatan yang masuk ke tempat yang tidak pernah dibuka sama saja dengan
tidak ada peringatan; itu sebabnya kanalnya dipisah dan yang rutin tidak dicampur dengan
yang butuh tindakan.

---

## 7. Runbook — apa yang dilakukan saat terjadi masalah

### API tidak merespons
1. Cek `docker compose ps` dan log 100 baris terakhir.
2. Cek ruang disk dan RAM.
3. Restart layanan `api`. Bila pulih, cari penyebabnya di log — jangan berhenti di restart.

### Basis data penuh
1. Cek tabel terbesar (biasanya `audit_event`, `attendance`, `qr_scan`).
2. Pindahkan partisi lama ke penyimpanan dingin (bukan hapus).
3. Tambah disk. Jangan menghapus data operasional untuk mengejar ruang.

### Absensi gagal massal pagi hari
Ini keadaan darurat — orang tidak bisa bekerja.
1. Cek face-service (bila fase 8 sudah aktif) — matikan sementara bila itu penyebabnya;
   absensi harus tetap jalan tanpa wajah.
2. Cek waktu server (NTP) dan koneksi ke MinIO.
3. Bila belum juga pulih: aktifkan mode pencatatan manual, beri tahu Finance, perbaiki, lalu
   masukkan data susulan lewat koreksi yang tercatat.

### Dugaan pencurian token
1. `revoke_sessions()` untuk pengguna terkait.
2. Paksa ganti kata sandi.
3. Periksa `audit_event` untuk aktivitas tidak wajar.
4. Bila menyangkut peran PM/HR/Finance: periksa dokumen yang terbit pada rentang waktu itu.

### Kunci penandatangan bocor
1. Tandai kunci tidak berlaku; terbitkan kunci baru di KMS.
2. Tanda tangan lama **tetap** terverifikasi — jangan panik menghapusnya.
3. Putuskan bersama pemilik produk apakah perlu pencabutan massal.
4. Catat kejadiannya; bila menyangkut data pribadi, ikuti kewajiban pemberitahuan UU PDP.

---

## 8. Distribusi aplikasi Android

**Dikunci (K-18):** mulai dengan **APK internal** yang dibagikan lewat tautan terlindungi, plus
pemeriksaan versi di dalam aplikasi ("versi baru tersedia, perbarui sekarang").

Alasan: tidak perlu menunggu review, dan pengguna terbatas pada karyawan sendiri.
Pertimbangkan Play Store (internal testing) bila jumlah perangkat > 50 dan pembaruan manual
mulai merepotkan.

**Wajib ada sejak awal:** pemeriksaan versi minimum di server. Bila aplikasi terlalu lama
tidak diperbarui, server menolak dengan pesan yang jelas — bukan galat aneh. Perangkat
lapangan yang tertinggal versi adalah sumber bug yang paling sulit dilacak.

---

## 9. Serah terima ke tim internal

Sebelum proyek dianggap selesai, yang berikut harus ada dan **sudah dicoba oleh orang selain
pembuatnya**:

1. Dokumen ini + README repositori yang bisa diikuti dari nol sampai aplikasi jalan.
2. Akses ke server, KMS, penyimpanan, dan domain — tercatat, bukan hanya di kepala satu orang.
3. Prosedur cadangan dan pemulihan, **sudah diuji**.
4. Panduan pengguna satu halaman per peran.
5. Daftar hal yang belum selesai dan yang sengaja ditunda, jujur dan lengkap.

Poin terakhir yang paling sering dilewati, dan yang paling merugikan orang berikutnya.
