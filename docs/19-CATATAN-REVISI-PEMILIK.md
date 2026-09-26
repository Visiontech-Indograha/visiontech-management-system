# 19 · Catatan Revisi Pemilik & PM

Daftar tunggal semua permintaan perubahan dari pemilik produk dan PM, beserta keputusan dan
statusnya, supaya tidak ada yang terlupa. Rincian teknis keputusan tetap di `docs/10` dan
`CHANGELOG.md`; berkas ini adalah indeksnya.

**Cara memakai:** setiap permintaan baru → tambah satu baris di tabel "Revisi" (tanggal, siapa,
permintaan apa adanya, keputusan, status). Ubah status saat dikerjakan; jangan hapus baris.

Status: **Selesai** · **Berjalan** · **Menunggu keputusan** · **Ditunda (pasca-MVP)**

## Revisi

| # | Tanggal | Dari | Permintaan | Keputusan / cara dikerjakan | Status |
|---|---|---|---|---|---|
| R-01 | 2026-09-25 | Pemilik | PM melihat rekap lembur untuk unitnya sendiri (V-28) | Rekap lembur: PM unit hanya unitnya; Finance/HR/OPS/Admin seluruh organisasi | Selesai |
| R-02 | 2026-09-25 | Pemilik | Tambah fitur "hapus karyawan" | Dikerjakan sebagai **arsip & pulihkan** (data historis tetap), plus **offboarding** (akhiri masa kerja, cabut akses) | Selesai |
| R-03 | 2026-09-26 | Pemilik | Kunci tanda tangan dokumen (fase 6) | Kunci Ed25519 lokal dari env dulu; **adaptor KMS wajib sebelum produksi** | Selesai (KMS: Ditunda sebelum produksi) |
| R-04 | 2026-09-26 | Pemilik | Kapan dokumen SK ditandatangani | Otomatis: PM = penerbit saat terbit, ketua = penerima saat menerima SK | Selesai |
| R-05 | 2026-09-26 | Pemilik | Utamakan fitur MVP saja; backend & web dulu, lalu mobile | Cuti, logbook kendaraan, notifikasi dikeluarkan dari MVP mobile (tidak ada endpoint MVP) | Selesai |
| R-06 | 2026-09-26 | PM (sprint) | Lokasi penugasan lewat **titik koordinat**: cari kota (mis. Dumai) lalu tetapkan titik pasti, untuk SK yang dibuat **dan yang sedang berjalan** | Pemilik: **tanpa adendum** — pada SK berjalan hanya titik absensi & radius yang berubah (tercatat di audit), teks lokasi dokumen tetap. Peta **Leaflet + OpenStreetMap**, pencarian kota lewat backend (Nominatim). Mobile: absen masuk mendahulukan titik SK berjalan | Selesai (kode); uji di peramban & HP belum |
| R-07 | 2026-09-26 | Pemilik | Deploy ke server; hapus backend & frontend lama | Kontainer lama dihapus (dengan persetujuan); API :8000 & web :8080 baru jalan; DB & MinIO tidak disentuh | Selesai |
| R-08 | 2026-09-26 | Pemilik | Laporan progres dalam bentuk PPT (persentase jadi/belum) | Deck 8 slide (Artifact Slides, unduh .pptx/PDF) | Selesai — perbarui tiap sprint |
| R-10 | 2026-09-26 | Pemilik | Validasi absensi dilakukan juga oleh **PM per divisinya** | PM memeriksa (setujui/tolak + catatan) absensi `NEEDS_REVIEW` karyawan di unit yang dipegangnya; di luar unit ditolak. OPS lintas unit, Finance tetap seluruh organisasi; ekspor CSV tetap Finance. PM melihat daftar absensi unitnya di web | Selesai (kode + uji API); swafoto: lihat Q-06 |
| R-09 | 2026-09-26 | Pemilik | Desain Figma sampai prototype | Prototype 5 alur (web & mobile) terhubung; layar menu samping PM & kamera swafoto belum; **desain ditunda** atas permintaan pemilik ("desain nanti saja") | Ditunda |

## Menunggu keputusan pemilik

| # | Pertanyaan | Pilihan | Dampak bila dibiarkan |
|---|---|---|---|
| Q-01 | Batas ukuran unggahan berkas | API sekarang 10 MB; dok 13 menyebut 15/25 MB | Foto/dokumen besar ditolak |
| Q-02 | Berkas logo perusahaan | Kirim berkas logo (SVG/PNG) | Desain & PDF SK memakai placeholder |
| Q-03 | Label status aset `RETIRED` | Usulan: "Dipensiunkan" | Label tampil sebagai kode |
| Q-04 | Domain + HTTPS untuk staging/produksi | Nama domain | Sesi web tidak bisa diperpanjang otomatis (cookie Secure), kamera/GPS peramban terbatas |
| Q-05 | HR boleh melihat swafoto absensi? (V-17) | Ya / Tidak | Sekarang hanya pemilik & Finance/Admin |
| Q-06 | PM boleh melihat swafoto absensi karyawan unitnya saat memvalidasi (R-10)? | Ya / Tidak | PM memvalidasi dari jarak, lokasi, dan penjelasan saja, tanpa foto |
