# Laporan uji perilaku manusia (29 Oktober 2026)

Uji nyata di lingkungan **lokal** (web Chrome, HP Android Dev flavor, API langsung), mengikuti `docs/diagram/05-matriks-uji.md`.
Hanya DB dev; produksi/beta tidak disentuh. Data uji berawalan `UJI-`.

## Cakupan
| Jalur | Cakupan | Status |
|---|---|---|
| API: otorisasi peran, IDOR, validasi, transisi, berkas, ekspor | 246 kasus (225 lulus, 18 temuan, 3 tak teruji) | selesai |
| Web PM (pm1): master data, jadwal, kirim/setujui/tolak/salin/massal, pindah hari, koreksi, pekerjaan klien, BAST, ekspor DOCX/PPTX | ±40 langkah | selesai |
| HP lapangan (ketua11): login, jadwal, mulai hari, foto wajib, hasil sebagian, pindah hari, laporan, selesai, koreksi/revisi, sinkron | alur utuh | selesai |
| Web modul lain (cuti, proyek, klien, otorisasi halaman) | PM1 dan OM | **sebagian** |
| Belum teruji | survei ACS/CCTV (tak ada data), BAST tanda tangan (HP), absen wajah (layanan wajah dev 503), lembur, mess/aset ajukan, unggah dokumen pribadi, akun HR/SUPER_ADMIN/PM2 di web, offline/antrean | lihat "Belum teruji" |

## Sudah diperbaiki dalam sesi ini (di `prod`)
| ID | Temuan | Perbaikan |
|---|---|---|
| T1 | ADMIN lama melewati `require_permission` termasuk hapus permanen (`DELETE_ANY`) | PR #186 + uji |
| T7 | Jadwal bisa ditutup lewat `/complete` saat koreksi terbuka | PR #193 (409 `CORRECTION_OPEN`) + uji |
| B1 | **500** ubah proyek: form web mengirim `pm_id` null, menjadi string `'None'` | PR #201 + uji |
| B2 | **500** kirim/setujui jadwal tanpa nama lokasi (`notification.body` NULL) | PR #201 + uji |
| T14 | Komentar jam buka absen 07:00 vs nilai 06:45 (06:45 dikonfirmasi pemilik) | PR #197 |
| T4 | Pemetaan status survei didokumentasikan | PR #197 |

## Temuan terbuka (belum diperbaiki)

### Tinggi
| ID | Temuan | Saran |
|---|---|---|
| A1 (T-01) | PM divisi lain dapat melihat absensi pekerja divisi lain di `GET /attendance` (lokasi, jam, jarak, `face_similarity`, `selfie_file_id`) dan tiket URL swafoto | Batasi daftar absensi ke divisi/relasi PM; uji IDOR absensi |

### Sedang
| ID | Temuan | Saran |
|---|---|---|
| A2 (T-02) | `GET /work-plans/daily/{id}/assets` dan `/orders/{id}/schedule` memberi 200 `[]` untuk ID acak dan semua peran (tanpa cek kepemilikan); pinjaman aset terlihat oleh semua pengguna `VIEW_TEAMS` | Cek akses jadwal/order; filter divisi |
| A3 (T-03) | `GET /clients` terbuka untuk EMPLOYEE dan TEAM_LEADER (memuat `pic_name`, `pic_phone`) | `require_permission` |
| A4 (T-04) | Unggah byte identik oleh pengguna lain mengembalikan `file_id` milik orang lain ("File sudah ada") — membocorkan keberadaan berkas | Dedup per pemilik |
| A5 (T-05) | Validasi berkas hanya magic bytes: PNG terpotong 18 byte dan HEIC palsu 324 byte diterima | Validasi dekode (Pillow) untuk gambar |
| A6 (T-06) | `/files/{id}` tanpa `X-Content-Type-Options: nosniff`; PDF inline dari origin API | Tambahkan header; `attachment` untuk non-gambar |
| W1 | Salinan jadwal kehilangan item pekerjaan; salinan kosong bisa diajukan dan disetujui | Salin item; larang kirim jadwal tanpa item (T-11) |
| W2 | Target desimal (1,5) diterima; target 99999999999 hanya "Ada isian yang belum benar" tanpa menunjuk kolom | Batas maksimum + pesan per kolom |
| W3 | Fase item tidak mengikuti template pekerjaan (template Instalasi tetap menyimpan fase Survei) | Isi fase dari template |
| W4 | Status label cuti "Disetujui HR" tampil setelah OM yang menyetujui | Label sesuai pemberi persetujuan |
| W5 | Rekap bulanan 27/28 Okt tidak konsisten (lintas hari, "Luar kota", lokasi Kantor Utama Medan untuk tim Pekanbaru) | Selidiki data seed vs logika rekap |
| W6 | Header jadwal 29 Okt "Selesai 100%" padahal "1 dari 2 pekerjaan selesai" setelah pindah hari | Hitung persen dari item aktif |
| W7 | Klien: nama `<script>…` dan emoji tersimpan tanpa validasi (aman karena React meng-escape, tetapi data kotor) | Sanitasi/validasi nama |
| W8 | Proyek: nomor kontrak ±150 karakter tersimpan (tanpa `max_length`) | `max_length` sesuai kolom |
| W9 | Dialog hapus proyek ambigu ("Hapus / Batalkan"); "hapus" sebenarnya mengarsipkan; tidak ada status Arsip; klien masih menghitung proyek arsip | Satu istilah + penjelasan dampak |
| O1 | Tiap rilis produksi memicu alarm Uptime Kuma sesaat (`/ready` gagal beberapa detik) | Kuma: retry 2–3 sebelum alarm |
| O2 | Log API: MinIO `NoSuchKey` untuk `logo_company.png`/`logo_client.png`; ekspor memakai logo bawaan | Unggah logo atau fallback senyap |

### Rendah / UX
| ID | Temuan |
|---|---|
| H1 | HP: hari kerja bisa dimulai tanpa absen masuk (mungkin disengaja; perlu keputusan) |
| H2 | HP: setelah "Simpan hasil kerja" tidak ada tanda sukses/pindah layar; chip menulis "Selesai 100%" sebelum simpan berhasil; banner galat menutupi tombol Simpan |
| H3 | HP: hari bisa diselesaikan saat item masih menunggu keputusan pindah hari (perlu keputusan) |
| H4 | HP: "PM … belum ada nomor HP" tampil di detail jadwal (informasi, tetapi tampak seperti galat) |
| W10 | Klik pertama "Setujui revisi" kadang tidak berefek (harus klik dua kali) |
| W11 | Jenis pekerjaan: material nama kosong tanpa galat; kebutuhan 0 diterima; satuan "Unit" terisi sebagai nilai (ketik "Meter" jadi "UnitMeter") |
| W12 | Pekerjaan klien: galat merah tetap tampil setelah kolom terisi; tidak ada kolom cari |
| W13 | Klik di luar dialog menutup form tanpa konfirmasi (kecuali form cuti yang sudah benar) |
| W14 | Cari klien tanpa hasil memakai "Belum ada klien terdaftar" (harus "tidak ada hasil"); validasi tanggal ganda (native + kustom); judul tab verifikasi "Halaman tidak ditemukan" padahal tampil |
| W15 | Efisiensi: ±40 klik untuk satu jadwal 2 item; nama lokasi tidak terisi otomatis dari hasil cari; tidak ada tombol Hapus pada jadwal DISETUJUI (harus Kembalikan → Draf → Hapus) |
| A7 | Nama berkas `../../` tersimpan di metadata (Content-Disposition aman); field tak dikenal diterima; kode galat tak sesuai dokumen (400 vs 422; 422 vs 409); tiket berkas di `?token=` |
| A8 | Peran FINANCE tidak ada di model V2 (hanya 6 `system_role`); akun `finance@` = EMPLOYEE; izin legacy OPS/FINANCE tidak berlaku (T3) |
| A9 | Di web, PM tidak punya tombol ajukan mess dan "Berkas saya" PM1 tanpa tombol unggah — alur belum jelas |

### Temuan model/aturan dari diagram yang belum ditangani
T2 (ADMIN lolos CREATE_PLAN tetapi approve/submit ditolak), T3 (Finance tinjau absensi — butuh peran V2 baru), T5 (`CANCELLED` tak pernah ditulis), T10/T11 (urutan ACC–BAST: diputuskan tidak wajib), T12 (ketua BAST vs ketua jadwal beda sumber), T13 (`CurrentUser.role = roles[0]`), T16 (ubah/hapus proyek dan klien tak cek divisi).

## Belum teruji
- Survei ACS/CCTV (tidak ada data; tak ada tombol buat tugas di web); format video wall dan IT belum ada.
- Tanda tangan BAST di HP, ACC, ekspor BAST final PDF, ekspor survei/BoQ.
- Absen wajah + GPS (layanan wajah dev 503), absen luar radius, absen offline, antrean sinkron saat offline.
- Lembur (hanya saat jadwal berjalan; jadwal sudah selesai sebelum diuji).
- Mess/aset (ajukan, pinjam), unggah dokumen pribadi (PDF/DOCX/PNG valid dan salah), akun HR/SUPER_ADMIN/PM2.
- Batas ukuran tanda tangan 300.000 byte, foto wajah 5 MB tepat.

## Keputusan yang diperlukan dari pemilik
1. Finance sebagai peran V2 baru (migrasi enum) atau tidak? (T3)
2. Hari kerja boleh dimulai tanpa absen masuk? (H1)
3. Hari boleh diselesaikan dengan item menunggu pindah hari? (H3)
4. Jadwal tanpa item boleh diajukan/disetujui? (W1/T-11)
5. Aturan akses absensi lintas divisi untuk PM (A1).

## Domain subkontraktor CCTV/ACS/Video wall/IT (dari riset dan diagram)
Celah terhadap alur lazim: format survei hanya ACS/CCTV; tidak ada kolom serial/IP/MAC per titik, checklist uji commissioning/ATP, punch list, rekap material vs BoQ, pengingat garansi/retensi, paket BAST lengkap (as-built + berita acara uji + kredensial). Detail: rencana `uji-menyeluruh-web-mobile-work-v2.md` bagian A–B dan D.
