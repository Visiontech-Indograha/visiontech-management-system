# Cadangan terenkripsi ke Windows 'pobonguar' (tarik malam hari)

> [!IMPORTANT]
> **LANGKAH PEMILIK (OWNER'S MANUAL STEP):** Seluruh eksekusi perintah di server produksi (`visiontech-bar`) maupun di mesin Windows (`pobonguar`) adalah kewenangan eksklusif pemilik. Agen AI dilarang melakukan SSH atau eksekusi perubahan langsung di server produksi.

Alur: server Linux `visiontech-bar` membuat cadangan DB + MinIO (prod dan beta) terenkripsi `age` -> Windows
`pobonguar` (Tailscale 100.94.81.43) MENARIK lewat SFTP baca-saja -> verifikasi sha256 -> retensi -> peringatan.
Kunci PUBLIK age ada di Linux; kunci PRIVAT hanya di Windows + satu salinan offline. Tidak ada rahasia di repo.

Yang dibuat repo: `deploy/backup-terenkripsi.sh`, `deploy/siapkan-backup-reader.sh`, `deploy/perkiraan-disk-cadangan.sh`,
`deploy/sanitasi-dump-biometrik.sh`, `deploy/windows/{Cadangan-Umum,Tarik-Cadangan,Daftar-Tugas,Uji-Pulih}.ps1`;
`backup-minio.sh` mengaktifkan `mc mirror --remove` secara bawaan sesuai keputusan retensi PDP pemilik.
Jangan tempel ke server tanpa membaca; perubahan di server dicadangkan dulu (ikuti `deploy/README.md`).

## 0. Prasyarat & Kepatuhan UU PDP No. 27/2022
- **Prinsip PDP (Data Biometrik)**: Kolom `face_embedding` pada tabel `employee` adalah Data Pribadi Spesifik (Pasal 4 ayat 2 huruf d UU PDP). Data mentah biometrik tidak boleh dikirim ke luar server tanpa enkripsi `age`. Untuk pemulihan ke lingkungan non-produksi (uji/staging), gunakan opsi `VMS_BACKUP_EXCLUDE_BIOMETRIC=1` atau jalankan `deploy/sanitasi-dump-biometrik.sh`.
- **Retensi MinIO 35 Hari**: Sesuai keputusan pemilik, berkas terhapus di MinIO dibuang maksimal **35 hari** (30 hari retensi DB/MinIO + maks 5 hari siklus cadangan). `mc mirror --remove` aktif agar berkas terhapus tidak abadi di mirror.
- Linux: `sudo apt install age` (>= 1.1), GNU tar, cron. Windows Server 2019: OpenSSH Client
  (`Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0`), `age.exe` (unduh rilis resmi FiloSottile/age ke
  `C:\Tools\age\`, tambah ke PATH), opsional `pg_restore.exe` (PostgreSQL client 18). `tar.exe` sudah bawaan.
- Perkiraan disk (jalankan di Linux, hanya baca): `bash deploy/perkiraan-disk-cadangan.sh <ct-db-prod> <db-prod> <ct-db-beta> <db-beta> <folder-mirror-prod> <folder-mirror-beta>`
  Rumus: `TOTAL = 1.3 x [ 34 x 0.35 x (DBprod+DBbeta) + 6 x (1+6c) x (MinIOprod+MinIObeta) ]`, c = laju ubah harian (bawaan 0.02).
  Disk Linux juga butuh: mirror kerja MinIO (= ukuran bucket, per lingkungan) + 3 hari arsip terenkripsi.

## 0b. Verifikasi pertama oleh pemilik (sebelum dijadwalkan)
1. `age --version` terpasang di Linux dan `age.exe --version` di Windows.
2. Satu siklus nyata: buat (bagian 4 Linux) -> tarik (`Tarik-Cadangan.ps1`, sha256 cocok di log) -> `Uji-Pulih.ps1` (dekripsi + `pg_restore --list` > 0 entri
   + hitungan berkas MinIO). Jadwalkan HANYA bila ketiganya lulus.

## 1. Windows: volume, akun, kunci age (Administrator PowerShell)
```powershell
# BitLocker pada volume cadangan (mis. D:); simpan recovery key DI LUAR mesin ini
Install-WindowsFeature BitLocker -IncludeAllSubFeature -IncludeManagementTools   # lalu restart bila diminta
Enable-BitLocker -MountPoint 'D:' -EncryptionMethod XtsAes256 -RecoveryPasswordProtector -UsedSpaceOnly:$false
Add-BitLockerKeyProtector -MountPoint 'D:' -RecoveryPasswordProtector   # tampilkan kunci, simpan offline
Enable-BitLockerAutoUnlock -MountPoint 'D:'   # perlu OS drive terenkripsi; bila tidak, buka kunci manual setelah restart
# Akun layanan + izin NTFS hanya akun ini (dan SYSTEM/Administrators untuk pemeliharaan)
$sandi = Read-Host -AsSecureString 'Sandi svc-cadangan'
New-LocalUser svc-cadangan -Password $sandi -PasswordNeverExpires -UserMayNotChangePassword
# beri hak "Log on as a batch job" ke svc-cadangan: secpol.msc > Local Policies > User Rights Assignment
New-Item -ItemType Directory -Force D:\cadangan-vms, D:\rahasia | Out-Null
foreach ($d in 'D:\cadangan-vms','D:\rahasia') {
  icacls $d /inheritance:r /grant:r 'svc-cadangan:(OI)(CI)F' 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' | Out-Null }
# VSS (pemulihan versi file): aktifkan perlindungan pada D: lewat Properties > Shadow Copies, atau
vssadmin Add ShadowStorage /For=D: /On=D: /MaxSize=10%
# jadwalkan snapshot: Task Scheduler > buat tugas "vssadmin create shadow /for=D:" harian 06:00 (Server mendukung)
# Buat pasangan kunci age di LUAR D:\cadangan-vms (folder cadangan tidak boleh memuat kunci)
New-Item -ItemType Directory -Force C:\kunci | Out-Null
age-keygen -o C:\kunci\vms-age.key        # mencetak "Public key: age1..." -> CATAT kunci publik itu
icacls C:\kunci /inheritance:r /grant:r 'Administrators:(OI)(CI)F' 'svc-cadangan:(OI)(CI)R' | Out-Null
# SALINAN OFFLINE: cetak/simpan C:\kunci\vms-age.key ke flash disk terenkripsi, simpan di brankas fisik. Sama untuk KEK enkripsi kolom.
```
Catatan: uji pulih (bagian 6) butuh kunci privat; `svc-cadangan` TIDAK perlu membacanya untuk menarik. Cabut hak baca
`svc-cadangan` pada `C:\kunci` bila ingin (hapus `'svc-cadangan:(OI)(CI)R'`); Anda menjalankan Uji-Pulih sebagai Administrator.

## 2. Windows: kunci SSH khusus (tanpa sandi, hanya untuk tugas ini)
```powershell
ssh-keygen -t ed25519 -N '""' -f D:\rahasia\backup_reader_ed25519 -C backup-reader@pobonguar
icacls D:\rahasia\backup_reader_ed25519 /inheritance:r /grant:r 'svc-cadangan:R' 'Administrators:F' | Out-Null
Get-Content D:\rahasia\backup_reader_ed25519.pub   # salin satu baris ini ke Linux (langkah 3)
```

## 3. Linux: kunci publik age + backup-reader (sebagai pengguna deploy, lalu sudo)
Hanya kunci PUBLIK yang dipasang. Skrip menolak berjalan bila berkas penerima memuat `AGE-SECRET-KEY`.
```bash
cd ~/deploy/vms-mvp     # lakukan juga untuk folder beta (VMS_DEPLOY_DIR beta)
git pull --ff-only      # atau salin deploy/*.sh baru; cadangkan skrip lama dulu: cp deploy/backup-minio.sh{,.bak}
printf '%s\n' 'age1...ISI_KUNCI_PUBLIK...' > age-recipients.txt     # tambah baris kedua = kunci publik cadangan/rotasi
chmod 600 age-recipients.txt
printf '%s\n' 'ssh-ed25519 AAAA...BARIS_PUB_WINDOWS... backup-reader@pobonguar' > /tmp/backup-reader.pub
sudo bash deploy/siapkan-backup-reader.sh /tmp/backup-reader.pub "$USER" && rm /tmp/backup-reader.pub
```
Hasil: pengguna `backup-reader` tanpa shell, `internal-sftp -R` (baca saja) terkurung di `/srv/vms-cadangan`
(`prod/`, `beta/`), kunci dibatasi `restrict,from="100.94.81.43"`. Pastikan IP Linux di Tailscale sebagai `<ip-linux>`.
Skrip menyimpan cadangan `50-backup-reader.conf.bak.*` bila ada dan menjalankan `sshd -t` sebelum reload.

## 4. Uji manual (belum dijadwalkan)
Linux (per lingkungan; `VMS_BACKUP_NAME` WAJIB beda):
```bash
cd ~/deploy/vms-mvp
VMS_BACKUP_NAME=prod VMS_BACKUP_DIR=$HOME/deploy/cadangan-kerja bash deploy/backup-terenkripsi.sh semua | tail -n 5
ls -l /srv/vms-cadangan/prod | tail -n 8      # .age + .sha256 + .manifest
```
Windows (Administrator; sekali manual untuk menerima sidik jari host ke known_hosts akun Anda, lalu salin ke akun layanan
bila tugas jalan sebagai svc-cadangan: `ssh-keyscan <ip-linux>` ke `C:\Users\svc-cadangan\.ssh\known_hosts`, bandingkan sidik jari
dengan `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` di Linux):
```powershell
sftp -i D:\rahasia\backup_reader_ed25519 backup-reader@<ip-linux>     # coba: ls prod ; put x (HARUS ditolak) ; exit
cd <repo>\deploy\windows
.\Tarik-Cadangan.ps1 -ServerHost <ip-linux> -KunciSsh D:\rahasia\backup_reader_ed25519 -Tujuan D:\cadangan-vms
Get-Content D:\cadangan-vms\log\cadangan-*.log -Tail 20
```
Peringatan: set `VMS_DISCORD_WEBHOOK` (webhook Discord) dan `VMS_KUMA_PUSH_URL` (monitor Push Uptime Kuma, interval 26 jam)
sebagai variabel MESIN: `[Environment]::SetEnvironmentVariable('VMS_DISCORD_WEBHOOK','<url>','Machine')`.

## 5. Jadwalkan
Linux cron (`crontab -e` pengguna deploy; DB + MinIO prod 02:00, beta 02:30; sesuaikan jalur):
```
0 2 * * *  VMS_DEPLOY_DIR=$HOME/deploy/vms-mvp  VMS_BACKUP_NAME=prod VMS_BACKUP_DIR=$HOME/deploy/cadangan-kerja bash $HOME/deploy/vms-mvp/deploy/backup-terenkripsi.sh semua >> $HOME/deploy/backup-enc-prod.log 2>&1
30 2 * * * VMS_DEPLOY_DIR=$HOME/deploy/vms-beta VMS_BACKUP_NAME=beta VMS_BACKUP_DIR=$HOME/deploy/cadangan-kerja bash $HOME/deploy/vms-beta/deploy/backup-terenkripsi.sh semua >> $HOME/deploy/backup-enc-beta.log 2>&1
```
Windows (Administrator): `.\Daftar-Tugas.ps1 -ServerHost <ip-linux> -KunciSsh D:\rahasia\backup_reader_ed25519` -> tugas
"VMS Tarik Cadangan" 03:30 dan "VMS Periksa Cadangan" 09:00 (hanya cek kesegaran; peringatan bila terbaru > 26 jam).
Retensi: DB harian 14 + mingguan 8 + bulanan 12; MinIO 35 hari (set mingguan penuh+inkremental). Kebijakan bisa diubah lewat parameter.

Penghapusan tuntas: salinan kerja Linux memakai `mc mirror --remove`; inkremental `tar` mencatat penghapusan. Berkas yang dihapus di
sistem tetap ada di arsip lama sampai set mingguannya dibuang. Bawaan `-RetensiMinioHari 28` (+ panjang set <= 7 hari) menjamin berkas
terhapus hilang paling lambat 35 hari (keputusan pemilik). Konsekuensi: titik pulih MinIO yang terjamin ~28 hari.

## 6. Uji pulih dan langkah pemulihan dari cadangan terenkripsi (LANGKAH PEMILIK)

### 6.1 Uji pulih otomatis bulanan (Windows Administrator, kunci privat dipasang)
```powershell
.\Uji-Pulih.ps1 -Identitas C:\kunci\vms-age.key -Lingkungan prod ; .\Uji-Pulih.ps1 -Identitas C:\kunci\vms-age.key -Lingkungan beta
```
Mendekripsi ke folder sementara, `pg_restore --list` (jumlah entri), hitung berkas di rantai arsip MinIO, hapus sementara, lapor di
`D:\cadangan-vms\log\uji-pulih-<env>-<bulan>.txt`.

### 6.2 Prosedur pemulihan penuh (Disaster Recovery)
> **PENTING**: Pemulihan ke server produksi hanya dilakukan saat insiden/bencana atas persetujuan pemilik, selalu pulihkan ke basis data/penyimpanan sementara terlebih dahulu untuk verifikasi integritas.

#### A. Pemulihan Database (PostgreSQL)
1. **Verifikasi Checksum**:
   ```powershell
   # Windows:
   (Get-FileHash -Algorithm SHA256 prod-db-20261111-020000.dump.age).Hash.ToLower()
   Get-Content prod-db-20261111-020000.dump.age.sha256
   ```
2. **Dekripsi dengan age**:
   ```powershell
   age.exe -d -i C:\kunci\vms-age.key -o prod-db-pulih.dump prod-db-20261111-020000.dump.age
   ```
3. **Verifikasi Isi Dump**:
   ```powershell
   pg_restore.exe --list prod-db-pulih.dump | Select-Object -First 20
   ```
4. **Pulihkan ke Basis Data Sementara / Bersih**:
   ```bash
   # Di Linux:
   pg_restore -U "$POSTGRES_USER" -d vms_recovery --clean --if-exists prod-db-pulih.dump
   ```
5. **(Khusus Lingkungan Non-Prod / Staging) Sanitasi Biometrik PDP**:
   ```bash
   bash deploy/sanitasi-dump-biometrik.sh --db vms_db_staging vms_staging
   ```

#### B. Pemulihan Berkas MinIO
1. **Dekripsi Arsip Penuh (Full) & Inkremental**:
   ```powershell
   age.exe -d -i C:\kunci\vms-age.key -o minio-full.tar prod-minio-20261108-020000-full.tar.age
   age.exe -d -i C:\kunci\vms-age.key -o minio-inc-1.tar prod-minio-20261109-020000-inc.tar.age
   age.exe -d -i C:\kunci\vms-age.key -o minio-inc-2.tar prod-minio-20261110-020000-inc.tar.age
   ```
2. **Ekstraksi Rantai Arsip Berurutan** (tar GNU dengan `--listed-incremental=/dev/null` agar penghapusan berkas sinkron):
   ```bash
   mkdir -p /tmp/minio-pulih
   tar -C /tmp/minio-pulih --listed-incremental=/dev/null -xf minio-full.tar
   tar -C /tmp/minio-pulih --listed-incremental=/dev/null -xf minio-inc-1.tar
   tar -C /tmp/minio-pulih --listed-incremental=/dev/null -xf minio-inc-2.tar
   ```
3. **Kembalikan Berkas ke MinIO**:
   ```bash
   # Gunakan mc mirror ke target MinIO
   mc mirror /tmp/minio-pulih/vms-files/ minio_target/vms-files/
   ```
4. Bersihkan folder sementara dan hapus berkas hasil dekripsi setelah selesai.

## 7. Rotasi kunci
1. Buat pasangan baru (`age-keygen`), tambahkan kunci PUBLIK baru sebagai baris kedua `age-recipients.txt` (cadangan baru terbaca KEDUA kunci).
2. Setelah retensi tertua lewat (atau enkripsi ulang arsip lama: `age -d -i lama | age -R baru`), hapus kunci publik lama dari berkas.
3. Pertahankan kunci privat lama sampai semua cadangan lama kedaluwarsa. Kunci SSH: buat baru, jalankan ulang `siapkan-backup-reader.sh` dengan `.pub` baru.
Kunci terbocor: cabut `backup-reader` (rollback di bawah), rotasi age, anggap cadangan lama terbuka.

## 8. Rollback
```bash
sudo rm /etc/ssh/sshd_config.d/50-backup-reader.conf /etc/ssh/backup-reader.authorized_keys && sudo sshd -t && sudo systemctl reload ssh
sudo userdel backup-reader; crontab -e   # hapus dua baris backup-terenkripsi
```
```powershell
Unregister-ScheduledTask 'VMS Tarik Cadangan' -Confirm:$false; Unregister-ScheduledTask 'VMS Periksa Cadangan' -Confirm:$false
```
Cadangan lama (`backup.sh`, `backup-minio.sh`, `backup-offsite.sh`) tidak diubah dan tetap jalan; `backup-minio.sh` mengaktifkan `--remove` secara bawaan sesuai kepatuhan retensi PDP.
