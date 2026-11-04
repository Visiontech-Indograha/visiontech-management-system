# Checklist desain sebelum disetujui

Isi per perubahan yang menyentuh skala, data, keamanan, atau operasi.

1. Dampak kapasitas
   - [ ] Jumlah kueri per permintaan dihitung (konstan terhadap n? ya/tidak).
   - [ ] Daftar memakai `LIMIT` di SQL dan indeks untuk filter+urutan.
   - [ ] Memori tambahan (per proses dan total server 4 GB) dicatat; batas `mem_limit` tidak dilanggar.
   - [ ] Pekerjaan CPU berat tidak berjalan di event loop.

2. Data dan migrasi
   - [ ] Expand -> migrate -> contract; migrasi kompatibel mundur.
   - [ ] Indeks tabel besar memakai `CONCURRENTLY` (migrasi baru).
   - [ ] Backfill dibatch; ada `downgrade()`.
   - [ ] Kolom sensitif (NIK, rekening, embedding) tidak masuk log, galat, atau respons tanpa izin.

3. Konkurensi dan keandalan
   - [ ] Transisi status memakai compare-and-set atau `FOR UPDATE`.
   - [ ] Mutasi berisiko ganda punya `Idempotency-Key` atau alasan tertulis tidak perlu.
   - [ ] Panggilan keluar punya timeout; retry hanya untuk operasi idempoten.
   - [ ] Kegagalan dependensi (face-service, MinIO, Discord, FCM) tidak menjatuhkan alur utama.

4. Keamanan
   - [ ] Izin global dan relasi (divisi/tim) diperiksa di service, bukan hanya di UI.
   - [ ] Respons tanpa hash, embedding, token, atau data divisi lain (uji dengan `vms-qa`).
   - [ ] Rate limit untuk endpoint publik atau mahal (login, reset, unggah, unduh).
   - [ ] Rahasia tidak masuk image (`.dockerignore`), Git, atau log.

5. Operasi
   - [ ] Log akses mencatat `request_id`, status, `duration_ms`; tanpa data pribadi.
   - [ ] Health tidak memeriksa DB pada `/health`.
   - [ ] Cara rollback jelas (image sebelumnya; migrasi tidak di-downgrade otomatis).
   - [ ] Cadangan dan RPO/RTO tidak berubah tanpa catatan.

6. Dokumentasi
   - [ ] Keputusan yang sulit dibalik ditulis sebagai ADR.
   - [ ] Angka yang belum diukur ditandai BELUM DIUKUR (jangan ditebak).

Big O cepat (contoh): daftar 10.000 baris dengan filter di Python = memuat 10.000 baris untuk setiap halaman. Dengan `LIMIT 20` + indeks = biaya sebanding 20 baris + pencarian indeks.
