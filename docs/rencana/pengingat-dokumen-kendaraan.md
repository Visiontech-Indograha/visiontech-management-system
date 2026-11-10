# Rencana: Pengingat Masa Berlaku Dokumen Kendaraan (10 Nov 2026)

Status: Disetujui perencanaan, implementasi menunggu perintah mulai dari pemilik. Tidak ada kode yang diubah.
Sumber data: origin/development @31558532. Tanda [VERIFIKASI] = belum dicek penuh di kode.

## 0. Keputusan pemilik (10 Nov 2026)
1. "Setelah 1 minggu" = pengingat harian dari H-7 sampai dokumen diperbarui, termasuk sesudah jatuh tempo ("Terlambat N hari").
2. Saluran: lonceng/notifikasi dalam aplikasi + notifikasi lokal HP dahulu. Email/WhatsApp = tahap 2.
3. SIM pengemudi IKUT (dokumen karyawan). Pengingat SIM dikirim ke OM, HSE, DAN karyawan pengemudi itu sendiri. Perlu relasi kendaraan-pengemudi (dirancang di PR 1).
4. Penerima: HSE kantor + OM kantor (salinan). PM/pemilik kendaraan opsional: tidak dibuat dulu. Pengganti bila kantor tanpa HSE: OM, lalu HR (ADMIN_HR_GA), lalu catat log + Discord.
5. Jam kirim 08:00 WIB.
6. Ambang default 30/21/14 hari lalu harian dari 7; dapat diubah per jenis dokumen oleh SA/OM. (default, menunggu konfirmasi)
7. Jenis dokumen awal: STNK, KIR, pajak tahunan, pajak 5 tahunan, SIM, asuransi. BPKB dikecualikan (tak punya masa berlaku). (default, menunggu konfirmasi)

## 1. Data yang ADA
- `vehicle` (db/06): office_id, division_id, vehicle_type, name, number_plate (unik aktif), team_id, status, soft delete.
- `vehicle_file`: type enum `vehicle_file_type_enum` = STNK|BPKB|KIR saja, path_file, status doc_status, active_at, expired_at NOT NULL. Tidak ada nomor dokumen, tidak ada pajak tahunan/pajak 5 tahunan/asuransi, tidak ada riwayat (satu baris per unggah; menimpa atau menambah? [VERIFIKASI] asset_service).
- `vehicle_inspection`: hanya foto inspeksi (tanpa tanggal berlaku).
- API: /assets/vehicles, /vehicles/{id}/files (GET, POST), /inspections (asset_route.py). Web: AssetCreateDialog (form kendaraan), belum ada kolom status berlaku [VERIFIKASI].
- SIM: `employee_file` (type 'SIM_A','SIM_B', expired_at NULL-able) = milik karyawan, bukan kendaraan. Sudah ada GET /documents/expiring (EXPIRED, CRITICAL<=7, WARNING<=30) + POST /documents/cron/expire-documents (izin RUN_SYSTEM_JOBS) untuk dokumen karyawan; kendaraan belum tercakup.
KURANG: jenis dokumen yang dapat dikonfigurasi (PAJAK, ASURANSI, dll), nomor dokumen, tanggal terbit, riwayat perpanjangan, ambang per jenis, penanda "dokumen berlaku saat ini", relasi kendaraan-pengemudi (untuk SIM).

## 2. Infrastruktur notifikasi & penjadwal
- Tabel `notification` (user_id, kind<=40, title, body, daily_plan_id, target, read_at); `NotificationRepository.insert_for_users` + siaran SSE (/events); web: NotificationBell; mobile: live_events.dart (SSE) + local_notifier.dart (flutter_local_notifications, lokal terjadwal, mis. attendance_reminders).
- TIDAK ADA push FCM (auth_device hanya token kredensial sidik jari). Tak ada email/WhatsApp [VERIFIKASI]. Discord hanya alert internal (core/alerts.py). Kampanye K3: tabel hse_campaigns (popup wajib baca), bukan pengingat.
- Penjadwal: TIDAK ada worker/APScheduler. Pola ada: endpoint cron `POST /cron/attendance/alert-missing` dan `/documents/cron/expire-documents` (izin RUN_SYSTEM_JOBS) dipicu cron host; deploy/autodeploy.sh dicron tiap menit (flock), healthcheck.sh cron 5 menit; app/cli.py (cleanup-idempotency, belum terjadwal). Server 4 GB: JANGAN tambah kontainer worker; pakai perintah CLI/endpoint cron + cron host, 1 kali/hari (cukup ringan).

## 3. Penerima (HSE)
- SystemRole.HSE ada (permissions.py; punya MANAGE/VIEW_VEHICLE_INSPECTIONS). Peran tambahan lewat `user_role_assignment` (ADR 0002, v2_0029, kolom role+office_id), aktif bila ROLE_ASSIGNMENT_ENABLED. OM boleh beri HSE (PR #410 [VERIFIKASI]).
- Templat kueri: `hr_user_ids_for_office` (peran utama di kantor + penugasan aktif). Buat `hse_user_ids_for_office(office_id)` serupa. Penerima = HSE kantor kendaraan.
- Fallback bila tak ada HSE di kantor: saran OM kantor itu lalu ADMIN_HR_GA kantor; bila tetap kosong, catat peringatan log + Discord alert (jangan diam).

## 4. Rancangan jadwal idempoten
- Tabel baru `document_reminder` (expand): (doc_kind, doc_id, due_date, stage, send_date, UNIQUE(doc_id, due_date, stage, send_date)) + `notification` tetap dipakai untuk isi. Unik DB = tidak ganda; INSERT ... ON CONFLICT DO NOTHING lalu kirim hanya baris baru (satu transaksi).
- Hari = tanggal WIB (core/time.py WIB). sisa = expired_date(WIB) - hari_ini.
- Tahap: sisa<=30 -> T30 (sekali), <=21 -> T21, <=14 -> T14 (sekali masing-masing, jadi bila cron mati lalu hidup tetap terkirim sekali, tahap terlewat tak dobel); sisa<=7 s.d. dibatalkan -> HARIAN (kunci send_date). Sesudah jatuh tempo: "terlambat N hari" sampai diperbarui.
- Berhenti otomatis: kueri hanya memilih dokumen yang expired_at-nya MASIH terbaru-per-(kendaraan,jenis) dan <= batas; saat berkas baru/expired_at maju, dokumen lama tak lagi terpilih. Dokumen sudah diganti = tak ada kiriman.
- Cron host 08:00 WIB (atau 01:00 UTC) memanggil CLI `python -m app.cli kirim-pengingat-dokumen`; aman dijalankan ulang tiap jam (idempoten).
- Tes: tanggal diinjeksi (dev offset di core/time.py), skenario lompat hari (cron mati 5 hari), dua proses bersamaan (tests/concurrency.py), perubahan tanggal di tengah jalan, batas tanggal 30/21/14/7/0/-1.

## 5. UI
- Web: kolom "Berlaku s.d." + lencana warna (hijau>30, kuning<=30, oranye<=14, merah<=7/terlambat) di daftar kendaraan; kartu ringkasan "Akan habis (30 hari)"; halaman "Pusat Pengingat" HSE (daftar urut paling mendesak, tombol Perbarui dokumen). Teks sederhana: "Habis 12 hari lagi", "Terlambat 3 hari".
- Mobile (HSE): daftar "Dokumen akan habis" + notifikasi dari SSE; cache Drift agar terlihat offline; notifikasi lokal terjadwal 08:00 dari cache (pola attendance_reminders) sebagai push pengganti FCM.

## 6. Data/migrasi, izin, audit, PR, estimasi, risiko
- Expand-contract: (a) tambah `vehicle_file`: doc_no, issued_at, tipe jadi VARCHAR/tabel `document_type`(kode, nama, ambang JSON, berlaku_untuk) menggantikan enum; (b) data awal STNK/KIR/PAJAK/SIM; (c) enum lama dipertahankan sampai rilis berikutnya. Riwayat: tiap perpanjangan = baris baru, lama status 'replaced'.
- Izin baru VIEW_DOCUMENT_REMINDERS (HSE, OM, SA) & MANAGE_DOCUMENT_TYPES; audit untuk ubah ambang/jenis dan tiap perpanjangan; RLS/cakupan kantor seperti aset.
- PR: 1 DB+model (1.5 hr) | 2 API jenis+riwayat+status (2) | 3 penjadwal+CLI+cron+tes waktu (2.5) | 4 web (2.5) | 5 mobile (2.5) | 6 deploy cron & QA (1). Total ~12 hari kerja.
- Risiko: data lama expired_at tidak akurat; cron host belum ada untuk API (butuh pemilik pasang); tanpa FCM, HP mati tak menerima sampai dibuka; banjir pengingat harian (grup per kendaraan dalam 1 notifikasi ringkas HSE).


## 7. Urutan PR dan definisi selesai
Semua PR ke `development`, satu fase kecil per PR, CI hijau, tidak langsung merge ke beta/prod.
- PR1 [DB]: migrasi expand (jenis dokumen, doc_no, issued_at, riwayat, `document_reminder`, relasi kendaraan-pengemudi). Selesai: migrasi naik/turun di vms_test, enum lama tetap, tes arsitektur SQL hijau.
- PR2 [API]: jenis dokumen + riwayat + status berlaku + ambang per jenis + izin/audit + `hse_user_ids_for_office`. Selesai: matriks peran lulus, OpenAPI snapshot dan tipe web diperbarui, kontrak lama tetap jalan.
- PR3 [Penjadwal CLI + cron host]: `python -m app.cli kirim-pengingat-dokumen`, idempoten, fallback penerima, SIM ke OM+HSE+pengemudi. Selesai: tes tanggal injeksi (30/21/14/7/0/-1), cron mati beberapa hari, dua proses bersamaan (xdist), perubahan tanggal; skrip cron di deploy/ beserta petunjuk.
- PR4 [Web]: kolom "Berlaku s.d." + lencana, kartu ringkasan, halaman Pusat Pengingat, pengaturan ambang. Selesai: lima kondisi layar, teks Indonesia sederhana, tes Vitest, verify web lulus.
- PR5 [Mobile]: daftar "Dokumen akan habis", SSE, cache Drift, notifikasi lokal 08:00. Selesai: tes widget, flutter analyze bersih, uji HP lewat UI.
- PR6 [QA]: uji nyata per peran lewat UI/HP, audit kebocoran antar kantor, laporan QA. Selesai: tanpa temuan terbuka.

## 8. Langkah milik pemilik
- Beri perintah mulai implementasi.
- Konfirmasi default (6) dan (7), atau ubah.
- Pasang cron host setelah PR3 rilis: panggil CLI harian 08:00 WIB (01:00 UTC) dengan flock; agen tidak menyentuh server.
- Isi relasi kendaraan-pengemudi (siapa mengemudikan kendaraan mana) dan periksa tanggal berlaku data lama.
