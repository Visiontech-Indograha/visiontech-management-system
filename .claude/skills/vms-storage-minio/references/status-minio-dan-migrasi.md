# Status MinIO, alternatif, dan migrasi penyimpanan (vms-storage-minio)

Sumber: riset 02 §3 (diverifikasi 2026-11-04), `docs/06` (Catatan MinIO), ADR 0003 R11-R13, A7-A9, D7. Tautan:
- MinIO (diarsipkan): https://github.com/minio/minio (dibuka 2026-11-04; README: "THIS REPOSITORY IS NO LONGER MAINTAINED", "We will no longer provide pre-compiled binary releases for the community version").
- minio-py (Apache-2.0): https://github.com/minio/minio-py (riset 02, push 2026-09-28).
- SeaweedFS (Apache-2.0): https://github.com/seaweedfs/seaweedfs (riset 02, push 2026-11-04).
- RustFS (Apache-2.0): https://github.com/rustfs/rustfs (riset 02).
- Garage (AGPL-3.0): https://github.com/deuxfleurs-org/garage (riset 02).
- AWS SigV4 POST policy (kondisi `content-length-range`, `starts-with`): dirujuk riset 02 §3.2 (dokumen AWS; belum dibuka ulang pada tanggal ini).

## 1. Fakta status

| Hal | Kondisi | Bukti |
|---|---|---|
| Repo MinIO | Diarsipkan oleh pemilik; read-only | GitHub (diperiksa 2026-11-04) |
| Binary dan image komunitas | Tidak dirilis lagi; binary lama tidak menerima pembaruan | README MinIO |
| Compose beta | `quay.io/minio/minio:latest`, tidak dipin | `deploy/beta/compose.infra.yml:22` |
| Compose dev | `bitnamilegacy/minio:2025.4.22` | `docker-compose.dev-db.yml:43` (riset 02; perlu cek ulang) |
| Rencana VMS Next | `cgr.dev/chainguard/minio` (dibangun dari sumber, dipin digest saat rilis) | `vms-next/docs/06` Catatan MinIO |
| Port | Beta: `127.0.0.1:9002` ke 9000, `127.0.0.1:9003` ke 9001 (hanya lokal) | `compose.infra.yml:27-31` |
| Volume | `vms_minio_data_beta` | `compose.infra.yml` |

Risiko: rantai pasok dan keamanan. Image tanpa pembaruan dan tanpa pin digest bisa berubah diam-diam. Prioritas P0 untuk pin digest, lalu migrasi ke penyimpanan yang masih dirawat.

## 2. Langkah jangka pendek (pin)

1. Pilih image yang masih dirilis dan dipin ke digest (`repo@sha256:…`). Catat tanggal dan sumber build.
2. Ganti `latest` di `deploy/beta/compose.infra.yml:22` dan `docker-compose.dev-db.yml:43` dengan digest.
3. Catat risiko di `SECURITY.md` (sudah ada di repo: 640 byte). Tambahkan entri: versi, digest, tanggal, rencana migrasi.
4. Pastikan layanan tidak punya port publik (sudah `127.0.0.1` di beta).
5. Pertahankan kredensial dari `infra.env` (bukan di compose, bukan di image). Hindari `minioadmin` (`config.py:224-225`).

Usaha perkiraan (riset 02 C-3): pin 0,5 hari.

## 3. Perbandingan kandidat

Diringkas dari riset 02 §3.1. Verifikasi ulang kompatibilitas S3 sebelum memilih.

| Kriteria | SeaweedFS | RustFS | Garage |
|---|---|---|---|
| Lisensi | Apache-2.0 | Apache-2.0 | AGPL-3.0 |
| Bintang (2026-11-04) | 35.908 | 35.734 | 4.825 |
| Presigned URL | Ya (riset) | Tidak tercantum jelas di README | Tidak tercantum |
| Bucket policy | Ya | Tidak tercantum jelas | Tidak tercantum |
| Lifecycle | Ya, kecuali transition | ILM disebut tersedia | Tidak tercantum |
| SSE-S3, SSE-KMS | Ya | SSE disebut tersedia | Tidak tercantum |
| Versioning | Ya (MFA Delete tidak) | Tidak dipastikan | Tidak dipastikan |
| Object Lock | Ya | Tidak dipastikan | Tidak dipastikan |
| Kecocokan untuk VMS | Kandidat utama (server 4 GB, tim kecil) | Menarik, tunggu matriks kompatibilitas dan rilis stabil | Multi-node; AGPL perlu kehati-hatian |

Rekomendasi (riset 02): SeaweedFS paling realistis. RustFS dipantau. Garage tidak untuk sekarang.

Keputusan belum final. Pertanyaan terbuka: apakah SeaweedFS diuji di staging atau di `vms_test` dulu (ADR 0002 keputusan 4 menunda staging; ADR 0001 pertanyaan terbuka 4).

## 4. Daftar panggilan S3 yang harus diuji

Uji setiap kandidat dengan panggilan yang benar-benar dipakai VMS:
- `put_object` (unggahan dengan `content_type` dan `length`).
- `get_object` (streaming ke respons).
- `presigned_get_object` (bila dipakai).
- `remove_object` (hapus objek).
- `list_objects` (inventaris untuk audit dan rekonsiliasi).
- `copy_object` (pindah dari karantina ke prefix final).
- Multipart upload (untuk berkas besar, bila ada).
- `bucket_exists` dan `make_bucket` (`storage.py:38-61`).
- `stat_object` (`object_exists`, `storage.py:141`).

Hasil uji dicatat di ADR atau runbook. Kegagalan satu panggilan menghentikan migrasi.

## 5. Adapter (ADR 0003 A7)

- Antarmuka generik di `core/storage` (Protocol atau ABC): `put`, `get`, `delete`, `exists`, `presign_get` (opsional), `list`, `copy`.
- Implementasi `MinioAdapter` (minio-py) hanya di satu berkas. Implementasi S3 generik (boto3 atau aiobotocore) disiapkan bila SeaweedFS dipakai.
- Konfigurasi endpoint dari `config.py` (`MINIO_*`); nama variabel dapat diubah jadi `OBJECT_STORE_*` saat migrasi, dengan alias untuk transisi.
- `presign_client()` (`storage.py:153-171`) memakai origin publik. Pastikan endpoint presign tetap tidak mengekspos port internal.

## 6. Migrasi tanpa downtime

Langkah (riset 02 C-3, dengan urutan):
1. **Adapter**: kode memanggil antarmuka. Tidak ada perubahan perilaku.
2. **Penyimpanan baru** berjalan di sebelah lama (compose terpisah, volume terpisah). Kredensial berbeda.
3. **Salin**: `rclone sync` atau `mc mirror --preserve` dari lama ke baru. Jalankan berulang sampai selisih nol. Idempoten.
4. **Verifikasi**: bandingkan jumlah objek dan ukuran dari `file_object` (`SUM(byte_size)`, `COUNT(*)` per office). Sampel checksum SHA-256 (`file_object.sha256`).
5. **Tulis baru**: konfigurasi tulis mengarah ke penyimpanan baru. Baca mencoba baru lalu lama (fallback) selama satu rilis.
6. **Baca baru**: setelah yakin, baca hanya dari baru.
7. **Simpan cadangan lama** selama satu siklus rilis (`docs/06` Rilis: rollback aplikasi bila perlu).
8. **Matikan lama** setelah backup dan uji pulih.

Aturan:
- `storage_key` tidak berubah. `file_object` tidak perlu diubah.
- Migrasi dijalankan saat beban rendah. Catat waktu UTC.
- Tidak ada penghapusan di sumber selama migrasi berjalan.
- Rencana rollback tertulis: kembalikan konfigurasi baca dan tulis ke lama.

Usaha perkiraan (riset 02 C-3): uji dan migrasi SeaweedFS 3-5 hari. Risiko: kompatibilitas S3 (presign, multipart).

## 7. Backup dan kebijakan

- Lokasi kedua untuk objek (riset 02 §3.4; `docs/06` Cadangan): `mc mirror` atau `rclone` harian ke penyimpanan lain atau luar situs.
- Uji pulih objek secara acak: unduh 10 objek dan bandingkan SHA-256 dengan `file_object.sha256`.
- Retensi cadangan sesuai kebijakan operasional (perlu keputusan pemilik).

## 8. Yang tidak dilakukan sekarang

- Tidak menambah Redis untuk penyimpanan berkas.
- Tidak memakai presigned PUT publik. POST policy hanya bila unggahan besar benar-benar dibutuhkan (riset 02 C-8).
- Tidak memakai CDN (`docs/06`: satu host, satu server 4 GB).
- Tidak memakai `cgr.dev` sebelum lisensi dan ketersediaan image diperiksa.

## 9. Checklist migrasi

- [ ] Image dipin ke digest dan tercatat di `SECURITY.md`.
- [ ] Adapter S3 generik dibuat; kode lama memanggil antarmuka.
- [ ] Kandidat diuji dengan daftar panggilan di bagian 4.
- [ ] Salinan dan verifikasi jumlah objek dan checksum.
- [ ] Fallback baca selama satu rilis.
- [ ] Cadangan lama disimpan; rencana rollback tertulis.
- [ ] Keputusan dicatat di ADR baru (usulan: ADR 0004).
