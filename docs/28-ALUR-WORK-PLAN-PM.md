# 28 — Alur Work Plan (SK): dari PM login sampai SK ditutup PM

Status: **draf untuk review pemilik** (2026-10-03). Flowchart ada di FigJam
[VMS — Alur Bisnis & Dokumentasi](https://www.figma.com/board/FzhPAxXOu5zLzGJ1KFr1Bh), diagram **WP-0 sampai WP-F**.
Dokumen ini berisi rincian data yang tidak muat di flowchart. Semua teks tombol dan pesan dikutip dari kode
(`web/src/features/work-plans/*`, `mobile/lib/features/plans/*`, `api/app/services/plan_*`).

Warna di flowchart: biru = PM di web, hijau = ketua di HP, kuning = menunggu/cek server, merah = CELAH, abu = proses server/arsip.

## 1. Status SK

| Kode | Label web | Label HP | Pemicu ke status ini |
|---|---|---|---|
| DRAFT | Draft | (disembunyikan) | PM "Buat SK" / PM "Buka draft revisi" / PM "Pulihkan draft" |
| PUBLISHED | SK terbit | Terbit | PM "Terbitkan SK" |
| APPEALED | Banding | Banding | Ketua "Ajukan banding" (web saja — CELAH) |
| ACCEPTED | Diterima | Diterima | Ketua "Terima SK" (HP) |
| IN_PROGRESS | Berjalan | Berjalan | Ketua "Mulai pelaksanaan" (web saja — CELAH); PM "Kembalikan penyelesaian" |
| COMPLETION_REVIEW | Review penyelesaian | Menunggu selesai | Ketua "Buat Laporan Akhir" (web saja — CELAH) |
| COMPLETED | Selesai | Selesai | PM "Setujui penyelesaian" |
| CANCELLED | Dibatalkan | Batal | PM "Batalkan pekerjaan" (dari SK terbit s.d. Review) |

Draft terarsip bukan status, melainkan tanda `deleted_at` (PM "Arsipkan draft").

## 2. Langkah PM per layar (web)

### A. Login (`/login`)
- Tampil: "Selamat datang", "Masuk dengan email dan password akun kantor Anda."
- Input:
  - **Email**: wajib, format email. Pesan galat: "Format email tidak valid." / "Email wajib diisi."
  - **Password**: wajib. Pesan galat: "Password wajib diisi."
- Tombol "Masuk" (berubah jadi "Memproses...") memanggil `POST /auth/login {platform:"web"}`, lalu `GET /auth/me`.
- Galat:
  - "Email atau kata sandi salah. Sisa n percobaan."
  - Kunci login: "Tunggu mm:ss".
  - Akun lapangan: "Akun Anda bukan kategori akun kantor. Silakan gunakan aplikasi HP Visiontech."

### Beranda (`/`)
- Kartu "SK berjalan", "SK menunggu tindakan", "Absensi perlu diperiksa".
- "Pekerjaan aktif": maksimal 6 baris berisi judul, lokasi · periode, dan status.

### Daftar (`/work-plans`, menu "Work plan")
- Filter "Semua status" + 8 status, dan centang "Tampilkan draft terarsip".
- Isi kartu: judul, badge status, nomor (atau "Nomor terbit saat SK diterbitkan"), lokasi, periode.
- Kartu draft terarsip punya tombol "Pulihkan draft".

### B. Dialog "Buat SK"
| Field | Tipe | Aturan / pesan | Sumber opsi |
|---|---|---|---|
| Judul pekerjaan | teks | "Judul pekerjaan wajib diisi." | — |
| Lokasi pekerjaan | pilih | "Pilih lokasi pekerjaan." | `GET /sites` (kantor + lokasi unit PM) |
| Uraian | teks panjang | opsional | — |
| Tanggal mulai | tanggal | "Tanggal mulai wajib diisi." | — |
| Tanggal selesai | tanggal | "Tanggal selesai wajib diisi." / "Tanggal selesai tidak boleh sebelum tanggal mulai." | — |
| PM | teks tetap | "PM pekerjaan otomatis adalah Anda." (OPS/ADMIN boleh memilih) | — |
| Ketua tim | pilih | "Pilih ketua tim." | `GET /work-plans/assignment-options` (staf lapangan unit, tanpa bentrok jadwal) |
| Anggota tim | centang | "Pilih minimal satu anggota tim." | sama, tanpa PM dan ketua |
| Kendaraan (opsional) | pilih | — | aset VEHICLE tersedia & belum terikat SK |
| Pengemudi kendaraan | pilih | "Pilih pengemudi kendaraan." (jika ada kendaraan) | ketua + anggota terpilih |

Saat "Simpan" ditekan, tiga permintaan dijalankan berurutan:
1. `POST /work-plans`
2. `PUT /work-plans/{id}/members`
3. `POST /assets/{id}/reserve` (hanya jika ada kendaraan)

Jika berhasil, muncul toast "Draft SK dan tim berhasil dibuat." lalu halaman pindah ke detail.

### C. Detail Draft
"Rincian SK" menampilkan: Nomor SK (Belum terbit), Revisi, Lokasi, Periode, PM, Ketua tim, Uraian.

| Tombol | Input | API | Toast |
|---|---|---|---|
| Sunting draft | Judul pekerjaan, Lokasi (teks bebas), Uraian, Tanggal mulai, Tanggal selesai | `PATCH /work-plans/{id}` | "Draft disimpan." |
| Atur tim | Ketua tim, Anggota tim | `PUT /members` | "Tim disimpan." |
| Tambah hari | Tanggal (dalam periode), Nama pekerjaan, Deskripsi pekerjaan (semua wajib) | `POST /days`, lalu `PUT /days/{d}/plan` | "Rincian hari ditambahkan." |
| Lampiran | jpg/jpeg/png/pdf, maks 10 MB | `POST /files/upload`, lalu `PUT /attachments` | "Lampiran ditambahkan." |
| Atur titik lokasi | Cari kota/tempat, titik peta, Nama lokasi (wajib, ≤200), Alamat (≤500), Radius 10–5000 m (default 100) | `PUT /location` | "Titik lokasi disimpan." |
| Arsipkan draft | Alasan pengarsipan (wajib) | `POST /archive` | "Arsipkan draft berhasil." |

### D. Terbitkan SK
Dialog "Terbitkan SK?", tombol "Ya, terbitkan", memanggil `POST /publish`.

Server memeriksa, berurutan:
1. Status DRAFT.
2. Versi data cocok.
3. "Ketua tim harus karyawan aktif."
4. "PM penerbit tidak boleh menerima SK sebagai ketua tim sendiri."
5. "Pilih minimal satu anggota tim."
6. "Semua anggota tim harus karyawan aktif."
7. "Jadwal personel bertabrakan dengan …"
8. "Rincian harian belum lengkap." (setiap tanggal periode wajib punya hari + ≥1 tugas)
9. Akun PM tertaut ke karyawan.

Hasil:
- Nomor `SK-YYYYMM-<8 karakter id>`.
- Dokumen INITIAL_ORDER berstatus "Menunggu penerimaan".
- Tanda tangan PM (Penerbit) dibuat otomatis.
- Toast "SK diterbitkan. Minta ketua tim membuka aplikasi mobile untuk menerimanya."

### E. Pemantauan saat Berjalan
- **Laporan harian**:
  - PM melihat Laporan, Kendala, Bukti, dan "Catatan PM".
  - Keputusan "Setujui laporan" / "Minta perbaikan", plus "Catatan (wajib jika dikembalikan)", lalu "Simpan keputusan".
  - API `POST /days/{d}/review`.
- **Laporan mingguan**: sama (`POST /weekly/{w}/review`), hanya untuk SK ≥ 7 hari.
- **Insiden**: "Selesaikan", lalu isi "Catatan penyelesaian" (wajib).
- **Lembur**: "Tinjau lembur", lalu Keputusan "Setujui"/"Tolak" + Catatan (opsional).
- **Adendum personel**:
  - Input: Ketua tim, Anggota tim, Alasan (wajib), lalu "Ajukan adendum".
  - API `POST /work-plans/{id}/changes {type:"PERSONNEL"}`.
- **Timeline tim**: "{disetujui}/{total} hari disetujui", laporan terlambat.

### F. Penutupan
- PM membaca panel "Laporan akhir": Laporan keseluruhan, Kendala keseluruhan, Lampiran, Diajukan oleh.
- **"Setujui penyelesaian"** (`POST /approve-completion`, tanpa konfirmasi). Syarat server:
  - "Terdapat laporan harian yang belum disetujui."
  - "Terdapat laporan mingguan yang belum disetujui."
  - "Laporan akhir belum diserahkan."
  - "Masih ada aset yang belum dikembalikan atau diverifikasi (Asset)."
- Hasil penutupan:
  - Status Selesai.
  - Laporan akhir dikunci.
  - Tanda tangan ketua (Penerbit) + PM (Penyetuju), nomor `{SK}-LA`.
  - Tersedia "Unduh PDF laporan akhir" dan "Mode presentasi laporan".
- **"Kembalikan penyelesaian"**: Alasan pengembalian wajib, status kembali Berjalan.
- **"Batalkan pekerjaan"**:
  - Alasan pembatalan wajib.
  - Semua dokumen menjadi WITHDRAWN dan usulan terbuka ditarik.
  - Aset yang hanya direservasi dilepas.

## 3. Langkah ketua di HP

1. Login HP (akun FIELD), buka tab **Surat Kerja**. Judul "SK Anda", subjudul "n SK · m sedang berjalan".
2. Kartu SK menampilkan judul, chip status, nomor, lokasi, dan periode.
3. Detail SK menampilkan nomor, judul, lokasi, chip "Anda ketua", dan uraian.
4. Saat status Terbit, muncul "Penerimaan SK" dengan tombol **Terima SK**:
   - Dialog "Terima surat kerja ini?", tombol "Terima".
   - API `POST /accept` (wajib online).
   - Snackbar "SK berhasil diterima."
5. Saat Berjalan:
   - "Lapor insiden": Kategori, Tingkat keparahan, Kronologi (wajib), Foto.
   - "Lapor lembur": Jumlah jam, Alasan.
   - Hari kerja:
     - Centang tugas.
     - "Uraian pekerjaan" (wajib; server minimal 10 karakter), "Kendala (boleh kosong)", Foto (GPS wajib untuk kamera).
     - Tombol "Simpan draf" / "Kirim ke PM". Bisa dikirim luring (antrean).

## 4. Daftar CELAH (untuk diputuskan pemilik)

| # | Celah | Rujukan |
|---|---|---|
| 1 | Ketua akun FIELD ditolak login web. Padahal "Mulai pelaksanaan", "Ajukan banding", "Ajukan perpanjangan", laporan mingguan, "Buat Laporan Akhir", dan "Terima/Tolak adendum" hanya ada di web. Akibatnya **SK macet di Diterima**. | `api/app/services/auth_service.py:108`, `web/src/features/work-plans/WorkPlanDetailPage.tsx:188`, `mobile/lib/features/plans/work_plans_screen.dart` |
| 2 | Tidak ada GET untuk usulan perubahan. Panel adendum/perpanjangan hilang setelah muat ulang. PM tidak pernah melihat permintaan perpanjangan ketua. | `web/src/features/work-plans/PlanChanges.tsx:21-27` |
| 3 | Pilihan "Adendum personel" berisi semua karyawan aktif, bukan staf lapangan unit. Anggota lama tidak tercentang dan PM tidak dikecualikan. | `PlanChanges.tsx:122-190` |
| 4 | "Buat SK" = 3 simpan terpisah. Bila langkah tim/kendaraan gagal, draf tetap ada tanpa tim. | `web/src/features/work-plans/api.ts:102-136` |
| 5 | "Tambah hari" hanya membuat 1 tugas. Hari tidak bisa diedit atau dihapus. Tanggal di luar periode tidak dicegah server. | `PlanForms.tsx:378-406`, `api/app/api/v1/endpoints/work_plans.py:240-267` |
| 6 | "Setujui penyelesaian" tanpa konfirmasi. Dialog "Terbitkan SK" tertutup walau gagal. | `WorkPlanDetailPage.tsx:159,245-272` |
| 7 | Form laporan harian/mingguan milik ketua ikut tampil untuk PM, lalu ditolak server. | `DailyReports.tsx:44-47,109` |
| 8 | Draf hasil "Buka draft revisi" buntu: tidak bisa diarsip (sudah punya dokumen) dan tidak bisa dibatalkan (status DRAFT). | `api/app/services/plan_transition_service.py:115-141` |
| 9 | HP: "Kirim ke PM" menutup layar walau kirim ditolak. Centang tugas tetap aktif setelah laporan dikirim. Header detail SK tidak dimuat ulang. | `mobile/lib/features/plans/plan_day_screen.dart:105-125,163` |
| 10 | Tidak ada notifikasi di setiap tahap. Pihak lain tahu hanya dengan membuka daftar. | — |
