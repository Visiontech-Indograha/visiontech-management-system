# Runbook Penanganan Insiden Pelindungan Data Pribadi (UU PDP No. 27/2022)

> [!CAUTION]
> **PENANDA STATUS & VERIFIKASI HUKUM:**
> Dokumen ini merupakan **DRAF PEDOMAN OPERASIONAL TEKNIS & TANGGAP DARURAT**. Seluruh isi, alur eskalasi, dan templat surat dalam dokumen ini **WAJIB MENDAPATKAN VERIFIKASI SERTA PERSETUJUAN DARI PENASIHAT HUKUM (LEGAL COUNSEL) PEMILIK** sebelum disahkan sebagai kebijakan kepatuhan resmi PT Visiontech Indograha.

---

## 1. Landasan Hukum & Ruang Lingkup

### 1.1 Dasar Hukum
1. **Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**:
   - **Pasal 4 ayat (2) & (3)**: Klasifikasi Data Pribadi Umum (nama lengkap, NIK, alamat, jabatan) dan Data Pribadi Spesifik (data biometrik wajah `face_embedding`, swafoto absensi, catatan kesehatan K3).
   - **Pasal 46 ayat (1), (2), (3)**: Kewajiban Pengendali Data Pribadi untuk menyampaikan pemberitahuan tertulis paling lambat **3 x 24 jam (72 jam)** jika terjadi kegagalan pelindungan data pribadi kepada:
     1. Subjek Data Pribadi (karyawan, pengguna, mitra); dan
     2. Lembaga/Otoritas Pengawas Pelindungan Data Pribadi (Kementerian Komunikasi dan Digital / Lembaga PDP).
   - **Pasal 53**: Kewajiban Penilaian Dampak Pelindungan Data Pribadi (DPIA) untuk pemrosesan berisiko tinggi.
   - **Pasal 54**: Penunjukan Pejabat/Petugas Pelindungan Data Pribadi (Data Protection Officer - DPO).
   - **Pasal 57 & Pasal 65–68**: Sanksi administratif dan ketentuan pidana atas pelanggaran data pribadi.

### 1.2 Klasifikasi Data dalam Ekosistem VMS
| Kategori Data | Contoh Entitas di VMS | Lokasi Penyimpanan | Klasifikasi PDP |
|---|---|---|---|
| **Biometrik Mentah** | Vektor embedding wajah (`face_embedding`, 512 dimensi) | PostgreSQL tabel `employee` | **Spesifik** (Pasal 4 ayat 2 huruf d) |
| **Media Identitas & Wajah** | Foto profil karyawan, swafoto absensi harian, foto titik survei | MinIO bucket `vms-files` (prefix privat) | **Spesifik** |
| **Identitas Kependudukan & Kontak** | Nama lengkap, NIK, nomor telepon, alamat rumah, tanggal lahir | PostgreSQL tabel `employee`, `user` | **Umum** (Pasal 4 ayat 3) |
| **Kepegawaian & Operasional** | Divisi, kantor tugas, riwayat absensi, surat tugas SPK, survei WO | PostgreSQL tabel `attendance`, `work_order` | **Umum** |
| **Kredensial & Sesi** | Hash kata sandi (Argon2id), refresh token, sesi login | PostgreSQL tabel `user`, `user_sessions` | **Sensitif Teknis** |

---

## 2. Struktur Tim Tanggap Insiden PDP (Isian Pemilik)

Pemilik wajib mengisi nama dan kontak penanggung jawab berikut:

| Peran Tanggap Insiden | Tanggung Jawab Utama | Nama Pejabat (Isian Pemilik) | Kontak Darurat (Isian Pemilik) |
|---|---|---|---|
| **Penanggung Jawab Utama (Pengendali Data / Direksi)** | Otorisasi pengumuman resmi, persetujuan tindakan hukum, keputusan pelaporan ke otoritas PDP | `[Isian Pemilik: Nama Direktur]` | `[Isian Pemilik: No. HP / Email]` |
| **Pejabat Pelindungan Data Pribadi (DPO)** | Mengoordinasikan penanganan insiden, memimpin audit DPIA darurat, menyusun draf notifikasi 72 jam | `[Isian Pemilik: Nama DPO]` | `[Isian Pemilik: No. HP / Email]` |
| **Koordinator Teknis & DevOps (CSIRT Lead)** | Mengisolasi sistem, membendung kebocoran, forensik digital, analisis akar masalah (RCA), pemulihan | `[Isian Pemilik: Lead DevOps]` | `[Isian Pemilik: No. HP / Email]` |
| **Penasihat Hukum (Legal Counsel)** | Meninjau kepatuhan regulasi, memvalidasi draf surat pemberitahuan, mitigasi dampak hukum | `[Isian Pemilik: Kuasa Hukum]` | `[Isian Pemilik: Kontak Legal]` |
| **Humas & Komunikasi Subjek Data** | Mengelola komunikasi resmi dengan karyawan/klien terdampak, menyalurkan bantuan narahubung | `[Isian Pemilik: Tim Komunikasi]` | `[Isian Pemilik: Kontak Humas]` |

---

## 3. Klasifikasi Tingkat Keparahan Insiden

| Tingkat | Kriteria | Batas Waktu Eskalasi Internal | Batas Notifikasi Eksternal (Pasal 46) |
|---|---|---|---|
| **Tingkat 1 (Rendah)** | Celah keamanan tertutup tanpa kebocoran data, anomali login lokal terblokir, gangguan ketersediaan tanpa kompromi integritas/kerahasiaan. | Dalam 12 jam ke DPO | Tidak wajib notifikasi eksternal |
| **Tingkat 2 (Sedang)** | Paparan data pribadi umum dalam jumlah terbatas (< 10 subjek data), kebocoran token sesi yang langsung dicabut tanpa eksfiltrasi data massal. | Dalam 4 jam ke Direksi & DPO | Dinilai oleh DPO & Legal Counsel |
| **Tingkat 3 (Kritis / Berat)** | Akses tanpa hak/eksfiltrasi database, terpaparnya data biometrik `face_embedding`, kebocoran berkas foto/KTP MinIO ke publik, atau ransomware. | **Seketika (< 1 jam)** ke Direksi, DPO, & Legal | **WAJIB MAKSIMAL 72 JAM (3x24 Jam)** kepada Subjek Data & Otoritas PDP |

---

## 4. Alur Kerja Operasional Tanggap Insiden (5 Fase)

```
[Fase 1: Deteksi & Triase] (T+0 s.d. T+2 Jam)
       │
       ▼
[Fase 2: Pembendungan & Isolasi] (T+2 s.d. T+6 Jam)
       │
       ▼
[Fase 3: Investigasi & Penilaian Dampak / DPIA] (T+6 s.d. T+24 Jam)
       │
       ▼
[Fase 4: Notifikasi Tertulis 72 Jam (Pasal 46)] (T+24 s.d. T+72 Jam)
       │
       ▼
[Fase 5: Pemulihan & Evaluasi Pasca-Insiden] (T+72 Jam s.d. T+14 Hari)
```

### Fase 1: Deteksi dan Triase Awal (T+0 s.d. T+2 Jam)
1. **Sumber Deteksi**:
   - Alarm Uptime Kuma atau notifikasi webhook Discord `#vms-alerts`.
   - Log anomali otentikasi pada tabel `user_sessions` atau lonjakan eror pada `api/app/core/logging_config.py`.
   - Laporan karyawan atau pihak ketiga mengenai kebocoran data.
   - Peringatan integritas berkas cadangan (kegagalan checksum sha256 pada `backup-offsite.sh` atau `Tarik-Cadangan.ps1`).
2. **Triase Awal**:
   - CSIRT memverifikasi apakah insiden melibatkan data pribadi (umum atau spesifik).
   - Jika terindikasi Tingkat 2 atau 3, aktifkan Tim Tanggap Insiden dan nyatakan status **KEADAAN DARURAT PDP**.

### Fase 2: Pembendungan dan Isolasi (T+2 s.d. T+6 Jam)
Lakukan tindakan pembendungan teknis tanpa menghapus barang bukti forensik:
1. **Isolasi Jaringan**:
   - Tutup akses publik luar: putuskan Cloudflare Tunnel atau jalankan `deploy/tutup-port-layanan.sh`.
   - Batasi akses administrasi hanya melalui jaringan privat terenkripsi Tailscale.
2. **Pencabutan Akses & Sesi**:
   - Cabut seluruh sesi aktif pengguna:
     ```sql
     DELETE FROM user_sessions;
     ```
   - Blokir sementara akun pengguna yang terindikasi terkompromi (`UPDATE "user" SET is_active = false WHERE ...`).
3. **Rotasi Rahasia Seketika (LANGKAH PEMILIK)**:
   - Rotasi secret key JWT (`JWT_SECRET_KEY`) di `api.env`.
   - Rotasi kredensial MinIO (`MINIO_ROOT_PASSWORD`, `MINIO_SECRET_KEY`).
   - Rotasi sandi basis data PostgreSQL dan kunci SSH offsite.
   - Recreate kontainer: `docker compose up -d --force-recreate`.
4. **Pengamanan Bukti Forensik**:
   - Salin dan bekukan log kontainer: `docker logs vms_api > /srv/forensik/api-incident-$(date +%s).log`.
   - Buat snapshot volume basis data dan penyimpanan MinIO dalam keadaan read-only.
   - Hitung nilai hash SHA-256 untuk semua artefak bukti log forensik.

### Fase 3: Investigasi dan Penilaian Dampak (DPIA Review) (T+6 s.d. T+24 Jam)
1. **Inventarisasi Dampak**:
   - Hitung jumlah baris data pribadi yang terakses/bocor.
   - Identifikasi apakah data biometrik (`face_embedding`) ikut terdampak.
   - Catat daftar nama dan email/nomor kontak karyawan atau mitra yang terdampak.
2. **Analisis Akar Masalah (Root Cause Analysis - RCA)**:
   - Bagaimana pelaku mendapatkan akses? (mis. kebocoran kredensial, eksploitasi dependensi, celah konfigurasi port).
   - Apakah kebocoran bersifat aktif (masih berlangsung) atau pasif (arsip masa lalu).
3. **Penilaian Risiko Hak Subjek Data**:
   - Potensi pencurian identitas, penyalahgunaan foto/wajah, penipuan finansial, atau kerugian sosial bagi karyawan.

### Fase 4: Kewajiban Pemberitahuan Tertulis 3x24 Jam (Pasal 46 UU PDP) (T+24 s.d. T+72 Jam)
> **BATAS KERAS WAKTU:** Surat pemberitahuan tertulis wajib dikirimkan **paling lambat 72 jam** sejak insiden dipastikan terjadi.

1. **Pemberitahuan kepada Lembaga/Otoritas Pengawas PDP**:
   - Kirimkan surat resmi sesuai **Templat A** melalui kanal aduan resmi Kementerian Komunikasi dan Digital / Lembaga PDP.
   - Tembuskan ke Badan Siber dan Sandi Negara (BSSN) jika insiden melibatkan serangan siber kritikal.
2. **Pemberitahuan kepada Subjek Data Pribadi**:
   - Kirimkan pemberitahuan resmi sesuai **Templat B** kepada seluruh karyawan/subjek data yang terdampak via email resmi perusahaan dan notifikasi aplikasi portal VMS.
   - Jika kontak perorangan tidak memungkinkan (mis. database kontak ikut rusak), lakukan pengumuman resmi tertulis melalui portal perusahaan.
3. **Muatan Wajib Pemberitahuan (Pasal 46 ayat 2 UU PDP)**:
   - [x] Rincian jenis data pribadi yang terungkap/bocor;
   - [x] Waktu kejadian dan kronologi singkat bagaimana data terungkap;
   - [x] Upaya pembendungan, mitigasi, dan pemulihan yang telah dilakukan perusahaan;
   - [x] Narahubung resmi dan rekomendasi langkah mitigasi bagi subjek data (mis. imbauan waspada pesan phishing, ganti sandi).

### Fase 5: Pemulihan dan Evaluasi Pasca-Insiden (T+72 Jam s.d. T+14 Hari)
1. **Pemulihan Bersih (LANGKAH PEMILIK)**:
   - Pulihkan basis data dan berkas MinIO dari cadangan terenkripsi `age` yang telah divalidasi integritasnya (`docs/CADANGAN-WINDOWS.md`).
   - Lakukan pemindaian kerentanan pada seluruh kontainer dan dependensi (`trivy`, `gitleaks`).
2. **Laporan Akhir Insiden (Post-Mortem Report)**:
   - Disusun oleh DPO bersama Tim DevOps dan diserahkan kepada Direksi paling lambat H+7 pasca insiden.
3. **Pembaruan Dokumen DPIA & Keamanan**:
   - Perbarui Analisis Dampak Pelindungan Data Pribadi (DPIA).
   - Evaluasi arsitektur penyimpanan (mis. percepatan rencana isolasi biometrik mandiri / enkripsi kolom spesifik).

---

## 5. Templat Surat dan Dokumen Resmi

### Templat A: Surat Pemberitahuan Insiden ke Otoritas Pengawas PDP

```
Nomor       : [Nomor Surat Resmi Perusahaan]
Lampiran    : [Jumlah Berkas Lampiran / Dokumen Teknis RCA]
Perihal     : Pemberitahuan Tertulis Kegagalan Pelindungan Data Pribadi
              (Pasal 46 Undang-Undang No. 27 Tahun 2022)

Kepada Yth.
Ketua / Pimpinan Lembaga Pelindungan Data Pribadi
c.q. Kementerian Komunikasi dan Digital Republik Indonesia
di Tempat

Dengan hormat,

Sehubungan dengan kewajiban Pengendali Data Pribadi berdasarkan Pasal 46 Undang-Undang 
Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi, kami yang bertanda tangan di bawah ini:

Nama Pengendali Data : PT Visiontech Indograha
Alamat Kantor        : [Alamat Kantor Pusat Perusahaan]
Narahubung / DPO     : [Nama Lengkap DPO / Pejabat PDP]
Jabatan              : Data Protection Officer (DPO)
Nomor Telepon/HP     : [Nomor Kontak Resmi]
Email Resmi          : [Email Resmi PDP/DPO]

Dengan ini menyampaikan pemberitahuan tertulis mengenai telah terjadinya insiden 
kegagalan pelindungan data pribadi pada sistem Visiontech Management System (VMS) kami, 
dengan rincian kronologis dan teknis sebagai berikut:

1. Waktu dan Kronologi Kejadian:
   a. Waktu Insiden Terdeteksi  : [Hari, Tanggal, Pukul WIB]
   b. Waktu Insiden Terjadi    : [Perkiraan Waktu Terjadinya Kebocoran/Akses Ilegal]
   c. Kronologi Singkat Kejadian:
      [Jelaskan secara ringkas bagaimana insiden terdeteksi, vektor serangan, 
      dan cakupan sistem yang terdampak tanpa membuka celah keamanan lebih luas]

2. Rincian Data Pribadi yang Terdampak:
   a. Kategori Data Umum       : [Sebutkan: Nama, NIK, No. Telepon, Alamat, dsb.]
   b. Kategori Data Spesifik   : [Sebutkan: Data Biometrik Wajah / Foto Swafoto / Nihil]
   c. Perkiraan Jumlah Subjek  : [Jumlah Individu/Karyawan yang Terdampak] orang

3. Upaya Penanganan dan Pemulihan yang Telah Dilakukan:
   a. Mengisolasi jaringan dan menutup seluruh akses luar pada [Tanggal & Waktu].
   b. Membekukan seluruh sesi aktif dan melakukan rotasi kunci rahasia serta kredensial sistem.
   c. Mengamankan log forensik digital dan memulihkan sistem dari cadangan terenkripsi age yang bersih.
   d. Mengirimkan notifikasi tertulis kepada seluruh subjek data pribadi yang terdampak.

4. Langkah Mitigasi Lanjutan:
   [Jelaskan audit sistem, penambalan celah keamanan, dan evaluasi kepatuhan internal yang sedang berjalan]

Demikian pemberitahuan ini kami sampaikan dengan penuh itikad baik guna memenuhi ketentuan 
peraturan perundang-undangan yang berlaku. Kami siap memberikan keterangan dan dokumen pendukung 
tambahan yang diperlukan oleh Lembaga.

[Kota], [Tanggal Surat Diterbitkan]
Hormat kami,
PT Visiontech Indograha

(Tanda Tangan & Cap Basah)


[Nama Direktur Utama / Penanggung Jawab]
Direktur / Pengendali Data Pribadi
```

---

### Templat B: Surat / Pemberitahuan Tertulis kepada Subjek Data Pribadi (Karyawan/Pengguna)

```
PEMBERITAHUAN PENTING MENGENAI PELINDUNGAN DATA PRIBADI ANDA
Nomor Referensi: PDP/NOTIF/[TAHUN]/[BULAN]/[NO]

Kepada Yth.
Bapak/Ibu Rekan Kerja / Mitra PT Visiontech Indograha
di Tempat

Dengan hormat,

PT Visiontech Indograha berkomitmen penuh untuk senantiasa menjaga keamanan dan kerahasiaan 
data pribadi Anda. Melalui surat resmi ini, sesuai dengan ketentuan Pasal 46 Undang-Undang 
Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP), kami menyampaikan informasi 
bahwa telah terjadi insiden keamanan siber yang berpotensi memengaruhi sebagian data pribadi Anda 
pada sistem Visiontech Management System (VMS).

1. Apa yang Terjadi?
   Pada tanggal [Tanggal], tim pemantau keamanan kami mendeteksi adanya [akses tidak sah / anomali] 
   pada sistem penyimpanan VMS. Tim teknis kami telah bergerak cepat dan berhasil mengisolasi serta 
   menutup celah tersebut dalam waktu [Jumlah Jam] jam sejak terdeteksi.

2. Data Pribadi Apa Saja yang Terdampak?
   Berdasarkan hasil investigasi forensik kami, data pribadi Anda yang terindikasi terdampak meliputi:
   - [ ] Data Identitas Umum : [Nama, Nomor Induk Karyawan, Nomor Telepon, Alamat Email]
   - [ ] Data Biometrik/Foto: [Foto Profil / Swafoto Absensi / Vektor Wajah]
   - [ ] Catatan Operasional : [Riwayat Penugasan, Lokasi Absensi]
   *(Catatan: Kata sandi akun Anda tersimpan dalam bentuk enkripsi hash Argon2id yang kuat 
   dan tidak tersimpan dalam bentuk teks polos).*

3. Apa yang Telah Kami Lakukan?
   - Kami telah memutus seluruh sesi login aktif dan merotasi seluruh kunci keamanan sistem.
   - Kami telah memperketat kontrol akses jaringan server dan memulihkan integritas data.
   - Kami telah melaporkan insiden ini secara resmi kepada Otoritas Pengawas Pelindungan Data Pribadi.

4. Apa Langkah yang Perlu Anda Lakukan?
   - Harap waspada terhadap upaya penipuan, pesan teks mencurigakan, atau panggilan dari pihak yang 
     mengaku dari manajemen perusahaan atau pihak eksternal yang meminta kode verifikasi/OTP.
   - Perbarui kata sandi akun VMS Anda saat pertama kali masuk kembali melalui portal resmi.
   - Jangan pernah membagikan tautan verifikasi atau identitas ke pihak mana pun.

5. Saluran Narahubung dan Bantuan Resmi:
   Apabila Anda memiliki pertanyaan, kendala, atau memerlukan verifikasi lebih lanjut, silakan 
   menghubungi Tim Pelindungan Data Pribadi (DPO) kami melalui:
   - Email Resmi  : [Email DPO / Bantuan PDP]
   - Nomor Hotline: [Nomor Telepon / WhatsApp Resmi Pengaduan PDP]
   - Jam Layanan  : [Jam Operasional Layanan, mis. Senin - Jumat, 08:00 - 17:00 WIB]

Kami menyampaikan permohonan maaf yang sebesar-besarnya atas ketidaknyamanan yang ditimbulkan. 
Perlindungan privasi dan keamanan data Anda adalah prioritas tertinggi kami.

Hormat kami,
Manajemen PT Visiontech Indograha
```

---

### Templat C: Formulir Log Perekaman Insiden Internal (PDP Incident Register)

| Parameter | Catatan Investigasi Internal |
|---|---|
| **ID Insiden** | `INC-PDP-[YYYYMMDD]-[NO]` |
| **Waktu Terdeteksi** | YYYY-MM-DD HH:MM:SS WIB |
| **Pelapor Pertama** | Nama / Sistem (mis. Alarm Discord / Log API / Laporan User) |
| **Deskripsi Kejadian** | Uraian singkat jenis kerentanan atau akses yang terjadi |
| **Klasifikasi Insiden** | Tingkat 1 (Rendah) / Tingkat 2 (Sedang) / Tingkat 3 (Kritis) |
| **Data Terdampak** | [ ] Umum (Nama/NIK/HP) &nbsp;&nbsp; [ ] Spesifik (Biometrik Wajah/Foto) &nbsp;&nbsp; [ ] Kredensial |
| **Jumlah Subjek Terdampak** | [Jumlah estimasi subjek data] |
| **Tindakan Pembendungan** | Tindakan isolasi, penutupan port, rotasi kunci rahasia |
| **Waktu Notifikasi Otoritas** | YYYY-MM-DD HH:MM:SS WIB (Maks T+72 Jam) |
| **Waktu Notifikasi Subjek Data** | YYYY-MM-DD HH:MM:SS WIB (Maks T+72 Jam) |
| **Status Penyelesaian** | Terbuka / Sedang Ditangani / Selesai / Ditinjau Legal |
| **Tanda Tangan DPO & Legal** | Divalidasi oleh: `[Nama DPO]` pada `[Tanggal]` |

---

## 6. Daftar Periksa Tindakan Cepat (Quick Action Checklist)

Gunakan daftar periksa berikut dalam 72 jam pertama insiden:

- [ ] **Jam 0–2**: Verifikasi keabsahan insiden dan aktifkan Tim Tanggap Insiden PDP.
- [ ] **Jam 2–4**: Lakukan isolasi teknis (`deploy/tutup-port-layanan.sh`, cabut sesi, rotasi secret).
- [ ] **Jam 4–6**: Amankan salinan log forensik dan snapshot database read-only.
- [ ] **Jam 6–24**: Selesaikan inventarisasi data terdampak (apakah ada `face_embedding` atau foto MinIO).
- [ ] **Jam 24–48**: Susun draf surat notifikasi otoritas dan subjek data dengan penasihat hukum.
- [ ] **Jam 48–72**: **KIRIM SURAT PEMBERITAHUAN RESMI** ke Otoritas PDP dan seluruh subjek data terdampak.
- [ ] **Hari ke-4 s.d. 14**: Pemulihan penuh sistem, rilis laporan investigasi RCA, dan perbarui dokumen DPIA.
