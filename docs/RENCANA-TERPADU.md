# Rencana terpadu (diperbarui 13 Nov 2026)

Satu daftar untuk semua pekerjaan yang belum selesai. Aturan kerja: `docs/SERAH-TERIMA-AI.md` (aturan 30 detik, merge hanya bila SEMUA cek CI lulus, E2E lewat UI tanpa injeksi, agen memanggil alat Skill di langkah pertama, tes harus gagal di kode lama). Pekerjaan lewat agen khusus (api/db/web/mobile-engineer, qa, architect, devops-engineer) di worktree terisolasi; agen tidak merge.

## Keadaan
- `development` memuat #489-#516 (ekspor laporan 3 format + bulanan, T-1..T-3, perbaikan E2E v4/v5/v6, lint mobile Fase 0, tes hapus_terjadwal, rencana absen web, brief Hikvision). `beta` sampai #514 (APK 2806 terpasang di HP uji). `prod` 1.8.4 (hotfix 1.8.5 menunggu "prod 1.8.5 ya").
- Sedang berjalan: Hikvision PR-1 (db) dan PR-2a (klien ISAPI, parser, simulator).

## Gelombang A - Hikvision langsung (prioritas pemilik; brief `docs/rencana/absensi-hikvision-langsung-isapi.md`)
Perangkat DS-K1T343MX (192.168.88.13, firmware V3.3.4, HTTP 80, 60.301 event tersimpan). Seluruhnya di VMS, tanpa PC iVMS. Syarat utama: tarik riwayat (target 1 tahun, minimal beberapa bulan). Uji pakai data simulasi; firewall belakangan.
1. PR-1 DB: hikvision_device, hikvision_event (UNIQUE device+nomor event), pemetaan employeeNo, kolom `source` absensi (berjalan).
2. PR-2a klien ISAPI (Digest, AcsEvent paginasi, dry-run tanggal tertua), parser event, simulator perangkat (berjalan).
3. PR-2b API penerima push (token di path, allowlist IP, batas 2 MiB, magic bytes) + simpan event mentah idempoten.
4. PR-3 CLI `hikvision-tarik`: impor riwayat per jendela 7 hari, dapat dilanjutkan, jeda, cron rekonsiliasi.
5. PR-4 UI admin: perangkat, pemetaan karyawan, status/antrean.
6. PR-5 pembentukan absen resmi dari event (aturan masuk/pulang, sesi lintas sumber HP/web/perangkat, mode BAYANGAN 1-2 minggu lalu AKTIF).
7. PR-6 devops: blok proxy hanya LAN (port 8080/8081 sudah terbuka di LAN; cek pemiliknya), skrip server siap tempel, cron.
8. QA: uji simulator, tangkapan asli (format JSON/XML, nilai event), uji nyata di mesin, bayangan.
Keputusan pemilik tersisa: 13 pertanyaan di brief (aturan tap kedua/19:00, foto disimpan atau tidak, masa simpan event 12 bulan, akun hanya-lihat di mesin, persetujuan tertulis wajah).

## Gelombang B - Absen web pekerja kantor (brief `docs/rencana/absen-web-kantor.md`)
Web = jalur utama pekerja kantor, HP = lapangan. 1) pengukuran FAR/FRR face-service; 2) gerbang kualitas dan petunjuk cahaya; 3) toleransi akurasi lokasi + status "menunggu verifikasi HR kantor tugas"; 4) pendaftaran wajah untuk pekerja kantor (enroll kini hanya TEAM_LEADER/EMPLOYEE) + persetujuan biometrik; 5) multi-bingkai, alignment, templat ganda, ambang disetel. Nomor migrasi dicek ulang (v2_0040+ dipakai Hikvision lebih dulu).

## Gelombang C - E2E dan verifikasi
- Selesaikan butir terblokir di tumpukan lokal dengan wajah palsu: BAST disahkan + isi dokumen, Jadwal harian HP setelah absen, galat lembur HP, A7, aset, mess, K3 popup, offboarding, peran ganda, suite v3 (`alur-e2e-v3-regresi`, 175 langkah).
- Beta: ulang setelah tiap kenaikan; butuh sambungan adb aktif.

## Gelombang D - Fitur dan keputusan klien yang belum dikode
Pengingat dokumen kendaraan (6 PR, menunggu "mulai"); penerima eksternal aset (ADR 0003); inspeksi kendaraan (layar Buat web+HP); lampiran lembur dan berkas mess; restore modul + UI Arsip (hapus terjadwal); persetujuan biometrik + kebijakan privasi (teks hukum dari pemilik); survei tanggal laporan dengan titik survei nyata.

## Gelombang E - Utang teknis
- Struktur kode Fase 1-5 (penyatuan komponen web, pecah berkas raksasa mobile, repository mobile, tes sejajar, token tunggal); menyusutkan baseline lint mobile (`docs/MOBILE-LINT.md`); tes arsitektur web (berkas >500 baris).
- RLS lalu enkripsi face_embedding (nomor migrasi digeser); golden mobile via workflow Linux (8 golden di-skip); hapus kode yatim `pages/projects`; Usability Test 5 orang per peran.
- Kecil: E5-10 (401 `/auth/refresh` di halaman login: butuh rancangan sesi, bukan penanda localStorage); jalur venv Windows di `gen:api:export` (verify.sh web gagal di worktree baru); tombol Coba lagi pada galat pilihan PM; cakupan tes 403/404 ekspor bulanan.

## Menunggu pemilik
Rilis prod 1.8.5; langkah server/sudo (cadangan Windows pobonguar, peran vms_api, cron retensi `--cek`, `VITE_APP_ENV: beta`); uji tangkapan HTTP Listening (192.168.88.127:8099) dan cek ISAPI di peramban; jawaban brief Hikvision; teks persetujuan wajah; Keluar manual di HP `.beta` dan sambungan adb; hapus cabang `golden-update/*`; pembersihan data uji beta lewat pgAdmin (skrip disiapkan saat E2E selesai).

## Pembersihan
Worktree agen (`.claude/worktrees/*`), DB `kt_*` di vms-test-db, data uji `QA-E2E*-`/`QA-UJI-` (beta, lokal), penangkap uji (`hik-tangkap/penangkap.py`), tumpukan lokal e2e-lokal.
