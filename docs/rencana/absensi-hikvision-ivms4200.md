# Rencana: absensi wajah Hikvision (iVMS-4200) di VMS

Status: RENCANA / Usulan. Tidak ada kode yang diubah. Pelaksanaan baru dimulai setelah semua paket kerja yang berjalan selesai dan terkonfirmasi sukses tanpa temuan, galat, cacat, atau utang.
Pemilik keputusan: pemilik VMS. Aturan bisnis di `00-KONTEKS-DOMAIN` tidak diubah dokumen ini.
Tanda "PERLU VERIFIKASI" = fakta tentang Hikvision yang tidak bisa dipastikan dari repo. Jangan dianggap benar sebelum dicek di perangkat asli atau dokumen resmi Hikvision.

## 0. Keadaan sekarang di VMS (terverifikasi di repo)

| Hal | Fakta | Sumber |
|---|---|---|
| Tabel absensi | `attendance`: satu baris per karyawan per hari; `clock_in_at`, `clock_out_at`, `in_lat/in_lng`, `office_id`, `target_location_type` (OFFICE / WORK_PLAN_DAILY), `face_status`, `om_approval_status`, `city_zone_status`, `meal_allowance_amount`. Tidak ada kolom sumber absen dan tidak ada koordinat pulang. | `db/06_master_schema_v2.sql` (tabel attendance) |
| Kantor | `office`: lat/lng, `attendance_radius_m` (default 100), `city_boundary_radius_m` (default 15000, batas dalam/luar kota), `clock_in_time`, `clock_out_time`, tarif uang makan dalam/luar kota. | `db/06_master_schema_v2.sql` (tabel office) |
| Lokasi tugas | Kantor, lokasi rencana kerja harian (`work_plan_daily.attendance_radius_m`), atau lokasi lain; jarak dihitung Haversine. | `attendance_session_repository.py` |
| Cakupan kantor | `attendance_office_scope`: SUPER_ADMIN dan OM lihat semua kantor, peran lain hanya `employee.office_id`; ADR 0002 menambah peran ganda dan penugasan kantor. | `shared/access/office_scope.py`, ADR 0002 |
| Wajah | `face-service` hanya menghitung embedding 512-d (InsightFace `w600k_mbf`); API menyimpan embedding karyawan; HP memakai model sama untuk cocok luring. Status wajah: MATCHED, MISMATCH, NOT_CHECKED, NOT_ENROLLED, SERVICE_DOWN, STALE. | `face-service/README.md`, modul `face` |
| Offline HP | `POST /attendance/offline`, idempoten per `client_op_id`, ditandatangani kunci Keystore perangkat. | `attendance_route.py` |
| ADR yang ada | 0001 peta transisi status order, 0002 peran ganda dan penugasan kantor. Belum ada ADR absensi. | `docs/adr/` |

Kesimpulan: sumber absen sekarang hanya HP/web (GPS + swafoto). Satu baris per hari tanpa catatan "dari mana" dan tanpa riwayat event mentah. Itu harus ditambah (bagian C).

## A. Opsi integrasi teknis

Semua fakta vendor di bagian ini PERLU VERIFIKASI (model perangkat, firmware, versi iVMS-4200, dan ketersediaan HikCentral belum diketahui).

| # | Opsi | Cara kerja singkat | Kelebihan | Risiko / kekurangan | Nilai |
|---|---|---|---|---|---|
| A1 | Perangkat mendorong event langsung ke API VMS (HTTP listening / alarm host lewat ISAPI) | Perangkat diatur mengirim event "wajah dikenali" ke URL tertentu. PERLU VERIFIKASI: model mendukung atau tidak, format muatan (JSON/XML), apakah gambar ikut, apakah pengirim bisa diberi otentikasi. | Tanpa perangkat lunak tambahan; hampir nyata-waktu. | Perangkat di jaringan lokal Pekanbaru harus menjangkau server (internet keluar atau VPN). Otentikasi pengirim sering lemah (PERLU VERIFIKASI). Tidak ada antrean bila server mati. | Sedang |
| A2 | VMS menarik dari iVMS-4200 / HikCentral lewat OpenAPI | Server menanyakan log kehadiran berkala. PERLU VERIFIKASI: iVMS-4200 adalah klien desktop dan belum tentu punya API server; HikCentral Professional punya OpenAPI tetapi berlisensi dan butuh server sendiri. | Resmi, ada pusat data bila HikCentral ada. | Bergantung ada tidaknya HikCentral dan lisensinya. Server VMS harus masuk ke jaringan kantor (risiko keamanan). | Rendah bila tanpa HikCentral |
| A3 | Impor berkas ekspor berkala | Admin mengekspor log kehadiran (CSV/Excel) dari iVMS-4200 lalu mengunggah ke VMS. PERLU VERIFIKASI: kolom dan format ekspor. | Paling sederhana, tanpa jaringan khusus; cocok untuk uji awal dan cadangan. | Tidak nyata-waktu; bergantung orang; salah format = gagal. | Cadangan |
| A4 | Perantara (agen lokal / gateway) di kantor | Satu mini-PC/program kecil di kantor Pekanbaru (jaringan sama dengan perangkat) menerima atau menarik event (ISAPI atau dari iVMS), menyimpan di antrean lokal, lalu mengirim ke API VMS lewat HTTPS keluar (atau Tailscale). | Perangkat tidak terbuka ke internet; tahan putus jaringan; satu tempat untuk kunci dan tanda tangan; satu titik pemantauan. | Satu komponen baru yang harus dirawat (perangkat keras, pembaruan, listrik); butuh admin kantor. | Tinggi |

### Saran

Saran: A4 (perantara di kantor) sebagai jalur utama, A3 (impor berkas) sebagai cadangan dan alat uji awal. A1 hanya bila perangkat terbukti mendukung kirim dengan tanda tangan; perantara pun bisa memakainya.
Alasan: perangkat ada di jaringan lokal Pekanbaru, server di tempat lain; tidak aman membuka perangkat kamera/akses ke internet. Perantara hanya melakukan sambungan KELUAR (tanpa port masuk). Antrean lokal menutup masalah putus jaringan dan event batch. Jalur ke server: HTTPS dengan tanda tangan per perangkat; Tailscale hanya bila server memang di baliknya (pertanyaan 6).
Belum diketahui: cara perantara mendapat event (ISAPI langsung ke perangkat atau baca dari iVMS). PERLU VERIFIKASI lewat uji perangkat asli pada Paket P0.

## B. Pemetaan identitas dan data wajah

| Topik | Rancangan | Saran dan alasan |
|---|---|---|
| Kunci pemetaan | Tabel pemetaan karyawan VMS <-> ID orang di perangkat (PERLU VERIFIKASI nama dan batas panjang "Employee No." / "Person ID"). | Pakai nomor induk karyawan internal (bukan KTP) bila muat; bila tidak, nomor pendek buatan VMS. Alasan: mudah dicek manusia. |
| Sumber kebenaran | VMS: daftar karyawan, status aktif, kantor. Perangkat hanya salinan. | Satu tempat untuk offboarding dan audit. |
| Wajah ganda | Wajah di VMS (embedding) dan di perangkat (templat Hikvision) adalah dua data terpisah, tidak bisa saling dipakai. | Tetap terpisah, tidak dikonversi. Admin kantor mendaftarkan di perangkat sekali. VMS hanya menyimpan status "terdaftar di perangkat: ya/tidak". |
| Kirim foto VMS ke perangkat | PERLU VERIFIKASI apakah didukung. | Ditunda: menyebarkan foto biometrik menambah risiko privasi. |
| Offboarding | Karyawan nonaktif -> tugas hapus orang di perangkat untuk admin kantor (otomatis lewat perantara bila API mendukung, PERLU VERIFIKASI). Event dari ID nonaktif ditolak dan dicatat. | Awalnya manual dengan daftar "belum dihapus dari perangkat" dan pengingat. |
| Privasi (UU PDP) | Wajah = data biometrik. Perlu persetujuan tertulis, tujuan terbatas (absensi), masa simpan, hak hapus. | Catat tanggal persetujuan di VMS. Konsultasi hukum internal PERLU. |
| Enkripsi | Perjalanan: HTTPS/terowongan. Di VMS hanya ID event, waktu, ID perangkat, status; tanpa gambar dan templat. Bila foto wajib disimpan: MinIO privat dengan SSE dan masa hapus. | Jangan simpan foto kecuali pemilik minta (pertanyaan 8). |

## C. Model data

Prinsip: tambah, jangan ubah makna kolom lama (kontrak aditif; APK lama tetap jalan).

| Elemen | Rancangan |
|---|---|
| Sumber absen | Enum `MOBILE`, `WEB`, `HIKVISION`, disimpan terpisah untuk masuk dan pulang (`clock_in_source`, `clock_out_source`) karena bisa campur. Baris lama diisi `MOBILE`. |
| `attendance_device` | `device_id`, `office_id` (kantor tetap), nama, nomor seri (PERLU VERIFIKASI), status, `last_seen_at`, kunci (hash/terenkripsi), `enabled`, zona waktu. |
| `attendance_device_person` | Pemetaan karyawan <-> ID orang di perangkat, tanggal persetujuan wajah, tanggal daftar, tanggal hapus. |
| `attendance_raw_event` (log mentah, tidak diubah) | `event_id` (UUIDv7), `device_id`, `device_event_key` (ID/seri event perangkat bila ada, PERLU VERIFIKASI; jika tidak, hash dari perangkat+orang+waktu), `person_ref`, `device_time`, `received_at`, `payload_hash`, `status` (DITERIMA, DIPROSES, DITOLAK, DUPLIKAT, TAK_DIKENAL, DIKOREKSI), `reason`. Unik pada (`device_id`, `device_event_key`). Dibersihkan setelah N bulan. |
| Idempotensi | Event sama dikirim dua kali = dibalas sukses tanpa efek ganda (pola sama dengan `client_op_id`). |
| Batch setelah offline | Event terlambat memakai `device_time` asli, diproses berurutan menurut waktu perangkat. Lebih tua dari 7 hari (saran) masuk antrean tinjau HR, tidak otomatis. |
| Jam perangkat salah | Catat selisih `received_at - device_time`. Selisih > 2 menit pada event baru = peringatan, tidak dikoreksi otomatis. Perangkat wajib NTP. Simpan UTC (`timestamptz`); hari kerja dan tampilan WIB (Asia/Jakarta). |
| Urutan masuk/pulang | Event sah pertama hari itu = masuk; event berikutnya = pulang (yang terakhir menimpa pulang sebelumnya, bukan baris baru). Event ganda dalam 2 menit = DUPLIKAT. Arah ditentukan VMS dari urutan karena perangkat umumnya hanya melapor "wajah dikenali" (PERLU VERIFIKASI mode check-in/out). |
| Pembatalan/koreksi | Event mentah tidak dihapus. Koreksi HR/OM dengan alasan wajib, tercatat di audit; event asli ditandai DIKOREKSI. |
| Kolom baru `attendance` | `clock_in_source`, `clock_out_source`, `clock_in_device_id`, `clock_out_device_id`, `clock_out_lat/lng`, `clock_out_distance_m` (semua boleh kosong). |

## D. Aturan lokasi

| Kasus | Aturan yang diusulkan | Catatan |
|---|---|---|
| Event Hikvision | Lokasi = lokasi tetap kantor pemilik perangkat; dianggap di dalam radius; `target_location_type` = OFFICE. Tidak memakai GPS HP. | Keamanan lokasi digantikan kepemilikan perangkat; perangkat hilang/dipindah harus bisa dinonaktifkan. |
| Masuk perangkat, pulang HP | Sah bila pulang HP memenuhi aturan lokasi sekarang: dalam radius kantor, atau di lokasi tugas hari itu, atau di luar radius dengan alasan + foto (jalur persetujuan OM). | Lokasi pulang divalidasi sendiri, tidak dibandingkan dengan perangkat. |
| Masuk HP, pulang perangkat | Sah; pulang perangkat = di kantor. Uang makan: pertanyaan 4. | |
| Dua masuk berturut-turut | Dilarang. Masuk kedua pada hari yang sama (sumber apa pun) = DUPLIKAT; baru dihitung pulang setelah jarak minimum kerja (saran 30 menit). | Mencegah tap ganda jadi pulang palsu. |
| Batas waktu antar-sumber | Masuk-pulang minimal 30 menit (konfigurasi per kantor); pulang paling lambat 24 jam setelah masuk. | |
| Karyawan lapangan absen di kantor | Boleh lewat perangkat kantor. Titik survei tetap lewat HP. | Tidak menggugurkan jadwal tugas. |
| Beda kantor | Saran: diterima, dicatat dengan kantor perangkat, ditandai agar HR kantor asal melihat (pertanyaan 5). | Cakupan HR/OM tetap `office_scope`. |
| Lembur | Pulang setelah `clock_out_time` + toleransi = dasar lembur seperti sekarang; sumber tidak memengaruhi. Persetujuan lembur tetap seperti aturan ada. | |
| Shift lewat tengah malam | Hari kerja ditentukan jadwal shift (tanggal mulai), bukan tanggal event. Pulang dalam 24 jam menempel ke baris masuk. | Hanya bila Pekanbaru punya shift malam (pertanyaan 3). |
| Perangkat tak dikenal / nonaktif | Event ditolak, dicatat TAK_DIKENAL, alarm ke admin. | |

## E. Dampak ke fitur lain

| Fitur | Dampak | Tindakan |
|---|---|---|
| Rekap bulanan | Perlu kolom sumber; hitung hadir/terlambat tetap dari `clock_in_at` dan `scheduled_in`. | Tambah kolom sumber di rekap dan ekspor. |
| Uang makan dalam/luar kota | Kantor menentukan zona dan tarif; event perangkat = dalam kota kantor. | Satu fungsi hitung untuk semua sumber; aturan tidak diubah. Keputusan campur: pertanyaan 4. |
| Lembur | Lihat bagian D. | Tes campur sumber. |
| Cuti/izin | Event perangkat pada hari cuti/izin disetujui = ditandai konflik untuk HR, tidak otomatis menolak. | Aturan konflik di layanan. |
| Monitor absensi | Tampilkan sumber dan peringatan "perangkat offline". | Perubahan tampilan web. |
| Notifikasi | Lupa pulang, event ditolak, perangkat offline, karyawan tidak terpetakan. | Pakai saluran yang ada. |
| Ekspor | Kolom sumber dan perangkat; tanpa data biometrik. | Tambah kolom di pembuat ekspor. |
| Audit log | Penerimaan, penolakan, koreksi, daftar/hapus perangkat dicatat; tanpa PII berlebih. | |
| Cakupan HR/OM | Perangkat terikat ke kantor; HR melihat event kantornya sesuai `attendance_office_scope`. Izin baru khusus kelola perangkat (mis. `device.manage`) untuk SUPER_ADMIN/HR kantor. | Ikuti ADR 0002 (union). |
| Peran ganda | Satu karyawan = satu ID di perangkat. | Tanpa perubahan. |
| APK lama | Tidak berubah: respons lama sama, kolom baru opsional; absen HP lama menghasilkan `MOBILE`. | Uji regresi APK lama (wajib), termasuk pulang HP setelah masuk perangkat. |
| Offline-first HP | Event HP offline lewat `client_op_id`; konflik dengan event perangkat diselesaikan menurut waktu kejadian, bukan waktu sinkron. | Uji: HP offline pulang, perangkat masuk, sinkron terlambat. |
| Web | Sumber `WEB` baru; lokasi web mengikuti aturan HP. | Pertanyaan 7. |

## F. Keamanan

| Hal | Rancangan |
|---|---|
| Otentikasi perangkat/perantara | Kunci berbeda per perangkat (atau per perantara dengan daftar perangkat). Saran: tanda tangan HMAC-SHA256 atas isi + waktu + nonce (anti putar ulang, batas 5 menit); mTLS opsional. Kunci bisa diputar dan dicabut dari VMS. Alasan: banyak perangkat tak mendukung mTLS (PERLU VERIFIKASI); HMAC bisa ditangani perantara. |
| Endpoint | Jalur khusus (mis. `/integrations/attendance/events`), terpisah dari JWT pengguna, izin sempit (hanya kirim event). |
| Pembatasan laju | Per perangkat dan per IP (mis. 60 event/menit, ukuran batch dibatasi); lonjakan = 429 dengan petunjuk coba lagi. |
| Validasi muatan | Skema ketat (Pydantic), ukuran maksimum, tipe waktu, format ID; field tak dikenal ditolak. XML (bila ada) diurai tanpa entitas eksternal (XXE). |
| Gambar wajah | Tidak disimpan default; bila perangkat mengirim foto, perantara membuangnya. |
| Log | Tanpa nama, NIK, foto, atau templat; hanya ID internal, ID perangkat, status. |
| Jaringan | Perantara hanya koneksi keluar. Perangkat: ganti sandi bawaan, matikan layanan tak perlu, firmware terbaru (PERLU VERIFIKASI kerentanan model). |
| Anti-penipuan | Ambang kecocokan dan anti-foto (liveness) ada di perangkat, tergantung model (PERLU VERIFIKASI). VMS tidak bisa menghilangkan risiko titip absen bila perangkat lemah. |

## G. Operasional

| Hal | Rancangan |
|---|---|
| Pemantauan perangkat | Heartbeat perantara tiap 1 menit; 5 menit tanpa heartbeat = peringatan, 15 menit = alarm ke admin dan HR kantor. |
| Antrean | Antrean lokal di perantara (berkas/SQLite), kirim ulang berjenjang; ukuran antrean dipantau. |
| Cadangan | Tabel baru masuk cadangan DB yang ada; perantara bisa dibangun ulang dari konfigurasi (kunci disimpan terpisah). |
| Fallback | Perangkat/jaringan mati: absen HP dan web TETAP jalan. Setelah pulih, event tertunda masuk lewat batch. Impor berkas (A3) sebagai pemulihan terakhir. |
| Peluncuran | Feature flag per kantor `absensi_hikvision_aktif` (default mati). Mulai kantor Pekanbaru, mode bayangan 1-2 minggu (event disimpan, tidak memengaruhi rekap, dibandingkan dengan data yang ada), lalu mode nyata. Bisa dimatikan tanpa rilis. |
| Kapasitas | Server 4 GB aman: event kecil (ratusan per hari per kantor), tanpa gambar. |
| Dokumentasi | Panduan admin kantor: daftar/hapus orang, ganti perangkat, uji sambungan. |

## H. Paket kerja

Urutan wajib. Estimasi hari kerja satu engineer, di luar waktu menunggu perangkat. Tiap paket satu PR kecil dan lolos `bash scripts/verify.sh`.

| No | Lapisan | Isi | Estimasi (hari) | Selesai bila / QA |
|---|---|---|---|---|
| P0 | Penelitian + pemilik | Jawab bagian I; uji sambungan ke perangkat asli; dapatkan contoh event nyata dan format ekspor; tulis ADR (Usulan -> Disetujui). | 3-5 | ADR disetujui pemilik; contoh muatan tersimpan sebagai fixture. |
| P1 | db | Migrasi aditif (expand): kolom sumber, `attendance_device`, `attendance_device_person`, `attendance_raw_event`, indeks, cakupan kantor; baris lama `MOBILE`. | 3 | Migrasi naik/turun di `vms_test`; tes arsitektur SQL lulus; baris lama utuh. |
| P2 | api | Penerima event + kunci perangkat, idempotensi, antrean, urutan masuk/pulang, aturan lokasi; fungsi hitung bersama uang makan/lembur. | 8-10 | Matriks campur sumber 3x3, event ganda, batch terlambat, jam salah; snapshot OpenAPI aditif; APK lama lulus. |
| P3 | api | Kelola perangkat (CRUD, putar kunci, nonaktif), pemetaan orang, daftar "belum dihapus dari perangkat", impor berkas A3, feature flag. | 5 | Matriks peran x endpoint; audit log; tes konkurensi. |
| P4 | mobile | Tampilkan sumber; pulang HP setelah masuk perangkat; sinkron offline dengan urutan benar. Tanpa layar baru bila bisa. | 3 | Tes widget + regresi APK lama; uji di HP uji. |
| P5 | web | Halaman perangkat (admin), kolom sumber di monitor/rekap/ekspor, peringatan perangkat offline. Bahasa Indonesia sederhana. | 5 | Lima kondisi layar; uji awam; tes Vitest. |
| P6 | devops | Paket perantara (kontainer/layanan), pemasangan di kantor, kunci, HTTPS/Tailscale, pemantauan dan alarm, runbook. | 5-6 | Pasang bersih dari nol; matikan jaringan -> antrean -> pulih tanpa kehilangan event. |
| P7 | qa | Uji penuh: campur sumber, zona waktu, tengah malam, offboarding, kebocoran data per peran, beban, regresi APK lama. | 4 | Laporan QA standar tanpa temuan terbuka. |
| P8 | pemilik | Uji nyata dengan perangkat asli (daftar di bawah), lalu mode bayangan 1-2 minggu di Pekanbaru, lalu nyala nyata. | 10-14 kalender | Persetujuan tertulis pemilik. |

Total perkiraan kerja engineer: sekitar 36-43 hari (di luar penantian perangkat dan mode bayangan).

Uji nyata oleh pemilik dengan perangkat asli (lewat UI/perangkat, bukan API/SQL):
1. Daftarkan 2 orang uji di perangkat; tap; event muncul di monitor web dengan sumber "Hikvision".
2. Masuk lewat perangkat, pulang lewat HP di dalam radius; pulang HP di luar radius (harus minta alasan/persetujuan); pulang lewat web.
3. Masuk HP, pulang perangkat.
4. Tap dua kali cepat; tap lagi setelah 5 menit (tidak boleh jadi dua masuk).
5. Cabut jaringan perangkat/perantara 30 menit, tap beberapa kali, sambungkan lagi: semua event masuk tepat sekali.
6. Ubah jam perangkat 10 menit salah: peringatan muncul.
7. Nonaktifkan karyawan: tap ditolak.
8. Karyawan lapangan tap di kantor; karyawan kantor lain tap di kantor Pekanbaru.
9. Hari lembur dan hari cuti.

## I. Pertanyaan untuk pemilik (maks 15)

| # | Pertanyaan | SARAN | ALASAN |
|---|---|---|---|
| 1 | Merek/model tepat perangkat di Pekanbaru, dan jumlahnya? | Kirim foto label + halaman info perangkat. | Kemampuan kirim event, arah masuk/keluar, anti-foto bergantung model. |
| 2 | Versi iVMS-4200, dan apakah ada HikCentral (berlisensi)? | Kirim nomor versi; tanya penyedia. | Menentukan A2 mungkin atau tidak. |
| 3 | Jam kerja dan shift Pekanbaru: ada shift malam? Toleransi terlambat? | Satu jadwal pagi dulu; shift malam fase berikutnya. | Menyederhanakan aturan hari kerja. |
| 4 | Uang makan bila masuk di kantor tapi pulang di luar kota (atau sebaliknya): ikut tempat masuk, pulang, atau terjauh? | Ikut aturan sekarang untuk lokasi tugas hari itu; pemilik konfirmasi. | Ini aturan bisnis, bukan keputusan teknis. |
| 5 | Karyawan kantor lain boleh tap di perangkat Pekanbaru? | Boleh, dicatat dan HR asal bisa lihat. | Mengurangi penolakan di lapangan tapi tetap terlacak. |
| 6 | Server dijangkau dari kantor lewat internet (HTTPS) atau hanya Tailscale? | HTTPS + tanda tangan; Tailscale lapis tambahan. | Perantara tidak perlu masuk jaringan internal server. |
| 7 | Boleh absen web dari luar kantor? | Ikuti aturan lokasi HP, jangan lebih longgar. | Lokasi web lebih mudah dipalsu. |
| 8 | Perlu simpan foto saat tap di perangkat sebagai bukti? | Tidak; hanya log. | Privasi UU PDP dan penyimpanan. |
| 9 | Kebijakan wajah ganda dan masa simpan: wajah VMS dan perangkat terpisah; templat perangkat dihapus saat karyawan keluar. | Setuju seperti itu. | Biometrik data sensitif; aturan harus jelas. |
| 10 | Siapa admin perangkat di Pekanbaru? | Satu orang tetap + satu cadangan, dari HR kantor. | Offboarding dan kunci perangkat butuh penanggung jawab. |
| 11 | Persetujuan wajah tertulis dari karyawan sudah ada? | Siapkan formulir sebelum pendaftaran. | Kewajiban UU PDP. |
| 12 | Data absensi Hikvision lama perlu diimpor? | Tidak; mulai dari tanggal peluncuran. | Mengurangi risiko data kotor. |
| 13 | Siapa menyetujui koreksi absen dari perangkat? | HR kantor; OM bila di luar radius. | Selaras aturan sekarang. |
| 14 | Kantor lain akan menyusul? | Ya, rancang per kantor, luncurkan Pekanbaru dulu. | Model data sudah per kantor; biaya tambahan kecil. |
| 15 | Toleransi selisih jam perangkat dan umur maksimum event terlambat? | 2 menit dan 7 hari. | Mencegah manipulasi waktu tanpa menolak event sah. |

## J. Risiko dan hal yang tidak diputuskan

| Risiko / hal terbuka | Dampak | Penanganan |
|---|---|---|
| Kemampuan perangkat tak sesuai dugaan (tak bisa kirim event, tak ada nomor event) | A1 gugur; idempotensi bergantung hash | P0 sebelum desain final; A3/A4 tetap bisa. |
| Perangkat terbuka ke internet / sandi bawaan | Pembobolan | Hanya koneksi keluar dari perantara; ganti sandi; firmware. |
| Titip absen (foto, orang lain) | Data tidak sah | Batas ada di perangkat; VMS mencatat sumber untuk audit; HP tetap punya swafoto + wajah. |
| Dua sistem wajah beda akurasi | Keluhan "di HP gagal, di perangkat lolos" | Wajar; dijelaskan ke pengguna. |
| Jam perangkat salah | Urutan masuk/pulang keliru | NTP, peringatan selisih, koreksi HR. |
| Data biometrik / UU PDP | Hukum | Persetujuan, data minimal, tanpa simpan gambar, masa simpan. |
| Perantara jadi titik gagal | Event terlambat | Antrean lokal, alarm, impor berkas cadangan. |
| Aturan uang makan campur sumber | Salah bayar | Keputusan pemilik (pertanyaan 4) sebelum P2. |
| Lisensi HikCentral / biaya | Biaya tak terduga | Tidak dibutuhkan di jalur yang disarankan. |
| Belum diputuskan | Model perangkat, jalur jaringan, uang makan campur, shift malam, simpan foto, kebijakan lintas kantor | Menunggu pemilik; ADR berstatus Usulan sampai disetujui. |

Langkah berikut: pemilik menjawab pertanyaan 1, 2, 3, dan 6 dulu (menentukan P0), lalu ADR absensi-Hikvision ditulis dan disetujui sebelum P1.
