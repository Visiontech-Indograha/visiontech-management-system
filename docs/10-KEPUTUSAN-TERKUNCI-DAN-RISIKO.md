# 10 · Keputusan Terkunci, Kebutuhan, dan Risiko

**Dokumen ini adalah pengunci.** Isinya bukan usulan dan bukan pertanyaan — semuanya sudah
diputuskan. Tujuannya agar cakupan tidak melebar dan tidak ada yang dibuka ulang di bulan
keempat.

Mengubah salah satu keputusan di sini hanya boleh atas instruksi langsung pemilik produk,
dan perubahannya ditulis di Bagian D beserta tanggalnya.

---

## Bagian A · Keputusan terkunci

| # | Hal | **Keputusan** |
|---|---|---|
| **K-01** | Kode lama | Backend dan web **dibangun ulang**. Flutter dan layanan wajah **diambil** dari `visiontech/mobile` dan `face_api_service`. `vti_api` dan `vti_frontend` tidak dipakai |
| **K-02** | Skala rancangan | ≤ 200 pengguna terdaftar, ≤ 60 bersamaan, ≤ 400 absensi/hari, ≤ 800 foto/hari |
| **K-03** | Server | Satu VPS di Jakarta, 4 vCPU · 8 GB · 160 GB. Staging terpisah 2 vCPU · 4 GB. Akses admin **hanya lewat Tailscale** |
| **K-04** | Domain | Subdomain perusahaan dengan pola `vms.<domain-perusahaan>`. Nama pastinya diisi saat fase 10 dari domain yang dimiliki perusahaan |
| **K-05** | Kunci tanda tangan | Fase 6: kunci Ed25519 di berkas terenkripsi, izin 600, di luar Git, dicadangkan terpisah. **Sebelum produksi (fase 10): wajib pindah ke KMS cloud**. Skema tidak berubah — hanya sumber kuncinya |
| **K-06** | Tanda tangan tersertifikasi (PSrE) | **Tidak untuk MVP.** Rancangan sudah siap disambungkan; keputusan memakai PSrE masuk fase lanjutan |
| **K-07** | Retensi data | Absensi & audit **5 tahun** · foto absensi **2 tahun** (setelah itu hanya `thumb`) · bukti laporan **5 tahun** · dokumen pribadi **2 tahun setelah karyawan keluar** · SK dan dokumen terbit **permanen** · embedding percobaan wajah **30 hari** |
| **K-08** | Penanggung jawab data pribadi | Peran **HR**. Nama orangnya diisi perusahaan sebelum fase 8 |
| **K-09** | Pengenalan wajah | Dibangun di **fase 8**, setelah sistem dipakai dan dipercaya. Bukan bagian dari MVP yang dirilis lebih dulu |
| **K-10** | Karyawan menolak daftar wajah | **Tidak ada konsekuensi merugikan.** Absensi tetap bisa dilakukan tanpa wajah, statusnya `NOT_ENROLLED`. Bila menolak berarti tidak bisa absen, persetujuannya tidak sah menurut UU PDP |
| **K-11** | Jam kerja | 08.00–17.00 WIB, disimpan di `organization.shift_start/shift_end` sehingga bisa diubah tanpa rilis ulang. Dukungan **shift** masuk fase lanjutan |
| **K-12** | Radius geofence | Bawaan **100 m**, dapat ditimpa per lokasi lewat `site.radius_m`. Akurasi GPS > 100 m **ditolak** |
| **K-13** | Absensi luring | ~~Tidak diizinkan.~~ **Diubah 2026-10-02 (Bagian D, R-34): absen lapangan luring diizinkan dengan pengamanan** — direkam & ditandatangani kunci Android Keystore, jam dari jangkar server + penghitung internal, jarak & status tetap dihitung server saat diterima. Yang boleh luring: laporan, foto, insiden, lembur, absen lapangan |
| **K-14** | Nomor dokumen | Nomor seri tanda tangan berpola `VTI/{tahun}/{urut 6 digit}`. Format nomor SK mengikuti format resmi perusahaan, diisi saat fase 6 dari contoh dokumen yang ada |
| **K-15** | Jenis dokumen pribadi awal | KTP, SIM A, SIM C, BPJS Kesehatan, BPJS Ketenagakerjaan, MCU, Kontrak/PKWT, Sertifikat keahlian. HR dapat menambah lewat halaman jenis dokumen |
| **K-16** | Application ID Android | `id.co.visiontech.vms`, nama tampilan **"Visiontech VMS"** |
| **K-17** | Platform mobile | **Android saja** untuk MVP. iOS masuk fase lanjutan |
| **K-18** | Distribusi aplikasi | APK internal lewat tautan terlindungi + pemeriksaan versi minimum di server. Play Store internal testing bila perangkat > 50 |
| **K-19** | Bahasa | Enum dan nama kolom Inggris; **seluruh teks pengguna Bahasa Indonesia**, termasuk pesan galat |
| **K-20** | Hash kata sandi | **argon2id** |
| **K-21** | MFA | Kolom sudah tersedia. **Diaktifkan untuk PM, HR, dan Finance di fase lanjutan** — bukan MVP |
| **K-22** | Migrasi data lama | **Tidak ada.** Sistem mulai dari basis data kosong |
| **K-23** | Modul di luar cakupan | Cuti, penggajian, stok/pembelian, portofolio, indikator HES, servis kendaraan, surat dinas — **tidak dibangun**. Masuk daftar fase lanjutan bila diminta |
| **K-24** | Notifikasi push | **Fase lanjutan.** MVP memakai penanda di dalam aplikasi |
| **K-25** | Peserta UAT | Satu tim utuh: 1 PM, 1 ketua tim, 2 anggota, 1 Finance, 1 HR. Selama 1 minggu pekerjaan nyata |

---

## Bagian B · Kebutuhan dari perusahaan

Ini bukan pertanyaan — ini **barang dan data** yang harus tersedia pada waktunya, karena
tidak bisa dibuat sendiri oleh developer.

| Dibutuhkan | Untuk apa | Paling lambat |
|---|---|---|
| **2 perangkat Android** (1 kelas bawah, 1 menengah) | Uji absensi, kamera, GPS | Awal fase 4 (minggu 9) |
| **Akses ke 1 lokasi proyek nyata** + koordinatnya | Uji geofence di lapangan | Awal fase 4 |
| **Daftar lokasi proyek** beserta koordinat dan radius | Data master `site` | Akhir fase 4 |
| **Logo, kop surat, identitas perusahaan** | Templat PDF dokumen | Awal fase 6 |
| **Contoh SK dan laporan akhir yang selama ini dipakai** | Menyesuaikan format PDF | Awal fase 6 |
| **Domain perusahaan** + akses DNS | Rilis | Fase 10 |
| **Akun penyedia KMS** | Kunci tanda tangan produksi | Fase 10 |
| **Nama penanggung jawab perlindungan data** | Kewajiban UU PDP | Sebelum fase 8 |
| **Formulir persetujuan biometrik** yang sudah disetujui manajemen | Pendaftaran wajah | Sebelum fase 8 |
| **≥ 30 karyawan untuk kalibrasi wajah** (sukarela, dengan persetujuan) | Mengukur FAR/FRR | Fase 8 |
| **Tim UAT** sesuai K-25 | Uji terima | Fase 10 |

Bila salah satu tidak tersedia pada waktunya, fase yang bersangkutan **tidak bisa
dinyatakan selesai** — bukan ditunda diam-diam, tetapi dicatat sebagai penghalang.

---

## Bagian C · Keputusan implementasi (diisi selama pembangunan)

Tabel ini sengaja kosong sekarang. Setiap kali spesifikasi ternyata ambigu dan diputuskan
sendiri oleh pelaksana, keputusannya ditulis di sini — bukan dikarang diam-diam lalu
ditemukan enam bulan kemudian.

| Tanggal | Task | Ambiguitas | Keputusan yang diambil | Menyimpang dari Bagian A? |
|---|---|---|---|---|
| 2026-09-29 | R-26 · cakupan unit PM pada adendum & simpan tim | Memeriksa ulang **seluruh** tim membuat PM tidak bisa mengajukan adendum/menyimpan tim bila OPS sebelumnya memasang personel lintas unit | Aturan **staf lapangan** berlaku untuk seluruh tim hasil perubahan (pegawai kantor tidak boleh tersisa). Aturan **unit PM** hanya untuk orang yang **baru ditambahkan**; anggota yang sudah ada di tim tidak diperiksa ulang. Ganti ketua lewat `PATCH /work-plans/{id}` kini melewati aturan yang sama | Tidak — menjaga R-23 tanpa memblokir SK buatan OPS |
| 2026-09-28 | R-26 · definisi staf lapangan untuk tim SK | Kolom `position` berupa teks bebas dan tidak konsisten, sedangkan model kewenangan mengenali karyawan biasa dari tidak adanya peran global kantor | Staf lapangan yang dapat menjadi ketua/anggota = karyawan aktif dengan akun aktif dan tanpa peran kantor `PM`, `OPS`, `ADMIN`, `HR`, `FINANCE`, `ASSET`. Peran lama `LEADER`/`MEMBER` tetap dianggap lapangan karena tidak memberi kewenangan global. Jabatan teks tidak dipakai sebagai filter | Tidak — mengikuti model kewenangan berbasis peran yang sudah terkunci dan menghindari filter nama jabatan yang rapuh |
| 2026-09-28 | R-23 · cakupan bawahan PM | Skema tidak memiliki relasi atasan-bawahan; data yang tersedia hanya penempatan unit, sementara pemilik meminta PM hanya memilih "bawahannya" | Untuk MVP, bawahan PM = karyawan aktif pada unit bisnis yang dikelola PM. OPS/OM dan ADMIN boleh lintas unit. Semua kandidat tetap harus bebas konflik SK pada periode yang dipilih; aturan dijaga API dan daftar pilihan web | Tidak — mengikuti struktur organisasi yang tersedia; relasi atasan langsung dapat ditambahkan bila perusahaan membutuhkannya |
| 2026-09-23 | P0-2 | P0-2 meminta `new_id()` → `uuidv7()`, tetapi DB dev memakai PostgreSQL 16 (Docker PostGIS 16, bukan PG18) yang belum punya `uuidv7()`. Versi plpgsql yang terpasang rusak sehingga semua INSERT gagal | UUIDv7 dibuat murni SQL di `new_id()` (migrasi `0002_fix_new_id`, disamakan di `db/01_schema.sql`); diganti `uuidv7()` saat pindah ke PG18 | Tidak — tetap UUIDv7. Catatan: server memakai PG16, bukan PG18 seperti tumpukan terkunci; **perlu konfirmasi** apakah produksi tetap PG16 |
| 2026-09-23 | P0-4 | Fungsi & trigger di `db/*.sql` menyebut tabel tanpa awalan skema (mengandalkan `SET search_path = vms, public` saat skema dipasang); dokumen tidak mengatur `search_path` koneksi aplikasi, sehingga `login_is_locked()` dkk. gagal "relation does not exist" | Setiap koneksi aplikasi (`app/db/session.py::make_engine`, dipakai juga `cli.py` dan uji) menyetel `search_path = vms, public` | Tidak |
| 2026-09-23 | P1-5 | Dokumen tidak menetapkan panjang minimal kata sandi; `create-admin` menerima kata sandi sebagai argumen baris perintah | Kata sandi admin minimal 12 karakter dan dibaca lewat `getpass` (tidak lagi argumen, agar tidak tersimpan di riwayat shell / daftar proses). Kebijakan untuk pengguna biasa belum ditetapkan | Tidak — **perlu konfirmasi** kebijakan kata sandi pengguna biasa |
| 2026-09-23 | P4-9 | Dok 17 §5.3 menyebut "tidak ada absensi sampai 09.00" dan "NEEDS_REVIEW > 2× rata-rata harian" tanpa rincian | Hari kerja = Senin–Jumat (K-11); rata-rata = 14 hari terakhir termasuk hari tanpa data; lonjakan butuh minimal 3 kasus agar rata-rata 0 tidak memicu peringatan tiap ada 1 kasus; hanya pemegang izin baru `run:system_jobs` (ADMIN) yang boleh memicu; pesan hanya angka & waktu. Belum ada anti-banjir (dedup) — menunggu penjadwal | Tidak — **perlu konfirmasi** hari libur nasional & shift |
| 2026-09-24 | P1-1 | Dok 08 §7: kunci privat tidak boleh di disk/DB server & wajib dari KMS; KMS baru tersedia fase 10 (K-05), sementara access token harus EdDSA sekarang | Kunci JWT (tujuan `JWT_ACCESS`, terpisah dari kunci dokumen) dibaca dari variabel lingkungan `JWT_PRIVATE_KEY_HEX` (seed Ed25519) + `JWT_KID`; di dev ada di `api/.env`, di produksi wajib disuntikkan dari secret manager/KMS. Tanpa nilai → kunci sementara (hanya dev/uji, satu proses). Satu `kid` aktif; verifikasi banyak `kid` (rotasi, dok 08 §7) menyusul bersama pencatatan kunci publik di `signing_key` | Tidak — **perlu konfirmasi** cara penyuntikan kunci di server produksi |
| 2026-09-24 | V-07 | Dok 03 §1 menyebut OPS "seluruh unit (baca)", sedangkan prototipe (`domain.js` `permissions.OPS`, `visiblePlans`) memberi OPS kewenangan PM lintas unit (CREATE_PLAN, PUBLISH, APPROVE_CHANGE, CANCEL_PLAN, REVIEW_OVERTIME, PROMOTE, OFFBOARD, …). Urutan kewenangan menempatkan prototipe di atas dok 03 | OPS = pengelola SK di semua unit: izin `create:plan`, `publish:plan`, `review:overtime` ditambahkan; penjaga `plan_access(PM_UNIT)` menerima OPS di unit mana pun. PROMOTE/OFFBOARD **belum** diberikan karena `manage:users` juga mencakup ubah data karyawan (prototipe: HR saja) — menunggu izin dipecah per transaksi | Tidak — **perlu konfirmasi** pemilik produk bahwa OPS memang boleh menerbitkan SK & memberhentikan karyawan |
| 2026-09-25 | V-29 | Skema tidak punya tempat lampiran draf SK (prototipe `plan.attachments`, ikut `snapshot`). Prototipe & API juga tidak punya tindakan menghapus karyawan (`deleted_at`), padahal ada RESTORE_EMPLOYEE | Tabel `work_plan_attachment (work_plan_id, file_id, sort_order)` + `PUT/GET /work-plans/{id}/attachments`; snapshot terbit memuat `attachments`. Hak DELETE ditambahkan hanya untuk tabel ini — tabel bukti lain (`report_evidence`, `final_report_evidence`) juga dihapus-lalu-diisi oleh API tetapi `db/03` tidak memberi DELETE ke `vms_app` (risiko pada instalasi baru yang memakai peran itu). `POST /employees/{id}/archive` (HR) menghapus lunak karyawan yang **sudah di-offboard**; `POST /employees/{id}/restore` membaliknya sebagai nonaktif; `GET /employees` menyembunyikan yang terhapus. Tanpa kolom alasan — jejak siapa & kapan ada di audit. Catatan: rute `/offboard` lama belum memeriksa SK berjalan seperti prototipe OFFBOARD (celah terpisah) | Ya — hapus karyawan dikonfirmasi pemilik 2026-09-25 |
| 2026-09-25 | V-28 | Peta izin prototipe memberi REPORT_OVERTIME hanya ke LEADER, tetapi isi case mengizinkan "ketua atau anggota"; peta izin API memberi FINANCE `review:overtime`, sedangkan prototipe hanya PM & OPS yang boleh meninjau | Ikuti isi case: ketua **dan** anggota boleh mengajukan. Tinjauan hanya pengelola SK (PM unit/OPS) dan bukan pengaju (juga dijaga CHECK di DB); FINANCE tidak meninjau, hanya membaca rekap. `permissions.py` tidak diubah | Tidak |
| 2026-09-25 | V-28 | Prototipe menampilkan rekap lembur ke semua peran (disaring SK yang terlihat); API memakai view agregat `v_overtime_recap` per organisasi | `GET /recaps/overtime`: Finance/OPS/Admin (`review:overtime`) melihat seluruh organisasi; **PM melihat rekap unit yang dipegangnya** (dikonfirmasi pemilik 2026-09-25); peran lain 403. Tim melihat lembur per SK lewat `GET /overtime?work_plan_id=`. Kueri rekap memakai `overtime_log` langsung (bukan `v_overtime_recap`) agar bisa disaring per unit | Ya — dikonfirmasi pemilik 2026-09-25 |
| 2026-09-26 | Revisi PM · lokasi | PM (sprint review) meminta lokasi penugasan ditetapkan lewat titik koordinat — cari kota (mis. Dumai) lalu tetapkan titik pasti — untuk SK yang dibuat **dan yang sedang berjalan**; aturan 2 melarang dokumen terbit berubah | Untuk SK berjalan **hanya titik geofence & radius** yang berubah (tercatat di audit `work_plan`), teks lokasi di dokumen SK tetap, tanpa versi dokumen baru. Peta & pencarian: OpenStreetMap (Leaflet + Nominatim lewat backend, tanpa API key). Setiap penetapan membuat `site` baru agar absensi lama tetap merujuk titik saat itu | Tidak — **dikonfirmasi pemilik 2026-09-26**: tanpa adendum (titik saja), peta Leaflet + OpenStreetMap |
| 2026-09-26 | Revisi pemilik · validasi absensi (R-10) | Pemilik meminta validasi absensi dilakukan juga oleh PM per divisinya; sebelumnya hanya Finance (`review:attendance`) | Izin `review:unit_attendance` untuk PM (unit yang dipegang, dicek di service + RLS `attendance_visibility`), OPS lintas unit; Finance/Admin seluruh organisasi; ekspor tetap Finance | Tidak — permintaan langsung pemilik 2026-09-26; akses swafoto PM menunggu Q-06 (dok 19) |
| 2026-09-26 | M12 | Dok 05 §3.12 hanya menyebut `POST /sync/operations` (batch, `client_op_id`) dan `GET /sync/status?since=`; jenis operasi & bentuk muatannya tidak dirinci | Jenis operasi mengikuti dok 02 A-08 (hanya aksi lapangan): `DAILY_REPORT_SAVE {plan_id, day_id, body, obstacle, evidence_file_ids}`, `DAILY_REPORT_SUBMIT {plan_id, day_id}`, `TASK_TOGGLE {plan_id, day_id, task_id}`, `INCIDENT_REPORT` (= badan `POST /hse/incidents`), `OVERTIME_REPORT {work_plan_id, hours, reason}`. Foto diunggah terpisah lewat `/files/upload` sebelum operasinya dikirim (dok 04 §7). Layanan sinkron memanggil ulang fungsi rute `hse` yang masih menyimpan logika di router (utang lapisan lama) agar aturannya tidak terduplikasi | Tidak |
| 2026-09-26 | Fase 6 | Dok 08 mewajibkan kunci privat di KMS/HSM ("pemegang akses KMS — sebelum fase 6") tetapi KMS belum ditentukan; dok 05 menulis `POST /documents/{id}/sign` manual | **Keputusan pemilik:** (1) kunci Ed25519 sementara dari `DOC_SIGNING_KEY_HEX` lewat antarmuka `DocumentSigner`, adaptor KMS **wajib sebelum produksi** (kosong → kunci sementara per proses, hanya dev/uji); (2) tanda tangan otomatis: penerbit = ISSUER saat terbit, ketua = ACCEPTOR saat menerima — tidak ada tombol "tanda tangani". Hash dokumen tetap dari trigger `plan_document_hash` (`snapshot::text`); payload bertanda tangan dikanonikkan RFC 8785. Token QR mentah tidak disimpan → PDF menerbitkan token baru tiap render. `verify_signature_qr` dipanggil tanpa konteks organisasi: bila RLS ditegakkan penuh (T-12) fungsi verifikasi perlu `SECURITY DEFINER`. Adendum belum ditandatangani otomatis (lanjutan). DoD "ubah satu huruf snapshot → DOCUMENT_CHANGED" belum teruji otomatis karena trigger kekekalan mencegah perubahan snapshot | Ya — dikonfirmasi pemilik 2026-09-26 (kecuali KMS: **wajib sebelum produksi**) |
| 2026-09-26 | OFFBOARD | Rute `/offboard` lama tidak memeriksa SK berjalan & tidak menutup riwayat jabatan (prototipe `domain.js` OFFBOARD melakukannya) | Diikuti prototipe: tolak bila masih PM/ketua/anggota SK yang bukan DRAFT/COMPLETED/CANCELLED; jabatan terbuka ditutup `GREATEST(valid_from, hari ini organisasi)` agar tidak melanggar CHECK; pesan respons memakai teks prototipe | Tidak |
| 2026-09-26 | Sites | Prototipe tidak punya tindakan kelola lokasi (data master); API memakai izin `create:plan` untuk POST/DELETE `/sites` dengan komentar "Or MANAGE_SITES" | Dipertahankan `create:plan` (PM, OPS, Admin — yang menyusun SK dan butuh lokasi); tidak menambah izin baru | Tidak — **perlu konfirmasi** bila lokasi hanya boleh dikelola Admin/OPS |
| 2026-09-25 | V-30 | Dok 05 §3.13 hanya menyebut `GET /timeline?from=&to=` "dikelompokkan per pekerjaan"; prototipe `operations.js` timeline() menampilkan semua SK terlihat kecuali CANCELLED/COMPLETED (draf ikut bagi pengelola) dengan status per hari | Diikuti prototipe: draf tetap tampil bagi pengelola, SK terarsip tidak. `from`/`to` menyaring SK yang periodenya beririsan. Status hari "Laporan belum dikirim" prototipe = `LATE`. Rekap absensi `month` default bulan berjalan organisasi | Tidak |
| 2026-09-25 | V-27 | Dok 05 §3.7 menulis `/assets/{id}/reserve · /release · /return · /verify-return · /check`, sedangkan API memakai `POST /assets/allocate` (body berisi `asset_id`) dan hanya petugas aset yang boleh; prototipe memberi RESERVE/RELEASE_ASSET juga ke PM (unitnya) & OPS | `/assets/allocate` dihapus, diganti `/assets/{id}/reserve`, `/release`, `/check` sesuai dok 05. Pesan/lepas: izin `manage:assets` ATAU pengelola SK (PM unit/OPS) lewat `check_plan_access(PM_UNIT)`. Jalur pengembalian lama (`/assets/allocations/{id}/return`, `/assets/returns/{id}/verify`) belum diganti nama — ditunda agar web tidak rusak | Tidak |
| 2026-09-24 | V-26 | Dok 05 §3.3 hanya mencantumkan `/request-completion` dan `/approve-completion`; prototipe juga punya RETURN_COMPLETE | Ditambahkan `POST /work-plans/{id}/return-completion` `{row_version, reason}` (PM unit/OPS). Catatan APPROVE_COMPLETE memakai field `reason` pada badan transisi yang sama | Tidak |
| 2026-09-24 | V-25 | Prototipe membentuk minggu (`chunkDays` 7 hari) saat SK dibuat dan **membekukan** daftar hari minggu yang sudah ada; setelah adendum perpanjangan, hari tambahan bisa tidak masuk minggu mana pun. Skema `weekly_report` hanya punya `covered_period`, tanpa daftar hari | Minggu selalu dihitung ulang dari hari kerja SK saat ini (urut tanggal, potongan 7, hanya bila ≥ 7 hari); baris `weekly_report` dibuat saat pertama disimpan dan `covered_period` diperbarui selama masih draf. Hari tambahan adendum ikut minggu terakhir/minggu baru — dianggap perbaikan celah prototipe. Skema tidak punya `submitted_at`/`reviewed_at` untuk mingguan; hanya `submitted_by`/`reviewed_by` dicatat | Tidak |
| 2026-09-24 | V-23 | Dok 05 §3.6 menaruh "tugas + teks" pada satu `PUT /work-plans/{id}/days/{day_id}`, sedangkan prototipe memisahkan SAVE_DAY (PM, draf: judul & daftar tugas) dari TOGGLE_TASK / SAVE_REPORT (ketua, SK berjalan) | `PUT …/days/{day_id}` = teks laporan ketua (V-16); `PUT …/days/{day_id}/plan` = SAVE_DAY; `POST …/days/{day_id}/tasks/{task_id}/toggle` = TOGGLE_TASK. Pemisahan mengikuti prototipe & kewenangannya yang berbeda | Tidak |
| 2026-09-24 | V-21 | Prototipe CANCEL_PLAN menandai dokumen & usulan perubahan `CANCELLED`, tetapi enum `document_status`/`change_status` di skema tidak punya nilai itu. Dok 05 hanya menyebut `/cancel · /restore`, tanpa jalur untuk DELETE_PLAN (arsip draf) | Dokumen & usulan terbuka menjadi `WITHDRAWN` (ditarik) — tanpa mengubah enum. Arsip draf memakai `POST /work-plans/{id}/archive` (alasan wajib), dipulihkan dengan `POST /work-plans/{id}/restore`; draf terarsip hanya terlihat pengelola lewat `GET /work-plans?archived=true`. Kolom baru `deleted_by`, `deletion_reason` (migrasi 0008) | Tidak — **perlu konfirmasi** apakah perlu status `CANCELLED` tersendiri untuk dokumen |
| 2026-09-24 | GET /attendance | Dok 05 §3.5 menyebut filter `plan_id`, tetapi tabel `attendance` tidak punya kaitan ke SK (hanya lokasi); prototipe menampilkan seluruh absensi kepada FINANCE/HR/OPS dan milik sendiri kepada yang lain | Filter `employee_id`, `from`, `to`, `status` + halaman. `plan_id` **belum didukung** sampai absensi ditautkan ke SK. FINANCE, HR, OPS, dan ADMIN melihat seluruh organisasi; lainnya hanya milik sendiri — permintaan karyawan lain menghasilkan daftar kosong (tidak dibocorkan) | Tidak — **perlu konfirmasi** apakah absensi perlu ditautkan ke SK |
| 2026-09-24 | V-12 | Dok 05 `POST /attendance/check-out` tidak membawa id sesi, sedangkan prototipe (CHECK_OUT) menutup sesi berdasarkan id tanggal berapa pun; aturan "sesi terbuka mencegah check-in" membuat sesi kemarin yang lupa ditutup mengunci karyawan bila check-out hanya mencari sesi hari ini | Check-out menutup **sesi terbuka terbaru milik sendiri, tanggal berapa pun**; status tidak diubah (pulang cepat hanya dicatat trigger). Karyawan yang lupa check-out kemarin menutupnya dulu, lalu check-in | Tidak |
| 2026-09-24 | Audit web↔API | Audit Gemini: hanya 6 dari ±50 panggilan web cocok dengan API; halaman pengguna, produk/kendaraan/barang, jenis dokumen, kebijakan & koreksi absensi adalah sisa web lama yang memanggil endpoint di luar kontrak dok 05 | **Diputuskan pemilik produk (2026-09-24): ikuti dok 01 §4.3.** Halaman di luar kontrak dihapus bertahap per fitur; halaman yang API-nya ada (login, karyawan, dokumen, absensi, lokasi) diselaraskan ke dok 05; fitur lain dibangun ulang dari prototipe saat endpoint-nya siap. API tidak ditambah endpoint untuk halaman lama | Tidak |
| 2026-09-24 | V-10 | Dokumen menuntut "tanggal dari server" tetapi tidak menetapkan zona waktunya; mesin aplikasi (Docker) berjalan UTC, sehingga `datetime.now()` menaruh absensi 00.00–07.00 WIB di tanggal kemarin | "Hari ini" = tanggal menurut `organization.timezone` dari jam server basis data (`now() AT TIME ZONE o.timezone`, `repositories/org_clock_repo.py`) — sama dengan trigger. Tanggal insiden tidak lagi diterima dari klien. Pembacaan jam langsung di `app/` dilarang di luar `core/time.py` (uji statis) | Tidak |
| 2026-09-24 | V-17 | Dok 08/13 menetapkan "dokumen pribadi hanya pemilik & HR" dan "URL dibuat setelah otorisasi", tetapi tidak merinci swafoto, bukti pekerjaan, dan berkas yang belum dilampirkan | Pengunggah selalu boleh; dokumen pribadi → pemilik + `manage:employee_documents` (HR/ADMIN); swafoto → pemilik + `review:attendance` (FINANCE/ADMIN; HR **tidak**, karena peta izin tidak memberinya tinjauan absensi); bukti laporan/insiden/laporan akhir → siapa pun yang melihat SK-nya (V-07); berkas belum dilampirkan, QR, dan wajah → hanya pengunggah. Selain itu 404. Deduplikasi per organisasi (sha256) tetap: pengunggah kedua berkas yang identik tidak otomatis mendapat akses, tetapi juga tidak memperoleh isi baru | Tidak — **perlu konfirmasi** apakah HR juga boleh melihat swafoto |
| 2026-09-24 | V-07 | Prototipe tidak menampilkan SK draf kepada ketua/anggota (`visiblePlans`), sedangkan kebijakan RLS `work_plan_visibility` (`db/03`) membolehkannya | Mengikuti prototipe (di atas `db/`): ketua, anggota, dan ASSET hanya melihat SK yang sudah terbit; SK tak terlihat → 404. RLS belum aktif untuk peran aplikasi (T-12), jadi aturan ini ditegakkan `plan_access_repo.py` | Tidak |
| 2026-10-01 | Absensi web vs mobile | Pemilik: "pisahkan pekerja lapangan absen di mobile dan pekerja kantor di web" — belum ada penentu jenis pekerja, tingkat ketegasan, maupun bukti hadir untuk absen web | **Disetujui pemilik (opsi rekomendasi, 2026-10-01).** (1) Kolom baru `employee.attendance_mode` (`FIELD`/`OFFICE`, Alembic 0013) diubah HR di Direktori; nilai awal OFFICE untuk akun berperan PM/OPS/HR/FINANCE/ASSET/ADMIN (daftar R-21), lainnya FIELD. (2) Server menolak kanal yang salah (403 `WRONG_ATTENDANCE_CHANNEL`) pada absen masuk & pulang; klien kirim `channel` (`MOBILE` bawaan untuk APK lama, `WEB` dari web) dan aturan diambil dari `attendance_mode` di DB. (3) Absen web memakai lokasi browser terhadap titik `site` + radius yang sama (jarak dihitung trigger), `source = WEB`; batas akurasi web **300 m** (HP tetap 100 m, K-12) karena laptop memakai WiFi; di luar radius → NEEDS_REVIEW **tanpa** swafoto (trigger hanya mewajibkan swafoto untuk MOBILE). **Diperluas R-33 (2026-10-02):** gerbang login per platform, cakupan lihat/tinjau per peran, lokasi per unit, penjelasan wajib — lihat docs/19 R-33 | Tidak |
| 2026-10-02 | Absen luring R-34 | Pemilik meminta absen lapangan saat luring tersinkron otomatis tanpa menetapkan: status setelah sinkron, batas waktu kirim, perlakuan absen pulang luring, dan apa yang terjadi bila HP dinyalakan ulang saat luring | **Disetujui pemilik (2026-10-02):** valid otomatis bila semua cek lolos, selain itu Perlu review; batas kirim 24 jam (lewat → Perlu review), > 7 hari ditolak; absen pulang luring disimpan dan berlaku saat absen masuk valid/disetujui, gugur bila ditolak. Diputuskan sendiri: HP dinyalakan ulang (jumlah boot berubah) → jam dari satelit GPS saja dan Perlu review; jam & GPS selisih > 5 menit → Perlu review; lokasi palsu (`isMocked`) → Perlu review; antrean dikirim berurutan dan berhenti pada gangguan sementara (401/5xx/tanpa sinyal) agar absen pulang tak terkirim sebelum absen masuknya | Ya — mengubah K-13 (Bagian D) |
| 2026-10-02 | PostgreSQL 18 | Pemilik: "pakai PostgreSQL 18 baik prod dan local" (menjawab catatan P0-2 2026-09-23). CI juga gagal karena repo PGDG bullseye (citra postgis 16-3.4) diarsipkan dan apt memperbarui biner PG di bawah server yang hidup | Citra tunggal `db/Dockerfile` (postgis 18-3.6 + pgvector) untuk compose & CI; DB uji lokal dipindah via dump/restore (isi identik). `new_id()` SQL dibiarkan (jalan di 16 & 18); ganti ke `uuidv7()` bawaan = pekerjaan terpisah. Produksi & DB uji server dipindah terpisah setelah konfirmasi pemilik (backup + restore) | Tidak — menutup selisih dengan A-05 |

Kolom terakhir yang paling penting. Baris yang menyimpang dari keputusan terkunci
dikumpulkan dan dilaporkan ke pemilik produk pada demo akhir fase.

---

## Bagian D · Perubahan keputusan terkunci

Diisi hanya bila pemilik produk mengubah salah satu keputusan di Bagian A.

| Tanggal | Keputusan | Dari | Menjadi | Alasan | Dampak pada jadwal |
|---|---|---|---|---|---|
| 2026-10-02 | K-13 Absensi luring | Absensi luring tidak diizinkan | Absen lapangan (HP) boleh luring: dicatat di antrean SQLite internal aplikasi + swafoto di folder internal, ditandatangani kunci EC P-256 Android Keystore (tidak bisa dikeluarkan dari HP); jam = jangkar jam bertanda tangan server + `elapsedRealtime` (jam HP diabaikan), dibandingkan waktu satelit GPS; dikirim otomatis saat online. Server: tanda tangan tidak cocok → ditolak `OFFLINE_TAMPERED`; valid otomatis hanya bila jam terverifikasi, terkirim ≤ 24 jam, lokasi asli, dalam radius — selain itu Perlu review dengan catatan server; > 7 hari ditolak. Absen pulang luring: masuk valid → langsung tercatat; Perlu review → ditahan, berlaku saat disetujui, gugur saat ditolak. Absen kantor (web) tetap wajib daring | Pekerja lapangan sering tanpa sinyal di lokasi proyek; pemilik meminta absen tetap bisa dan tersinkron otomatis, dengan tanggal/jam/lokasi tidak bisa diubah dari data aplikasi | Tidak menggeser fase; selesai 2026-10-02 (R-34) |

---

## Bagian E · Risiko

Diurutkan berdasarkan dampak × kemungkinan. Kolom terakhir adalah penanganan yang **sudah
masuk rencana**, bukan niat.

| # | Risiko | Dampak | Kemungkinan | Sudah ditangani dengan |
|---|---|---|---|---|
| **R-01** | Cakupan melebar di tengah jalan | Tinggi | **Tinggi** | Cakupan dikunci pada prototipe (K-23); dokumen ini sebagai pengunci; permintaan baru masuk daftar lanjutan, tidak menyela |
| **R-02** | Wajah salah menolak orang yang benar | Tinggi | Sedang | Wajah hanya bukti pendukung; kalibrasi FAR/FRR wajib (fase 8 P8-5); bisa dimatikan tanpa mematikan absensi |
| **R-03** | Pengguna lapangan menolak memakai aplikasi | Tinggi | Sedang | Absensi di fase 4 bukan terakhir; UAT dengan pengguna nyata; mobile-first; panduan bergambar |
| **R-04** | Data biometrik atau dokumen pribadi bocor | **Sangat tinggi** | Rendah | Lapisan pertahanan dokumen 08; embedding bukan foto; akses HR + pemilik saja; Tailscale menutup akses admin dari internet |
| **R-05** | Developer tunggal berhenti/berhalangan | Tinggi | Sedang | Seluruh keputusan tertulis di `docs/`; `CLAUDE.md` di akar repo; kode ber-uji; tidak ada pengetahuan yang hanya di kepala satu orang |
| **R-06** | Estimasi 20–24 minggu meleset | Sedang | **Tinggi** | Titik henti aman di minggu 14; fase 6–8 bisa digeser tanpa membuat sistem tidak berguna |
| **R-07** | Hash dokumen dihitung dari PDF, bukan snapshot | Tinggi | Sedang | Dikunci di A-09; uji khusus "cetak ulang tetap VALID" di fase 6 |
| **R-08** | RLS bocor karena koneksi dipakai ulang | **Sangat tinggi** | Rendah | Satu permintaan = satu sesi = satu transaksi; `set_config(..., true)`; `statement_cache_size=0` bila PgBouncer; ada ujinya |
| **R-09** | Antrean luring kehilangan laporan lapangan | Tinggi | Sedang | Operasi ditolak tidak pernah dihapus; layar "perlu perhatian"; regresi R11 dokumen 07 |
| **R-10** | Lazy loading async melempar `MissingGreenlet` di produksi | Sedang | **Tinggi** | Semua relasi dimuat eksplisit `selectinload`; aturan di dokumen 12; ditangkap uji integrasi |
| **R-11** | `shadcn_ui` Flutter kurang lengkap | Sedang | Sedang | Diverifikasi di P0-7 sebelum seluruh UI dibangun di atasnya; komponen yang kurang dibuat sendiri dengan token yang sama (A-18) |
| **R-12** | pgvector sulit dipasang di PG18 Windows | Rendah | Sedang | Hanya memengaruhi lingkungan lokal; alternatif basis data di Docker; produksi Linux tidak bermasalah |
| **R-13** | GPS lapangan tidak seakurat di kantor | Sedang | **Tinggi** | Uji di lokasi nyata sejak fase 4; radius per lokasi; di luar radius ditandai bukan ditolak |
| **R-14** | Cadangan tidak pernah diuji sampai dibutuhkan | **Sangat tinggi** | Sedang | Pemulihan diuji di fase 9 sebagai DoD, lalu setiap 6 bulan |
| **R-15** | Tailscale bermasalah → akses admin hilang | Sedang | Rendah | Akses konsol darurat penyedia VPS diaktifkan dan prosedurnya ditulis di runbook (dokumen 09) |
| **R-16** | Dokumen `visiontech/docs` lama dipakai sebagai spesifikasi | Sedang | Sedang | Ditandai **RUJUK** bukan PAKAI di dokumen 01; perbedaannya ditulis eksplisit |
| **R-17** | Tanda tangan dianggap setara PSrE padahal bukan | Sedang | Sedang | Dinyatakan terbuka di dokumen 08 §7; dikunci sebagai fase lanjutan (K-06) |
| **R-18** | Kompresi memblokir server saat unggahan besar | Sedang | Sedang | Kompresi di `run_in_threadpool`; batas ukuran; kompresi awal sudah dilakukan di perangkat |

---

## Bagian F · Fase lanjutan (setelah MVP)

Dikunci sebagai **daftar tunggu**, bukan janji. Tidak ada yang dikerjakan sebelum MVP rilis.

| Prioritas | Fitur | Pemicu untuk mulai |
|---|---|---|
| 1 | Notifikasi push | Persetujuan sering tertahan karena tidak ada yang tahu |
| 2 | MFA untuk PM, HR, Finance | Setelah sistem memegang data produksi |
| 3 | Dukungan shift (jam kerja selain 08.00–17.00) | Bila ada unit yang bekerja di luar jam itu |
| 4 | Integrasi mesin absensi kantor | Skema sudah siap (`attendance_source = MACHINE`) |
| 5 | Input laporan dengan suara | Bila mengetik di lapangan terbukti menjadi hambatan |
| 6 | Tanda tangan tersertifikasi PSrE | Bila dokumen perlu kekuatan hukum penuh ke pihak luar |
| 7 | iOS | Bila ada staf yang memakai iPhone |
| 8 | Dasbor analitik / gudang data | Setelah ada data historis ≥ 1 tahun |
| 9 | Modul cuti | Bila diminta secara eksplisit |
