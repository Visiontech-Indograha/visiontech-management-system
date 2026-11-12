# Uji kegunaan (usability testing)

Tujuan: mengukur seberapa mudah orang awam memakai VMS untuk tugas nyata mereka. Ini berbeda dari uji fungsi (apakah fitur jalan) dan E2E (apakah alur lulus). Uji kegunaan mencari tempat orang bingung, salah klik, atau menyerah.

## 1. Kapan dijalankan
- Sebelum rilis MINOR atau MAJOR yang menyentuh layar.
- Setelah perubahan UX besar: ganti istilah, ganti tata letak, ganti navigasi, layar baru (mis. persetujuan wajah, inspeksi kendaraan).
- Ulang untuk peran yang temuannya berat setelah diperbaiki.
- Rilis PATCH tanpa perubahan layar tidak perlu.

## 2. Peserta
- 5 pengguna awam per peran (karyawan, ketua tim, HR, Finance, OM, PM, HSE). Lima orang cukup menemukan sebagian besar masalah; tambah 5 lagi hanya bila temuan masih banyak.
- Bukan pengembang, bukan orang yang ikut merancang. Idealnya pekerja sungguhan. Satu orang tidak dipakai dua kali untuk layar yang sama.
- Akun uji pemilik/QA, data uji dihapus setelah dipakai. Jangan sentuh aplikasi produksi di HP pengguna.

## 3. Tugas nyata per peran
Tulis 4-6 tugas per peran sebagai tujuan, bukan langkah. Contoh: "Anda sakit besok, ajukan cuti." Jangan menyebut nama menu atau tombol.
- Karyawan (HP): absen masuk, ajukan cuti, lihat jadwal hari ini, baca dan konfirmasi K3.
- Ketua tim: lihat tim hari ini, bantu anggota yang gagal absen.
- HR: tambah karyawan, setujui dokumen, kelola mess.
- Finance: ekspor rekap absensi, cek lembur.
- OM/PM: buat tugas klien, susun jadwal, setujui pengajuan.
- HSE: terbitkan K3 untuk satu kantor.
Tiap tugas punya hasil jadi yang jelas dan batas waktu (mis. 3 menit).

## 4. Ukuran
| Ukuran | Cara |
|---|---|
| Tingkat selesai | Selesai sendiri / selesai dengan bantuan / gagal, per tugas |
| Waktu | Detik dari mulai sampai selesai (bandingkan dengan batas) |
| Salah klik | Hitung klik atau ketukan yang bukan jalur benar, dan berapa kali kembali |
| Kepuasan | Skor kemudahan 1-5 per tugas; di akhir SUS 10 pertanyaan (versi Indonesia) atau 3 pertanyaan ringkas bila waktu singkat |
| Kebingungan istilah | Catat kata yang ditanyakan atau ditafsir salah |

## 5. Skrip fasilitator
1. Sambut, jelaskan: "Kami menguji aplikasinya, bukan Anda. Tidak ada jawaban salah."
2. Minta izin catat layar dan suara. Beri tahu boleh berhenti kapan saja.
3. Minta peserta berpikir keras ("ceritakan apa yang Anda lihat dan pikirkan").
4. Berikan satu tugas pada satu waktu, dibaca apa adanya.
5. Diam. Jangan memberi petunjuk, jangan menunjuk. Bila macet 60 detik, tanya "apa yang Anda cari?"; bila 2 menit atau lebih, catat "dibantu" lalu lanjut.
6. Setelah tiap tugas: skor kemudahan 1-5.
7. Akhir: SUS atau 3 pertanyaan ringkas, lalu "Apa yang paling membingungkan?"
8. Ucapkan terima kasih; hapus data uji.

## 6. Bentuk laporan
Satu berkas per putaran uji, singkat:
- Ringkasan: versi, tanggal, peran, jumlah peserta.
- Tabel tugas x peserta: selesai, waktu, salah klik, skor.
- Skor SUS rata-rata per peran.
- Temuan berurut dampak: P1 (menggagalkan tugas), P2 (memperlambat), P3 (kosmetik). Tiap temuan: layar, apa yang terjadi, kutipan peserta, saran, bukti (tangkapan layar).
- Daftar istilah yang membingungkan.
- Putusan: LULUS / TIDAK LULUS.

## 7. Kriteria lulus (per peran)
- Tingkat selesai tanpa bantuan minimal 80% dari semua tugas, dan tidak ada tugas dengan gagal pada 2 peserta atau lebih.
- Waktu median tiap tugas di dalam batas.
- SUS rata-rata minimal 68 (atau skor ringkas rata-rata minimal 4 dari 5).
- Nol temuan P1 yang belum ditangani.
Tidak lulus: rilis ditahan, temuan P1 dikirim ke arsitek sebagai brief, uji ulang peran itu.

## 8. Catatan
- Temuan kegunaan bukan keputusan bisnis; usulan istilah atau alur baru dibawa ke pemilik dengan format keputusan.
- Pedoman layar dan glosarium: skill `vms-ux-design-system`.
