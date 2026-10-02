# 29 — Laporan uji E2E alur SK v2

Alur mengikuti flowchart SK2-0 s.d. SK2-F di FigJam "VMS — Alur Bisnis & Dokumentasi" (disetujui pemilik 2026-10-03).
Uji dilakukan dengan klik/isi nyata, bukan suite otomatis.

## 1. PR1 — Buat SK, Sunting SK, Terbit, Adendum, Terima, Berjalan otomatis, notifikasi (lokal, 2026-10-03)

**Lingkungan:** API lokal :8000 (branch `feature/sk-alur-v2-pr1`), web Vite :5173, DB uji lokal PG18 (`vms_db_test_local18`).
HP nyata Realme RMX3933 (ketua) dan emulator Pixel_10_Pro_XL (anggota), APK debug dengan `API_BASE_URL=http://127.0.0.1:8000`
lewat `adb reverse tcp:8000 tcp:8000`.

**Akun:** PM Dimas (unit Infrastruktur Jaringan), ketua Eko, anggota Fajar & Hendra (Hendra pemegang SIM A).

| # | Langkah | Hasil |
|---|---|---|
| S1 | PM klik **Buat SK** → halaman `/work-plans/new`; **Simpan** kosong | Galat per field: judul, deskripsi, tanggal, kategori, ketua |
| S2 | Isi judul, deskripsi keseluruhan, kategori Instalasi; Tipe terkunci "Infrastruktur Jaringan" | ✔ |
| S3 | Lokasi kerja → **+ Lokasi baru**: GPS browser tidak tersedia → pesan bantuan; ketik lat/long manual (-6.9, 107.6) → cari "Monas Jakarta" → pilih hasil → koordinat tertimpa hasil cari (-6.175402, 106.827169) → geser marker → tertimpa lagi (-6.176313, 106.828756); ubah nama & deskripsi → Simpan lokasi | ✔ urutan manual → cari → geser terbukti |
| S4 | Rentang 3–4 Okt → 2 kartu hari; **+ Tambah hari kerja** → hari ke-3 (5 Okt); **+ Tambah detail pekerjaan** di hari 1; isi 4 detail; lampirkan foto ke detail pertama | ✔ |
| S5 | Alat: Drone; Ketua: Eko (hilang dari daftar anggota); anggota Fajar + Hendra | ✔ hanya staf lapangan unit PM yang tidak terikat SK lain yang tampil |
| S6 | Kendaraan roda dua (Honda Vario) | Driver kosong: "Tidak ada ketua/anggota dengan SIM yang sesuai tipe kendaraan." ✔ |
| S7 | Ganti ke mobil (Triton) → driver: Hendra (SIM A) → **Simpan** | Draf tersimpan dengan isi lengkap (tim, aset, driver, 3 hari, lampiran) ✔ |
| S8 | **Sunting SK** | Pratinjau A4 "PRATINJAU DRAF" (kategori, tipe, lokasi + koordinat, PM, tim + jabatan, alat & kendaraan, detail per hari) ✔ |
| S9 | **Ubah isi** → form terisi data draf → Simpan | ✔ satu `PUT /full` |
| S10 | **Terbitkan SK** → **Ya, terbitkan** | Nomor `SK-202610-a1475919`, status Terbit, dokumen v1 "Menunggu tanda tangan" + TTD PM ✔ |
| S11 | HP ketua: login → tab Surat Kerja → lonceng **2** → Notifikasi → ketuk "…terbit" | Detail SK lengkap + tombol Tinjau SK ✔ |
| S12 | **Tinjau SK** | Dokumen A4 sama dengan PM, TTD "Penerbit (PM)" + QR, status Menunggu tanda tangan ✔ |
| S13 | **Ajukan adendum** "Mohon tambah 1 hari kerja untuk instalasi kabel" → Kirim ke PM | Status Adendum diminta, banner di HP ✔ |
| S14 | Web PM: lonceng 1, kotak alasan adendum → **Buka revisi** → Ubah isi → + Tambah hari kerja (6 Okt, "Instalasi kabel") → Simpan → Terbitkan | Revisi 2 terbit; dokumen v1 **Tidak berlaku**, v2 Menunggu tanda tangan ✔ |
| S15 | HP ketua: SK berisi 4 hari → **Terima SK** → konfirmasi | v2 **Berlaku** dengan 2 TTD; tanggal mulai = hari ini → status langsung **Berjalan** ✔ |
| S16 | Notifikasi | PM: adendum diminta, diterima, mulai berjalan. Anggota: terbit, diterima, mulai berjalan ✔ |
| S17 | Emulator anggota (Fajar): Surat Kerja → SK | Hanya melihat (tanpa Terima/Ajukan adendum); Aksi cepat & hari kerja tampil ✔ |

**Temuan & perbaikan selama uji:**
- T-1: penampil HP memakai dokumen pertama dari daftar (urut versi naik) → menampilkan versi lama setelah revisi. Diperbaiki: pakai versi terakhir.
- T-2: lokasi baru tanpa radius → kartu lokasi menampilkan "Radius absensi - m". Diperbaiki: radius awal 100 m.
- T-3: tanggal di dokumen A4 berformat ISO. Diperbaiki: "3 Oktober 2026".
- T-4: aplikasi debug di emulator sempat tertahan di layar pembuka setelah emulator dinyalakan ulang; pulih setelah data aplikasi dibersihkan (bukan bug alur).

**Suite (hanya penyesuaian uji lama yang memeriksa alur lama):** web 145 lulus, Flutter 88 lulus, API — lihat CHANGELOG.
