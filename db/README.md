# Skema Basis Data Visiontech VMS

Rancangan PostgreSQL untuk membangun ulang prototipe ini menjadi aplikasi sungguhan.
Disusun dari pemindaian model data prototipe (`js/domain.js`) agar tidak ada aturan bisnis yang hilang.

**Target:** PostgreSQL 18 (keputusan pemilik 2026-10-02; skema tetap jalan di 16+), PostGIS 3.6, pgvector 0.7+, pgcrypto, btree_gist, pg_trgm, citext.

Kunci utama memakai fungsi pembungkus `new_id()` yang saat ini mengembalikan `gen_random_uuid()`.
Pada PostgreSQL 18+ cukup ganti isinya menjadi `uuidv7()` supaya nilainya urut waktu — tanpa
menyentuh satu pun definisi tabel.

| Berkas | Isi |
|---|---|
| `01_schema.sql` | Ekstensi, tipe enum, tabel, indeks, batasan |
| `02_functions.sql` | Fungsi, trigger, tampilan rekap, pembuat partisi |
| `03_policies.sql` | Peran basis data, hak akses, Row Level Security |
| `04_signature_auth.sql` | Tanda tangan digital ber-QR, kunci penandatangan, sesi login (JWT) |
| `05_face.sql` | Pengenalan wajah untuk absensi (pgvector), persetujuan biometrik, retensi |

Urutan pemasangan: `01` → `02` → `03` → `04` → `05`.

> **Status: rancangan, belum dieksekusi.** Di mesin ini `psql` tidak terpasang dan mesin Docker
> sedang mati, jadi kelima berkas belum pernah dijalankan pada server sungguhan. Anggap ini draf
> yang perlu diuji lebih dulu.
>
> Cara menguji begitu Docker Desktop menyala:
>
> ```bash
> docker run --rm -d --name vms-db -e POSTGRES_PASSWORD=dev -p 5432:5432 pgvector/pgvector:pg16
> docker exec -i vms-db psql -U postgres -c "CREATE DATABASE vms"
> docker exec -i vms-db psql -U postgres -d vms -v ON_ERROR_STOP=1 < db/01_schema.sql
> docker exec -i vms-db psql -U postgres -d vms -v ON_ERROR_STOP=1 < db/02_functions.sql
> docker exec -i vms-db psql -U postgres -d vms -v ON_ERROR_STOP=1 < db/03_policies.sql
> docker exec -i vms-db psql -U postgres -d vms -v ON_ERROR_STOP=1 < db/04_signature_auth.sql
> docker exec -i vms-db psql -U postgres -d vms -v ON_ERROR_STOP=1 < db/05_face.sql
> ```
>
> Citra resmi proyek: `db/Dockerfile` (PostgreSQL 18 + PostGIS 3.6 + pgvector), dipakai
> `docker-compose.yml` dan CI. Bangun dengan `docker build -t vms-db:18 db`. Data PG18 ada di
> `/var/lib/postgresql/18/docker` — pasang volume di `/var/lib/postgresql`, bukan `.../data`.

---

## 1. Peta relasi

```
organization ──┬── business_unit ──┬── employee ──┬── employee_assignment
               │                   │              ├── employee_document ──→ file_object
               │                   │              ├── app_user ──┬── user_role
               │                   │              │              ├── user_session   (rantai rotasi refresh)
               │                   │              │              └── login_attempt  (deteksi percobaan login)
               │                   │              ├── biometric_consent
               │                   │              └── face_enrollment  (embedding 512 dimensi)
               │                   │
               ├── site (titik GPS + radius)
               │
               ├── work_plan ──┬── work_plan_member      (susunan tim, berjangka waktu)
               │               ├── work_plan_day ── work_plan_task
               │               │        └── daily_report ── report_evidence ──→ file_object
               │               ├── weekly_report
               │               ├── final_report ── final_report_evidence
               │               ├── plan_document  (SK/revisi/adendum, immutable)
               │               │        └── document_signature ──→ qr_token
               │               ├── plan_change    (usulan perpanjangan / personel)
               │               ├── incident_report ── incident_event / incident_evidence
               │               ├── overtime_log
               │               └── asset_allocation ── asset_return
               │                        └──→ asset
               ├── attendance   (partisi bulanan; titik GPS, swafoto, hasil cocok wajah)
               │        └──→ face_check              (partisi bulanan, embedding percobaan)
               ├── signing_key ── signature_serial_counter
               ├── qr_token ── qr_scan               (partisi bulanan)
               ├── offline_operation                 (antrean luring, idempoten)
               └── audit_event                       (partisi bulanan)
```

### Hubungan yang perlu diperhatikan

- **`work_plan.leader_employee_id` vs `work_plan_member`.** Kolom pada header menyimpan ketua
  yang berlaku sekarang agar kueri harian ringan. Tabel `work_plan_member` menyimpan
  riwayat lengkap dengan `valid_period`, sehingga pergantian ketua lewat adendum personel
  tetap dapat ditelusuri: baris lama ditutup, baris baru dibuka, dan keduanya menunjuk
  `added_by_document_id` ke dokumen yang mengesahkannya.
- **`plan_document` bersifat tetap.** Trigger menolak perubahan pada `snapshot`, `number`,
  `version`, `kind`, dan data penerbitan. Perubahan apa pun harus menjadi versi baru.
  "Terkunci" bukan kolom, melainkan turunan lewat `document_is_locked()`, supaya statusnya
  tidak pernah basi.
- **`document_signature` menunjuk dokumen lewat `signable_type` + `signable_id`.** Tanda tangan
  bisa dipasang pada SK, laporan akhir, atau berita acara pengembalian aset tanpa menambah
  tabel baru.
- **`asset_allocation` memakai exclusion constraint.** Satu aset mustahil dialokasikan ke dua
  pekerjaan pada rentang waktu yang beririsan, ditegakkan indeks GiST, bukan oleh kode aplikasi.
- **`attendance` tidak mempercayai perangkat.** Jarak dihitung ulang di basis data dengan
  `ST_Distance` terhadap titik lokasi proyek. Nilai jarak kiriman aplikasi diabaikan.

---

## 2. Keamanan

1. **Isolasi tenant lewat RLS.** Setiap tabel bisnis menyaring `organization_id` dari
   `current_setting('app.organization_id')`. Bila konteks tidak diset, kebijakan menghasilkan
   nol baris — gagal tertutup, bukan gagal terbuka.
2. **Akses per peran dan per keterlibatan.** Kewenangan pada satu pekerjaan mengikuti penugasan
   di SK (`is_plan_leader`, `is_plan_member`), bukan hanya label peran. Ini menutup celah yang
   sempat terjadi di prototipe: ketua yang diganti kehilangan hak ketua, tetapi tetap punya hak
   anggota selama masih terdaftar.
3. **Data pribadi dibatasi.** `employee_document` hanya terlihat oleh pemilik dan HR. Nomor
   dokumen disimpan tersamar (`number_masked`) plus hash untuk deteksi duplikat; nomor asli
   tidak pernah masuk basis data.
4. **Token QR tidak pernah disimpan mentah.** Hanya SHA-256-nya. Verifikasi memakai
   `verify_qr_scan()` / `verify_signature_qr()`, yang sekaligus memeriksa kedaluwarsa,
   pencabutan, batas pemindaian, dan jarak ke lokasi.
5. **Kunci privat tidak ada di basis data.** `signing_key` hanya menyimpan kunci publik dan
   rujukan ke KMS/HSM. Penandatanganan terjadi di luar Postgres; basis data menyimpan hasilnya.
6. **Data biometrik terpisah dan paling ketat.** Hanya HR dan pemilik data yang boleh membacanya;
   peran pelaporan (`vms_readonly`) dicabut haknya sama sekali.
7. **Aplikasi tidak boleh menghapus.** Hak `DELETE` dicabut; pengarsipan memakai `deleted_at`.
   Tabel `audit_event` bahkan tidak bisa di-`UPDATE` oleh peran aplikasi.
8. **Pemisahan tugas ditegakkan basis data.** Pemeriksa tidak boleh sama dengan pengaju
   (`asset_return`, `employee_document`, `overtime_log`) — dicek lewat `CHECK`, bukan hanya UI.
9. **Berkas tidak disimpan di basis data.** Hanya metadata dan `storage_key` privat; isi berkas
   berada di object storage dengan URL bertanda tangan berumur pendek.

---

## 3. QR sebagai tanda tangan digital (`04_signature_auth.sql`)

QR di sini bukan sekadar penanda dokumen, melainkan **bukti keaslian tanda tangan**. Alurnya:

1. PM/HR menandatangani dokumen. Aplikasi menghitung SHA-256 isi dokumen, meminta KMS
   menandatanganinya (Ed25519), lalu memanggil `register_document_signature()`.
2. Fungsi itu mengambil nomor seri berikutnya lewat `next_signature_serial()`
   (format `VTI/2026/000123`, unik per organisasi karena penghitungnya dikunci per baris),
   menyimpan **snapshot** nama, jabatan, dan unit penandatangan saat itu — bukan rujukan hidup,
   sehingga mutasi jabatan di kemudian hari tidak mengubah dokumen lama — lalu menerbitkan satu
   `qr_token` bertujuan `DOCUMENT_VERIFY`.
3. QR yang tercetak berisi token acak itu. Tokennya sendiri hanya tersimpan sebagai hash. QR hasil
   foto layar tetap sah karena yang diperiksa adalah isinya, bukan gambarnya.

**Yang muncul ketika QR dipindai** (keluaran `verify_signature_qr()`):

| Kolom | Isi |
|---|---|
| `state` | `VALID`, `REVOKED`, `KEY_EXPIRED`, `DOCUMENT_CHANGED`, atau `UNKNOWN` |
| `serial_number` | Nomor seri tanda tangan |
| `signer_name`, `signer_position`, `signer_unit` | Identitas penandatangan pada saat menandatangani |
| `signer_role` | `ISSUER` / `ACCEPTOR` / `WITNESS` / `APPROVER` |
| `document_number`, `document_title` | Dokumen yang ditandatangani |
| `signed_at` | Waktu penandatanganan (dengan zona waktu) |
| `key_id`, `algorithm`, `document_sha256_hex` | Bahan pemeriksaan kriptografis lanjutan |
| `note` | Penjelasan berbahasa manusia bila status bukan `VALID` |

Tiga sifat penting:

- **`DOCUMENT_CHANGED` terdeteksi otomatis.** Hash dokumen dihitung ulang saat pemindaian dan
  dibandingkan dengan hash yang ditandatangani. Dokumen yang diubah setelah ditandatangani
  langsung ketahuan, tanpa perlu menaruh kepercayaan pada aplikasi.
- **Tanda tangan tidak bisa diubah.** Trigger `tg_signature_immutable()` menolak semua UPDATE
  kecuali pencabutan (`revoked_at` + alasan). Mencabut tidak menghapus jejak.
- **Setiap pemindaian tercatat** di `qr_scan` (siapa, kapan, dari mana), jadi ada bukti bahwa
  verifikasi memang dilakukan.

`v_signature_public` menyajikan versi ringkas untuk halaman verifikasi publik: tanpa data pribadi
selain yang memang sudah tercetak di dokumen.

---

## 4. Login: sesi JWT dengan rotasi refresh (`04_signature_auth.sql`)

- **Access token JWT berumur pendek (5–15 menit), algoritma EdDSA (Ed25519).** Tidak disimpan di
  basis data — memang itu gunanya token mandiri. Kunci publiknya ada di `signing_key`
  (`purpose = 'JWT_ACCESS'`) sehingga kunci bisa dirotasi tanpa memaksa semua orang login ulang:
  token lama tetap terverifikasi lewat `kid`-nya sendiri sampai kedaluwarsa.
- **Refresh token acak 32 byte, disimpan hanya sebagai SHA-256** di `user_session`, umur bawaan
  14 hari (dapat diatur lewat parameter `issue_session`).
- **Satu perangkat = satu `family_id`.** Setiap `rotate_session()` menutup baris lama
  (`state = 'ROTATED'`, `rotated_to` menunjuk penerus) dan menerbitkan yang baru.
- **Deteksi pencurian token.** Bila refresh token yang sudah dirotasi dipakai lagi, itu tanda
  token bocor: seluruh rantai (`family_id`) langsung dicabut dan pengguna harus login ulang.
  Fungsi mengembalikan `reused = true` supaya aplikasi bisa mengirim peringatan.
- **Pembatasan percobaan login.** `login_attempt` mencatat login dan IP; `login_is_locked()`
  mengunci setelah sejumlah kegagalan dalam jendela waktu (bawaan 15 menit). Penguncian dihitung
  dari data, bukan disimpan sebagai status yang bisa basi.
- **Pencabutan menyeluruh** lewat `revoke_sessions()` — dipakai saat ganti kata sandi,
  offboarding, atau permintaan pengguna ("keluarkan semua perangkat").
- Kata sandi memakai **argon2id** (dihitung di aplikasi; basis data hanya menyimpan hasilnya),
  dan kolom `mfa_secret_enc` sudah tersedia bila OTP nanti diaktifkan.

Klaim access token yang disarankan: `sub` (user id), `org`, `roles`, `sid` (session id), `jti`,
`iat`, `exp`, `aud`. Nilai `sub` dan `org` itulah yang disetel API ke `app.user_id` dan
`app.organization_id` pada setiap transaksi — dan itu yang dibaca RLS.

---

## 5. PostGIS dan pgvector

**PostGIS** dipakai untuk hal yang memang geografis:
- `site.location` (titik proyek) + `radius_m`.
- `attendance.location` — jarak dihitung dengan `ST_Distance`; di luar radius wajib swafoto.
- `qr_scan.location` — memastikan QR dipindai di lokasi yang benar.
- Indeks GiST pada ketiganya.

**pgvector dipakai untuk pengenalan wajah pada absensi** (`05_face.sql`), bukan untuk QR — isi QR
adalah data pendek dan pasti, jadi yang tepat untuk QR adalah token acak + hash.

- `face_enrollment.embedding` — `vector(512)`, indeks **HNSW** `vector_cosine_ops`
  (`m = 16`, `ef_construction = 64`). Yang disimpan adalah embedding, **bukan foto**.
- `match_face(org, embedding, limit)` — pencarian 1:N, mengembalikan kandidat terbaik beserta
  kemiripan kosinusnya.
- `verify_face_for_attendance(org, karyawan, embedding, …)` — verifikasi 1:1 saat absensi:
  "apakah wajah ini benar orang yang mengaku?" Hasilnya `MATCH`, `NO_MATCH`, `LOW_QUALITY`,
  `NOT_ENROLLED`, atau `SKIPPED`.
- `face_check` (partisi bulanan) mencatat tiap percobaan beserta kemiripan **dan ambang yang
  berlaku saat itu** — jadi hasil lama tetap bisa dijelaskan meski ambangnya kemudian diubah.

Aturan yang sengaja ditegakkan di basis data:

1. **Persetujuan dulu, baru embedding.** `biometric_consent` wajib berstatus `GRANTED`; trigger
   menolak pendaftaran tanpa itu. Menarik persetujuan otomatis menonaktifkan seluruh embedding
   karyawan tersebut.
2. **Embedding tidak bisa diubah.** Perubahan berarti pendaftaran ulang, sehingga riwayat utuh.
3. **Wajah adalah bukti pendukung, bukan hakim.** Absensi yang tidak cocok **tidak ditolak
   diam-diam**: `tg_attendance_face_flag()` menaikkannya ke `NEEDS_REVIEW` agar diperiksa
   manusia — perlakuan yang sama dengan absensi di luar radius.
4. **Ambang batas ada di data**, bukan di kode: `organization.face_match_threshold` (bawaan 0,65).
   **Angka ini wajib dikalibrasi dengan data nyata** (ukur FAR dan FRR) sebelum dipakai di
   lapangan; 0,65 hanya titik awal yang wajar untuk model 512 dimensi.
5. **Masa simpan percobaan terbatas.** `purge_face_probes()` (jadwalkan harian lewat pg_cron)
   mengosongkan `probe_embedding` setelah `face_probe_retention_days` (bawaan 30 hari). Hasil
   pencocokannya tetap tersimpan sebagai bukti audit.
6. **Deteksi keaslian wajah (liveness)** dikerjakan di perangkat atau layanan terpisah;
   `organization.face_liveness_required` menentukan apakah absensi tanpa liveness diterima.
   Tanpa ini, foto dari galeri bisa menembus pencocokan.

Dimensi 512 mengikuti model yang umum (ArcFace/InsightFace). Bila model Anda memakai dimensi lain
(128 untuk FaceNet, 192, atau 768), ubah `vector(512)` di `face_enrollment` dan `face_check` —
sisanya tidak perlu berubah.

---

## 6. Dirancang agar bisa dipakai ulang dan tumbuh

- **Multi-tenant sejak awal.** Menambah perusahaan atau cabang tidak perlu migrasi besar.
- **Partisi bulanan** pada `attendance`, `qr_scan`, `face_check`, dan `audit_event` — tabel yang
  tumbuh paling cepat. `ensure_month_partitions()` dijadwalkan harian (pg_cron) untuk menyiapkan
  bulan depan.
- **Enum mudah diperluas** dengan `ALTER TYPE ... ADD VALUE`, tanpa menulis ulang tabel.
- **Jam kerja, radius, dan ambang wajah ada di data**, bukan di kode:
  `organization.shift_start/shift_end/geofence_radius_m/face_match_threshold` dan `site.radius_m`.
  Aturan berubah tanpa rilis ulang aplikasi.
- **Snapshot JSONB** membuat format dokumen bisa berkembang tanpa merusak dokumen lama.
- **Tanda tangan memakai `signable_type` + `signable_id`**, jadi jenis dokumen baru tidak
  memerlukan tabel tanda tangan baru.
- **`offline_operation` idempoten** lewat `client_op_id`, jadi aman untuk sinkronisasi ulang
  dan bisa dipakai perangkat mana pun.
- **Tampilan siap pakai** (`v_overtime_recap`, `v_document_expiry`, `v_plan_progress`,
  `v_signature_public`) memisahkan bentuk layar dari struktur tabel; layar boleh berubah tanpa
  mengubah skema.

### Yang perlu ditinjau ulang saat volume naik
| Pemicu | Langkah berikutnya |
|---|---|
| Absensi > 5 juta baris/tahun | Pindahkan partisi lama ke penyimpanan dingin; ganti indeks tanggal ke BRIN |
| Laporan berat mengganggu operasional | Tambah replika baca khusus untuk `vms_readonly` |
| Karyawan terdaftar wajah > 100 ribu | Naikkan `ef_search`, tinjau ulang `m`/`ef_construction`, pertimbangkan pemilahan per unit |
| Audit dipakai untuk analitik | Alirkan ke gudang data; simpan 12 bulan terakhir saja di OLTP |
| Banyak tenant besar | Pertimbangkan pemisahan skema atau basis data per tenant besar |
| Verifikasi QR publik ramai | Sajikan `v_signature_public` dari replika baca + cache pendek |

---

## 7. Hal yang masih perlu Anda putuskan

Sudah diputuskan dan sudah terpasang: **tujuan QR** (tanda tangan digital dokumen), **metode
login** (JWT EdDSA + rotasi refresh token), dan **kegunaan pgvector** (pengenalan wajah).

Yang tersisa:

1. **Retensi data** — berapa lama absensi, audit, dan berkas bukti disimpan. Untuk wajah sudah ada
   bawaan 30 hari bagi embedding percobaan; embedding pendaftaran bertahan selama karyawan aktif
   dan persetujuannya berlaku.
2. **Penyedia KMS/HSM** untuk kunci penandatangan dan kunci JWT (AWS KMS, GCP KMS, atau perangkat
   lokal). Skema hanya menyimpan rujukannya, jadi pilihan ini tidak mengubah tabel.
3. **Model dan penyedia pengenalan wajah** — menentukan dimensi embedding dan cara deteksi
   liveness.
4. **Kepatuhan data biometrik (UU PDP)** — siapa penanggung jawabnya, seperti apa bentuk formulir
   persetujuan, dan ke mana karyawan mengadu bila pencocokan salah.
5. **Zona waktu** disimpan per organisasi; bila ada proyek lintas zona, pertimbangkan per lokasi.
