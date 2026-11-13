# Pengingat dokumen kendaraan dan SIM (cron milik pemilik server)

Perintah (dijalankan dari kontainer/venv API, memakai peran pemilik seperti `hapus-terjadwal`):

```
python -m app.cli pengingat-dokumen --dry-run     # hanya hitung, tidak menulis
python -m app.cli pengingat-dokumen               # kirim notifikasi
python -m app.cli pengingat-dokumen --tanggal 2026-12-01   # tanggal bisnis pengganti (uji)
```

Aturan: tahap T30, T21, T14 tepat pada harinya, lalu harian dari H-7 sampai H0 dan setelah lewat tempo
(maksimal 30 hari). Penerima: HSE dan OM kantor dokumen, pengemudi kendaraan, dan pemilik SIM. Aman diulang:
`document_reminder` mencegah kiriman ganda pada hari yang sama. Dokumen yang sudah diganti tidak diingatkan.
Keluaran: satu baris JSON berisi jumlah (kandidat, dikirim, dilewati, tanpa penerima, notifikasi, per tahap).
Notifikasi masuk kotak masuk; siaran langsung (SSE) hanya untuk proses API, jadi muncul saat aplikasi memuat ulang.

Contoh baris cron (sekali sehari, 07:00 WIB; sesuaikan nama kontainer, JANGAN dipasang otomatis):

```
0 7 * * * docker exec vms_api python -m app.cli pengingat-dokumen >> /var/log/vms-pengingat-dokumen.log 2>&1
```
