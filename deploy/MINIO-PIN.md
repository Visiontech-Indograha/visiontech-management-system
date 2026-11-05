# MinIO: pin digest dan status proyek

## Status
Repo komunitas `minio/minio` sudah diarsipkan (README: tidak dipelihara, tanpa rilis biner komunitas). Image `latest` tidak lagi mendapat pembaruan keamanan. Alternatif untuk dinilai nanti: SeaweedFS, RustFS, Garage. TIDAK ada migrasi sekarang; adapter S3 di `core/storage` memudahkan pindah (ADR 0003).

## Image yang dipakai
- Beta: `deploy/beta/compose.infra.yml` (dipin ke digest, lihat langkah 4).
- Prod: compose prod ada di server, bukan di repo. Pemilik cek tag/digest sebenarnya (langkah 1).
- Dev: `docker-compose.dev-db.yml` memakai `bitnamilegacy/minio:2025.4.22` (versi tetap, tidak ikut pin ini).

## Langkah pin (pemilik, di server)
1. Digest yang SEDANG berjalan (bukan yang terbaru di registry):
   `docker inspect --format '{{.Image}} {{index .RepoDigests 0}}' vms_minio_beta vms_minio_prod`
   atau `docker image inspect quay.io/minio/minio:latest --format '{{index .RepoDigests 0}}'`.
   Alternatif: `docker buildx imagetools inspect quay.io/minio/minio:latest` (digest indeks multi-arsitektur).
2. Ganti baris `image:` di compose beta dan prod menjadi `quay.io/minio/minio@sha256:<DIGEST>`. Simpan tag sebagai komentar.
3. `docker compose config -q`, lalu `docker compose up -d minio` (data di volume tidak berubah). Cek `/ready` API dan unggah satu berkas uji.
4. Catat digest dan tanggal di sini (2026-11-05, diambil dari image yang sedang berjalan di server):
   - Beta: `sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` (sudah dipin di `deploy/beta/compose.infra.yml`).
   - Prod: `sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` (sama dengan beta).
   - STATUS PROD: compose prod ada di server dan BELUM dipin (masih tag lama). Menunggu jendela perawatan karena butuh membuat ulang kontainer minio prod (`docker compose up -d minio`).

## Memperbarui digest dengan aman
1. Cadangkan bucket (`mc mirror`) dan DB; pastikan cadangan terakhir < 26 jam.
2. Tarik image kandidat, `docker buildx imagetools inspect <tag>` untuk digest baru.
3. Terapkan di beta dulu, uji unggah/unduh/tiket /files, tunggu minimal 1 hari, baru prod.
4. Rollback: kembalikan digest lama (simpan di komentar compose); format data tidak berubah antarrilis dekat, tetapi jangan loncat jauh tanpa uji beta.
5. Dependabot `docker` tidak menjangkau compose di server; tinjau digest tiap kuartal.
