# 02 · Keputusan Arsitektur (ADR)

Setiap keputusan ditulis dengan **alternatif yang saya tolak** dan alasannya, supaya Anda
bisa membantahnya. Kode `A-xx` dipakai sebagai rujukan di dokumen lain.

**Seluruh keputusan di dokumen ini terkunci.** Sumber: **P** = ditetapkan pemilik produk ·
**R** = ditetapkan pelaksana atas mandat pemilik produk. Keduanya sama mengikatnya.
Perubahan hanya atas instruksi pemilik produk, dicatat di dokumen 10 Bagian D.

---

## Ringkasan

| ID | Keputusan | Sumber |
|---|---|---|
| A-01 | Bangun ulang backend & web; pakai ulang Flutter & layanan wajah | R |
| A-02 | Backend Python + FastAPI, **SQLModel + asyncpg + Alembic (async)** | **P** |
| A-03 | Aturan bisnis di lapisan servis, meniru `domain.js` satu-ke-satu | R |
| A-04 | RLS tetap aktif sebagai lapis pertahanan kedua, bukan satu-satunya | R |
| A-05 | PostgreSQL 18 + PostGIS + pgvector; `new_id()` → `uuidv7()` | R |
| A-06 | Web: React + TS + Vite + **shadcn/ui** + TanStack Query + **Zustand** | **P** |
| A-07 | Mobile: Flutter (go_router, dio, drift) + **shadcn_ui** | **P** |
| A-08 | Luring memakai antrean idempoten di perangkat + `client_op_id` | P |
| A-09 | Yang ditandatangani adalah **snapshot JSON kanonik**, bukan PDF | R |
| A-10 | Pengenalan wajah sebagai layanan terpisah | R |
| A-11 | JWT EdDSA berumur pendek + refresh berotasi | P |
| A-12 | Berkas di **MinIO**, akses lewat URL bertanda tangan pendek | P |
| A-13 | PDF dibuat di server (WeasyPrint), bukan di browser | R |
| A-14 | Satu monorepo, empat komponen | R |
| A-15 | Bahasa: nilai enum Inggris, seluruh teks pengguna Indonesia | R |
| A-16 | Waktu disimpan UTC, ditampilkan WIB, dihitung dari jam server | R |
| **A-17** | **Mobile-first**: rancang layar ponsel dulu, baru tablet, baru desktop | **P** |
| **A-18** | **Wajib pakai komponen pustaka**; buat sendiri hanya bila tidak ada | **P** |
| **A-19** | **Backend berlapis**: router → controller → service → repository | **P** |
| **A-20** | **Kompresi wajib untuk foto/gambar**; dokumen disimpan apa adanya | **P** |
| **A-21** | Prototipe = **MVP**; pengembangan berlanjut setelahnya | **P** |
| **A-22** | Pemisahan state: TanStack Query (server) vs Zustand (klien) | R |
| **A-23** | Hash kata sandi **argon2id**, bukan bcrypt | R |

---

## A-01 · Bangun ulang backend & web, pakai ulang Flutter & layanan wajah

**Keputusan.** Backend dan web ditulis baru di atas skema `db/`. Kode Flutter dan layanan
pengenalan wajah dari percobaan lama diambil dan disesuaikan.

**Alasan.** Perbedaan antara model peran lama (role statis pada akun) dan model yang Anda
pilih (kewenangan mengikuti SK) menyentuh hampir setiap endpoint dan setiap tabel. Gap
Analysis milik proyek lama sendiri menandai 13 dari 14 baris fondasi sebagai "Beda (besar)"
atau "Belum ada". Sebaliknya, Flutter dan layanan wajah hampir tidak menyentuh model peran —
yang mahal di sana adalah kamera, GPS, penyimpanan luring, dan model wajah.

**Alternatif yang ditolak.**
- *Migrasi bertahap dari backend lama.* Ditolak: selama transisi ada dua model identitas
  hidup berdampingan. Itu sumber bug otorisasi, dan otorisasi adalah hal yang paling tidak
  boleh salah di sistem ini.
- *Bangun ulang semuanya termasuk Flutter.* Ditolak: membuang 2–3 minggu kerja yang sudah
  benar tanpa alasan produk.

**Risiko.** "Bangun ulang" sering berarti mengulang kesalahan lama. Penangkalnya: prototipe
V2 dan skema `db/` sudah memuat pelajaran itu, dan uji prototipe dipakai sebagai pembanding.

---

## A-02 · FastAPI + SQLModel + asyncpg + Alembic (async)

**Keputusan Anda.** Python 3.12, FastAPI, **SQLModel** sebagai ORM, **asyncpg** sebagai
driver, **Alembic** untuk migrasi — seluruhnya gaya `async`.

> Ini menggantikan pilihan sebelumnya (SQLAlchemy sinkron + psycopg 3). Di bawah ditulis
> konsekuensinya supaya tidak menjadi kejutan di tengah jalan — semuanya bisa diatasi,
> tetapi harus disiapkan sejak fase 0.

**Yang bagus dari pilihan ini.** SQLModel menyatukan model basis data dan skema Pydantic
dalam satu kelas, jadi tidak ada lagi dua definisi yang harus dijaga tetap sama. asyncpg
adalah driver PostgreSQL tercepat di Python. Keduanya memang pasangan alami FastAPI.

**Empat konsekuensi yang wajib disiapkan sejak awal:**

1. **Tipe kolom khusus tidak dikenali SQLModel.** `geography(Point,4326)` (PostGIS) dan
   `vector(512)` (pgvector) harus dideklarasikan lewat `sa_column` dengan tipe SQLAlchemy
   aslinya:
   ```python
   location: Any = Field(sa_column=Column(Geography("POINT", srid=4326)))
   embedding: Any = Field(sa_column=Column(Vector(512)))
   ```
   Tanpa ini, migrasi akan membuat kolom yang salah tipe.

2. **PostGIS mengembalikan objek WKB, bukan angka.** Ini sudah pernah menjatuhkan proyek
   sebelumnya — `visiontech/web` mengalami *fatal rendering error* karena objek WKB PostGIS
   dilempar mentah ke React. **Aturan:** kolom geografi tidak pernah keluar apa adanya dari
   API. Selalu diubah menjadi `{lat, lon}` di lapisan skema respons.

3. **asyncpg + PgBouncer butuh penyetelan.** asyncpg memakai *prepared statement* dengan
   nama, yang bertabrakan dengan PgBouncer mode transaction. Bila nanti memakai PgBouncer:
   setel `statement_cache_size=0` dan `prepared_statement_cache_size=0` pada engine. Bila
   tidak, akan muncul galat `prepared statement "__asyncpg_stmt_x__" already exists` yang
   muncul acak di produksi dan sangat membingungkan untuk dilacak.

4. **RLS menuntut satu transaksi per permintaan.** `SET LOCAL app.user_id` hanya berlaku di
   dalam transaksi. Dengan async ini justru lebih mudah salah: satu sesi tidak boleh dipakai
   dua task bersamaan. **Aturan:** satu permintaan = satu sesi = satu transaksi, dibuat lewat
   dependency FastAPI, tidak pernah dibagikan ke `asyncio.gather`.

**Yang harus diwaspadai dari async SQLAlchemy** (ini yang membuat saya semula menyarankan
sinkron): *lazy loading* relasi tidak bekerja di async dan melempar
`MissingGreenlet`. Penangkalnya sederhana asal disiplin sejak awal — muat relasi secara
eksplisit dengan `selectinload()`, jangan pernah mengandalkan akses atribut relasi setelah
sesi ditutup.

**Alembic harus diinisialisasi dalam mode async** (`alembic init -t async`), dan seluruh
fungsi PL/pgSQL serta kebijakan RLS dari `db/` ikut masuk migrasi lewat `op.execute()`.

---

## A-03 · Aturan bisnis di lapisan servis, meniru `domain.js` satu-ke-satu

**Keputusan.** Setiap `case` di `transition()` menjadi satu fungsi servis Python dengan nama
yang sama (`publish_plan`, `accept_plan`, `request_personnel_change`, …). Fungsi
mengembalikan hasil atau galat bernama, tidak melempar galat mentah.

**Alasan.** Kesetaraan nama membuat perbandingan dengan prototipe bisa dilakukan mata
telanjang, dan uji domain prototipe bisa diterjemahkan langsung menjadi uji Python. Bila
suatu saat perilaku berbeda, ketahuan cepat.

**Aturan yang tidak boleh dilanggar:** logika bisnis **tidak** ditulis di router/endpoint dan
**tidak** ditulis di frontend. Frontend boleh menyembunyikan tombol; server tetap wajib
menolak.

---

## A-04 · RLS sebagai lapis kedua, bukan satu-satunya

**Keputusan.** RLS di `db/03_policies.sql` tetap aktif di produksi. Tetapi otorisasi utama
tetap diperiksa di lapisan servis, dengan galat yang bisa dijelaskan ke pengguna.

**Alasan.** RLS hebat untuk mencegah kebocoran, buruk untuk menjelaskan. Baris yang tersaring
RLS menghilang diam-diam — pengguna melihat "data kosong", bukan "Anda tidak berwenang".
Karena itu keduanya dipakai: servis memberi alasan, RLS menjadi jaring pengaman bila ada bug
di servis.

**Konsekuensi.** Uji wajib mencakup kasus "servis lupa memfilter" — pastikan RLS menangkapnya.

---

## A-05 · PostgreSQL 18 + PostGIS + pgvector

**Keputusan.** PostgreSQL 18 (sudah terpasang di mesin Anda), PostGIS untuk geofence,
pgvector untuk wajah. Isi `new_id()` diganti menjadi `uuidv7()`.

**Alasan.** Server sudah ada, dan PG18 menyediakan `uuidv7()` bawaan — kunci utama urut waktu
membuat indeks lebih padat dan sisipan lebih cepat, gratis, tanpa mengubah tabel.

**Yang perlu dilakukan:** memasang **pgvector** (belum ada). Dua jalan: kompilasi/instal biner
pgvector untuk PG18 Windows, atau jalankan basis data di Docker dengan citra yang sudah
menyatukan PostGIS + pgvector. Untuk produksi di VPS Linux, keduanya mudah.

---

## A-06 · Web: React + TypeScript + Vite + shadcn/ui + TanStack Query + Zustand

**Keputusan Anda.** Satu pustaka komponen: **shadcn/ui** (Radix UI + Tailwind). State klien
memakai **Zustand**. State server memakai TanStack Query. Tipe API dibangkitkan otomatis dari
OpenAPI (`gen:api`), tidak ditulis tangan.

**Alasan.** shadcn/ui tidak dipasang sebagai dependensi melainkan **disalin ke dalam repo**,
jadi komponennya bisa disesuaikan tanpa melawan pustaka. Ini cocok untuk sistem yang butuh
label Bahasa Indonesia, sasaran sentuh besar, dan varian khusus lapangan.

**Alternatif yang ditolak.** MUI (sulit disesuaikan tanpa melawan temanya, dan `vti_frontend`
membuktikan campuran MUI + Tailwind + styled-components jadi berantakan), Ant Design (gaya
visualnya sangat khas dan sulit dinetralkan).

**Aturan lengkap ada di dokumen 11** (mobile-first, atomic design, DRY, kapan boleh membuat
komponen sendiri).

**Aksesibilitas bukan tambahan.** Layar dipakai di lapangan, di bawah matahari, oleh orang
yang tidak terbiasa aplikasi. Target: kontras minimal 4,5:1, sasaran sentuh ≥ 44 px, tidak
ada informasi yang hanya disampaikan lewat warna, dan semua dialog bisa ditutup dengan
keyboard. Ini juga sebabnya prototipe melarang `alert()`/`confirm()` bawaan browser —
larangan itu tetap berlaku di aplikasi sungguhan. Radix (dasar shadcn/ui) sudah menangani
fokus dan ARIA, jadi larangan ini justru lebih mudah dipatuhi.

---

## A-07 · Mobile: Flutter + shadcn_ui

**Keputusan Anda.** Flutter dengan pustaka komponen **shadcn_ui** (port shadcn untuk
Flutter), go_router (navigasi), dio (HTTP), **drift** (basis data lokal untuk antrean
luring), `flutter_secure_storage` (token).

**Manfaatnya nyata:** satu bahasa visual di web dan Android. Nama komponen, varian, dan
token warna sama, jadi tidak ada dua sistem desain yang harus dijaga tetap mirip.

**Satu hal yang harus diverifikasi di fase 0** — saya sampaikan supaya tidak menjadi kejutan:
`shadcn_ui` adalah paket komunitas yang jauh lebih muda daripada shadcn/ui versi web.
Sebelum menaruh seluruh antarmuka di atasnya, **P0-7 wajib memeriksa** apakah komponen inti
yang kita butuhkan sudah ada dan stabil: form + validasi, dialog, sheet, select, date picker,
tabel/list, toast. Bila ada yang belum ada, jalannya bukan mengganti pustaka, melainkan
membuat komponen itu sendiri **memakai token desain yang sama** — persis aturan A-18.

**State di Flutter.** Zustand adalah pustaka JavaScript, jadi tidak bisa dipakai di Flutter.
Padanannya yang paling dekat filosofinya (sederhana, tanpa banyak upacara) adalah
**Riverpod**. Struktur state-nya dibuat sepadan dengan Zustand di web — satu store per
domain — supaya cara berpikirnya tetap sama di kedua sisi.

**Android saja untuk MVP.** iOS ditunda sampai ada permintaan nyata — menambahkannya berarti
menambah perangkat uji, akun pengembang, dan proses review.

---

## A-08 · Luring: antrean idempoten di perangkat

**Keputusan.** Setiap aksi lapangan yang dibuat saat luring disimpan di drift dengan
`client_op_id` (UUID dari perangkat), lalu dikirim saat daring. Server menyimpannya di
`offline_operation` dan menolak duplikat berdasarkan `client_op_id`.

**Aturan yang harus tegas:**
- Aksi yang boleh luring: laporan harian, foto bukti, catatan insiden, catatan lembur.
- Aksi yang **tidak boleh** luring: absensi masuk/pulang (butuh waktu server yang tepercaya
  dan geofence yang dihitung server), penerbitan dokumen, persetujuan apa pun.
- Bila sinkronisasi ditolak server (mis. dokumen sudah terkunci), perangkat **menyimpan**
  penolakan itu dan menampilkannya sebagai daftar "perlu perhatian" — tidak dibuang diam-diam.

**Alasan aturan absensi:** jam HP bisa diubah dan lokasi bisa dipalsukan. Prototipe sudah
memilih jalur ini dan saya tidak melihat alasan mengubahnya.

---

## A-09 · Yang ditandatangani adalah snapshot JSON kanonik, bukan PDF

**Keputusan.** SHA-256 yang disimpan di `document_signature.document_sha256` dihitung dari
**bentuk kanonik JSON** snapshot dokumen (JSON Canonicalization Scheme, RFC 8785), bukan dari
berkas PDF. PDF menampilkan hash itu dan QR-nya, tetapi PDF bukan sumber kebenaran.

**Alasan — ini penting dan mudah salah.** PDF tidak deterministik: ganti versi WeasyPrint,
ganti font, ganti tanggal cetak, maka byte-nya berubah dan hash tidak cocok lagi. Akibatnya
`verify_signature_qr()` akan melaporkan `DOCUMENT_CHANGED` pada dokumen yang sebenarnya utuh —
kegagalan paling merusak kepercayaan yang bisa terjadi pada fitur ini.

**Konsekuensi.** Perlu satu fungsi kanonikalisasi yang dipakai bersama oleh penerbitan dan
verifikasi, dengan uji "hash sama setelah PDF dibuat ulang dengan versi berbeda".

---

## A-10 · Pengenalan wajah sebagai layanan terpisah

**Keputusan.** Layanan Python tersendiri (`face-service`), hanya bisa diakses dari backend
(jaringan internal, bukan internet), dengan antarmuka: `POST /embed` (gambar → vektor 512)
dan `POST /liveness`. Pencocokan dan penyimpanan tetap dilakukan basis data lewat
`match_face()` / `verify_face_for_attendance()`.

**Alasan.** Model wajah butuh RAM besar dan pustaka native yang berat; memisahkannya menjaga
backend tetap ringan dan bisa di-*restart* cepat. Selain itu, memisahkan layanan membuat
batas data biometrik jelas: hanya satu komponen yang pernah melihat gambar wajah.

**Aturan keras:** gambar wajah **tidak** disimpan layanan ini. Ia menerima gambar,
mengembalikan vektor, lalu melupakannya.

---

## A-11 · JWT EdDSA + refresh berotasi

Sudah diputuskan dan sudah ada di `db/04_signature_auth.sql`. Ringkas: access token EdDSA
5–15 menit (tidak disimpan), refresh 32 byte acak disimpan sebagai SHA-256, dirotasi setiap
pemakaian, token lama yang dipakai ulang mencabut seluruh rantai perangkat.

**Dikunci:** refresh token untuk **web** disimpan di cookie
`HttpOnly; Secure; SameSite=Strict` dengan path terbatas `/api/v1/auth`; untuk **Android**
dikirim di body dan disimpan di `flutter_secure_storage`. Alasan: cookie HttpOnly menutup
pencurian lewat XSS, sedangkan di aplikasi Android cookie justru merepotkan.

---

## A-12 · Berkas di S3/MinIO

**Keputusan.** Isi berkas tidak pernah masuk basis data. Basis data menyimpan metadata dan
`storage_key`. Unduhan lewat URL bertanda tangan berumur **≤ 5 menit**, dibuat hanya setelah
otorisasi diperiksa.

**Tambahan wajib untuk gambar:** validasi *magic bytes*, batas ukuran, dan **re-encode**
dengan Pillow sebelum disimpan. Re-encode membuang metadata EXIF (termasuk koordinat GPS yang
tidak kita minta) sekaligus menetralkan berkas gambar yang disusupi muatan berbahaya.

---

## A-13 · PDF dibuat di server

**Keputusan.** SK, adendum, laporan akhir, dan berita acara dirender di server dengan
Jinja2 + WeasyPrint dari snapshot dokumen.

**Alasan.** Dokumen bertanda tangan harus sama persis siapa pun yang mencetaknya. Cetakan
browser bergantung pada perangkat, pengaturan margin, dan versi peramban. Prototipe memakai
cetak browser karena memang tidak punya server — itu batasan prototipe, bukan pilihan desain.

---

## A-14 · Satu monorepo, empat komponen

```
vms/
├── api/            FastAPI + SQLAlchemy + Alembic
├── web/            React + Vite
├── mobile/         Flutter
├── face-service/   layanan pengenalan wajah
├── db/             berkas SQL (dipindahkan dari prototipe)
├── docs/           dokumen ini + spesifikasi
└── (prototype/ dihapus 2026-10-20 — riwayat git 84008895)
```

**Alasan.** Perubahan kontrak API hampir selalu menyentuh dua komponen sekaligus. Monorepo
membuatnya bisa dilakukan dalam satu commit dan satu CI, jadi kontraknya tidak pernah
"sementara tidak cocok".

---

## A-15 · Bahasa

Nilai enum dan nama kolom dalam bahasa Inggris (`PUBLISHED`, `AWAITING_ACCEPTANCE`); **semua
teks yang dilihat pengguna dalam bahasa Indonesia**, termasuk pesan galat. Pemetaan enum →
label disimpan di satu berkas, tidak tersebar.

**Pesan galat ditulis untuk manusia.** Bukan "409 Conflict" melainkan "Dokumen sudah diganti
versi yang lebih baru. Muat ulang halaman sebelum menyimpan." Prototipe sudah memakai gaya
ini; pertahankan.

---

## A-16 · Waktu

Simpan `timestamptz` (UTC), tampilkan WIB, dan **hitung dari jam server** untuk hal yang
menentukan hak: batas jam masuk, kedaluwarsa dokumen, kedaluwarsa token. Jam perangkat hanya
dipakai untuk tampilan.

Satu helper `core/time.py` yang bisa "dibekukan" saat pengujian; tidak ada `datetime.now()`
tersebar di kode. Proyek lama menemukan 14 pemanggilan tersebar — itu membuat uji jadi rapuh.

---

## A-17 · Mobile-first, termasuk untuk web kantor

**Keputusan Anda.** Setiap layar web dirancang **untuk ponsel lebih dulu**, lalu tablet, lalu
desktop. Bukan sebaliknya.

**Alasan.** Meski web dipakai di kantor, merancang dari layar sempit memaksa kita memilih apa
yang benar-benar penting. Layar desktop yang dikecilkan hampir selalu jelek; layar ponsel
yang dilebarkan hampir selalu baik. Selain itu PM dan Finance akan sesekali membuka web dari
ponsel — dan saat itu terjadi, halamannya harus tetap bisa dipakai, bukan sekadar "tampil".

**Cara menerapkannya:** CSS ditulis untuk lebar dasar (ponsel) tanpa *media query*; penyesuaian
hanya ditambahkan ke atas lewat `md:` (tablet) dan `lg:` (desktop). Tidak ada `max-width`
query. Rincian titik henti dan pola tata letak ada di dokumen 11.

---

## A-18 · Wajib pakai komponen pustaka; buat sendiri hanya bila tidak ada

**Keputusan Anda.** Urutannya mengikat:

```
1. Ada di shadcn/ui (web) atau shadcn_ui (Flutter)?      → pakai
2. Tidak ada, tapi bisa disusun dari komponen yang ada?  → susun
3. Benar-benar tidak ada?                                → buat sendiri,
                                                            memakai token desain yang sama,
                                                            taruh di pustaka bersama
```

**Alasan.** Ini yang mencegah antarmuka menjadi tambal sulam. Setiap komponen buatan sendiri
adalah komponen yang harus dirawat, diuji aksesibilitasnya, dan dijaga konsisten selamanya.

**Aturan tambahan:** komponen buatan sendiri **tidak boleh** dibuat langsung di dalam halaman.
Ia masuk ke pustaka komponen bersama dengan dokumentasi singkat dan contoh pemakaian —
kalau tidak, komponen yang sama akan ditulis ulang tiga kali oleh orang yang berbeda.

---

## A-19 · Backend berlapis: router → controller → service → repository

**Keputusan Anda.** Struktur backend mengikuti praktik enterprise dengan lapisan yang jelas,
supaya mudah dirawat dan mudah dicari.

| Lapisan | Tugasnya | Yang **tidak** boleh ada di sini |
|---|---|---|
| **Router** | Jalur HTTP, status, dokumentasi OpenAPI | Aturan bisnis, akses basis data |
| **Controller** | Orkestrasi satu kasus pakai, batas transaksi, memanggil beberapa servis | Aturan bisnis rinci, SQL |
| **Service** | Aturan bisnis (padanan `domain.js`), otorisasi | SQL mentah, detail HTTP |
| **Repository** | Akses data, kueri, pemuatan relasi | Keputusan bisnis |

**Kapan lapisan boleh dilewati.** Untuk pembacaan sederhana (mis. daftar master data),
controller boleh langsung memanggil repository tanpa service — memaksakan empat lapisan pada
operasi yang tidak punya aturan bisnis hanya menghasilkan berkas kosong. Yang tidak pernah
boleh dilewati: **router tidak pernah menyentuh repository atau basis data langsung.**

Struktur folder lengkap ada di dokumen 12.

---

## A-20 · Kompresi wajib untuk foto; dokumen disimpan apa adanya

**Keputusan Anda.** **Hanya foto/gambar yang dikompresi.** PDF, Word, PowerPoint, dan Excel
diterima, divalidasi, lalu disimpan utuh tanpa diproses ulang.

**Alasan.** Foto dari kamera HP modern berukuran 3–8 MB. Dengan 800 foto per hari, itu
2–6 GB per hari sebelum dikompresi — biaya penyimpanan dan, yang lebih terasa, waktu unggah
dari lapangan dengan sinyal buruk. Foto dikompresi menjadi tiga ukuran WebP, hemat ± 90%.

**Kenapa dokumen tidak disentuh:** formatnya sudah terkompresi (ZIP), penghematannya kecil,
sementara risikonya nyata — dokumen bisa rusak atau berubah tampilan, dan PDF bertanda tangan
akan rusak tanda tangannya. Untuk berkas yang menjadi bukti kepegawaian dan bukti pekerjaan,
risiko itu tidak sepadan dengan selisih ukurannya.

Skema lengkap ada di **dokumen 13**.

---

## A-21 · Prototipe adalah MVP, bukan produk akhir

**Keputusan Anda.** Seluruh isi prototipe = cakupan **MVP**. Setelah MVP rilis, pengembangan
berlanjut dengan fitur-fitur berikutnya.

**Konsekuensi pada cara membangun** — ini yang penting, dan sebabnya keputusan ini bukan
sekadar catatan:

1. **Basis data sudah disiapkan untuk tumbuh** — multi-tenant, partisi bulanan, enum yang
   bisa diperluas. Tidak perlu diubah saat fitur bertambah.
2. **Setiap modul punya batas yang jelas** supaya modul baru bisa ditambahkan tanpa membongkar
   yang lama.
3. **Kontrak API diberi versi sejak awal** (`/api/v1`), supaya aplikasi Android versi lama di
   lapangan tidak rusak ketika API berkembang.
4. **Pustaka komponen dibangun untuk dipakai ulang**, bukan sekadar untuk layar yang ada
   sekarang — karena akan ada layar-layar berikutnya.

Daftar kandidat fase lanjutan ada di dokumen 03 §3.

---

## A-22 · Pemisahan state: server vs klien

**Keputusan.** Dua jenis state, dua alat, tidak dicampur:

| Jenis | Contoh | Alat |
|---|---|---|
| **State server** | Daftar pekerjaan, detail SK, absensi | **TanStack Query** |
| **State klien** | Filter aktif, langkah wizard, tema, draf form, status luring | **Zustand** |

**Alasan.** Kesalahan paling umum di aplikasi React adalah menyalin data server ke dalam store
global. Begitu disalin, ia langsung basi dan harus disinkronkan manual — dan sinkronisasi
manual itulah sumber bug "data di layar tidak sama dengan data sebenarnya".

**Aturan:** data yang berasal dari API **tidak pernah** disimpan di Zustand. Yang boleh
disimpan hanyalah *identitas* (mis. `selectedPlanId`), lalu datanya diambil dengan
TanStack Query memakai identitas itu.

---

## A-23 · Hash kata sandi: argon2id

**argon2id**, bukan bcrypt. Alasannya: bcrypt membatasi kata sandi pada 72 byte (lebih panjang
dari itu diam-diam dipotong) dan hanya sulit dari sisi komputasi. argon2id juga sulit dari
sisi memori, yang membuat serangan dengan GPU jauh lebih mahal. argon2id adalah rekomendasi
OWASP saat ini.

Pustaka: `argon2-cffi`, dipanggil lewat `passlib` atau langsung. Parameter mengikuti
rekomendasi OWASP yang berlaku saat implementasi (dicatat di kode beserta tanggalnya, supaya
bisa ditinjau ulang).

bcrypt tidak dipakai. Ia masih aman asal kata sandi dipangkas secara sadar dan `rounds` ≥ 12,
tetapi tidak ada alasan memilihnya untuk sistem baru.
