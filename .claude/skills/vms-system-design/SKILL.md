---
name: vms-system-design
description: Desain sistem VMS - arsitektur komponen, alur data, kapasitas server 4 GB, caching, antrean, rate limit, timeout dan circuit breaker, idempotensi, RLS, observability, cadangan, dan analisis Big O di tingkat sistem. Pakai saat memutuskan pola skala, menambah komponen, atau menilai dampak performa dan keamanan sebuah perubahan.
---

# vms-system-design - desain sistem VMS

Tujuan skill: keputusan teknis di tingkat sistem yang masuk akal untuk satu server 4 GB, dengan bukti dari kode dan dokumen. Setiap angka di sini bersumber; angka yang belum diukur ditandai BELUM DIUKUR.

## 1. Arsitektur komponen (VMS lama, produksi)

```
Browser (web React/Vite)            HP (APK Flutter)
        │ HTTPS                            │ HTTPS (API)
        ▼                                  │
 vms_web :8080  (nginx/Caddy, proxy)       │
        │ /api/v1/*                        │
        ▼                                  ▼
 ┌──────────────────── vms_api :8000 (FastAPI, monolit berlapis) ────────────────────┐
 │ routes -> controllers/services -> repositories (SQLAlchemy async, asyncpg)        │
 └───────┬───────────────────────────┬──────────────────────────────┬────────────────┘
         ▼                           ▼                              ▼
  vms_db_prod :5433           MinIO vms_minio_prod          vms_face (internal,
  PostgreSQL 18 + PostGIS      (berkas; URL presigned;       tanpa port publik;
  + pgvector                   /vms-files/* via Caddy)       token internal)
  (Master Schema V2)
Beta: vms_beta_web :8081, vms_beta_api :8001, vms_beta_db :5435, MinIO :9002/9003
```

Sumber: `docker-compose.yml`, `deploy/compose.limits.yml`, `deploy/autodeploy.sh` (port), `deploy/README.md` (Caddy, face, MinIO), `vms-next/docs/08` bagian "Server".

Yang TIDAK ada di VMS lama (sumber: riset `02` dan `01` T7):
- Redis: tidak ada di `docker-compose.yml`.
- Antrean pesan, broker, worker terpisah: tidak ada.
- Mesin feature flag: tidak ada.
- Metrik (`/metrics`), OpenTelemetry: tidak ada.

## 2. Alur data utama

1. Permintaan web/HP -> `vms_web` (proxy) -> `vms_api`.
2. `vms_api`: dependensi auth (JWT, sesi di `user_sessions`) -> izin global (`require_permission`) -> cek relasi (divisi/tim/SK) -> service (batas transaksi) -> repository (SQL) -> DB.
3. Berkas: API membuat URL presigned ke MinIO; klien mengunduh/unggah langsung dengan URL berumur pendek.
4. Wajah: API memanggil `vms_face` dengan token internal (hanya saat absen masuk/pulang; `vms-next/docs/06`, "Berkas dan wajah").
5. Offline HP: perubahan disimpan lokal (outbox), lalu dikirim saat sinkron. Idempotensi sinkron memakai `client_op_id` (riset `01` F-08: 3 round trip minimum per operasi).

## 3. Kapasitas server 4 GB

- Spesifikasi: 4 GB RAM, 2 CPU (`deploy/compose.limits.yml`, komentar; `vms-next/docs/08`).
- Pengukuran 2026-10-28 (`deploy/compose.limits.yml`): face prod 482 MB + beta 259 MB, swap 561 MB. Karena itu batas memori dipasang.
- Batas saat ini: `api` 768m, `web` 128m, `face` 768m; log `json-file` 10m x 3 (sumber: `compose.limits.yml`).
- Memori `vms_db_prod`, `vms_minio_prod`, dan `vms_uptime_kuma`: BELUM DIUKUR dalam dokumen. Ukur: `docker stats --no-stream`.
- Aturan keputusan: setiap komponen baru harus punya (a) anggaran memori tertulis, (b) batas `mem_limit`, (c) alasan kenapa tidak cukup dengan komponen yang ada. Tanpa ketiganya, jangan tambah komponen.
- Server preview bersama dan staging: ditunda karena RAM (`vms-next/docs/06`, butir 6; ADR 0002 keputusan 4).

## 4. Big O di tingkat sistem

Pakai satu ukuran: biaya per permintaan = jumlah kueri x biaya tiap kueri, dengan n = jumlah baris yang tersentuh.

| Pola | Kompleksitas kini | Dampak | Sumber |
|---|---|---|---|
| `apply_list` memuat seluruh tabel, lalu memfilter dan memotong di Python | O(N) memori dan waktu per halaman, N = seluruh baris | TINGGI saat data tumbuh | `api/app/core/list_params.py:58-67`; riset `01` F-05 |
| Daftar tanpa `LIMIT` (projects, clients, divisions, job_positions) | O(N) respons | SEDANG | riset `01` F-06 |
| Bulk jadwal: kueri per sel | O(sel) kueri; kasus terburuk puluhan ribu | SEDANG-TINGGI | riset `01` F-07 |
| Hitung log aktivitas `COUNT(*)` per halaman; `ORDER BY created_at` tanpa indeks | O(N) per halaman | SEDANG (naik seiring data) | riset `01` F-10 |
| Refresh token: `refresh_token_hash` tanpa indeks | O(sesi) per refresh | SEDANG, naik | `db/06_master_schema_v2.sql:139`; riset `01` F-04 |
| Argon2 sinkron di `async def` | memblokir event loop | SEDANG | riset `01` F-17 |

Aturan desain:
- Kueri per permintaan harus konstan terhadap n. Gunakan JOIN atau `IN (...)` untuk batch, bukan kueri per baris.
- Daftar wajib `LIMIT` di SQL (bukan di Python). Daftar baru memakai keyset `(created_at, id)`; `OFFSET` baru dilarang.
- Indeks untuk kolom filter dan urutan yang sering dipakai. Dokumentasikan rencana `EXPLAIN ANALYZE` untuk endpoint yang disentuh.
- Tabel log bertumbuh linear. Partisi bulanan sudah ada (riset `01` F-10 dan ringkasan `vms-next`); pastikan kueri memakai kolom partisi.
- Pekerjaan CPU berat (hash sandi, pembuatan dokumen): jalankan di threadpool (`run_in_threadpool`) atau keluarkan dari jalur permintaan.

## 5. Caching

- Sudah ada: TanStack Query `staleTime` di 10 berkas web; `Cache-Control` di `team_route.py:177` (`private, no-cache`) dan `media_stream_route.py:74` (`public, max-age=3600`) (riset `01` T7).
- Belum ada: lapisan cache aplikasi dan Redis. Ini sah untuk satu instance dengan beban kecil.
- Keputusan: tambah cache hanya bila ada pengukuran (p95 atau kueri berulang yang terbukti). Dokumentasikan di ADR.
- Pola bila dibuat: cache-aside; TTL dengan jitter agar tidak serentak (mencegah cache stampede); invalidasi saat tulis; kunci cache memuat peran/divisi agar tidak bocor lintas divisi.
- Pantau: rasio hit, dan pastikan respons yang di-cache tidak memuat data lintas divisi.

## 6. Antrean dan pekerjaan latar

- Belum ada antrean pesan atau worker. Tidak perlu broker (Kafka, RabbitMQ) untuk satu server 4 GB.
- Pilihan bila diperlukan: (a) tabel outbox di PostgreSQL + pekerja sederhana; (b) tugas latar dalam proses dengan batas waktu. Keduanya perlu ADR.
- Notifikasi FCM dan pengiriman Discord berjalan di jalur permintaan saat ini; beri timeout (bagian 7).

## 7. Rate limit, timeout, retry, circuit breaker

- Lockout login sudah ada (`auth_session_repository.py:32`, `:66-81`; `auth_service.py:94-103`) (riset `01` T8).
- Belum ada rate limiter umum (F-19). Endpoint unduhan, face, upload, dan `/auth/refresh` tidak dibatasi.
- Target yang sudah diputuskan (ADR 0002 keputusan 9, VMS Next): login dan reset sandi 6 per menit per IP+akun; endpoint umum 120 per menit per pengguna; polling notifikasi 6 per menit per akun (usulan `vms-next/docs/06`).
- Penyimpanan penghitung: PostgreSQL atau memori per proses. Memori per proses hanya sah untuk satu instance (riset `01` T7-T8).
- Bila memakai Redis + sliding window ZSET: anggota ZSET harus unik (mis. `f"{now_ms}-{uuid4().hex}"`). Anggota `str(now_ms)` bisa tertimpa pada milidetik yang sama (riset `01` T8, catatan untuk PDF).
- Timeout: setiap panggilan HTTP keluar (face-service, Discord, FCM) WAJIB timeout eksplisit (riset `01` T8: sedang, 0,5-1 hari).
- Retry: hanya untuk operasi idempoten, dengan exponential backoff dan jitter. Saat ini `api/app/core/storage.py:31` memakai `urllib3.Retry(total=1, backoff_factor=0.2)`.
- Circuit breaker: belum ada. Tambahkan hanya bila dependensi (face-service) terbukti sering gagal dan timeout sudah ada.

## 8. Idempotensi dan konkurensi

- Endpoint mutasi: 189 (121 POST, 31 PUT, 5 PATCH, 32 DELETE), tanpa `Idempotency-Key` (riset `01` F-03). Idempotensi hanya untuk sinkron offline (`client_op_id`).
- Aturan keputusan: wajibkan `Idempotency-Key` untuk pembuatan yang berisiko ganda (absen, pengajuan cuti/lembur, pembuatan pekerjaan, unggah). Tidak perlu untuk GET atau PUT yang sudah idempoten.
- Implementasi yang disepakati di VMS Next: tabel PostgreSQL (kunci unik user + endpoint + key, simpan respons, masa berlaku) + Redis hanya untuk anti-balapan (`vms-next/docs/07`, fase 1). Untuk VMS lama, cukup tabel PostgreSQL bila Redis tidak ada.
- Transisi status: gunakan compare-and-set (`UPDATE ... WHERE status = :dari`) atau `SELECT ... FOR UPDATE` (riset `01` F-12: approve/reject jadwal harian tanpa keduanya). Pola `FOR UPDATE` sudah dipakai di sekitar 12 titik (riset `01` F-12).
- Tes konkurensi (`asyncio.gather`) belum ada (F-14). Tambahkan untuk transisi status.

## 9. Keamanan di tingkat sistem

- Sudah sesuai (riset `01` ringkasan 8): argon2id, rotasi refresh token dengan deteksi reuse (batas family 24 jam), access token 15 menit, refresh di cookie HttpOnly (web), `NUMERIC(12,2)`, `TIMESTAMPTZ`, log JSON dengan request ID.
- RLS: `set_config('app.user_id', ...)` ada di `api/app/database/session.py`, tetapi tidak ada satu pun `CREATE POLICY` di `db/` maupun `api/alembic_v2/` (riset `02`). Isolasi divisi dijaga di kode aplikasi (23 repositori menyebut `division_id`).
- Keputusan RLS: tambah RLS hanya bila (a) ada multi-tenant, atau (b) kebocoran lintas divisi berulang setelah perbaikan kode. Bila dipasang: tabel baru wajib `GRANT` ke `vms_api`, fungsi baru wajib `SECURITY DEFINER SET search_path` (`deploy/README.md`, bagian "Peran runtime API"). Rujukan tes `api/tests/test_rls_app_role.py` yang disebut `deploy/README.md` TIDAK ADA di repo sumber; verifikasi dulu.
- Rahasia di image: `api/.env` berisi kunci (F-01, prioritas P0). Pastikan `.dockerignore` mengecualikan `.env`; `COPY . .` di build context `./api` memasukkan semua berkas.
- Kontainer API berjalan sebagai root, tanpa `HEALTHCHECK`, tanpa multi-stage (F-02). Face-service sudah non-root (`USER face`).
- Sisi biometrik dan data pribadi: NIK dan rekening dienkripsi AES-256-GCM di aplikasi, pencarian dengan blind index HMAC; tampilan dimask (`vms-next/docs/06`). Di VMS lama, belum ada enkripsi kolom (sumber: ADR 0001 keputusan 10 untuk VMS Next).

## 10. Observability

- Sudah ada: log JSON dengan `request_id` (`api/app/core/logging_config.py:19`, `:22-44`, `:59-62`); `/health` (liveness tanpa DB) dan `/ready` (DB) di `api/app/main.py:56-74`; alarm Discord dari `deploy/healthcheck.sh`.
- Belum ada: `duration_ms`, `http_path`, `status`, dan `user_id` yang konsisten di log akses; metrik RED/USE; tracing (`traceparent`) (riset `01` T13, F-20).
- Target bertahap:
  1. Log akses: `request_id`, metode, rute (bukan URL penuh), status, `duration_ms`. Tanpa email, nama, NIK.
  2. Metrik RED per rute (laju, galat, durasi) bila ada kebutuhan dan anggaran memori.
  3. Tracing OpenTelemetry: ditunda; perlu ADR.
- Health endpoint: `/ready` boleh memeriksa DB; `/health` tidak boleh (riset `01` T24). Body publik minimal.
- Catatan nama header: VMS lama memakai `X-Request-ID`; web dan HP harus memakai yang sama (riset `01` T13).

## 11. Cadangan dan pemulihan (RPO, RTO)

- Cadangan DB harian `pg_dump` pukul 01:30 (prod) dan 01:45 (beta), ke MinIO `vms-backups` dan `~/deploy/*/backups` (`vms-next/docs/08`). Retensi lokal 14 hari (`deploy/README.md`).
- RPO: sampai sekitar 24 jam bila tidak ada cadangan tambahan. Angka ini turunan dari jadwal, bukan hasil uji.
- RTO: BELUM DIUKUR. Ukur dengan `deploy/uji-pulih-cadangan.sh` (tiap bulan dan setelah perubahan skema besar).
- Berkas MinIO belum ikut dicadangkan (`deploy/README.md`). Cadangan DB masih di server yang sama, kecuali salinan luar-situs (`deploy/backup-offsite.sh`) aktif.

## 12. Migrasi skema aman

- Expand -> migrate -> contract. Rilis N hanya menambah kolom NULLABLE atau tabel baru (`vms-next/docs/06`, butir 4).
- Indeks untuk tabel besar: `CREATE INDEX CONCURRENTLY` (riset `01` T26; 37 indeks lama tanpa CONCURRENTLY, berlaku untuk baseline).
- Backfill dibatch.
- Setiap migrasi punya `downgrade()` (riset `01` T23: 24 berkas). Downgrade tidak dijalankan otomatis oleh deploy.

## 13. Kapan menambah komponen (tabel keputusan)

| Kebutuhan | Pilihan minimum | Tambah komponen bila |
|---|---|---|
| Cache data baca | TanStack Query, `Cache-Control` | ada pengukuran; lebih dari satu instance |
| Rate limit | penghitung di PostgreSQL / memori per proses | lebih dari satu instance API |
| Idempotensi | tabel PostgreSQL | banyak instance dan anti-balapan terbukti |
| Pekerjaan latar | tugas dalam proses dengan timeout | beban pekerjaan melebihi kapasitas CPU satu server |
| Pemantauan | log JSON + health + alarm Discord | ada kebutuhan grafik dan anggaran memori |
| Isolasi data | pemeriksaan di kode + tes | kebocoran berulang atau multi-tenant |

## Referensi

- `references/checklist-desain.md` - daftar periksa sebelum menyetujui desain.
- `docs/PANDUAN-AGENTIK.md` bagian 4.
- `.claude/agents/architect.md`.

## Riwayat

- v0.1 - 2026-11-04 - Awal. Disusun dari sumber di repo dan folder riset (lihat docs/PANDUAN-AGENTIK.md bagian 14).
