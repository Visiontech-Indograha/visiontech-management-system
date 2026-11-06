# Rencana keluar dari MinIO komunitas

MinIO komunitas diarsipkan (tanpa pembaruan keamanan). Saat ini dipin ke digest (`deploy/MINIO-PIN.md`). Dokumen ini memilih pengganti. Belum ada migrasi dijalankan.

## Kriteria
S3 kompatibel (presigned URL, multipart), lisensi terbuka dan proyek aktif, RAM kecil (server 4 GB, sisa untuk objek sekitar 300 MB), satu node, mudah dicadangkan, adapter `core/storage` (ADR 0003) tidak berubah selain endpoint dan kunci.

## Opsi
| Opsi | RAM satu node (perkiraan, harus diukur) | Catatan |
|---|---|---|
| Garage (Rust, AGPL) | 50-150 MB | Sangat ringan, dirancang untuk node kecil; subset S3 (presigned dan multipart ada; tanpa SSE-S3 penuh, lifecycle terbatas). |
| SeaweedFS (Go, Apache-2.0) | 300-600 MB (master+volume+filer+s3) | Matang, fitur kaya, tetapi beberapa proses; berat untuk 4 GB. |
| RustFS (Rust, Apache-2.0) | 100-300 MB | Kompatibilitas MinIO tinggi, tetapi masih muda; risiko stabilitas. |

## Rekomendasi: Garage
Alasan: RAM terendah (aman di server 4 GB bersama DB, API, face service), satu biner, replikasi tidak dibutuhkan, dan fitur VMS yang dipakai (put/get, presigned GET, bucket privat) tercakup. Syarat: uji dulu di beta bahwa presigned URL, multipart, dan header Content-Type berjalan; bila ada fitur MinIO yang dipakai tetapi tak didukung (SSE, lifecycle), pakai SeaweedFS sebagai cadangan pilihan.

## Langkah migrasi tanpa downtime
1. Pasang Garage di beta, ukur RAM, jalankan tes unggah dari UI dan HP.
2. Pastikan cadangan berkas (`backup-minio.sh`) dan uji pulih lulus sebelum mulai.
3. Pasang Garage di prod berdampingan (port internal, tanpa publik); salin awal `mc mirror` MinIO -> Garage.
4. Tambah konfigurasi baca-ganda (baca dari Garage, jatuh ke MinIO bila tak ada); tulis ke keduanya sementara.
5. Sinkron ulang `mc mirror --overwrite` sampai selisih nol; bandingkan hitungan objek dan checksum sampel.
6. Alihkan endpoint penulisan API ke Garage (satu perubahan env, deploy biasa). MinIO tetap hidup tanpa tulis.
7. Pantau 7 hari; bila tenang, hentikan MinIO, simpan volumenya 30 hari, lalu hapus. Rollback = kembalikan env endpoint.
