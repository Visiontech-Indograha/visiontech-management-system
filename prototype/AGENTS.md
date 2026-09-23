# Petunjuk untuk agen berikutnya

## Koordinasi aktif (instruksi pengguna terbaru)

Pengguna meminta Codex bekerja bersama Gemini Pro melalui **satu file komunikasi aktif: [KOMUNIKASI.md](KOMUNIKASI.md)**. Baca sebelum mulai tugas dan tambahkan balasan di bagian paling bawah file yang sama. Jangan menimpa pesan atau membalas atas nama agen lain.

`COLLABORATION.md`, `coordination/codex.md`, `coordination/gemini.md`, dan mailbox JSON adalah arsip protokol sebelumnya. Jangan membagi percakapan baru ke sana; tidak perlu menjalankan bridge.py untuk komunikasi.

Gemini sedang mengerjakan `js/workplans.js` dan kemudian `tests/browser.mjs`, menurut pengguna. Codex mengambil review/QA tanpa mengubah file aplikasi sampai pembagian tugas disepakati dalam `KOMUNIKASI.md`. Catatan berhenti di bawah adalah riwayat serah terima, bukan pembatalan permintaan kolaborasi terbaru.

Baca **[agent.md](agent.md)** terlebih dahulu. File itu adalah catatan serah terima utama: tujuan pengguna, keputusan yang sudah disetujui, implementasi aktual, alur bisnis, hasil pengujian, keterbatasan, dan pekerjaan lanjutan.

- Pengguna meminta pekerjaan dihentikan pada 22 September 2026 untuk diteruskan oleh agen lain. Implementasi belum dinyatakan selesai seluruhnya. Lanjutkan hanya ketika pengguna meminta kelanjutan.
- Pertahankan **HTML, CSS, dan JavaScript biasa**. Jangan memasang kembali React, Vite, framework, bundler, `node_modules`, atau dependensi runtime.
- Prototipe harus tetap bisa dibuka langsung melalui `index.html` tanpa server atau internet.
- Desktop dan mobile merupakan pilihan pratinjau terpisah. Menu, data terlihat, serta tindakan dibatasi per peran; jangan menggabungkannya kembali menjadi satu halaman semua-peran.
- Semua peran memakai satu data simulasi bersama. Transaksi harus mengikuti aturan bisnis, bukan sekadar berpindah ke halaman status contoh.
- Jangan menulis ulang isi SK/adendum lama menggunakan data terbaru. Dokumen terbit memiliki snapshot sendiri.
- Jangan menghapus ulang isi proyek. Workspace sudah dibangun ulang. Arsip implementasi lama berada di luar workspace; lokasi dan alasan pemindahan dijelaskan dalam `agent.md`.
- Baca bagian yang relevan dan buat perubahan terarah untuk menghemat token. Jangan menganggap catatan pekerjaan lanjutan sebagai perubahan yang sudah diterapkan.
