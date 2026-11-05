---
name: vms-storage-minio
description: >-
  Pakai skill ini untuk penyimpanan berkas dan objek VMS: unggahan foto dan dokumen (swafoto absensi, foto titik survei, dokumen karyawan, lampiran jadwal), validasi tipe MIME, magic bytes, dan ukuran, akses berkas lewat /files/{id}/url dan tiket bertanda tangan, bucket MinIO atau S3 (privat, kebijakan, SSE, lifecycle, versioning), kuota per kantor, pemindaian malware dan karantina, backup bucket, migrasi penyimpanan tanpa downtime, dan status MinIO komunitas yang sudah diarsipkan (pin digest, alternatif SeaweedFS, RustFS, Garage). Kata kunci: MinIO, S3, bucket, objek, object storage, presigned URL, unggahan, upload, file, berkas, foto, magic bytes, MIME, SSE, enkripsi, lifecycle, kuota, ClamAV, malware, karantina, SeaweedFS, RustFS, Garage, /uploads, media.
---

# vms-storage-minio · Berkas dan objek VMS

Basis kode (`origin/beta`, diperiksa 2026-11-04): `api/app/core/storage.py`, `api/app/core/image.py`, `api/app/modules/system/controllers/files_controller.py`, `api/app/modules/system/routes/files_route.py`, `api/app/modules/system/routes/media_stream_route.py`, `api/app/main.py`, `api/app/core/security.py` (tiket), `deploy/beta/compose.infra.yml`, `docker-compose.dev-db.yml`. Target: `vms-next/docs/06` (MinIO, Berkas dan wajah), ADR 0001 keputusan 10, ADR 0003 (A7, A8, A9).

Penanda: `(bukti: file:baris)` = kondisi kode. `Target:` = standar baru.

## 1. Aturan keras

1. **Tidak ada mount statis untuk unggahan pengguna.** `api/app/main.py:54-57` masih mount `/uploads` pada `origin/beta` (HEAD `d1a3d4e5`). Perbaikannya ada di commit `0c0f98eb` pada cabang `hotfix/uploads-anonim`, dan belum masuk `origin/beta` (diperiksa dengan `git merge-base --is-ancestor 0c0f98eb origin/beta`: gagal). Ini insiden nyata: foto karyawan bisa dibaca tanpa login. Hapus mount sebelum merilis apa pun yang menyentuh berkas.
2. **Berkas pribadi tidak pernah masuk `api/uploads/`.** Folder itu ikut ke image (`api/Dockerfile:27`, `COPY . .`) dan dapat dibaca rute `/media/*` yang publik. Rute itu hanya untuk contoh (`media_stream_route.py:1-10`: "hanya berkas… `api/uploads/<folder rujukan>/`"; foto karyawan, dokumen, swafoto, inspeksi tidak disajikan di sana).
3. **Akses berkas hanya lewat `/api/v1/files/{id}/url`** setelah pemeriksaan akses per berkas (`files_route.py:60-79`). Jangan membuat URL publik ke MinIO.
4. **Bucket privat.** Tidak ada kebijakan publik. Tes: `GET` objek tanpa tanda tangan harus 403.
5. **Validasi di server, bukan percaya klien.** Tipe dari magic bytes (`filetype.guess`, `files_controller.py:69`), bukan header `Content-Type` klien. Ukuran dibatasi sebelum disimpan (`:55-62`).
6. **Batas unggahan sama di API, web, dan mobile** (aturan `CLAUDE.md` proyek).
7. **Tiket akses tetap EdDSA** (`security.py:124-151`). Jangan diganti presigned publik (ADR 0003 C-7 usulan).
8. **Tes penyimpanan memakai bucket uji** (`db_guard.py:28-35`): port 9000 dan 9001 (produksi) ditolak untuk tes. Bucket uji di port lain (riset 02, `MinIO uji server = :9100`).

## 2. Peta kode

| Fungsi | Lokasi | Catatan |
|---|---|---|
| Klien MinIO dan retry | `storage.py:31` | `urllib3.Retry(total=1, backoff_factor=0.2)` |
| Cek bucket | `storage.py:38-61` | `bucket_ready`, `ensure_bucket` (membuat bucket bila belum ada) |
| Unggah | `storage.py:65-86` | `upload_file(object_name, file_data: bytes, content_type)`: `content_type` dari pemanggil, tanpa allowlist di sini |
| Baca bytes | `storage.py:89-127` | `get_image_bytes`, `get_object_bytes` |
| Hapus, cek ada | `storage.py:129-150` | `delete_object`, `object_exists` |
| Presign | `storage.py:153-186` | `presign_client()` (`:153`), `get_presigned_url()` (`:174`, default 5 menit). **Tidak dipanggil rute mana pun** (grep) |
| Unggahan | `files_controller.py:49-100` | Batas 10 MB (`:26`), magic bytes (`:69`), `is_decodable_image` (`:77`), dedup per pemilik (`:89-99`) |
| Tipe yang diizinkan | `files_controller.py:29-37` | JPEG, PNG, WebP, HEIC, PDF, DOC, DOCX |
| Cache gambar | `files_controller.py:28` | `private, max-age=1500` |
| Rute URL | `files_route.py:60-79` | Varian `thumb`/`view`/`full`, berlaku 5 menit |
| Tiket | `security.py:124-151` | `FILE_TICKET_TTL` 5 menit (`:125`), jendela 1800 detik (`:128`) |
| Rute publik contoh | `media_stream_route.py` | `Cache-Control: public, max-age=3600` (`:74`) untuk berkas contoh |
| Konfigurasi | `config.py:115-125` | `MINIO_ENDPOINT`, `MINIO_BUCKET=vms-files`, `MINIO_PUBLIC_URL`, `MINIO_REGION` |
| Penjaga kredensial bawaan | `config.py:214-228` | Bila `APP_ENV=production`, `minioadmin` ditolak (`ValueError`) |
| Infra beta | `deploy/beta/compose.infra.yml:22` | `image: quay.io/minio/minio:latest` (tidak dipin) |
| Infra dev | `docker-compose.dev-db.yml:43` | `bitnamilegacy/minio:2025.4.22` (riset 02; perlu cek ulang) |

Model data: `file_object` (`db/06:724-735`) menyimpan `storage_key UNIQUE`, `mime_type`, `byte_size`, `sha256 BYTEA`, dan `UNIQUE (office_id, sha256)`. Target (`docs/03`): satu tabel `file_objects` untuk semua berkas; entitas lain hanya menyimpan `file_id`, bukan path.

## 3. Alur unggahan (kondisi sekarang dan target)

Kondisi (`files_controller.py`):
1. Baca hingga `MAX_FILE_SIZE + 1` byte (`:55`). Lebih dari 10 MB → 413 `FILE_TOO_LARGE`. Kosong → 400 `FILE_EMPTY`.
2. `filetype.guess` dari isi (`:69`). Tipe tidak ada di allowlist → 415 `INVALID_FILE_TYPE` (`:72-75`).
3. Gambar harus bisa didekode (`:77`). HEIC tidak didukung → 415; gambar rusak → 422 `IMAGE_CORRUPT`.
4. SHA-256 dan kunci dedup per pemilik (`:89-99`). Berkas sama dari pemilik sama → respons "sudah ada".
5. Kompresi gambar (varian `thumb`, `view`, `full`) lalu simpan ke MinIO (`upload_file`).
6. Catat `file_object`.

Target (tambahan):
- **Pemindaian malware** sebelum berkas dapat diakses: unggah ke prefix `quarantine/`, pindai, pindahkan ke prefix final bila bersih, hapus bila terinfeksi (riset 02 C-2). Kolom `scan_status` (`pending`, `clean`, `infected`). Akses hanya untuk `clean`.
- **Kuota per kantor** (riset 02 C-6). Sumber: `SUM(byte_size) WHERE office_id = :o`.
- **Batas per jenis**: foto swafoto, foto titik survei, dokumen karyawan, lampiran jadwal bisa beda. Pusatkan di satu modul (`core/upload_policy.py`, usulan riset 02 C-1). Ukuran foto kamera HP diukur dulu sebelum menetapkan batas.
- **Galat generik**: pesan Bahasa Indonesia tanpa nama berkas yang berisi PII.

## 4. Validasi unggahan (terpusat)

Detail di `references/validasi-unggahan-dan-akses.md`.

Ringkas:
- Magic bytes (`filetype`) untuk tipe. Jangan percaya ekstensi atau `Content-Type`.
- Ukuran: baca dengan batas (`read(MAX+1)`), jangan `read()` tanpa batas.
- Gambar: dekode untuk memastikan tidak terpotong (`image.py`, `is_decodable_image`).
- Dokumen (PDF, DOCX): tolak makro dan konten aktif bila ada pemindai. Dicatat sebagai pertanyaan terbuka.
- Nama berkas: jangan pakai nama dari klien sebagai `storage_key`. Gunakan UUID.
- Dedup SHA-256 per pemilik sudah benar (tidak membocorkan keberadaan berkas milik orang lain).

## 5. Akses dan tiket

- `GET /api/v1/files/{id}/url?variant=` memeriksa akses lalu mengembalikan URL bertiket (5 menit) (`files_route.py:60-79`).
- Browser men-cache gambar hingga 1500 detik (`files_controller.py:28`). Tiket berlaku minimal sejak diterbitkan (`security.py:127-128`).
- `get_presigned_url` MinIO tidak dipakai. Jika suatu hari dipakai, batasi 15 menit maksimum (`docs/06` dan ADR 0003 A8: "maks 15 menit").
- **Header**: berkas pribadi memakai `private`, `no-store` atau `private, no-cache`. Hindari `public` untuk berkas pribadi. `media_stream_route.py:74` memakai `public` hanya untuk berkas contoh (perlu cek bila suatu hari berkas pengguna masuk ke sana).
- `X-Content-Type-Options: nosniff` untuk semua respons berkas (`files_controller.py:190`, `media_stream_route.py:74`).
- Header keamanan dan CSP web di `web/Caddyfile:12` (riset 01 T12).

## 6. Bucket, enkripsi, lifecycle, dan versioning

Target (riset 02 C-3, C-4, C-5; `docs/06`):
- **Bucket privat**. Kebijakan minimal: hanya akun layanan VMS.
- **SSE** (enkripsi sisi server): SSE-S3 atau SSE-KMS. Kunci SSE-KMS disimpan di luar server (riset 02 C-4). Di MinIO: `set_bucket_encryption` (minio-py). Di SeaweedFS: SSE-S3 (ADR 0003 riset 02 §3.1).
- **Lifecycle**: `quarantine/` dan `tmp/` dihapus setelah 1 hari; versi lama dihapus setelah 30 hari (bila versioning aktif). Pastikan prefix tidak dipakai berkas final.
- **Versioning**: aktif untuk pemulihan berkas terhapus lunak. Hapus lunak di aplikasi (`delete_at`) tidak menghapus objek; hapus fisik lewat job terjadwal yang juga memeriksa `file_object`.
- **Kredensial**: `minioadmin` tidak boleh dipakai di luar lokal (`config.py:224-225` menandai). Kredensial dari Docker secret atau `.env` yang tidak masuk image (`api/.dockerignore` belum ada, riset 01 F-01).

## 7. Backup bucket

- Target: salinan bucket ke lokasi kedua (riset 02 §3.4, `docs/06` Cadangan). Gunakan `mc mirror` atau `rclone` ke MinIO kedua atau penyimpanan luar situs.
- Uji pulih ke bucket uji, bukan produksi. Catat hasil bersama uji pulih database (`vms-db` bagian 9).
- Pastikan `pg_dump` dan bucket dicadangkan pada waktu yang konsisten (metadata `file_object` harus cocok dengan objek di bucket).

## 8. Status MinIO dan alternatif

Fakta (diperiksa 2026-11-04 di `https://github.com/minio/minio`):
- Repo diarsipkan (`archived`) dan README menyatakan "no longer maintained" serta "no longer provide pre-compiled binary releases for the community version". Binary lama tidak menerima pembaruan.
- Dampak untuk VMS: `quay.io/minio/minio:latest` (`compose.infra.yml:22`) tidak dipin dan tidak mendapat pembaruan keamanan.
- `docs/06` (Catatan MinIO) menyebut rencana `cgr.dev/chainguard/minio` (terawat, dibangun dari sumber) dengan pin digest saat rilis. Verifikasi dulu bahwa image ini tersedia dan lisensinya diterima sebelum dipakai.
- ADR 0003 R13: MinIO dicatat sebagai bahan sejarah dan tidak diadopsi sebagai dependensi baru.

Langkah segera (riset 02 C-3, jangka pendek):
1. Pin image ke digest (`image@sha256:…`), bukan `latest`.
2. Catat risiko di `SECURITY.md`.

Alternatif (riset 02 §3.1, cek ulang sebelum memilih):

| Kandidat | Lisensi | Catatan |
|---|---|---|
| SeaweedFS (`https://github.com/seaweedfs/seaweedfs`) | Apache-2.0 | Presigned, bucket policy, lifecycle (tanpa transition), SSE-S3 dan SSE-KMS, versioning, Object Lock. Kandidat utama untuk server 4 GB |
| RustFS (`https://github.com/rustfs/rustfs`) | Apache-2.0 | Klaim kompatibilitas S3 luas; presigned dan bucket policy belum tercantum jelas di README. Versi 1.0.x; status produksi perlu konfirmasi |
| Garage (`https://github.com/deuxfleurs-org/garage`) | AGPL-3.0 | Dirancang untuk klaster multi-node. Presigned, bucket policy, enkripsi at rest tidak tercantum. AGPL perlu hati-hati bila dimodifikasi dan diberikan ke pihak lain |

Uji kompatibilitas: gunakan kumpulan panggilan yang benar-benar dipakai VMS (PutObject, GetObject, presign GET, DeleteObject, ListObjects, CopyObject, multipart untuk berkas besar). Jalankan di staging atau DB/MinIO uji saja, atas perintah user.

Klien: `minio-py` (Apache-2.0, `https://github.com/minio/minio-py`) dipakai sebagai adapter. Target ADR 0003 A7: port/protokol S3-generik di `core/storage`, adapter MinIO hanya di satu berkas. Ini memudahkan pindah ke SeaweedFS atau lainnya.

## 9. Migrasi penyimpanan tanpa downtime

Detail di `references/status-minio-dan-migrasi.md`.

Ringkas (riset 02 C-3):
1. Tulis adapter S3 generik. Kode memanggil antarmuka, bukan `minio` langsung.
2. Jalankan dua penyimpanan paralel: unggahan baru ke penyimpanan baru (konfigurasi), baca dari keduanya sampai data dipindah.
3. Salin objek dengan `rclone` atau `mc mirror` (idempoten). Verifikasi jumlah objek dan checksum.
4. Pindahkan baca ke penyimpanan baru. Pertahankan penyimpanan lama sebagai cadangan selama satu siklus rilis.
5. Hapus penyimpanan lama setelah verifikasi dan cadangan.
6. Simpan `storage_key` yang sama agar `file_object` tidak perlu diubah.

## 10. Kuota dan pemantauan

- Kuota per kantor: hitung dari `file_object.byte_size` (`SUM` dengan indeks `office_id`). Batas di `settings` (usulan 80% kapasitas). Tampilkan sisa kuota di halaman admin (riset 02 C-6).
- Pantau: ukuran bucket, jumlah objek karantina, kegagalan unggah, latensi MinIO (RED dan USE, lihat `vms-api` bagian 7). Belum ada metrik (riset 01 T13).

## 11. Checklist

- [ ] Tidak ada mount `/uploads` (`main.py:54-57` sudah dihapus atau diganti).
- [ ] Berkas pribadi tidak ada di `api/uploads/`; `api/.dockerignore` mengecualikannya.
- [ ] Akses lewat `/files/{id}/url` dengan pemeriksaan akses; tiket 5 menit.
- [ ] Header cache untuk berkas pribadi `private`/`no-store`; `nosniff` ada.
- [ ] Validasi magic bytes, ukuran dengan batas baca, dan dekode gambar.
- [ ] Nama objek UUID; tidak memakai nama dari klien.
- [ ] Bucket privat; SSE aktif bila tersedia; kredensial bukan `minioadmin`.
- [ ] Image dipin ke digest; status MinIO tercatat di `SECURITY.md`.
- [ ] Lifecycle untuk karantina dan tmp; versioning dan hapus fisik terjadwal.
- [ ] Backup bucket dan uji pulih tercatat.
- [ ] Kuota per kantor dihitung dan ditampilkan (bila diminta).

## 12. Skill global yang boleh dipanggil atau dilebur

- **`security-review`**: tinjau perubahan unggahan, akses berkas, header cache, dan kebijakan bucket sebelum merge. Wajib untuk perubahan yang menyentuh `/uploads` atau `/media`.
- **`code-review`**: tinjau diff `storage.py`, `files_controller.py`, dan route berkas.
- **`simplify`**: merapikan kode unggahan tanpa mengubah urutan validasi atau header keamanan.
- **`postman:api-testing`**: menguji `/files/upload` dan `/files/{id}/url` dengan koleksi. Lengkapi dengan tes pytest yang memakai bucket uji.

## 13. Berkas referensi

- `references/validasi-unggahan-dan-akses.md`: alur validasi, tipe, ukuran, tiket, header, dan tes.
- `references/status-minio-dan-migrasi.md`: status arsip MinIO, pin digest, perbandingan alternatif, dan langkah migrasi.
