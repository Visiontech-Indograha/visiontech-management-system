# 25 · Laporan Uji — R-26 Tim SK hanya staf lapangan

## 1. Informasi umum

| | |
|---|---|
| Nama aplikasi | VMS — Visiontech Management System (web + aplikasi lapangan Android) |
| Modul / fitur | R-26: pemilihan ketua & anggota SK hanya staf lapangan; celah `PATCH` ganti ketua; dialog "Atur tim" memuat tim saat ini. Ikut diuji ulang: R-21 (pesan & kunci login, kartu peran kantor di HP), R-23 (penerimaan SK di HP) |
| Tanggal pengujian | 2026-09-29 |
| Penguji | Claude (agen), atas permintaan pemilik |
| Lingkungan | **Development lokal + DB/MinIO UJI terpisah di server** (`vms_db_test` :5434, `vms_minio_test` :9100). Bukan produksi. Web: Vite dev di peramban bawaan (Chromium). HP: Realme RMX3933 (Android), APK debug → API uji lewat `adb reverse` |
| Data uji | Organisasi `UJI-E2E Visiontech` (skrip `.local_tests/seed_e2e.py`): unit LAP & LAIN, 9 akun (admin, ops/OM, pm, hr, finance, ketua, anggota, teknisi dua, teknisi unit lain). Sandi disimpan di `.local_tests/e2e-logins.txt` (tidak di Git, tidak ditulis di dokumen) |

## 2. Skenario pengujian

| ID | Deskripsi | Langkah | Data uji | Hasil yang diharapkan | Hasil aktual | Status |
|---|---|---|---|---|---|---|
| TC-01 | Login web dengan akun sah | Buka `/login` → isi email & sandi → Masuk | Akun OPS UJI | Masuk ke beranda | Beranda "Selamat sore, ops" tampil | Pass |
| TC-02 | Login web dengan sandi salah (R-21) | Isi sandi salah → Masuk | Akun OPS UJI, sandi salah | Pesan "Email atau kata sandi salah. Sisa N percobaan." | Tampil "Sisa 4 percobaan", lalu "Sisa 3 …" | Pass |
| TC-03 | Pilihan ketua/anggota saat OPS membuat SK hanya staf lapangan | Work plan → Buat SK → isi judul, lokasi, tanggal 12–13 Okt | Akun OPS UJI | Hanya 4 teknisi; OM/OPS, Admin, HR, Finance, PM **tidak** muncul | Ketua & anggota: Teknisi Anggota, Teknisi Dua, Teknisi Ketua, Teknisi Unit Lain. Pegawai kantor tidak ada | Pass |
| TC-04 | OPS boleh memilih PM & personel lintas unit (R-23) | Di dialog yang sama | Akun OPS UJI | Pilihan PM tampil; teknisi unit lain boleh | Pilihan PM: "PM UJI Lapangan"; Teknisi Unit Lain tersedia | Pass |
| TC-05 | Simpan SK draf + tim (tulis → baca ulang) | Pilih PM, ketua Teknisi Ketua, anggota Teknisi Anggota + Teknisi Unit Lain → Simpan | Akun OPS UJI | SK draf tersimpan dengan tim tersebut | Halaman SK draf; DB: LEADER Teknisi Ketua (LAP), MEMBER Teknisi Anggota (LAP), Teknisi Unit Lain (LAIN) | Pass |
| TC-06 | PM hanya dapat menambah personel unitnya | Login PM → buka SK → Atur tim | Akun PM UJI | Teknisi unit lain tidak ditawarkan sebagai orang baru | Pilihan tambahan hanya teknisi unit LAP | Pass |
| TC-07 | Dialog "Atur tim" memuat tim saat ini | Login PM → Atur tim | Akun PM UJI | Ketua terpilih, anggota lama tercentang, anggota lintas unit pilihan OPS tetap tampil | **Sebelum perbaikan:** ketua "Pilih ketua", anggota tidak tercentang, Teknisi Unit Lain tidak tampil → bila disimpan, anggota itu hilang diam-diam. **Setelah perbaikan (web `TeamDialog`):** ketua Teknisi Ketua, Teknisi Anggota ✓, Teknisi Unit Lain ✓ | Fail → diperbaiki → Pass |
| TC-08 | PM menambah anggota tanpa menghapus anggota lintas unit (aturan R-26: unit PM hanya untuk orang baru) | Centang Teknisi Dua → Simpan | Akun PM UJI | "Tim disimpan."; anggota lintas unit tetap | Toast "Tim disimpan."; DB: 4 anggota aktif, Teknisi Unit Lain tetap | Pass |
| TC-09 | Ganti ketua lewat `PATCH` ke luar unit / pegawai kantor ditolak | Uji otomatis API (tidak ada jalur UI yang menawarkan pilihan ini) | — | 422 `PERSONNEL_OUTSIDE_PM_UNIT` / `PERSONNEL_NOT_FIELD_STAFF` | 3 uji `test_plan_assignment_scope.py::*patch*` lulus | Pass (otomatis) |
| TC-10 | Isi hari kerja & terbitkan SK | Tambah hari 12 & 13 Okt (nama + deskripsi) → Terbitkan SK → Ya, terbitkan | Akun PM UJI | Nomor SK terbit; petunjuk agar ketua membuka HP | `SK-202609-0cb82dfb` terbit; teks "Minta ketua membuka aplikasi mobile …" | Pass |
| TC-11 | HP: ketua melihat SK terbit | HP → login ketua → Surat Kerja | Akun ketua UJI | SK muncul berstatus Terbit, label "Anda ketua" | Tampil, dengan 2 hari kerja | Pass |
| TC-12 | HP: ketua menerima SK (R-23) | Buka SK → Terima SK → Terima | Akun ketua UJI | Status Diterima; dokumen SK berlaku dan ditandatangani ketua | HP: "Diterima". DB: `ACCEPTED`; dokumen `INITIAL_ORDER` `EFFECTIVE`, diterima oleh Teknisi Ketua UJI | Pass |
| TC-13 | HP: staf lapangan tidak melihat kartu kantor (R-21) | Profil | Akun ketua UJI | Label "Karyawan lapangan", tanpa kartu kantor | Sesuai | Pass |
| TC-14 | HP: PM melihat kartu "Segera hadir" dan tetap bisa absen (R-21) | Keluar → login PM | Akun PM UJI | Kartu "Menu Project Manager — Segera hadir"; tombol Absen masuk ada | Sesuai | Pass |

Uji otomatis pada kode yang sama:
- API: ruff & mypy bersih; suite penuh di DB UJI (hasil di §4).
- Web: lint & typecheck bersih; `workplans.test.tsx` 13/13.
- Mobile: tidak ada perubahan kode mobile; `flutter test` 77/77 dan analyze bersih (2026-09-29).

## 3. Catatan & rekomendasi

| # | Temuan | Tingkat | Tindak lanjut |
|---|---|---|---|
| T-1 | TC-07: dialog "Atur tim" tidak memuat tim saat ini (komentar kode lama "API tidak mengirim daftar anggota" sudah basi; `GET /members` ada) | Sedang (risiko data hilang) | **Diperbaiki** dalam R-26 + uji web baru |
| T-2 | Nama yang tampil di web ("Selamat sore, ops") dan HP (Profil "leader") diambil dari email, bukan nama lengkap karyawan | Rendah | Usulan: `/auth/me` membawa nama karyawan. Dicatat untuk keputusan (bukan bagian R-26) |
| T-3 | Absensi di lokasi (docs/22 C1–C4) dan luring/sinkron (E1–E7) belum diuji pada putaran ini | — | Putaran berikutnya; perlu titik lokasi uji sesuai posisi HP |
| T-4 | Uji nyata menemukan bahwa suite API dan API lokal selama ini menulis ke **DB & MinIO produksi** (docs/24 A-00) | Kritis (proses) | Ditutup: DB/MinIO UJI terpisah + penjaga `tests/db_guard.py` (uji menolak berjalan ke produksi) |

Catatan penguji: dua kali login gagal pada TC-01 disebabkan penguji salah mengetik huruf pertama sandi
(q/Q), bukan bug. Hal ini terbukti lewat sidik jari hash sandi di log API sementara, yang sudah dihapus.
