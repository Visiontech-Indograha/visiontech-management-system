# Runbook: hapus terjadwal (retensi data, UU PDP)

Perintah: `python -m app.cli hapus-terjadwal --cek | --terapkan [--paksa]` (salah satu mode WAJIB).
Memakai peran pemilik (`MIGRATION_DATABASE_URL`), seperti perintah CLI lain.

## Dua tindakan
- A. Anonimisasi karyawan yang keluar lebih dari 30 hari (`employee.separated_at`): berkas pribadi (foto, KTP/dokumen,
  swafoto absensi), embedding wajah, telepon, alamat dihapus. Baris karyawan dan absensi tetap.
- B. Hapus permanen arsip per jenis setelah batas retensi: karyawan/klien/dokumen 5 th, aset (alat, kendaraan) 2 th,
  mess/divisi/jabatan 1 th. Baris yang masih dirujuk data lain DITAHAN (job lanjut), bukan dipaksa.

Kebijakan ada di tabel `retention_policy`; semua `is_active=false` (job tidak menghapus apa pun) sampai pemilik
mengaktifkan per jenis. Mode `--cek` melapor semua jenis dan tidak menulis apa pun.

## Langkah pemilik/operator
1. Cek dulu (aman, tanpa perubahan):
   `docker exec <api> python -m app.cli hapus-terjadwal --cek` -> kirim angka `kandidat` per jenis ke pemilik.
2. Pemilik menyetujui angka. Bila jumlah satu jenis melebihi `RETENTION_MAX_PER_TYPE` (bawaan 500), `--terapkan`
   berhenti untuk jenis itu (status `diblokir`, kode keluar 1). Tinjau lalu jalankan dengan `--paksa` secara manual.
3. Aktifkan per jenis, mulai dari `employee_personal_files` (30 hari), baru jenis arsip satu per satu:
   `UPDATE retention_policy SET is_active = true, update_at = now() WHERE data_type = 'client';`
   Jenis: employee_personal_files, employee_row, client, employee_file, tool, vehicle, company_mess, division, job_position.
4. Jalankan manual sekali: `... hapus-terjadwal --terapkan`, cek ringkasan di Discord (#vms-alerts) dan tabel `retention_run_log`.
5. Pasang cron host, 02:30 WIB, SEBELUM cadangan harian (cadangan hari itu sudah tanpa data yang dihapus):
   `30 2 * * *  docker exec <api> python -m app.cli hapus-terjadwal --terapkan >> /var/log/vms-hapus-terjadwal.log 2>&1`
   (host WIB; bila host UTC pakai `30 19 * * *`). Dua proses bersamaan aman: advisory lock, yang kedua keluar "sedang berjalan".
6. Esok hari: cek Discord dan `SELECT run_at, status, counts FROM retention_run_log ORDER BY run_at DESC LIMIT 3;`.

## Perilaku
- Batch kecil (`RETENTION_BATCH_SIZE`, 50) per baris satu transaksi, `FOR UPDATE SKIP LOCKED`; batas waktu total
  `RETENTION_MAX_SECONDS` (1200 dtk), sisanya dilanjutkan esok hari. Cron mati berhari-hari: otomatis menyusul.
- Berkas MinIO dihapus setelah commit, di luar event loop, idempoten. Gagal hapus objek: DB tetap benar, tercatat
  `berkas_gagal`, kode keluar 1; bersihkan sisa dengan `scripts/bersihkan_berkas_yatim.py`.
- Audit: `RETENTION_ANONYMIZE` / `RETENTION_PURGE` (aktor SYSTEM, platform system_cron) berisi hanya jenis, id baris,
  jumlah berkas. Tanpa nama, NIK, kunci berkas, atau embedding.
- Pemulihan karyawan ditolak bila sudah keluar > 30 hari (pesan: data pribadi sudah dihapus).

## Berhenti / rollback
- Hentikan jenis: `UPDATE retention_policy SET is_active = false WHERE data_type = '...';` atau hapus baris cron.
- Pemusnahan tidak dapat dibatalkan. Cadangan lama masih memuat data yang sudah dihapus: atur masa simpan cadangan
  (saran 35 hari) dan jangan memakai `mc mirror` tanpa `--remove` (keputusan pemilik terpisah).
- Kode keluar: 0 sukses/sedang berjalan, 1 ada gagal atau jenis diblokir.
