# Laporan uji perilaku manusia (29 Oktober 2026)

Uji nyata di lingkungan **lokal** (web Chrome, HP Android Dev flavor, API langsung), mengikuti `docs/diagram/05-matriks-uji.md`.
Hanya DB dev; produksi/beta tidak disentuh. Data uji berawalan `UJI-`.
Status diperbarui setelah PR #186, #193, #197, #201, #209, #210, #211, #212, #213 dan B5 (runbook Uptime Kuma, logo NoSuchKey).

## Cakupan
| Jalur | Cakupan | Status |
|---|---|---|
| API: otorisasi peran, IDOR, validasi, transisi, berkas, ekspor | 246 kasus (225 lulus, 18 temuan, 3 tak teruji) | selesai; temuan diperbaiki (lihat bawah) |
| Web PM (pm1): master data, jadwal, kirim/setujui/tolak/salin/massal, pindah hari, koreksi, pekerjaan klien, BAST, ekspor DOCX/PPTX | ±40 langkah | selesai |
| HP lapangan (ketua11): login, jadwal, mulai hari, foto wajib, hasil sebagian, pindah hari, laporan, selesai, koreksi/revisi, sinkron | alur utuh | selesai |
| Web modul lain (cuti, proyek, klien, otorisasi halaman) | PM1 dan OM | **sebagian** |
| Belum teruji | survei ACS/CCTV (tak ada data), BAST tanda tangan (HP), absen wajah (layanan wajah dev 503), lembur, mess/aset ajukan, unggah dokumen pribadi, akun HR/SUPER_ADMIN/PM2 di web, offline/antrean | lihat "Belum teruji" |

## Sudah diperbaiki
| ID | Temuan | Perbaikan |
|---|---|---|
| T1 | ADMIN lama melewati `require_permission` termasuk hapus permanen (`DELETE_ANY`) | PR #186 + uji |
| T7 | Jadwal bisa ditutup lewat `/complete` saat koreksi terbuka | PR #193 (409 `CORRECTION_OPEN`) + uji |
| B1 | **500** ubah proyek: form web mengirim `pm_id` null, menjadi string `'None'` | PR #201 + uji |
| B2 | **500** kirim/setujui jadwal tanpa nama lokasi (`notification.body` NULL) | PR #201 + uji |
| T14 | Komentar jam buka absen 07:00 vs nilai 06:45 (06:45 dikonfirmasi pemilik) | PR #197 |
| T4 | Pemetaan status survei didokumentasikan | PR #197 |
| A1 | PM divisi lain melihat absensi dan swafoto pekerja divisi lain | PR #211 (hanya PM divisi terkait) + uji |
| A2 | `/work-plans/daily/{id}/assets` dan `/orders/{id}/schedule` memberi 200 `[]` tanpa cek akses | PR #211 (cakupan aset/jadwal/order) |
| A3 | `GET /clients` terbuka untuk EMPLOYEE dan TEAM_LEADER | PR #211 |
| A4 | Unggah byte identik membocorkan `file_id` milik orang lain | PR #211 (dedup per pemilik) |
| A5 | Validasi berkas hanya magic bytes; PNG terpotong dan HEIC palsu diterima | PR #211 (dekode gambar); HEIC asli diterima di PR #213 |
| A6 | `/files/{id}` tanpa `X-Content-Type-Options: nosniff` | PR #211 (header; `attachment` untuk non-gambar) |
| A8 | Peran FINANCE tidak ada di model V2; `finance@` = EMPLOYEE | PR #213 (peran FINANCE + jangkauan PM atas absensi tim) |
| T3 | Finance tinjau absensi (butuh peran V2 baru) | PR #213 |
| T13 | `CurrentUser.role = roles[0]` | PR #211 dan #213 (`has_role` untuk seluruh daftar peran) |
| W1 | Salinan jadwal kehilangan item; salinan kosong bisa diajukan | PR #213 (salin item; `PLAN_EMPTY` 422) |
| W2 | Target tanpa batas maksimum; galat tak menunjuk kolom | PR #213 (batas `le`, dua desimal, selaras kolom DB) |
| W3 | Fase item tidak mengikuti template pekerjaan | PR #213 (`PHASE_BY_KIND`) |
| W4 | Label cuti "Disetujui HR" tampil setelah OM yang menyetujui | PR #210 + uji web |
| W6 | Header jadwal "Selesai 100%" saat item dipindah | PR #210 (persen dari item aktif) |
| W8 | Proyek: nomor kontrak tanpa `max_length` | PR #213 (batas selaras kolom DB) |
| W9 | Dialog hapus proyek ambigu; "hapus" sebenarnya mengarsipkan | PR #210 (istilah "Arsipkan" dan penjelasan) |
| W11 | Jenis pekerjaan: material tanpa galat; kebutuhan 0 diterima; satuan "Unit" terisi | PR #210 |
| W12 | Pekerjaan klien: galat merah tetap tampil; tidak ada kolom cari | PR #210 |
| W14 | Cari klien tanpa hasil memakai "Belum ada klien terdaftar" | PR #210 (empty state klien) |
| H1 | HP: hari kerja bisa dimulai tanpa absen masuk | PR #209 (`CHECKIN_REQUIRED` 409) |
| H2 | HP: tidak ada tanda sukses setelah "Simpan hasil kerja"; chip "Selesai 100%" sebelum simpan | PR #209 |
| H3 | HP: hari bisa diselesaikan saat item menunggu pindah hari | PR #209 |
| H4 | HP: "PM … belum ada nomor HP" tampak seperti galat | PR #209 |
| O1 | Tiap rilis produksi memicu alarm Uptime Kuma sesaat | B5: panduan retry (Retries 3, interval 20 dtk) di `docs/RUNBOOK-PRODUKSI.md` bagian 10 |
| O2 | Log API: MinIO `NoSuchKey` untuk logo pengganti | B5: fallback senyap (`core/storage.py`, log debug) + uji |

## Temuan terbuka (belum diperbaiki)

### Sedang
| ID | Temuan | Saran |
|---|---|---|
| A7 | Nama berkas `../../` tersimpan di metadata (Content-Disposition aman); field tak dikenal diterima; kode galat tak sesuai dokumen (400 vs 422; 422 vs 409); tiket berkas di `?token=` | Rapikan kode galat dan tiket berkas |
| A9 | Di web, PM tidak punya tombol ajukan mess dan "Berkas saya" PM1 tanpa tombol unggah | Perjelas alur |
| W5 | Rekap bulanan 27/28 Okt tidak konsisten (lintas hari, "Luar kota", lokasi Kantor Utama Medan untuk tim Pekanbaru) | Selidiki data seed vs logika rekap |
| W10 | Klik pertama "Setujui revisi" kadang tidak berefek (harus klik dua kali) | Belum ditemukan penyebabnya |
| W13 | Klik di luar dialog menutup form tanpa konfirmasi (kecuali form cuti) | Belum ada perubahan kode |
| W7 | Klien: nama `<script>…` dan emoji tersimpan. Skema baru memangkas spasi, pola nama belum dibatasi | Tambah validasi pola nama |

### Rendah / UX
| ID | Temuan |
|---|---|
| W15 | Efisiensi: ±40 klik untuk satu jadwal 2 item; nama lokasi tidak terisi otomatis; tidak ada tombol Hapus pada jadwal DISETUJUI |

### Model/aturan dari diagram yang belum ditangani
| ID | Temuan |
|---|---|
| T2 | ADMIN lolos CREATE_PLAN tetapi approve/submit ditolak |
| T5 | `CANCELLED` tak pernah ditulis |
| T12 | Ketua BAST vs ketua jadwal beda sumber |
| T16 | Ubah/hapus proyek dan klien tak cek divisi |

T10/T11 (urutan ACC–BAST) diputuskan tidak wajib.

## Belum teruji
- Survei ACS/CCTV (tidak ada data; tak ada tombol buat tugas di web); format video wall dan IT belum ada.
- Tanda tangan BAST di HP, ACC, ekspor BAST final PDF, ekspor survei/BoQ. **Ekspor PDF belum berjalan di Windows lokal.**
- Absen wajah + GPS (layanan wajah dev 503), absen luar radius, absen offline, antrean sinkron saat offline.
- Lembur (hanya saat jadwal berjalan; jadwal sudah selesai sebelum diuji).
- Mess/aset (ajukan, pinjam), unggah dokumen pribadi (PDF/DOCX/PNG valid dan salah), akun HR/SUPER_ADMIN/PM2.
- Batas ukuran tanda tangan 300.000 byte, foto wajah 5 MB tepat.

## Keputusan pemilik
Keputusan lama yang sudah diterapkan: Finance sebagai peran V2 (T3, #213); hari kerja wajib absen masuk (H1, #209); item menunggu pindah hari menahan penyelesaian hari (H3, #209); jadwal tanpa item tidak bisa diajukan (W1, #213); absensi lintas divisi hanya untuk PM divisi terkait (A1, #211).

## Domain subkontraktor CCTV/ACS/Video wall/IT (dari riset dan diagram)
Celah terhadap alur lazim: format survei hanya ACS/CCTV; tidak ada kolom serial/IP/MAC per titik, checklist uji commissioning/ATP, punch list, rekap material vs BoQ, pengingat garansi/retensi, paket BAST lengkap (as-built + berita acara uji + kredensial). Detail: rencana `uji-menyeluruh-web-mobile-work-v2.md` bagian A–B dan D.
