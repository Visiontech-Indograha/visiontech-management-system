# Uji pengguna awam dan template review UX

Catatan: skill `vms-qa` sudah memuat cara uji awam per peran, audit kebocoran data, dan Playwright. File ini fokus pada pedoman desain dan template review. Untuk pelaksanaan uji lengkap, ikuti `vms-qa`.

## 1. Tujuan

Memastikan pekerja lapangan dan atasan proyek yang awam teknologi bisa menyelesaikan tugas utama tanpa bantuan. Uji ini menemukan istilah yang membingungkan, layar yang kosong tanpa penjelasan, dan tombol yang tidak terlihat. Temuan uji awam pernah menghasilkan penggantian istilah (BAST, dll.), jadi uji ini punya dampak nyata (memori `vms-bahasa-sederhana`).

## 2. Kapan dijalankan

- Sebelum rilis layar kunci (absen, cuti, sinkron, popup K3, jadwal, serah terima).
- Setelah perubahan istilah atau alur.
- Minimal tiga pengguna per putaran. Lima pengguna mengungkap sebagian besar masalah utama (praktik umum usability, dari pengetahuan umum; belum diverifikasi sumber).

## 3. Cara menjalankan

### 3.1 Persiapan

1. Pilih peserta yang sesuai peran: pekerja lapangan (absen, cuti, sinkron), atasan proyek (jadwal, persetujuan), admin (data master). Jangan pakai orang tim pengembang.
2. Siapkan akun uji lokal dari `scripts/akun-uji-lokal.txt`. Data uji buatan sendiri dihapus setelah sesi (aturan `CLAUDE.md`). Jangan menebak sandi berulang (ada lockout).
3. Jangan pakai data produksi atau HP produksi pengguna (aturan `CLAUDE.md`). Gunakan HP uji atau HP peserta yang sudah disetujui, dengan APK dev.
4. Siapkan skenario tertulis dengan tujuan, bukan langkah. Contoh: "Anda baru tiba di lokasi. Catat kehadiran hari ini."
5. Siapkan alat rekam layar (izin peserta). Catat waktu sebelum tugas pertama selesai.

### 3.2 Saat sesi

- Jelaskan: "Kami sedang menguji aplikasinya, bukan Anda. Tidak ada jawaban salah."
- Jangan membantu kecuali peserta benar-benar buntu lebih dari batas (misalnya 2 menit). Catat jika membantu.
- Minta peserta berpikir keras (think aloud): "Apa yang Anda cari sekarang?"
- Jangan menjelaskan istilah. Catat istilah yang ditanyakan peserta. Itu temuan.
- Catat: tugas selesai atau tidak, jumlah tap salah, waktu, kata yang tidak dimengerti, tombol yang tidak ditemukan.

### 3.3 Setelah sesi

- Ringkas temuan per layar. Kelompokkan: istilah, alur, tombol, galat, kondisi kosong.
- Prioritaskan: tugas utama gagal lebih penting daripada salah tulis.
- Ubah istilah sesuai glosarium (`glosarium-bahasa.md`). Perbarui istilah yang diminta pemilik saja.
- Hapus data uji yang dibuat.

## 4. Template review UX (satu layar)

Salin dan isi untuk setiap layar yang direview.

```
Layar: <nama layar> (web | mobile) · Berkas: <path>
Pengguna: <peran> · Tujuan utama: <satu kalimat>

1. Tujuan dan aksi utama
   - Aksi utama terlihat tanpa scroll? (ya/tidak)
   - Ada lebih dari satu aksi utama? (ya/tidak)

2. Lima kondisi layar
   - Memuat (skeleton berbentuk konten): ada / tidak
   - Kosong (penjelasan + aksi): ada / tidak
   - Sebagian (peringatan jelas): ada / tidak / tidak perlu
   - Berhasil: ada / tidak
   - Galat (kalimat manusiawi + Coba lagi): ada / tidak

3. Bahasa
   - Istilah terlarang di layar (glosarium): <daftar>
   - Kalimat terlalu panjang atau teknis: <daftar>
   - Tombol memakai kata kerja: ya/tidak

4. Target dan kontras
   - Target sentuh 48 dp (mobile) atau 44 px (web aksi lapangan): ya/tidak/perlu cek
   - Kontras teks 4.5:1: ya/tidak/perlu cek (nilai: __:1)
   - Status tidak hanya warna (ikon + teks): ya/tidak

5. Aksesibilitas
   - Label tombol ikon: ya/tidak
   - Fokus terlihat dan urutan benar (web): ya/tidak/perlu cek
   - Skala teks 1.5 tidak memecah layout (mobile): ya/tidak/perlu cek
   - Reduced motion dihormati (animasi): ya/tidak/tidak ada animasi

6. Luring (offline)
   - Status sinkron atau data terakhir tampil: ya/tidak/tidak perlu

7. Token dan komponen
   - Warna dari token (tanpa hex atau kelas palet): ya/tidak
   - Komponen dari atom/molekul atau shared/ui: ya/tidak

8. Uji awam (bila dilakukan)
   - Peserta: <n> · Tugas selesai tanpa bantuan: <n>/<total>
   - Istilah yang tidak dimengerti: <daftar>
   - Tempat macet: <daftar>

9. Keputusan
   - Wajib perbaiki sebelum rilis: <daftar>
   - Perbaikan berikutnya: <daftar>
```

## 5. Skenario contoh (tujuan, bukan langkah)

| Layar | Tujuan | Keberhasilan |
|---|---|---|
| Absen | "Catat kehadiran Anda hari ini di lokasi." | Absen tersimpan (atau tersimpan offline dengan status jelas). |
| Cuti | "Ajukan cuti untuk tanggal yang Anda inginkan." | Pengajuan terkirim dan status terlihat. |
| Popup K3 | "Baca panduan keselamatan sampai selesai." | Popup tutup setelah waktu baca dan konfirmasi. |
| Jadwal (atasan) | "Kirim jadwal minggu ini ke tim." | Jadwal terkirim dan tim melihatnya. |
| Serah terima | "Serahkan pekerjaan yang sudah selesai." | Serah terima tercatat dengan tanda tangan. |
| Sinkron | "Cek apakah data Anda sudah terkirim." | Peserta bisa menjelaskan status tiap data. |

## 6. Catatan teknis

- Tes UI di web: gunakan tab Chrome sendiri, tutup setelah selesai (aturan `CLAUDE.md`).
- Tes di HP: APK dev dan HP uji. Jangan menyentuh aplikasi produksi di HP pengguna. Jangan restart adb atau putus pairing wireless-debug.
- Tes otomatis tidak menggantikan uji awam. Keduanya saling melengkapi.
