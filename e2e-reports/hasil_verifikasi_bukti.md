# Verifikasi foto bukti absen (tanpa pencocokan wajah)
Akun: ketua11@uji-nyata.test, HP fisik, APK dev, 3 Nov 2026 ~21:16 WIB (SKIP_ATTENDANCE_HOURS_CHECK=true).

## LULUS
- Absen masuk di luar radius (94960 m dari Duri): dialog penjelasan -> langkah 1 "Swafoto absen masuk" -> langkah 2 "Foto bukti di luar radius" (kamera berwatermark biasa) -> "Absen masuk tercatat", status Perlu review.
- Watermark (koordinat, alamat, waktu, logo Visiontech Indograha + logo TIM) terbaca jelas, proporsional, di kedua layar kamera.
- DB: face_status=MATCHED (skor 95), face_photo_path (swafoto) dan out_of_radius_photo_path (bukti) BERBEDA; bukti tidak memicu mismatch/flag wajah. Flag hanya ATTENDANCE_FLAGGED karena di luar radius/terlambat.
- API: POST /attendance/{id}/evidence milik sendiri = 200 (path bukti yang ada tidak ditimpa); file milik akun lain = 422 EVIDENCE_NOT_OWNED; UUID rusak = 422.
## Tidak teruji
- Langkah "Foto bukti keterlambatan" / tombol "Tambah foto bukti": tidak muncul karena baris sudah ditandai Terlambat tetapi sekaligus di luar radius (satu foto bukti dipakai untuk keduanya). Kasus terlambat-di-dalam-radius tak bisa dibuat (GPS HP tetap di luar radius).
- Absen PULANG: setelah disetujui OM kartu menampilkan "Absen pulang mandiri ditutup pukul 19:00" (waktu 21:17) sehingga langkah bukti pulang tak bisa dijalankan.
- C (web OM, blok "Foto bukti" vs "Verifikasi Wajah"): ekstensi Chrome tidak terhubung ("Browser extension is not connected"). BELUM diverifikasi.
## Temuan
- Evidence pada absensi orang lain mengembalikan 404 NOT_FOUND (bukan 422) -- wajar (tidak membocorkan keberadaan); 422 hanya untuk file bukan milik sendiri.
- Preview kamera langkah bukti sempat hitam (kamera depan/gelap), rana tetap berfungsi.
## Screenshot
e2e-reports/screenshots/ketua11/mobile_bukti_00..10.png (07 swafoto, 08 foto bukti di luar radius, 09 hasil, 10 setelah disetujui)
## Pembersihan
Dihapus: baris attendance uji, 8 notifikasi, sesi curl, 4 file_object uji. Berkas fisik di storage tidak dicari/dihapus. HP kini login sebagai ketua11 (gudang sudah keluar; sesi gudang di HP tidak dipulihkan). Persetujuan OM lewat API login om@ (sesi curl dihapus).
