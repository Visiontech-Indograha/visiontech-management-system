# 04 · Arsitektur Sistem

---

## 1. Peta komponen

```
                        Internet
                            │
                   ┌────────▼────────┐
                   │  Caddy (HTTPS)  │  sertifikat otomatis, header keamanan
                   └───┬─────────┬───┘
            /          │         │            /api/*
   berkas statis ◄─────┘         └─────► ┌──────────────┐
   (web React)                           │   API        │  FastAPI
                                         │  (uvicorn)   │  aturan bisnis + otorisasi
   Android (Flutter) ────── /api/* ─────►│              │
                                         └──┬────┬───┬──┘
   Pemindai QR (peramban apa pun)            │    │   │
        └──── /verifikasi/{token} ───────────┘    │   │
                                                  │   │
                   ┌──────────────────────────────┘   └──────────────┐
                   ▼                                                 ▼
        ┌────────────────────┐                            ┌────────────────────┐
        │  PostgreSQL 18     │                            │  face-service      │
        │  PostGIS + pgvector│◄───── hanya dari API ──────│  (Python, internal)│
        │  RLS aktif         │                            │  gambar → vektor   │
        └────────┬───────────┘                            └────────────────────┘
                 │
                 ▼
        ┌────────────────────┐        ┌──────────────────┐
        │  S3 / MinIO        │        │  KMS (kunci)     │
        │  foto & lampiran   │        │  tanda tangan    │
        └────────────────────┘        └──────────────────┘
```

**Aturan jaringan:** hanya Caddy yang terbuka ke internet (443). API, basis data,
face-service, dan MinIO berada di jaringan internal. face-service **tidak pernah** diakses
langsung oleh aplikasi mobile.

### Tailscale — akses administratif

Server sudah terpasang **Tailscale**, dan itu dipakai sebagai satu-satunya jalur masuk
administratif. Pembagiannya:

| Terbuka ke internet (publik) | Hanya lewat tailnet (Tailscale) |
|---|---|
| `443` — web, API, halaman verifikasi QR | SSH (`22`) |
| `80` — pengalihan ke 443 saja | Konsol MinIO |
| | PostgreSQL (`5432`) |
| | Pemantauan (Uptime Kuma) |
| | Seluruh lingkungan **staging** |
| | face-service |

```
        Internet                        Tailnet (Tailscale)
           │                                    │
        443 saja                       SSH · MinIO console · psql
           │                           staging · pemantauan
           ▼                                    ▼
      ┌─────────────────────────────────────────────┐
      │  VPS produksi                               │
      │  ufw: deny semua kecuali 80/443 + tailscale0│
      └─────────────────────────────────────────────┘
```

**Keputusan yang mengikat:**

1. **Port 22 ditutup dari internet.** SSH hanya lewat alamat Tailscale. Ini menghapus
   seluruh kelas serangan tebak-kata-sandi SSH sekaligus — yang merupakan sumber serangan
   paling ramai pada VPS mana pun.
2. **PostgreSQL dan MinIO tidak pernah mendengarkan di antarmuka publik.** Keduanya
   mengikat ke `127.0.0.1` untuk akses antar-container, dan ke `tailscale0` bila perlu
   diakses dari laptop pengelola.
3. **Staging tidak punya alamat publik.** Cukup dibuka lewat `tailscale serve` di dalam
   tailnet. Konsekuensinya bagus: staging tidak bisa diindeks mesin pencari dan tidak bisa
   dibuka orang luar, sehingga aman berisi data contoh yang menyerupai kenyataan.
4. **Tailscale ACL membatasi per perangkat**, tidak semua anggota tailnet boleh menyentuh
   basis data produksi. Perangkat diberi tag (`tag:server`, `tag:admin`, `tag:ci`) dan
   aturannya ditulis di berkas ACL, bukan diingat-ingat.
5. **Kunci autentikasi CI** memakai auth key yang bisa kedaluwarsa (*ephemeral*), sehingga
   runner yang selesai tidak meninggalkan perangkat menggantung di tailnet.
6. **Tailscale bukan pengganti autentikasi aplikasi.** Berada di dalam tailnet tidak membuat
   seseorang otomatis berwenang; login, peran, dan RLS tetap berlaku sepenuhnya.

**Yang tidak dipakai:** Tailscale Funnel untuk produksi. Web produksi harus bisa diakses
pengguna umum lewat domain perusahaan dan sertifikat biasa; menyalurkannya lewat Funnel
menambah ketergantungan yang tidak perlu pada satu layanan pihak ketiga.

---

## 2. Alur permintaan dan otorisasi

Setiap permintaan yang menyentuh data menempuh urutan tetap:

1. **Caddy** meneruskan ke API (header keamanan, batas ukuran unggahan).
2. **Middleware autentikasi** memverifikasi JWT (EdDSA) dengan kunci publik dari
   `signing_key`, mengambil `sub`, `org`, `roles`, `sid`.
3. **Middleware sesi basis data** membuka transaksi dan menjalankan
   `SET LOCAL app.user_id`, `app.organization_id`, `app.actor_label`.
   → inilah yang menghidupkan RLS dan audit otomatis.
4. **Router** hanya mem-parsing masukan dan memanggil servis. Tidak ada aturan bisnis di sini.
5. **Servis** memeriksa kewenangan (termasuk `is_plan_leader` / `is_plan_member`), menjalankan
   aturan, menulis, dan mengembalikan hasil atau galat bernama.
6. **Basis data** menjadi jaring pengaman terakhir: RLS, `CHECK`, exclusion constraint,
   trigger immutability.
7. Transaksi ditutup. `SET LOCAL` hilang bersama transaksi — tidak bocor ke permintaan lain.

**Kegagalan pada langkah 3 harus fatal.** Bila konteks tidak tersetel, RLS menghasilkan nol
baris dan aplikasi akan tampak "kosong" alih-alih memberi galat. Karena itu middleware wajib
menolak permintaan bila konteks gagal disetel, bukan melanjutkan diam-diam.

---

## 3. Penguncian optimistis (mencegah dua orang saling menimpa)

Prototipe sudah memakai `rowVersion`; skema `db/` meneruskannya lewat trigger
`tg_bump_row_version()` pada `work_plan`.

Alurnya: klien membaca `row_version` → mengirimnya kembali saat menyimpan → bila sudah berubah,
server menolak dengan pesan **"Data berubah di sesi lain. Muat ulang sebelum menyimpan."**
(kode SQL `40001`, dipetakan menjadi HTTP 409).

Tanpa ini, dua PM yang membuka SK yang sama akan saling menghapus perubahan tanpa sadar.

---

## 4. Alur absensi (paling banyak jebakannya)

```
Android                         API                          PostgreSQL
  │ ambil lokasi + akurasi       │                                │
  │ (tolak bila akurasi > 100 m) │                                │
  │ ambil swafoto (watermark)    │                                │
  │──── POST /attendance ───────►│                                │
  │     {plan, lat, lon, akurasi,│ 1. waktu = jam SERVER          │
  │      foto, client_op_id}     │ 2. unggah foto → S3            │
  │                              │ 3. INSERT attendance ─────────►│
  │                              │                    trigger geofence:
  │                              │                    jarak = ST_Distance(...)
  │                              │                    radius = site ?? organisasi
  │                              │                    di luar radius → NEEDS_REVIEW
  │                              │◄────── hasil + jarak + status ─┤
  │◄─── 201 + status + pesan ────│                                │
```

**Yang sengaja tidak dipercaya dari perangkat:** waktu, jarak, dan status. Ketiganya dihitung
ulang di server. Yang diambil dari perangkat hanya koordinat mentah, akurasi, dan foto.

**Terlambat / pulang cepat** ditentukan dengan membandingkan jam server terhadap
`organization.shift_start` / `shift_end`, lalu disimpan sebagai penanda — bukan sebagai
penolakan. Penilaian tetap di tangan Finance.

**Kenapa absensi tidak boleh luring:** kedua hal yang menentukan keabsahannya (waktu server
dan perhitungan jarak) tidak ada di perangkat. Absensi luring berarti mempercayai jam HP.

---

## 5. Alur tanda tangan QR

**Saat menandatangani:**

```
1. Snapshot dokumen dibekukan (JSONB)
2. hash = SHA-256( kanonikalisasi_JSON(snapshot) )      ← RFC 8785, bukan PDF
3. tanda_tangan = KMS.sign(hash, kunci privat org)      ← kunci tidak pernah keluar KMS
4. register_document_signature(...) → nomor seri + qr_token
5. PDF dirender: isi dokumen + nomor seri + hash + QR
```

**Saat dipindai:**

```
QR → /verifikasi/{token} → verify_signature_qr(token)
     ├─ token tidak dikenal          → UNKNOWN
     ├─ tanda tangan dicabut         → REVOKED + alasan
     ├─ kunci sudah kedaluwarsa      → KEY_EXPIRED
     ├─ hash dokumen ≠ hash sekarang → DOCUMENT_CHANGED
     └─ sisanya                      → VALID
                                        + nomor seri, nama, jabatan, unit,
                                          nomor & judul dokumen, waktu
     (setiap pemindaian dicatat di qr_scan)
```

Halaman verifikasi bisa dibuka siapa saja tanpa login, tetapi hanya menampilkan informasi
yang memang sudah tercetak di dokumen — tidak ada data pribadi tambahan.

**Yang harus diuji sejak awal:** cetak ulang PDF dengan versi WeasyPrint berbeda, lalu pindai
QR-nya. Hasilnya wajib tetap `VALID`. Bila `DOCUMENT_CHANGED`, berarti hash keliru dihitung
dari PDF, bukan dari snapshot.

---

## 6. Alur pengenalan wajah *(fase 8)*

**Pendaftaran:** HR mencatat persetujuan → karyawan mengambil 3–5 foto → face-service
mengubahnya menjadi vektor → disimpan di `face_enrollment`. Foto asli tidak disimpan kecuali
karyawan menyetujuinya secara terpisah.

**Saat absensi:**

```
swafoto → face-service /liveness  ── gagal ──► LOW_QUALITY → NEEDS_REVIEW (tetap tercatat)
        → face-service /embed → vektor
        → verify_face_for_attendance(org, karyawan, vektor)
             kemiripan ≥ ambang  → MATCH     → absensi normal
             kemiripan < ambang  → NO_MATCH  → NEEDS_REVIEW, Finance memeriksa
             belum terdaftar     → NOT_ENROLLED → absensi normal + pengingat daftar
```

**Prinsip yang tidak boleh dilanggar:** wajah tidak pernah menjadi satu-satunya penentu.
Orang yang wajahnya tidak dikenali tetap bisa absen; absensinya masuk antrean pemeriksaan.
Sistem yang menolak orang datang bekerja karena kamera tidak yakin akan ditinggalkan
penggunanya dalam seminggu.

---

## 7. Kerja luring dan sinkronisasi

**Di perangkat (drift):** tabel `outbox` berisi `client_op_id`, jenis aksi, muatan, berkas
terkait, waktu pembuatan (jam perangkat, hanya untuk urutan), status.

**Sinkronisasi:** saat daring, kirim berurutan per pekerjaan. Server menyimpan setiap operasi
di `offline_operation`; `client_op_id` yang sama dikirim dua kali → dikembalikan hasil yang
pertama (idempoten), bukan galat.

**Bila server menolak** (mis. dokumen sudah terkunci, tugas sudah dinilai):

- Operasi ditandai `REJECTED` dengan alasan berbahasa manusia.
- Muncul di layar **"Perlu perhatian"** dengan tombol untuk melihat dan menyalin isinya.
- **Tidak pernah dihapus diam-diam.** Kehilangan laporan yang sudah diketik di lapangan
  adalah cara tercepat membuat orang berhenti memakai aplikasi.

**Berkas (foto)** diunggah terpisah dengan penerusan (resumable) dan dicoba ulang dengan
jeda bertambah. Laporan hanya dianggap terkirim setelah semua lampirannya terkirim.

---

## 8. Lingkungan

| Lingkungan | Untuk apa | Data |
|---|---|---|
| **lokal** | Pengembangan | Data contoh (`seed`), boleh dihapus kapan saja |
| **staging** | Uji terima, demo ke Anda | Data contoh yang menyerupai kenyataan; **bukan** data karyawan asli |
| **produksi** | Dipakai perusahaan | Data asli |

**Aturan keras:** data karyawan asli — terutama dokumen pribadi, foto, dan data wajah —
tidak pernah disalin ke staging atau ke komputer developer. Bila perlu data yang mirip,
buat data palsu (`Faker`).

---

## 9. Migrasi skema

Alembic, satu migrasi per perubahan, **maju saja** (tidak mengandalkan `downgrade` di
produksi). Berkas `db/01`–`db/05` menjadi baseline `0001`; setelah itu setiap perubahan
menjadi migrasi tersendiri.

Fungsi PL/pgSQL dan kebijakan RLS ikut diversikan lewat migrasi, bukan dijalankan manual —
kalau tidak, produksi dan pengembangan akan diam-diam berbeda.

---

## 10. Titik kegagalan yang sudah diantisipasi

| Bila ini mati | Akibat | Rencana |
|---|---|---|
| face-service | Absensi tidak bisa mencocokkan wajah | Absensi **tetap diterima**, ditandai `SKIPPED`, diperiksa manusia |
| S3/MinIO | Foto tidak bisa diunggah | Aksi masuk antrean di perangkat, dicoba ulang |
| KMS | Dokumen tidak bisa ditandatangani | Penerbitan ditunda dengan pesan jelas; dokumen tidak terbit setengah jadi |
| Basis data | Semua berhenti | Ini titik gagal tunggal; ditangani lewat cadangan + PITR (dokumen 09) |
| Internet lapangan | Laporan tidak terkirim | Antrean luring; absensi memang butuh sinyal |

Perhatikan pola yang sama pada semua baris: **gagal dengan jelas, jangan gagal diam-diam**,
dan jangan pernah menghalangi orang bekerja karena komponen pendukung sedang bermasalah.
