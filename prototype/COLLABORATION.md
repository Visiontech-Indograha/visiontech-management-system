# Koordinasi Codex × Gemini Pro

> **ARSIP — digantikan oleh [KOMUNIKASI.md](KOMUNIKASI.md).** Pengguna meminta satu file bersama. Semua pesan, balasan, dan pembagian tugas baru hanya ditambahkan di `KOMUNIKASI.md`; protokol di bawah disimpan sebagai riwayat.

## Tujuan bersama

Menyelesaikan MVP/prototipe Visiontech yang ringan: HTML, CSS, JavaScript biasa; dibuka melalui `index.html`; ruang kerja desktop/mobile terpisah per peran; transaksi lintas peran; dokumen dan lampiran dapat dipratinjau dengan benar.

Pengguna menyatakan Gemini Pro sedang bekerja melalui Antigravity CLI pada workspace ini. Codex belum memiliki kanal pesan langsung ke proses CLI tersebut. Jembatan yang tersedia adalah file bersama. **Status awal: menunggu konfirmasi Gemini bahwa pesan koordinasi telah dibaca.**

**Pembaruan terbaru:** pengguna menghentikan sementara Antigravity/Gemini selama jembatan disiapkan. Kanal terminal sekarang tersedia melalui `coordination/bridge.py`; instruksi di `coordination/README.md`. Jembatan menyimpan pesan persisten, tetapi tidak menyuntikkan pesan ke sesi CLI dan tidak menjalankan model. Setelah Gemini dilanjutkan, ia perlu membaca inbox dan membalas sendiri.

**Pembaruan setelah penyiapan jembatan:** pengguna mengonfirmasi Gemini sekarang sedang mengerjakan **`js/workplans.js`**. File ini merupakan area edit eksklusif Gemini sampai dilepas. Informasi berasal dari pengguna; belum ada acknowledgment atau balasan Gemini melalui mailbox. Codex tetap pada review/QA dan koordinasi, tanpa menyunting file aplikasi. Kepemilikan file lain belum dipersempit dari pembagian konservatif di bawah.

## Pembagian awal untuk menghindari tabrakan

| Area | Penanggung jawab awal | Ketentuan |
|---|---|---|
| `js/workplans.js` | Gemini — dikonfirmasi pengguna | Sedang dikerjakan. Codex tidak mengedit, memformat ulang, atau menimpa file ini. |
| `tests/browser.mjs` | Gemini — pembaruan pengguna berikutnya | Sedang dikerjakan sekarang. Codex tidak mengubah file ini; perpindahan fokus belum dianggap melepas kepemilikan workplans.js. |
| `index.html`, `js/`, `css/`, `tests/`, `README.md` | Gemini | Codex hanya membaca; daftar file aktif dikonfirmasi oleh Gemini. |
| `coordination/codex.md` | Codex | Pesan keluar, hasil QA, dan usulan untuk Gemini. |
| `coordination/gemini.md` | Gemini | Konfirmasi, file yang sedang diedit, progres, keputusan, dan tugas untuk Codex. |
| `AGENTS.md`, `GEMINI.md`, dokumen koordinasi | Codex saat menyiapkan jembatan | Perubahan pembagian berikutnya harus dinyatakan di kotak pesan dan diakui penerima. |

Ini adalah pembagian konservatif sementara, bukan klaim bahwa Gemini telah menyetujuinya. Codex dapat mengambil implementasi tertentu setelah Gemini melepas file/tugas tersebut secara eksplisit. Tidak ada edit serentak pada file yang sama.

## Cara bertukar pekerjaan

1. Masing-masing hanya menulis kotak pesannya sendiri. Tambahkan ID pesan, waktu, status, file terkait, dan langkah reproduksi jika melaporkan bug.
2. Penerima mengakui ID pesan di kotak pesannya sendiri. Pesan yang belum diakui tetap dianggap belum dibaca.
3. Sebelum pindah area edit, tuliskan file/tugas yang dilepas atau diminta. Tunggu kesepakatan untuk tugas yang menyentuh file pihak lain.
4. Jangan mengembalikan atau menimpa perubahan pihak lain berdasarkan `agent.md` yang lebih lama.
5. Pengujian Codex berjalan pada salinan di folder temporary dengan output terpisah; tidak mengganggu screenshot/log pengujian Gemini.
6. Hasil test berlaku untuk snapshot yang disebutkan. Jika kode berubah setelahnya, jangan menyebut hasil tersebut sebagai validasi revisi terbaru.
7. Jangan reset data browser pengguna, menghapus proyek, memasang framework, atau menjalankan dua server/build tanpa kebutuhan.

## Tanda selesai

- Kedua pihak sudah melaporkan status pekerjaan dan temuan yang masih terbuka.
- Pengujian aturan bisnis serta alur browser lulus pada revisi yang sama.
- Pratinjau/cetak dokumen dan pemisahan peran/perangkat diverifikasi.
- Keterbatasan simulasi dijelaskan tanpa mengklaim backend atau verifikasi resmi.

Untuk memulai sesi Gemini kembali, pengguna cukup menyampaikan: **“Baca GEMINI.md, jalankan inbox untuk gemini, lalu beri acknowledgment dan balasan ke Codex melalui coordination/bridge.py sebelum melanjutkan edit.”**
