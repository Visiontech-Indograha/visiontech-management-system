# Rencana: absensi Hikvision LANGSUNG (ISAPI) ke API VMS, tanpa PC iVMS-4200

Status: RANCANGAN / Usulan. Tidak ada kode, skema, server, atau perangkat yang diubah dokumen ini. Pembuat: arsitek. Dasar: `origin/development` @ 6e206b5d (kepala Alembic `v2_0039_indeks_organisasi_tenant`).
Menggantikan sebagian `docs/rencana/absensi-hikvision-ivms4200.md` (opsi A4: perantara + HMAC). Bagian model data, aturan lokasi, dan pertanyaan bisnis di dokumen itu tetap berlaku kecuali disebut lain di sini.
Pemilik keputusan: pemilik VMS. Aturan bisnis `00-KONTEKS-DOMAIN` tidak diubah dokumen ini.

Penanda:
- PERLU VERIFIKASI = fakta Hikvision/jaringan yang berasal dari materi luar atau ingatan, belum dicek di perangkat Pekanbaru atau dokumen resmi. JANGAN dianggap benar dan JANGAN dikodekan sebagai kepastian.
- (bukti: berkas) = fakta dari repo `origin/development`.
- LANGKAH PEMILIK = hanya pemilik atau teknisi kantor yang mengerjakan. Agen tidak menyentuh perangkat Hikvision, server, atau prod.

Kebutuhan baru pemilik (13 Nov 2026): perangkat Hikvision Pekanbaru mengirim absensi LANGSUNG ke backend/PostgreSQL lewat ISAPI, tanpa PC iVMS-4200 sebagai perantara. Absensi kantor Pekanbaru (Hikvision) boleh CAMPUR dengan HP/web dalam satu hari dan tetap valid.

## 0. Ringkasan putusan yang diusulkan

| # | Usulan | Alasan singkat |
|---|---|---|
| 1 | Jalur utama = perangkat mendorong event (HTTP Listening/Push) ke endpoint penerima baru di API | Tanpa PC perantara, hampir nyata-waktu, tanpa komponen baru di server |
| 2 | Fallback/rekonsiliasi = tarik (pull) ISAPI `AcsEvent` lewat perintah CLI terjadwal (cron), bukan layanan baru | Tutup celah putus jaringan; RAM 4 GB tidak bertambah |
| 3 | Event mentah disimpan lebih dulu (tabel baru), baru diolah ke `attendance` | Bukti, idempotensi, bisa diproses ulang |
| 4 | Sumber absen dicatat (`clock_in_source`, `clock_out_source`) dan satu sesi masuk-pulang boleh lintas sumber | Syarat "campur tetap valid" |
| 5 | Endpoint penerima TIDAK dibuka ke internet; hanya LAN/VPN privat; HTTP polos hanya di jaringan privat | Perangkat tak menandatangani HMAC dan sering tanpa TLS |
| 6 | Foto dari perangkat: default TIDAK disimpan (usulan), embedding dari perangkat tidak pernah disimpan | PDP; lihat bagian 2.8 |
| 7 | Rilis berfitur-bendera per kantor, mode bayangan dulu | Aman untuk absensi yang dipakai penggajian |

## 1. Keadaan nyata kode (terverifikasi di `origin/development`)

### 1.1 Tabel dan alur absensi

| Hal | Fakta | Bukti |
|---|---|---|
| Tabel `attendance` | Satu baris per sesi masuk; kolom: `employee_id`, `attendance_date`, `target_location_type` (OFFICE/WORK_PLAN_DAILY), `office_id`, `daily_plan_id`, `scheduled_in/out`, `clock_in_at`, `clock_out_at` (NULL = sesi terbuka), `in_lat`/`in_lng` NOT NULL, `face_match_score` NOT NULL, `face_photo_path` VARCHAR(255) NOT NULL, `face_status` (MATCHED, MISMATCH, NOT_CHECKED, NOT_ENROLLED, SERVICE_DOWN, STALE), `distance_to_target_m`, `is_within_attendance_radius`, `om_approval_status` (AUTO_VALID, PENDING_OM, APPROVED_BY_OM, REJECTED_BY_OM), `city_zone_status`, `meal_allowance_amount`, `create_at/update_at/delete_at`. TIDAK ada kolom sumber absen, tidak ada koordinat/jarak pulang, tidak ada kolom perangkat. | `db/06_master_schema_v2.sql:614-641` |
| Sumber tidak disimpan | `AttendanceSessionRepository.insert(... source="MOBILE" ...)` menerima argumen `source`, tetapi SQL INSERT tidak menulisnya. Jadi "dari mana" absen sekarang tidak terekam sama sekali. | `attendance_session_repository.py:438-470` dan INSERT sekitar baris 550 |
| Satu masuk per hari | Ditegakkan di service (`ALREADY_CHECKED_IN`, 409; masuk kedua hanya bila yang lama ditolak) dan kunci baris karyawan (`lock_employee`); BUKAN constraint unik di DB. | `attendance_session_service.py:83,384,467`; repository `lock_employee` |
| Sesi terbuka | `open_session(employee_id, valid_only)`: sesi terbaru tanpa `clock_out_at`. Pulang hanya untuk sesi VALID (AUTO_VALID/APPROVED). | `attendance_session_repository.py:97`; service `check_out` baris 470-498 |
| Pulang | `close()` hanya mengisi `clock_out_at` (+ catatan/bukti luar zona). Tidak ada lat/lng pulang. Pulang tidak pernah membuat baris baru. | repository `close` (baris 616) |
| Kanal dikunci per jenis pekerja | `CHANNEL_OF_MODE = {"FIELD": "MOBILE", "OFFICE": "WEB"}`: pekerja kantor hanya boleh web, pekerja lapangan hanya HP, kecuali admin; selain itu `WRONG_ATTENDANCE_CHANNEL` (403). | `attendance_session_service.py:92-120` |
| Batas pulang mandiri | Pulang online ditutup pukul `ATTENDANCE_CLOSE_TIME` (bawaan 19:00) kecuali ada lembur aktif; sesi yang lupa ditutup ditutup otomatis oleh cron; sesi tanggal sebelumnya berakhir tengah malam (kerja malam tidak lintas hari). | service baris 502-549; `attendance_cron_controller.py` |
| Wajah | Swafoto wajib di HP/web; dicocokkan lewat `face-service` (embedding 512-d), ambang di API (`MATCH_THRESHOLD`); layanan mati = PENDING_OM. Pekerja kantor belum bisa mendaftar wajah (hanya TEAM_LEADER/EMPLOYEE). | `docs/rencana/absen-web-kantor.md` A3 |
| Lokasi | Haversine ke target (kantor/lokasi tugas); luar radius = PENDING_OM + penjelasan + foto bukti. | `attendance_session_repository.py` (insert) |
| Rekap, uang makan | `meal_allowance_amount` dihitung saat INSERT dari zona kota kantor utama; rekap uang makan memakai `meal_allowance_recap`; lembur lewat `has_active_overtime`. | repository `insert`, `meal_allowance_recap` (baris 1117), `has_active_overtime` (1194) |
| Mobile offline | `POST /attendance/offline` idempoten per `client_op_id`. | `attendance_offline_service.py` |
| Cron | Perintah CLI sudah ada: `python -m app.cli <perintah>` (`create-admin`, `seed`, `cleanup-idempotency`, `buat-partisi`, `hapus-terjadwal`, `backup-db`). Pola ini dipakai untuk tarik ISAPI. | `api/app/cli.py:188-215` |
| Rate limit | Token bucket di memori per IP/pengguna, satu instance saja; IP klien dibaca dari `X-Forwarded-For` hanya bila peer ada di `TRUSTED_PROXY_IPS`. | `api/app/core/rate_limit.py`, `config.py:192` |
| Retensi PDP | Tabel `retention_policy`, `retention_run_log`; CLI `hapus-terjadwal` (kebijakan NONAKTIF sampai pemilik menyalakan; wajib `--cek` dulu). | migrasi `v2_0036`, `docs/SERAH-TERIMA-AI.md` bagian 2 |
| Penyimpanan berkas | MinIO via `file_object`; akses lewat `/files/{id}/url`; validasi gambar di `app/core/image.py`. | skill `vms-storage-minio` |
| Pemetaan karyawan | `employee.employee_no VARCHAR(50)` unik aktif (`uq_employee_no_active`). | `db/06:104,117` |

### 1.2 Apa yang harus berubah supaya "Hikvision" menjadi sumber sah dan CAMPUR valid

1. Catat sumber. Tambah `attendance.clock_in_source` dan `clock_out_source` (nilai `MOBILE`, `WEB`, `HIKVISION`; NULL pada baris lama dibaca `MOBILE`), serta `clock_in_device_id`/`clock_out_device_id` (boleh NULL). Perbaiki `insert()` agar menulis sumber (kini dibuang).
2. Lepas kunci kanal. `_employee_for_channel` menolak pekerja kantor lewat HP dan pekerja lapangan lewat web. Penerima Hikvision TIDAK lewat `_employee_for_channel` (perangkat bukan kanal pengguna), jadi masuk Hikvision boleh bagi siapa pun yang terpetakan. Bagian "pulang lewat HP/web setelah masuk Hikvision" tetap tunduk pada aturan kanal sekarang: pekerja kantor pulang lewat web (sudah sah), pekerja lapangan yang kebetulan tap di kantor lalu pulang lewat HP (sah). Tidak ada perubahan aturan kanal yang diperlukan untuk campur; yang perlu hanya `open_session` mengenali sesi yang dibuka perangkat.
3. Baris masuk dari perangkat harus memenuhi kolom NOT NULL tanpa memalsukan data:
   - `in_lat`/`in_lng` = koordinat kantor pemilik perangkat; `distance_to_target_m` = 0; `is_within_attendance_radius` = true; `target_location_type` = `OFFICE`; `om_approval_status` = `AUTO_VALID` (kehadiran fisik di perangkat kantor menggantikan GPS; sama dengan usulan D di rencana lama).
   - `face_match_score` = 0 dan `face_status` = `NOT_CHECKED` BUKAN pilihan baik karena rekap/monitor membaca arti "wajah belum dicek". Usulan: tambah nilai `face_status` = `DEVICE` (CHECK diperluas, expand-only) dan `face_match_score` = 0; perangkat yang melakukan verifikasi wajah, bukan VMS. Pemilik/QA perlu menyetujui nama nilai.
   - `face_photo_path` NOT NULL: bila foto perangkat tidak disimpan (usulan default), isi dengan penanda tetap `device:<device_id>` (bukan jalur berkas). `/files/...` tidak boleh mencoba membukanya. Alternatif lebih bersih (lebih mahal): migrasi `ALTER COLUMN face_photo_path DROP NOT NULL` (pelonggaran, kompatibel mundur, tetapi membuka kemungkinan NULL bagi pembaca lama; perlu audit pembaca). Keputusan teknis untuk PR db; saran: penanda tetap.
4. Pulang dari perangkat = `close(at=waktu_event)` pada sesi terbuka yang valid; tidak membuat baris baru. Pulang dari HP/web pada sesi yang dibuka perangkat sudah jalan lewat `close()` yang sama (tidak menyentuh kolom sumber masuk).
5. Aturan arah: perangkat umumnya melapor "wajah dikenali" tanpa arah (PERLU VERIFIKASI mode check-in/out per model). VMS menentukan arah dari urutan: tidak ada sesi terbuka hari itu = masuk; ada sesi terbuka valid dan lewat jarak minimum = pulang; ulang dalam jendela duplikat = DUPLIKAT. Jarak minimum masuk-pulang 30 menit dan jendela duplikat 2 menit adalah saran awal (rencana lama bagian C/D) yang DIKONFIRMASI pemilik (pertanyaan 4 di bagian 8).
6. Pulang setelah `ATTENDANCE_CLOSE_TIME`: pembatas 19:00 hanya untuk pulang mandiri online. Event perangkat adalah fakta kejadian, bukan permintaan; usulan: event perangkat setelah jam tutup tetap dicatat sebagai pulang (bukan ditolak), dan tanda lembur mengikuti aturan sekarang. Ini aturan bisnis: dibawa ke pemilik (pertanyaan 5).
7. Uang makan dan zona kota: dihitung saat masuk dari kantor pemilik perangkat (dalam kota kantor itu). Fungsi hitung sudah di `insert()`; harus dipanggil dengan jalur yang sama untuk semua sumber (refaktor kecil: ambil bagian hitung jadi fungsi bersama). Campur sumber tidak mengubah tarif; kasus masuk di kantor tapi pulang di luar kota tetap pertanyaan bisnis rencana lama (4).
8. Rekap/ekspor/monitor: tambah kolom sumber di keluaran; hitungan hadir/terlambat tetap dari `clock_in_at` vs `scheduled_in`.
9. Karyawan yang tidak punya `employee_no` terpetakan, atau nonaktif: event ditolak dan dicatat (tidak dibuat absen). Lihat 2.5.

## 2. Rancangan endpoint penerima

### 2.1 Alur

```
Perangkat Hikvision (LAN Pekanbaru)
   |  HTTP POST multipart/form-data  (JSON AccessControllerEvent + JPEG)   [PERLU VERIFIKASI format]
   v
Jalur masuk privat (LAN/VPN) --> API VMS  POST /api/v1/integrations/hikvision/events/{token}
   |-- otentikasi (token + allowlist IP + rate limit)
   |-- simpan event mentah (tabel baru), UNIQUE (device_serial_no, serial_no_event)
   |-- filter major 5 / minor yang diizinkan --> olah ke attendance (service)
   v
PostgreSQL
Cron CLI "hikvision-tarik" (tiap N menit) --> ISAPI AcsEvent (pull) --> jalur simpan yang SAMA
```

Satu fungsi layanan `HikvisionEventService.ingest(raw, source="PUSH"|"PULL")` dipakai kedua jalur, sehingga idempotensi dan aturan sesi identik.

### 2.2 Otentikasi (perangkat tidak menandatangani HMAC)

Perangkat Hikvision pada umumnya hanya mengirim POST ke URL yang diisi teknisi; kemampuan header kustom atau tanda tangan tidak umum (PERLU VERIFIKASI per model/firmware). Lapisan yang diusulkan, semuanya dipakai bersamaan:

1. Token rahasia di path URL: `/api/v1/integrations/hikvision/events/{token}`. Token acak 32 byte (base64url) per perangkat, disimpan sebagai hash SHA-256 di tabel perangkat (bukan teks), dibandingkan dengan `hmac.compare_digest`. Alasan di path: hampir semua firmware mendukung mengisi URL; header kustom belum pasti (PERLU VERIFIKASI). Risiko: token tampil di log akses proxy. Mitigasi: log akses dan log API menyamarkan segmen terakhir path (bukan menulis URL penuh); token dapat diputar dari menu admin. Jika ternyata perangkat mendukung header kustom (PERLU VERIFIKASI), pindahkan token ke header dan path dibiarkan tanpa token.
2. Allowlist IP: hanya IP LAN perangkat terdaftar (kolom `allowed_cidr` per perangkat, mis. `192.168.88.13/32`). IP diambil lewat `client_ip()` yang sudah ada (hanya percaya `X-Forwarded-For` dari proxy di `TRUSTED_PROXY_IPS`). Jangan lupa: bila penerima ada di belakang NAT/proxy yang menyembunyikan IP sumber, allowlist tak berguna; periksa saat uji jaringan (pertanyaan 3).
3. Digest (untuk arah keluar saja): Digest dipakai VMS saat MENARIK dari perangkat (bagian 3). Untuk arah masuk (push) perangkat umumnya tidak melakukan tantangan Digest ke penerima; JANGAN mengandalkan itu. PERLU VERIFIKASI apakah firmware mendukung Basic/Digest ke penerima; bila ada, boleh ditambahkan sebagai lapisan keempat tetapi bukan pengganti 1 dan 2.
4. Rate limit: per perangkat, ember token di memori (pola `rate_limit.py`, grup baru `hikvision`), usulan 120 permintaan/menit/perangkat dan 30/menit untuk token tidak dikenal per IP. Permintaan di atas batas = 429 `Retry-After`. Mode `RATE_LIMIT_ENFORCE` seperti grup lain.
5. Batas ukuran: baca tubuh bertahap, tolak di atas 2 MiB total (JPEG dari perangkat umumnya puluhan-ratusan KB; nilai dikonfirmasi lewat sampel nyata, PERLU VERIFIKASI), bagian JSON maks 64 KiB, maksimum 2 bagian berkas; status 413. Jangan memuat seluruh tubuh tanpa batas ke memori (RAM 4 GB).
6. Validasi gambar: periksa magic bytes JPEG (`FF D8 FF`) dan dekode ringan dengan `app/core/image.py` bila disimpan; jangan percaya `Content-Type` bagian. Bagian gambar yang gagal validasi = event tetap diolah tanpa gambar (gambar tidak wajib untuk absensi), dicatat `image_rejected`.
7. Respons selalu 200 dengan badan kecil tetap untuk event valid/duplikat/difilter (agar perangkat tidak mengulang tanpa henti); 401 untuk token salah (tanpa petunjuk); 413/429/415 sesuai kasus; 5xx hanya galat nyata (perangkat boleh mencoba lagi). Perilaku retry perangkat PERLU VERIFIKASI (apakah ia mengulang pada non-2xx, berapa kali, berapa lama antrean di perangkat).
8. Rute ini DIKECUALIKAN dari JWT/`require_permission` dan harus didaftarkan sebagai penjaga khusus di `api/tests/architecture/test_route_guards.py` (pengecualian keamanan yang disadari; ditinjau arsitek). Tidak ada rute baru lain tanpa izin.
9. Tipe konten: `multipart/form-data` utama; terima juga `application/json` murni (beberapa mode kirim tanpa gambar, PERLU VERIFIKASI) dan tolak XML (atau urai tanpa entitas eksternal bila terbukti perlu; XXE).

### 2.3 Filter event

Hanya event dengan `majorEventType == 5` (Event Akses; nilai ini dari materi luar, PERLU VERIFIKASI) dan `subEventType` dalam set yang dapat diatur: usulan awal `75` (verifikasi wajah lolos), `1` (kartu lolos), `38` (sidik jari lolos). Semua nilai minor PERLU VERIFIKASI terhadap dokumentasi ISAPI Hikvision untuk model Pekanbaru; jangan dikodekan keras: simpan di tabel konfigurasi per perangkat (`allowed_sub_events INT[]`) atau pengaturan sistem. Event lain (pintu terbuka paksa, alarm, wajah tak dikenal, dll.) disimpan sebagai `FILTERED` tanpa efek ke absen (agar bisa diaudit; ukuran kecil) atau dibuang bila volumenya tinggi (keputusan setelah melihat sampel).
Nama field JSON (`AccessControllerEvent`, `employeeNoString`, `cardNo`, `serialNo`, `currentVerifyMode`, `dateTime`, `deviceName`) berasal dari materi luar: PERLU VERIFIKASI dengan sampel nyata. Parser memakai Pydantic dengan `extra="ignore"` dan SEMUA field opsional kecuali yang dibutuhkan; kegagalan parsing = event disimpan `PARSE_ERROR` untuk diperiksa, bukan dibuang.

### 2.4 Idempotensi

- `UNIQUE (device_serial_no, serial_no_event)` pada tabel event mentah, `INSERT ... ON CONFLICT DO NOTHING RETURNING`. Konflik = balas 200 `duplikat` tanpa efek. `serial_no_event` = field `serialNo` event (PERLU VERIFIKASI: apakah naik monoton dan apakah di-reset saat perangkat dihapus/restart).
- Jika `serialNo` tidak ada atau tidak dapat dipercaya (PERLU VERIFIKASI), jatuh ke kunci turunan: hash SHA-256 dari (serial perangkat, `employeeNo`, `dateTime` perangkat, `minor`), simpan di kolom `event_key` dan pasang UNIQUE di kolom itu sebagai gantinya. Desain skema memuat kedua kolom agar tidak butuh migrasi ulang.
- Pengolahan ke `attendance` ikut dalam transaksi yang sama dengan penyimpanan event (satu commit) dan memakai `lock_employee` (kunci baris karyawan) supaya push dan pull yang serentak tidak membuat dua sesi.

### 2.5 Pemetaan karyawan

- Tabel `attendance_device_person`: (`device_id`, `employee_no_device`, `card_no` opsional) -> `employee_id`. UNIQUE (`device_id`, `employee_no_device`) bila aktif.
- Usulan kunci: `employee_no_device` = `employee.employee_no` VMS (nomor induk karyawan yang sudah unik aktif). Dengan begitu pemetaan bisa otomatis (cocok persis) dengan konfirmasi admin, dan tabel pemetaan hanya menampung pengecualian. PERLU VERIFIKASI batas panjang/aturan karakter `employeeNo` di perangkat (umumnya angka/huruf pendek). Bila `employee_no` VMS tidak muat, pakai nomor pendek buatan VMS.
- Pengelola: HR kantor Pekanbaru (admin perangkat, pertanyaan 6), lewat halaman admin web (PR pemetaan). Izin baru khusus (mis. `device.manage`) sesuai `cakupan kantor` ADR 0002: HR hanya melihat perangkat dan pemetaan kantornya; lintas kantor = 404.
- Event dari nomor tak terpetakan: simpan `UNMAPPED`, tampilkan di daftar "perlu dipetakan" (bukan membuat absen). Karyawan nonaktif/berhenti: `REJECTED_INACTIVE`, dicatat, alarm ringan ke admin.
- Pegawai bukan karyawan VMS (tamu, kontraktor di perangkat): tidak terpetakan, diabaikan.

### 2.6 Zona waktu dan jam perangkat

- Event membawa waktu perangkat dengan offset (mis. `2026-11-13T08:01:05+07:00`; format PERLU VERIFIKASI). Parser menerima ISO-8601 dengan offset; tanpa offset dianggap waktu zona perangkat (kolom `device.timezone`, bawaan `Asia/Jakarta`). Simpan UTC (`TIMESTAMPTZ`), hari kerja `attendance_date` dihitung di zona kantor (WIB, `core/time.py`).
- Simpan `device_time` (UTC) dan `received_at` (waktu server). Selisih = `received_at - device_time`. Event "baru" (bukan hasil tarik/penumpukan) dengan selisih > 2 menit -> peringatan (tidak dikoreksi otomatis) dan tampil di halaman perangkat; selisih > 24 jam atau di masa depan > 5 menit -> `CLOCK_SUSPECT`, event disimpan tapi TIDAK diolah ke absen sampai HR menindak. Nilai 2 menit dan 7 hari (umur maksimum event terlambat otomatis) adalah saran rencana lama (pertanyaan 15 sana); dikonfirmasi pemilik.
- Event lebih tua dari 7 hari: `NEEDS_REVIEW` (HR), tidak otomatis menjadi absen.
- Urutan pengolahan batch (hasil pull): urut menurut `device_time`, bukan `received_at`.
- Perangkat wajib NTP (LANGKAH PEMILIK; bagian 5).

### 2.7 Penyimpanan foto dan PDP

- Dasar kerja yang diusulkan: foto dari perangkat TIDAK disimpan secara default. Absen cukup dibuktikan oleh perangkat (id karyawan + waktu + sub-event). Ini mengurangi data biometrik dan sesuai usulan rencana lama (pertanyaan 8 sana: "tidak simpan foto").
- Bila pemilik minta foto bukti: simpan hanya foto event yang diolah menjadi absen (bukan seluruh foto), lewat `file_object` di bucket privat MinIO (kunci khusus awalan `hik/`), akses hanya lewat `/files/{id}/url`, DAN masuk kebijakan retensi: tambah baris `retention_policy` `hikvision_event_photos` = 30 hari (selaras putusan pemilik "30 hari data pribadi"), diaktifkan pemilik; dihapus lewat `hapus-terjadwal`. Event mentah (tanpa gambar) memakai kebijakan arsip terpisah (saran 12 bulan; nilai dikonfirmasi pemilik, bagian 8).
- JANGAN simpan embedding atau templat wajah dari perangkat (perangkat tidak mengirimnya di event; jangan juga ditarik lewat `FDLib`). Wajah di VMS (embedding `face-service`) dan wajah di perangkat adalah data terpisah, tidak dikonversi.
- Dasar hukum/persetujuan (UU PDP): wajah = data biometrik (data pribadi spesifik). Karyawan harus memberi persetujuan tertulis untuk pendaftaran wajah di perangkat dan untuk pemrosesan absensi; VMS mencatat tanggal persetujuan di `attendance_device_person.consent_at` (kolom wajib sebelum pemetaan boleh aktif). Teks persetujuan ditulis pemilik/hukum internal (butir terbuka SERAH-TERIMA 5.48). Konsultasi hukum internal PERLU; dokumen ini bukan nasihat hukum.
- Jangan menaruh foto/token/nomor karyawan di log; log hanya `device_id`, `event_id`, status, dan `employee_id` internal.
- Kunci "cegah pengambilan massal": pemetaan hanya mengubah izin pegawai; tidak ada endpoint ekspor foto perangkat.

### 2.8 Pengolahan ke `attendance` (aturan)

1. Cari `employee_id` dari pemetaan; periksa karyawan aktif, kantor perangkat = salah satu kantor yang boleh (beda kantor diterima dan ditandai, rencana lama pertanyaan 5).
2. Kunci baris karyawan (`lock_employee`). Hitung `attendance_date` (WIB). Cari sesi terbuka valid dan sesi hari itu.
3. Tidak ada sesi hari itu -> INSERT masuk (sumber `HIKVISION`, `clock_in_at = device_time`). Jika ada sesi hari itu yang berstatus ditolak (REJECTED_BY_OM) -> sama dengan aturan HP: boleh masuk ulang.
4. Ada sesi terbuka valid dan `device_time - clock_in_at >= jarak minimum` -> `close(at=device_time)` dan isi `clock_out_source = HIKVISION`, `clock_out_device_id`.
5. Ada sesi terbuka tetapi masih di dalam jendela duplikat -> `DUPLICATE`. Sesi sudah ditutup pada hari itu dan event baru datang: bukan "pulang kedua"; hari itu satu sesi saja -> `IGNORED_AFTER_CHECKOUT` (alternatif "pulang terakhir menimpa" dari rencana lama harus diputuskan pemilik, pertanyaan 4).
6. Sesi terbuka tetapi PENDING_OM (mis. masuk HP luar zona menunggu OM): event perangkat -> `NEEDS_REVIEW`, bukan pulang (sama dengan `CHECKOUT_NOT_VALID`).
7. Hasil tiap event disimpan di kolom `status`/`reason` tabel event (bagian 4) supaya halaman admin dan investigasi bisa melihat alasannya.
8. Cuti/izin disetujui pada hari itu: event diterima, ditandai konflik untuk HR (tidak otomatis menolak).

## 3. Fallback: tarik (pull) ISAPI Search

- Tujuan: rekonsiliasi dan menutup celah saat jaringan/penerima mati (event yang tidak pernah dikirim ulang oleh perangkat). Bukan jalur utama.
- Titik akses: `POST http://<ip-perangkat>/ISAPI/AccessControl/AcsEvent?format=json` dengan tubuh `AcsEventCond` (`searchID`, `searchResultPosition`, `maxResults`, `major`, `minor`, `startTime`, `endTime`) — nama field dan batas `maxResults` PERLU VERIFIKASI. Paginasi lewat `searchResultPosition` sampai `responseStatusStrg` menunjukkan selesai (PERLU VERIFIKASI nilai status).
- Bentuk: perintah CLI baru `python -m app.cli hikvision-tarik --sejak <iso>|--otomatis [--perangkat <id>] [--cek]` di `api/app/cli.py` (pola `hapus-terjadwal`/`buat-partisi`), dipanggil cron tiap 5-15 menit. BUKAN layanan/daemon baru: nol tambahan kontainer, RAM nol di luar proses sesaat (anggaran 4 GB aman; batas memori proses CLI: `maxResults` kecil, jangan memuat semua).
- Jendela tarik: `--otomatis` membaca `device.last_pull_to` dan menarik dari (last_pull_to - tumpang tindih 10 menit) sampai sekarang; tumpang tindih aman karena UNIQUE. Perangkat yang tidak terjangkau: catat `last_pull_error`, naikkan hitung gagal, alarm ke Discord lewat pola `alerts.py` setelah N kali (saran: 3 berturut-turut).
- Autentikasi ke perangkat: HTTP Digest (`httpx.DigestAuth`; PERLU VERIFIKASI apakah perangkat memakai Digest atau Basic; sebagian firmware lama tak mendukung Digest-SHA256). Tetapkan timeout eksplisit (connect 3 dtk, total 15 dtk); retry hanya untuk operasi baca idempoten dengan backoff, maksimum 3 kali.
- Kredensial perangkat: JANGAN di repo, `.env.example` (hanya nama variabel kosong), maupun DB teks biasa. Pilihan yang diusulkan: berkas rahasia server `hikvision.env` (chmod 600, di luar Git, pola `api.env`) berisi `HIKVISION_DEVICE_<ID>_USER` / `_PASS`, dimuat oleh CLI; tabel perangkat hanya menyimpan nama variabel (`credential_ref`). Akun perangkat khusus baca (operator/viewer, bukan admin) bila perangkat mendukung (PERLU VERIFIKASI). Kredensial dirotasi oleh teknisi; log tidak boleh memuat sandi.
- Di mana CLI berjalan: server prod di LAN 192.168.88.x (bagian 6). PERLU VERIFIKASI apakah server dapat menjangkau 192.168.88.13 (pertanyaan 3); jika perangkat berada di LAN lain, pull butuh rute VPN/Tailscale ke LAN perangkat.
- Pull tidak mengubah konfigurasi perangkat; hanya baca. Tidak ada perintah tulis (hapus orang, ubah jam) pada tahap ini.

## 4. Skema database (usulan; expand-only)

Nomor migrasi: kepala sekarang `v2_0039`. `docs/rencana/absen-web-kantor.md` memesan `v2_0040`/`v2_0041` dan rencana RLS memesan nomor berikutnya: ambil nomor bebas terbaru saat PR dibuka (perkiraan `v2_0042`; JANGAN menebak, cek `ls api/alembic_v2/versions` dan PR terbuka). Setiap migrasi baru wajib baris `down_revision` di `api/tests/architecture/test_alembic_v2.py` dan `downgrade()`.

### 4.1 Tabel baru (UUIDv7 untuk PK baru sesuai skill `vms-db`; `TIMESTAMPTZ`, tanpa `FLOAT`)

`attendance_device`
- `device_id` PK; `office_id` NOT NULL FK `office` (kantor tetap; kolom kantor siap RLS); `name`; `device_serial_no` (UNIQUE aktif); `model` (info, PERLU VERIFIKASI); `ip_address` (info); `allowed_cidr` (allowlist push); `token_hash CHAR(64)` (SHA-256 token path); `token_rotated_at`; `credential_ref` (nama variabel rahasia untuk pull); `timezone` default `Asia/Jakarta`; `allowed_sub_events INT[]`; `enabled`; `shadow_mode BOOLEAN NOT NULL DEFAULT TRUE` (mode bayangan: simpan, jangan olah); `last_seen_at`; `last_event_at`; `last_pull_to`; `last_pull_error`; `clock_skew_s`; `create_at/update_at/delete_at`.

`attendance_device_person`
- `device_id` FK, `employee_no_device`, `card_no` (nullable), `employee_id` FK, `consent_at TIMESTAMPTZ` (wajib sebelum aktif, lihat 2.7), `consent_ref`, `enrolled_at`, `removed_at`, `create_at/delete_at`. UNIQUE (`device_id`, `employee_no_device`) WHERE `delete_at IS NULL` dan `removed_at IS NULL`.

`attendance_device_event` (log mentah; tidak diubah selain `status/processed_*`)
- `event_id` PK; `device_id` FK; `device_serial_no` (salinan, untuk UNIQUE sesuai usulan pemilik); `serial_no_event BIGINT NULL`; `event_key CHAR(64) NULL` (hash cadangan, 2.4); `major_event_type INT`; `sub_event_type INT`; `employee_no_device VARCHAR(50)`; `card_no_hash` (hash, bukan kartu mentah); `verify_mode` (teks pendek, PERLU VERIFIKASI); `device_time TIMESTAMPTZ`; `received_at TIMESTAMPTZ DEFAULT now()`; `source` (`PUSH`/`PULL`); `status` (`RECEIVED`, `PROCESSED`, `FILTERED`, `DUPLICATE`, `UNMAPPED`, `REJECTED_INACTIVE`, `PARSE_ERROR`, `CLOCK_SUSPECT`, `NEEDS_REVIEW`, `IGNORED_AFTER_CHECKOUT`) dengan CHECK; `reason TEXT NULL`; `attendance_id UUID NULL` FK (absen yang terpengaruh); `payload_hash CHAR(64)`; `payload JSONB NULL` (JSON mentah TANPA gambar; di-null-kan oleh kebijakan arsip); `photo_file_id UUID NULL` FK `file_object` (hanya bila diizinkan). 
- Constraint: `UNIQUE (device_serial_no, serial_no_event)` (sesuai usulan pemilik; NULL tidak bentrok di PostgreSQL, sehingga baris tanpa `serialNo` dilindungi oleh `UNIQUE (device_serial_no, event_key)` yang kedua).
- Indeks: (`device_id`, `device_time` DESC); (`status`) parsial `WHERE status IN ('UNMAPPED','NEEDS_REVIEW','CLOCK_SUSPECT')`; (`received_at`) untuk retensi. Tabel bisa dipartisi bulanan bila volume besar (PERKIRAAN: ratusan sampai ribuan event/hari/kantor; belum perlu partisi).
- `office_id` ikut disalin ke event (turunan dari perangkat) bila RLS kelak memerlukannya; semua tabel baru `GRANT` ke `vms_api` (lihat `deploy/PERAN-RUNTIME.md`, migrasi `v2_0038`) dan RLS-ready: kolom kantor ada, kebijakan ditambahkan di gelombang RLS (jangan `ENABLE RLS` di migrasi ini).

Perubahan pada `attendance` (expand, kolom boleh NULL, tidak mengubah makna kolom lama):
`clock_in_source`, `clock_out_source` (CHECK `MOBILE|WEB|HIKVISION`, NULL = baris lama = MOBILE/WEB sesuai kanal), `clock_in_device_id`, `clock_out_device_id`, dan nilai `face_status = 'DEVICE'` (CHECK diperluas). Rencana lama menambahkan juga `clock_out_lat/lng/distance` untuk HP; di luar lingkup ini.
Catatan beban: `ALTER TABLE ... ADD COLUMN` nullable tanpa default cepat; CHECK tambahan pakai `NOT VALID` lalu `VALIDATE CONSTRAINT`; indeks pada tabel besar `CONCURRENTLY` dalam `autocommit_block`.

Baris retensi: `INSERT INTO retention_policy` untuk `hikvision_events` (arsip, nonaktif sampai pemilik menyalakan) dan `hikvision_event_photos` (30 hari), dengan pola `v2_0036`. `hapus-terjadwal` perlu cabang baru; itu PR terpisah.

### 4.2 Urutan pasang skema

Tabel baru dibuat lewat Alembic (bukan mengubah `db/06`/`db/08` yang berisi baseline); ikuti catatan bahwa tabel dengan FK dibuat setelah rujukannya (`vms-db` 2.1). Tes `test_sql_matches_schema.py` memerlukan sinkron bila tabel masuk `db/`: tanya db-engineer apakah tabel Alembic-only cukup (preseden: tabel `retention_policy` di `v2_0036`).

## 5. Langkah konfigurasi di perangkat (LANGKAH PEMILIK / TEKNISI KANTOR)

Agen tidak mengubah perangkat. Nama menu berbeda antar model dan firmware: semuanya PERLU VERIFIKASI. Panduan siap tempel untuk teknisi (isi `<...>` setelah pertanyaan dijawab):

1. Catat model, nomor seri, versi firmware, IP perangkat; foto label. Kirim ke arsitek (pertanyaan 1-2).
2. Amankan perangkat: ganti sandi bawaan admin, matikan layanan yang tak dipakai, jangan buka port perangkat ke internet/router (tanpa port-forward). Perbarui firmware bila direkomendasikan Hikvision (PERLU VERIFIKASI kerentanan model).
3. Waktu: aktifkan NTP (zona UTC+7), samakan jam dengan server. Catat bila NTP tak tersedia di LAN (PERLU VERIFIKASI server NTP lokal).
4. Buat akun khusus untuk tarik (viewer/operator, bukan admin) bila perangkat mendukung; kirim sandinya ke pemilik lewat jalur aman (bukan chat/repo).
5. Konfigurasi HTTP Listening (jalur utama): antarmuka web perangkat -> menu Integration/Protocol -> HTTP Listening (atau Event/Alarm Server; nama PERLU VERIFIKASI). Isi: URL/IP alamat penerima VMS (bagian 6), port, path `/api/v1/integrations/hikvision/events/<TOKEN>` (TOKEN diberi pemilik/arsitek, rahasia), protokol HTTP, format JSON bila ada pilihan, kirim gambar bila ada pilihan dan hanya bila pemilik memutuskan menyimpan foto (pertanyaan 8). Pada beberapa firmware path dan host harus dipisah ("Destination IP/Domain", "URL"); PERLU VERIFIKASI.
6. Uji: gunakan tombol "Test"/"Uji" di menu (bila ada). Tap oleh 1 orang uji. Periksa halaman admin VMS (setelah PR web) atau minta arsitek melihat log event (tanpa token).
7. Skrip tempel pemeriksaan jaringan dari PC di LAN yang sama (tidak mengubah apa pun). Contoh generik, ganti `<...>`:
   - Jangkau penerima: `curl -sv -m 5 http://<ip-server>:<port>/health` (harus 200).
   - Jangkau perangkat untuk pull (setelah akun ada; ISAPI `deviceInfo` hanya membaca): `curl -s -m 5 --digest -u <akun>:<sandi> http://<ip-perangkat>/ISAPI/System/deviceInfo` (port biasanya 80/443; 8000 umumnya port SDK Hikvision bukan HTTP — PERLU VERIFIKASI, jangan dianggap benar).
   - Cek jam perangkat: `curl -s -m 5 --digest -u <akun>:<sandi> http://<ip-perangkat>/ISAPI/System/time`.
8. Pendaftaran orang di perangkat (employeeNo = `employee_no` VMS), persetujuan tertulis karyawan sebelum foto wajah diambil (2.7). Nonaktifkan/hapus orang di perangkat saat karyawan berhenti (daftar "belum dihapus dari perangkat" di halaman admin).

Verifikasi 192.168.88.13:8000: dalam catatan pemilik perangkat/iVMS ada di `192.168.88.13:8000`. Port 8000 lazimnya SDK/port layanan Hikvision (bukan ISAPI HTTP, yang biasanya 80/443), dan alamat itu mungkin PC iVMS-4200 bukan perangkat. Teknisi diminta menjalankan `deviceInfo` di atas pada port 80 dan 443 perangkat sebenarnya. Hasil jadi masukan bagi bagian 3 dan pertanyaan 3.

## 6. Jaringan, jalur masuk HTTP, dan keamanan prod

### 6.1 Fakta repo tentang jalur masuk

- Prod: klien -> Cloudflare Tunnel -> kontainer web (Caddy `web/Caddyfile`) -> API `vms_api :8000` (`docs/CATATAN-IP-KLIEN.md`). Port host: web 8080, API 8000, DB 5433 (`skill vms-devops-infra`; `deploy/README.md`).
- Server di LAN 192.168.88.160 (alamat SSH dan MinIO di `deploy/README.md`), Tailscale 100.117.92.14.
- Caddy mempercayai `X-Forwarded-For` dari rentang privat dan 100.64.0.0/10 lalu menambahkan peer di kanan; `TRUSTED_PROXY_IPS` mengatur sisi API (`docs/CATATAN-IP-KLIEN.md`, `config.py:192`).
- TIDAK ADA di repo: aturan firewall/ufw terpasang, isi crontab prod, dan pengaturan port forward. PERLU VERIFIKASI oleh pemilik (pertanyaan 3).

### 6.2 Usulan jalur

- Perangkat TIDAK memakai jalur Cloudflare/HTTPS publik (banyak firmware hanya HTTP dan tidak mengikuti redirect HTTPS; usulan pemilik butir f). Buat jalur HTTP terpisah, privat-saja, ke API: opsi (a) blok Caddy khusus yang mendengarkan HANYA di antarmuka LAN (mis. `192.168.88.160:8082`) dan hanya meneruskan path `/api/v1/integrations/hikvision/*` ke `vms_api`; opsi (b) memetakan port host kontainer API ke antarmuka LAN yang sama dengan pembatasan path di Caddy. Saran: (a). Detail jadi ADR/PR devops, bukan PR ini.
- Jangan mengikat ke `0.0.0.0` dan jangan masukkan jalur ini ke Cloudflare Tunnel atau Tailscale Funnel. Jangan ada redirect HTTP -> HTTPS pada blok ini.
- Jika kantor Pekanbaru berada di LAN berbeda dari server (kemungkinan, Pekanbaru kota lain; PERLU VERIFIKASI), perangkat mengirim lewat VPN/Tailscale: pasang subnet router/Tailscale di kantor Pekanbaru, atau perangkat mengirim ke alamat tailnet server. Itu pekerjaan pemilik/teknisi. Pada kasus itu HTTP di dalam tailnet terenkripsi oleh Tailscale; tetap bukan internet publik.
- Firewall server: izinkan port penerima hanya dari IP/CIDR perangkat/kantor (LANGKAH PEMILIK dengan skrip tempel `ufw allow from <cidr> to any port <port> proto tcp`; sudo = pemilik).

### 6.3 Risiko dan mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Endpoint tanpa tanda tangan; token di path | Siapa pun yang tahu token + berada di allowlist bisa memalsukan absen | Token acak panjang per perangkat, hash di DB, allowlist IP, rate limit, putar token; log menyamarkan path; JANGAN publik |
| Terbuka ke internet | Pemalsuan absen massal, pemindaian | Tidak dipublikasikan; hanya LAN/VPN; bukan Tunnel/Funnel |
| HTTP polos | Sadapan di LAN (token terlihat) | Hanya jaringan privat/tailnet; segmentasi; rotasi token; pertimbangkan VLAN perangkat |
| Perangkat dibobol/sandi bawaan | Pemalsuan di sumber | Ganti sandi, firmware, tanpa port-forward |
| Jam perangkat salah | Urutan masuk/pulang keliru | NTP; peringatan selisih; `CLOCK_SUSPECT` |
| Lonjakan/unggahan besar | Habis memori (4 GB) | Batas 2 MiB, baca bertahap, rate limit, tanpa gambar bila tak perlu |
| Pull menahan kredensial perangkat | Bocor | Berkas server chmod 600 di luar Git, akun viewer |
| Biometrik/PDP | Hukum | 2.7: persetujuan, minimisasi, retensi 30 hari foto, tanpa embedding |
| Titip absen/foto palsu | Data tidak sah | Liveness/anti-foto ada di perangkat (PERLU VERIFIKASI model); VMS mencatat sumber untuk audit |
| Penerima mati | Event hilang | Pull sebagai rekonsiliasi; perangkat menyimpan event lokal (kapasitas PERLU VERIFIKASI) |

Deploy ke prod: hanya setelah "prod ... ya" dari pemilik. Perubahan konfigurasi perangkat Hikvision: hanya oleh pemilik/teknisi. Sebelum itu semua pengujian memakai simulator multipart dan beta/lokal.

## 7. Anggaran RAM / komponen

Tidak ada kontainer atau layanan baru (penerima = rute API; pull = CLI + cron). Tambahan blok Caddy di kontainer web yang sudah ada. Beban: ratusan event/hari/kantor; tubuh multipart dibatasi 2 MiB. Tidak ada tambahan `mem_limit`. Bila volume kelak besar, ADR terpisah (antrean/outbox PostgreSQL), bukan broker.

## 8. Pertanyaan untuk pemilik (dengan saran dan alasan; diam 30 detik = saran berlaku, kecuali yang berlabel TUNGGU)

| # | Pertanyaan | SARAN | ALASAN |
|---|---|---|---|
| 1 | Merek, model, jumlah, dan versi firmware perangkat Pekanbaru (foto label + halaman info) | Kirim foto; satu perangkat dulu | Nama menu, format event, dan dukungan Digest/HTTP-Push bergantung model |
| 2 | Apakah alamat 192.168.88.13:8000 itu perangkat atau PC iVMS-4200? Port web perangkat (80/443) | Teknisi menguji `deviceInfo` di port 80/443 | 8000 umumnya port SDK; jangan dianggap ISAPI |
| 3 | Apakah server prod/beta bisa dijangkau dari LAN perangkat lewat HTTP? Satu LAN atau Pekanbaru jaringan lain (butuh VPN/Tailscale)? | Jalur HTTP privat khusus di LAN/tailnet; tanpa internet | Perangkat HTTP-only; keamanan |
| 4 | Aturan campur: setelah masuk (Hikvision/HP/web), tap kedua Hikvision di hari yang sama = pulang atau diabaikan? Jarak minimum masuk-pulang (30 menit)? Jendela duplikat 2 menit? Pulang terakhir menimpa atau yang pertama dipakai? | Pulang = tap pertama setelah 30 menit; sesudah pulang diabaikan; duplikat 2 menit | Mencegah tap ganda jadi pulang palsu; ini aturan bisnis |
| 5 | Tap perangkat setelah jam 19:00 (tutup pulang mandiri): tetap dicatat pulang? Lembur ikut aturan sekarang? | Tetap dicatat pulang; lembur ikut aturan lama | Event perangkat adalah fakta kehadiran |
| 6 | Siapa teknisi kantor Pekanbaru (akses perangkat) dan siapa admin pemetaan (HR kantor)? Satu tetap + satu cadangan | Teknisi: nama; admin: HR kantor Pekanbaru | Rotasi token, offboarding, pendaftaran wajah |
| 7 | Daftar pegawai Pekanbaru dan nomor yang dipakai di perangkat (employeeNo): sama dengan nomor induk (`employee_no`) di VMS? | Samakan dengan `employee_no`; kirim daftar | Pemetaan otomatis, sedikit pengecualian |
| 8 | Simpan foto tap dari perangkat? | Tidak (log saja); bila ya, 30 hari lalu dihapus | PDP, ruang disimpan, risiko |
| 9 | Persetujuan tertulis karyawan untuk wajah di perangkat sudah ada? Siapa menulis teksnya? | Siapkan formulir sebelum pendaftaran wajah | Kewajiban UU PDP |
| 10 | Masa simpan event mentah (tanpa foto) | 12 bulan lalu arsip/hapus | Audit absensi vs minimisasi data |
| 11 | Kantor lain boleh tap di perangkat Pekanbaru? | Boleh, dicatat, HR kantor asal melihat | Mengurangi penolakan, tetap terlacak |
| 12 | Mode bayangan 1-2 minggu sebelum nyata? | Ya | Bandingkan dengan data HP/web tanpa risiko gaji |
| 13 | Boleh server menarik (pull) dari perangkat memakai akun viewer? | Ya, akun viewer; kredensial di berkas server | Fallback tanpa perantara |

## 9. Urutan PR kecil (satu PR per lapisan; semua ke `development`)

| PR | Lapisan | Isi | Selesai bila |
|---|---|---|---|
| 1 | docs | Dokumen ini (PR ini) + ADR "absensi Hikvision langsung" berstatus Usulan | Pemilik meninjau |
| 2 | db | Migrasi expand: tabel `attendance_device`, `_person`, `_event`, kolom sumber/perangkat di `attendance`, `face_status='DEVICE'`, baris retensi; `GRANT` ke `vms_api`; tes `test_alembic_v2` | Naik/turun di DB uji pribadi; baris lama utuh |
| 3 | api | Perbaiki `insert()` menulis `clock_in_source` (mobile/web); fungsi hitung uang makan/zona dipakai bersama; `HikvisionEventService.ingest` + penerima `POST .../events/{token}`: token hash, allowlist, rate limit, batas ukuran, magic bytes, filter, UNIQUE, pemetaan, aturan sesi 2.8 | Tes simulator multipart (bawah); matriks campur sumber; APK lama lulus; snapshot OpenAPI |
| 4 | api | CLI `hikvision-tarik` + klien ISAPI Digest (timeout, retry), kredensial dari berkas server, alarm perangkat offline | Tes dengan klien palsu (mock HTTP); `--cek` tanpa menulis |
| 5 | web | Halaman admin perangkat (daftar, tambah, putar token, nonaktifkan), pemetaan orang (termasuk daftar "perlu dipetakan" dan "belum dihapus dari perangkat"), izin `device.manage`, bahasa Indonesia awam | Lima kondisi layar; Vitest; uji awam |
| 6 | api+web | Rekap/monitor/ekspor: kolom sumber, peringatan perangkat offline/jam salah | Ekspor tanpa biometrik; regresi rekap |
| 7 | devops | Blok Caddy HTTP privat khusus path Hikvision, `hikvision.env`, cron pull (skrip tempel untuk pemilik), runbook | `bash -n`, `docker compose config` bersih; langkah pemilik tertulis |
| 8 | qa | Audit kebocoran per peran, uji campur sumber, jam salah, tengah malam, offboarding | Laporan QA standar |
| 9 | pemilik | Uji nyata di Pekanbaru (bagian 10) + mode bayangan | Persetujuan tertulis |

Tiap PR lolos `bash scripts/verify.sh`; urutan ketat (2 sebelum 3, 3 sebelum 4, dst.). Rilis MINOR (kontrak aditif). `CHANGELOG.md` tidak di-commit (catatan rilis di deskripsi PR).

### 9.1 Uji tanpa perangkat nyata

- Simulator multipart di tes API (`api/tests/modules/attendance/`): fixture membuat tubuh `multipart/form-data` dengan bagian JSON `AccessControllerEvent` dan bagian JPEG kecil sah, berdasarkan sampel NYATA yang disanitasi bila pemilik menyediakannya (PERLU VERIFIKASI bentuk sampai ada). Kasus: event sah masuk; sub-event 75/1/38; sub-event lain terfilter; duplikat `serialNo`; dua push serentak (`dua_bersamaan`, tepat satu sesi); token salah (401, tanpa detail); IP di luar allowlist; tubuh > 2 MiB (413); JPEG palsu (magic bytes salah, event tetap diolah tanpa gambar); JSON rusak (`PARSE_ERROR`); employeeNo tak terpetakan; karyawan nonaktif; waktu dengan offset berbeda; jam di masa depan; event > 7 hari; masuk perangkat lalu pulang web; masuk web lalu pulang perangkat; masuk HP luar zona (PENDING_OM) lalu tap perangkat; hari cuti.
- Simulator ISAPI pull: server HTTP palsu (`httpx.MockTransport`) yang meniru paginasi `AcsEvent` dan tantangan Digest; uji timeout, kegagalan berturut-turut, tumpang tindih jendela tanpa duplikasi.
- Tes arsitektur: rute penerima terdaftar sebagai pengecualian penjaga; tidak ada `LIKE '%`/OFFSET baru; tidak ada token/foto di log (asersi pada keluaran log).
- Tes DB hanya atas perintah pemilik ke DB uji pribadi; jangan DB dev (`55433`).

## 10. Rencana uji nyata di perangkat Pekanbaru (LANGKAH PEMILIK + teknisi; lewat perangkat dan UI, tanpa suntik API/SQL)

Prasyarat: PR 2-7 selesai di beta; jalur HTTP privat aktif; perangkat dikonfigurasi (bagian 5); fitur per kantor `shadow_mode` aktif.
1. Daftarkan 2 orang uji di perangkat; tap; event muncul di halaman admin perangkat dan monitor web berstatus "diterima" tanpa memengaruhi rekap (mode bayangan).
2. Matikan mode bayangan untuk perangkat uji: masuk perangkat, pulang web (pekerja kantor) -> satu sesi, sumber masuk "Hikvision", sumber pulang "Web"; rekap, uang makan, lembur benar.
3. Pekerja lapangan: masuk HP (lapangan), pulang tap perangkat kantor -> sah sesuai keputusan pertanyaan 4; masuk perangkat, pulang HP.
4. Tap dua kali cepat; tap lagi 5 menit kemudian: tidak jadi dua masuk.
5. Cabut jaringan perangkat 30 menit, tap beberapa kali, sambungkan lagi: event masuk tepat sekali (via push ulang perangkat atau pull).
6. Ubah jam perangkat 10 menit salah: peringatan muncul; ubah 1 hari salah: `CLOCK_SUSPECT`, tidak jadi absen.
7. Nonaktifkan karyawan uji: tap ditolak dan tercatat.
8. Karyawan kantor lain tap di Pekanbaru (bila pertanyaan 11 disetujui).
9. Hari cuti dan hari lembur.
10. Putar token: token lama 401, token baru berfungsi.
Hapus data uji lewat UI setelah selesai.

## 11. Yang TIDAK dilakukan di rencana ini

Tidak mengubah aturan bisnis; tidak menyentuh server/prod/perangkat; tidak menyimpan embedding atau templat wajah dari perangkat; tidak mengirim foto VMS ke perangkat; tidak mengekspos perangkat atau penerima ke internet; tidak menambah layanan/kontainer.

## 12. Daftar PERLU VERIFIKASI (ringkas, untuk fixture dan uji perangkat)

1. Model/firmware; dukungan HTTP Listening/Push dan format (JSON/XML, multipart).
2. Nilai `majorEventType` = 5 dan minor 75/1/38; nama field JSON; apakah ada `serialNo` monoton; apakah arah masuk/keluar tersedia.
3. Format `dateTime` dan offset; zona perangkat; NTP.
4. Perilaku retry dan antrean lokal perangkat saat penerima tidak menjawab; kapasitas penyimpanan event.
5. Dukungan header kustom/otentikasi ke penerima; apakah URL path panjang diterima; panjang maksimum URL.
6. ISAPI `AcsEvent` (nama field, `maxResults`, paginasi), Digest vs Basic, akun viewer.
7. Port ISAPI sebenarnya (80/443) dan peran 192.168.88.13:8000.
8. Ukuran tipikal JPEG; apakah perangkat mengirim gambar dalam bagian multipart yang sama.
9. Keterjangkauan server dari LAN perangkat; firewall; apakah Pekanbaru jaringan lain.
