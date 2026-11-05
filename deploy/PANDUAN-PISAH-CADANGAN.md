# Panduan: memisahkan cadangan prod dan beta

Untuk pemilik. Perubahan ini OPSIONAL: selama `VMS_BACKUP_DIR` dan `VMS_BACKUP_NAME` tidak diisi, `backup.sh`
berperilaku persis seperti sebelumnya. Jangan mengganti nama folder `~/deploy/vms-mvp`, `~/deploy/vms-beta`,
`~/deploy/visiontech`, dan jangan mengubah nama proyek compose (volume Docker terikat pada nama itu).

Hasil akhir: `~/cadangan/prod/prod-harian-20261105-013001.dump`, `~/cadangan/beta/beta-pra-deploy-<sha>-....dump`.
Retensi tetap 7 berkas per lingkungan. Retensi hanya menghitung `<awalan>-*.dump` dan berkas nama lama `<nama DB>-*.dump`
milik DB itu, jadi lingkungan lain tidak pernah terhapus dan cadangan lama tidak hilang mendadak.

## Urutan aman (ulangi per lingkungan)
1. Salin skrip baru dari repo ke server (ikuti deploy/README.md: cadangkan dulu skrip lama, mis. `cp backup.sh backup.sh.lama`):
   `backup.sh`, `autodeploy.sh`, `healthcheck.sh`, `backup-offsite.sh`. Tanpa variabel baru, perilaku belum berubah.
2. Buat folder: `mkdir -p ~/cadangan/prod ~/cadangan/beta && chmod 700 ~/cadangan ~/cadangan/*`.
3. COPY (jangan pindah dulu) cadangan lama: `cp -p ~/deploy/vms-mvp/backups/*.dump ~/cadangan/prod/`
   (beta: dari `~/deploy/vms-beta/backups/` ke `~/cadangan/beta/`). Bila folder lama bercampur, salin berkas
   `vms_beta-*` ke beta dan `vms_v2-*` ke prod.
4. Isi `deploy.env` lingkungan itu (chmod 600 tetap):
   - prod (`~/deploy/vms-mvp/deploy.env`): `VMS_BACKUP_DIR=/home/ageng/cadangan/prod` dan `VMS_BACKUP_NAME=prod`
   - beta (`~/deploy/vms-beta/deploy.env`): `VMS_BACKUP_DIR=/home/ageng/cadangan/beta` dan `VMS_BACKUP_NAME=beta`

   `backup.sh`, `backup-offsite.sh`, dan `healthcheck.sh` membaca `deploy.env`; `autodeploy.sh` meneruskan ke `backup.sh`.
   Cron memanggil skrip yang sama, jadi cron tidak perlu diubah selama jalurnya `~/deploy/<lingkungan>/backup.sh`.
   Bila cron memakai jalur `backups/` secara eksplisit (mis. `find` atau `rsync` sendiri), perbarui ke folder baru.
5. Uji sekali: `cd ~/deploy/vms-mvp && ./backup.sh uji-pisah`. Harus mencetak `/home/ageng/cadangan/prod/prod-uji-pisah-<stempel>.dump`
   dan "minio: vms-backups/prod-uji-pisah-...". Ulangi untuk beta.
6. Uji pulih: `ssh ageng@192.168.88.160 "bash -s" < deploy/uji-pulih-cadangan.sh` (memakai `backup.sh`, jadi otomatis
   membuat berkas di folder baru; SHA-256 lokal dan MinIO harus sama).
7. Setelah beberapa hari cadangan harian baru muncul di folder baru, folder lama boleh dibersihkan. Jangan hapus
   sebelum cadangan luar server (`backup-offsite.sh`) terbukti jalan dari folder baru.
8. Opsional, seragamkan nama berkas lama (tidak wajib; nama lama tetap dihitung retensi):
   `cd ~/cadangan/prod && for f in vms_v2-*.dump; do mv "$f" "prod-${f#vms_v2-}"; done` (beta: `vms_beta-` menjadi `beta-`).
   Objek lama di MinIO tidak diubah; kedaluwarsa 30 hari otomatis.

## Membatalkan
Hapus dua baris `VMS_BACKUP_*` dari `deploy.env` lingkungan itu: skrip kembali memakai `backups/` dan nama DB.
Berkas di `~/cadangan/*` tidak dihapus otomatis. Untuk membatalkan penuh, kembalikan skrip dari `*.lama`.
Cadangan lama di `backups/` tidak pernah dihapus oleh langkah di atas (langkah 3 hanya menyalin).

## Uji tanpa server
`bash scripts/uji-backup-retensi.sh` membuktikan di folder sementara: dua lingkungan satu folder tidak saling hapus,
berkas nama lama tetap dihitung/aman, dan bawaan (tanpa variabel) tidak berubah.
