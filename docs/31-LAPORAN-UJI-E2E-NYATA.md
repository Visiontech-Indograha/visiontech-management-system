# 31 — Laporan uji end-to-end nyata dengan data user asli

Rencana: pemilik meminta bukti keberhasilan sistem lewat uji end-to-end dengan **akun dan data karyawan asli**.
Lingkungan (keputusan pemilik 2026-10-06): **lokal, salinan data produksi** — dump prod (`visiontech_db_20261006_1924_sebelum_bersih`)
dipulihkan ke DB `vms_e2e`, lalu dibersihkan dengan `real.sql` dan ditata dengan `hierarki.sql` (hasil sama dengan dry-run di prod).
API lokal :8000 (`FACE_ENROLLMENT_REQUIRED=true`), face-service :8001, web :5173, Realme untuk HP. **DB produksi tidak diubah oleh uji ini.**
Sandi uji hanya di salinan lokal (tidak di repo). Bukti mentah: `docs/bukti-e2e/`.

## Ringkasan (diperbarui 2026-10-06 malam)
| Kelompok | Status | Cara |
|---|---|---|
| A. Akun, peran, hierarki | **12/12 lulus** | skrip API + SQL (`bukti-e2e/skenario-A-akun-hierarki.txt`) |
| E1–E3, E5, F1 (SK v2, absen di titik SK, otorisasi negatif) | **15/15 lulus** | skrip API akun asli (`bukti-e2e/skenario-E-F-sk-otorisasi.txt`) |
| B. Wajah — pendaftaran dan gerbang | menunggu uji fisik pemilik | HP Realme (gerakan nyata) + webcam laptop |
| C. Wajah — absensi online | menunggu uji fisik | HP + web |
| D. Luring | menunggu uji fisik | HP mode pesawat |
| E4. Adendum, aset, laporan harian/mingguan, penutupan | menunggu | web + HP |

## A. Akun, peran, hierarki — hasil
- A1 Administrator `ageng@visiontech.id` login **web dan HP** lulus (setelah perbaikan T2); tidak kena gerbang wajah.
- A2 PM **Ramadani** (unit CCTV & ACS): 17 personel dapat ditugaskan (CCTV_ACS + bekas Site Support/Electrical); PM **Handoko** (Wall Display): 2 (Ahmadi, Shofan). **Azman** tidak punya izin PM.
- A3 Kanal: lapangan di web ditolak (`NOT_OFFICE_ACCOUNT`), kantor di HP ditolak (`NOT_FIELD_STAFF`); kebalikannya diterima.
- A4 Unit sampah impor hilang (8 unit bersih), nomor pegawai bersih, 1 organisasi.

## E/F — hasil (SK v2 dengan akun asli)
PM Ramadani membuat SK (lokasi baru dari koordinat peta, 2 hari, ketua Yulfi, anggota Asrul + Heru) → terbit → notifikasi ke ketua →
ketua menerima → **Berjalan** → anggota melihat lokasi SK dan absen di titik → **AUTO_VALID (jarak 0 m)**; absen 1,4 km dari titik tanpa
penjelasan ditolak; PM Handoko tidak melihat SK unit Ramadani (404); teknisi tidak bisa membuat SK dan tidak bisa memakai pencarian alamat;
Finance (izin `manage:sites`) boleh mencari alamat.

## Temuan
| # | Temuan | Status |
|---|---|---|
| T1 | PM Ramadani **bisa menunjuk ketua dari unit lain** (Wall Display) dan daftar calon ketua memuat 19 orang semua unit; hanya anggota yang dibatasi unit | **Menunggu keputusan pemilik**: dibatasi ke unit PM, atau ketua lintas unit memang diizinkan |
| T2 | Administrator (tanpa karyawan) **ditolak login di HP** | **Diperbaiki** (PR #20) |
| T3 | PM hanya mengenal **satu unit** (unit karyawannya); Ramadani/Handoko di unit MANAGEMENT → daftar bawahan kosong | **Diatasi lewat data** (`hierarki.sql`: gabung unit; keputusan pemilik) |
| T4 | Pencarian alamat (`/geo/search`) hanya untuk pembuat SK; Finance (kantor) tidak bisa memakai peta lokasi dinamis | **Diperbaiki** (PR #19) |
| T5 | Dialog "Tambah lokasi kerja" hanya isian lintang/bujur | **Diperbaiki** (PR #19: peta, cari alamat, penanda, lat/long manual) |

## Langkah uji fisik (menunggu pemilik)
Akun uji ada di `.local_tests/e2e-logins.txt` (mesin lokal). APK debug terhubung ke `127.0.0.1:8000` lewat `adb reverse`.
- **B1 (HP):** login teknisi (mis. Asrul) → gerbang wajib daftar → persetujuan → kamera: ikuti tantangan acak, coba arah salah untuk melihat pesan "salah arah", jauh/dekat, "luruskan wajah".
- **B2 (web, webcam laptop):** login Azman di `http://127.0.0.1:5173` → gerbang → persetujuan → webcam.
- **C1/C3/C4:** absen masuk/pulang dengan wajah (cocok), orang lain (NO_MATCH → Perlu review), web kantor dengan verifikasi webcam, dan face-service dimatikan.
- **D1:** mode pesawat → absen luring → sinyal kembali → sinkron (ditandai Perlu review; pencocokan wajah luring di HP belum ada).
- **E4:** adendum, serah terima aset, laporan harian/mingguan, laporan akhir, penutupan.

## Batas yang diketahui (jujur)
Pencocokan wajah di HP saat luring belum dibangun; face-service belum terpasang di server produksi; kalibrasi FAR/FRR (P8-5) belum dilakukan;
lisensi komersial model InsightFace belum diputuskan.
