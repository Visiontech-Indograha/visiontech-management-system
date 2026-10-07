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

## K. Absen di kantor tanpa/terikat SK (2026-10-07, emulator + web lokal, DB salinan prod)

Kode branch `fix/absen-kp-tanpa-sk` (PR #37), API lokal :8000, emulator Pixel (APK debug). Dua kantor: Kantor Visiontech Pekanbaru (r 500 m) dan Kantor Dumai (uji, hanya lokal).

| No | Langkah | Hasil | Status | Bukti |
|---|---|---|---|---|
| K1 | Heru (lapangan CCTV_ACS) membuka Absensi | Pilihan: lokasi SK + kedua kantor; pilih kantor → peringatan "bukan lokasi SK", tombol tetap aktif | Lulus | `bukti-e2e/K1-hp-peringatan-bukan-lokasi-sk.jpg` |
| K1b | Heru absen masuk di kantor (0 m) | Valid otomatis, tanpa tinjauan | Lulus | `bukti-e2e/K1b-hp-heru-absen-kantor-valid.jpg` |
| K2 | Yulfi absen di kantor 799 m (di luar radius) + penjelasan + swafoto | Perlu review; PM Ramadani melihatnya di web "Absensi anggota" | Lulus | `K2-hp-yulfi-perlu-review.jpg`, `K2-web-pm-tinjau.jpg` |
| K3 | PM menyetujui di web | Web: Disetujui; HP Yulfi: Disetujui, absen pulang terbuka | Lulus | `K3-web-pm-disetujui.jpg`, `K3-hp-yulfi-disetujui.jpg` |
| K4 | Heru absen pulang luring (mode pesawat + koneksi diputus) | "Absen pulang tersimpan luring" | Lulus | `K4-hp-luring-tersimpan.jpg` |
| K5 | Sinyal kembali | Sinkron otomatis (`POST /attendance/offline` 200), DB: pulang 11:49, AUTO_VALID, tanpa ganda | Lulus | `K5-hp-luring-tersinkron.jpg` |

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
