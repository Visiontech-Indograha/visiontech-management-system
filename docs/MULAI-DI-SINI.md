# MULAI DI SINI

> **Melanjutkan pekerjaan yang sedang berjalan?** Baca `docs/23-SERAH-TERIMA-AGEN.md`: berisi
> keadaan terakhir, aturan kerja dari pemilik, lingkungan (server, APK, Flutter), dan daftar yang terbuka.

**Dokumen pembuka.** Ditulis untuk dibaca lebih dulu oleh siapa pun — manusia atau agen AI —
yang membuka folder ini **tanpa konteks percakapan sebelumnya**.

Setelah membaca satu dokumen ini, Anda tahu: apa yang dibangun, kenapa, apa yang sudah
diputuskan, apa yang sudah ada, dan apa langkah pertama.

---

## 1. Apa ini

**Visiontech Management System (VMS)** — aplikasi manajemen pekerjaan lapangan untuk
PT Visiontech. Menggantikan pencatatan manual untuk: surat keputusan penugasan (SK),
absensi lapangan ber-GPS, laporan harian/mingguan/akhir, aset, insiden K3, lembur, dan
dokumen kepegawaian.

**Bentuknya tiga permukaan:**
1. **Web** (React) — PM, HR, Finance, Aset, OPS. Dipakai di kantor, **tetapi wajib bisa
   dipakai dari ponsel**.
2. **Android** (Flutter) — ketua tim dan anggota di lapangan. Wajib bisa bekerja **tanpa
   sinyal**.
3. **Halaman verifikasi publik** — siapa pun yang memegang dokumen bisa memindai QR untuk
   memastikan tanda tangannya asli.

**Statusnya sekarang:** prototipe sudah selesai dan disetujui, skema basis data sudah
selesai, **aplikasi sungguhan belum mulai dibangun**.

---

## 2. Tiga hal yang membuat sistem ini berbeda

Ini bukan aplikasi absensi biasa. Bila Anda hanya mengingat tiga hal dari dokumen ini,
ingat ketiganya:

### 2.1 Kewenangan mengikuti SK, bukan jabatan
Siapa yang menjadi **ketua** pada satu pekerjaan ditentukan oleh **surat keputusan yang
sedang berlaku**, bukan oleh label pada akun. Ganti ketua lewat adendum personel, maka
kewenangannya berpindah hari itu juga, dan ketua lama kehilangan haknya — tetapi tetap
punya hak anggota bila namanya masih terdaftar di tim.

Inilah alasan utama kode dari percobaan-percobaan sebelumnya tidak bisa dipakai ulang.

### 2.2 Dokumen terbit tidak pernah berubah
SK, revisi, dan adendum masing-masing punya nomor dan **snapshot** sendiri. Versi lama
otomatis terkunci saat versi baru terbit. QR pada dokumen, bila dipindai, menyebutkan nama
penandatangan, jabatan, nomor seri, nomor dokumen, dan waktu — serta **langsung memberi tahu
bila isi dokumen diubah setelah ditandatangani**.

### 2.3 Sistem tidak mempercayai perangkat
Waktu dan jarak absensi **dihitung ulang di server**. Jam HP bisa diubah, lokasi bisa
dipalsukan. Pengenalan wajah hanyalah bukti pendukung — tidak cocok berarti **diperiksa
manusia**, bukan ditolak diam-diam.

---

## 3. Prinsip yang mengikat seluruh pekerjaan

| # | Prinsip | Artinya dalam praktik |
|---|---|---|
| 1 | **Prototipe adalah kebenaran** | Bila aplikasi sungguhan berbeda perilakunya dari prototipe, yang salah adalah aplikasi sungguhan |
| 2 | **Gagal dengan jelas** | Tidak ada yang gagal diam-diam. Data pengguna tidak pernah hilang tanpa pemberitahuan |
| 3 | **Jangan halangi orang bekerja** | Komponen pendukung mati (wajah, penyimpanan) → pekerjaan tetap bisa dilakukan, ditandai untuk diperiksa |
| 4 | **Server yang memutuskan** | Frontend boleh menyembunyikan tombol; server tetap wajib menolak |
| 5 | **Bahasa Indonesia untuk manusia** | Semua pesan galat ditulis untuk orang lapangan, bukan untuk programmer |
| 6 | **Mobile-first** | Rancang layar ponsel dulu, baru tablet, baru desktop — termasuk untuk web kantor |
| 7 | **Pakai komponen pustaka** | Buat komponen sendiri hanya bila benar-benar tidak ada |
| 8 | **DRY untuk pengetahuan** | Satukan yang harus berubah bersama; jangan satukan yang kebetulan mirip |
| 9 | **Jangan menebak** | Bila spesifikasi ambigu, catat keputusannya di dokumen 10 Bagian C |
| 10 | **Cakupan terkunci** | MVP = isi prototipe. Permintaan baru masuk daftar lanjutan, tidak menyela |

---

## 4. Tumpukan teknologi — sudah dikunci

| Bagian | Teknologi |
|---|---|
| **Backend** | Python 3.12 · FastAPI · **SQLModel** · **asyncpg** · **Alembic** (async) |
| **Basis data** | PostgreSQL 18 · PostGIS · pgvector · **RLS aktif** |
| **Penyimpanan** | **MinIO** (S3-compatible); **kompresi hanya untuk foto**, dokumen disimpan apa adanya |
| **Web** | React 19 · TypeScript · Vite · **shadcn/ui** · Tailwind · TanStack Query · **Zustand** |
| **Mobile** | Flutter · **shadcn_ui** · Riverpod · go_router · dio · drift |
| **Wajah** | Layanan Python terpisah · InsightFace/ArcFace 512 dimensi |
| **Auth** | JWT EdDSA pendek + refresh berotasi · argon2id |
| **PDF** | Jinja2 + WeasyPrint di server |
| **Proxy** | Caddy |
| **CI/CD** | **GitHub Actions**; hasil build & peringatan dikirim ke **Discord** |
| **Jaringan** | **Tailscale** untuk SSH, psql, MinIO, staging. Hanya 443 yang publik |

Daftar pustaka lengkap: **dokumen 14**. Jangan menambah pustaka UI atau pengelola state
kedua — aturannya di dokumen 14 §6.

---

## 5. Struktur repositori yang akan dibuat

```
vms/
├── CLAUDE.md               ← salin dari dokumen 15 di folder ini
├── docs/                   ← salin SELURUH isi folder rencana ini
├── db/                     ← salin dari prototipe: 5 berkas SQL
├── prototype/              ← salin prototipe V2, DIBEKUKAN sebagai rujukan
├── api/                    FastAPI (struktur di dokumen 12)
├── web/                    React (struktur di dokumen 11)
├── mobile/                 Flutter
├── face-service/           layanan wajah (fase 8)
├── docker-compose.yml
└── README.md
```

---

## 6. Bahan yang harus disalin sebelum mulai

Semua ada di komputer ini. **Salin, jangan tulis ulang.**

| Bahan | Lokasi sekarang | Salin ke | Kenapa penting |
|---|---|---|---|
| **Skema basis data** | `visiontech-V2/db/` (5 berkas SQL) | `vms/db/` | Fondasi data lengkap: 30+ tabel, RLS, tanda tangan, wajah |
| **Prototipe** | `visiontech-V2/` (`index.html`, `js/`, `css/`, `tests/`) | `vms/prototype/` | **Spesifikasi produk.** 49 transaksi, 162 layar, 19 uji domain |
| **Rencana ini** | folder ini | `vms/docs/` | Seluruh keputusan dan standar |
| **Kode Flutter** | `visiontech-vms/visiontech/mobile/` | `vms/mobile/` | Kamera berwatermark, geofence, sinkronisasi — hemat 2–3 minggu |
| **Layanan wajah** | `visiontech-vms/face_api_service/` | `vms/face-service/` | Kerangka pgvector sudah benar |
| **Caddyfile & konfigurasi web** | `visiontech-vms/visiontech/web/` | `vms/web/` | Header keamanan, `vite.config.ts`, skrip `gen:api` |

**Yang TIDAK disalin:** `visiontech/backend/` (kecuali pola `core/` dan `storage/`),
`vti_api/`, `vti_frontend/`. Alasannya di dokumen 01 — model perannya bertabrakan dengan
prinsip 2.1 di atas.

---

## 7. Keadaan mesin ini

| Hal | Status |
|---|---|
| PostgreSQL 18 | **Terpasang, layanan `postgresql-x64-18` berjalan** |
| PostGIS 3.6 | **Tersedia** |
| pgcrypto, btree_gist, pg_trgm, citext | Tersedia |
| **pgvector** | **BELUM TERPASANG** — dibutuhkan `db/05_face.sql` (fase 8) |
| Docker Desktop | Terpasang, mesin sedang mati |
| Git | Prototipe **belum** di bawah Git |
| **Tailscale** | **Sudah terpasang di server** — dipakai untuk SSH, psql, konsol MinIO, dan staging. Port 22 ditutup dari internet |
| Skema `db/` | **Belum pernah dieksekusi sekali pun** |

---

## 8. Langkah pertama, berurutan

```
1. Buat folder vms/ dan jalankan git init
2. Salin seluruh bahan di §6
3. Salin dokumen 15 menjadi vms/CLAUDE.md
4. Jalankan db/01_schema.sql → 02 → 03 → 04 di PostgreSQL 18
   → perbaiki galat yang muncul
   → ganti isi new_id() menjadi uuidv7() (PG18 sudah punya)
5. Jadikan hasilnya baseline Alembic 0001
6. Mulai fase 0 (dokumen 06)
```

**Langkah 4 adalah pekerjaan pertama yang benar-benar bernilai.** Sampai skema berjalan di
basis data sungguhan, seluruh isi `db/` masih berstatus dugaan. Jangan menulis satu baris
kode aplikasi sebelum langkah ini selesai.

### Daftar periksa sebelum menutup tahap perencanaan

Tandai satu per satu. Selama masih ada yang kosong, jangan mulai fase 0.

**Sudah siap (tidak perlu tindakan):**

- [x] Cakupan produk terkunci — MVP = isi prototipe (dok 03, K-23)
- [x] 23 keputusan arsitektur ditetapkan (dok 02)
- [x] 25 keputusan operasional terkunci (dok 10 Bagian A)
- [x] Tumpukan teknologi dan seluruh pustaka ditetapkan (dok 14)
- [x] Standar frontend dan backend ditulis (dok 11, 12)
- [x] Antrean kerja 11 fase dengan DoD per fase (dok 06)
- [x] Strategi uji + 12 regresi wajib (dok 07)
- [x] Aturan keamanan, UU PDP, biometrik (dok 08)
- [x] CI/CD dan aturan notifikasi (dok 17)
- [x] Skema basis data lengkap, 5 berkas SQL (`db/`)
- [x] PostgreSQL 18 + PostGIS terpasang dan berjalan
- [x] Tailscale terpasang di server

**Perlu dikerjakan untuk masuk fase 0:**

- [ ] Folder `vms/` dibuat dan `git init` dijalankan
- [ ] Bahan disalin sesuai §6
- [ ] Dokumen 15 disalin menjadi `vms/CLAUDE.md`
- [ ] Akun GitHub + repositori dibuat
- [ ] Server Discord + 4 kanal + 4 webhook disiapkan
- [ ] `db/01`–`db/04` berhasil dijalankan di PostgreSQL 18, galat diperbaiki
- [ ] `new_id()` diganti menjadi `uuidv7()`

**Belum diperlukan sekarang — jangan dikejar dulu:**

- [ ] pgvector (baru dibutuhkan fase 8)
- [ ] Domain + KMS (fase 10)
- [ ] Perangkat Android uji + lokasi proyek (fase 4)
- [ ] Logo dan contoh SK (fase 6)

Daftar lengkap kebutuhan beserta tenggatnya ada di **dokumen 10 Bagian B**.

---

## 9. Peta dokumen

| # | Dokumen | Baca kapan |
|---|---|---|
| — | **MULAI-DI-SINI** *(ini)* | Pertama, selalu |
| 00 | Ringkasan Eksekutif | Untuk gambaran menyeluruh |
| 01 | Inventaris Aset | Sebelum menyalin bahan |
| 02 | Keputusan Arsitektur | Sebelum menulis kode apa pun |
| 03 | Cakupan Produk | Saat ragu apakah sesuatu termasuk cakupan |
| 04 | Arsitektur Sistem | Sebelum fase 0 |
| 05 | Kontrak API | Saat membuat endpoint |
| 06 | **Rencana Fase** | **Antrean kerja harian** |
| 07 | Rencana Pengujian | Sebelum menulis uji |
| 08 | Keamanan & Kepatuhan | Sebelum menyentuh auth, berkas, biometrik |
| 09 | Operasional & Rilis | Fase 9–10 |
| 10 | **Keputusan Terkunci & Risiko** | **Sebelum mengubah apa pun yang terasa besar** |
| 11 | **Standar Frontend** | Sebelum menulis komponen |
| 12 | **Standar Backend** | Sebelum menulis endpoint/servis |
| 13 | Pengelolaan Berkas & Kompresi | Saat menangani unggahan |
| 14 | Daftar Pustaka | Sebelum menambah dependensi |
| 15 | Templat `CLAUDE.md` | Saat membuat repo baru |
| 16 | Glosarium | Saat menemukan istilah yang asing |
| 17 | CI/CD & Notifikasi | Saat menyiapkan pipeline atau peringatan |

---

## 10. Cara kerja per iterasi

```
1. Buka dokumen 06, ambil task berikutnya yang belum selesai
2. Baca standar yang relevan (11 untuk frontend, 12 untuk backend)
3. Tulis uji untuk aturan bisnisnya lebih dulu
4. Kerjakan
5. Jalankan lint + tipe + uji
6. Periksa daftar regresi wajib (dokumen 07 §3) masih hijau
7. Bila ada yang ambigu dan diputuskan sendiri → catat di dokumen 10 Bagian C
8. Tandai task selesai hanya bila DoD fase terpenuhi
```

**Satu task per iterasi.** Jangan mengerjakan tiga task sekaligus lalu kehilangan jejak
mana yang benar-benar selesai.

---

## 11. Yang tidak boleh dilakukan

- ❌ Mengubah prototipe di `prototype/`. Itu rujukan, bukan kode hidup.
- ❌ Memakai `alert()`, `confirm()`, `prompt()` bawaan browser. Memblokir halaman dan
  membekukan otomasi uji.
- ❌ Menulis aturan bisnis di router atau di frontend.
- ❌ Mengembalikan objek model SQLModel langsung sebagai respons API.
- ❌ Menyimpan data hasil API di Zustand.
- ❌ Menambah pustaka UI atau pengelola state kedua.
- ❌ Mengompresi PDF atau berkas Office. Hanya foto yang dikompresi.
- ❌ Menyalin data karyawan asli ke staging atau ke komputer developer.
- ❌ Menyimpan rahasia di Git.
- ❌ Menebak saat spesifikasi ambigu — catat keputusannya di dokumen 10 Bagian C.
- ❌ Mengirim data pribadi, koordinat, atau jejak tumpukan ke Discord (dokumen 17 §2).
- ❌ Membuka port 22 ke internet — akses server hanya lewat Tailscale.
- ❌ Menambah fitur di luar cakupan MVP. Daftar lanjutan ada di dokumen 10 Bagian F.

---

## 12. Bila Anda menemukan pertentangan

Urutan kewenangan, dari yang paling tinggi:

```
1. Instruksi langsung pemilik produk (pengguna)
2. Dokumen 02 (Keputusan Arsitektur) dan 10 (Keputusan Terkunci)
3. Perilaku prototipe di prototype/ dan js/domain.js
4. Skema basis data di db/
5. Dokumen standar (11, 12, 13, 14)
6. Dokumen lain di folder ini
```

Bila dokumen 02 dan prototipe bertentangan, dokumen 02 yang berlaku — di situ pertentangannya
sudah disadari dan diputuskan. Bila keduanya diam, ikuti skema basis data.
