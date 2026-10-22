# 40 — Lingkungan beta & prod, dan migrasi data V1 → Master Schema V2

## Tujuan
Tidak ada lagi server mati karena rilis. Setiap perubahan melewati **beta** yang identik dengan **prod**
(API, MinIO, face, web, DB, aplikasi HP) sebelum menyentuh prod.

```
development ──merge──▶ beta (server beta, data salinan prod) ──uji lolos──▶ prod
```

## Lingkungan di server `visiontech-bar`
| | prod | beta |
|---|---|---|
| Folder | `~/deploy/vms-mvp` | `~/deploy/vms-beta` |
| Branch dipantau `autodeploy.sh` | `prod` | `beta` |
| Kontainer | `vms_api`, `vms_web`, `vms_face` | `vms_beta_api`, `vms_beta_web`, `vms_beta_face` |
| DB | `vms_db_prod` → DB `vms_v2` | `vms_db_beta` → DB `vms_beta` |
| MinIO | `vms_minio_prod` | `vms_minio_beta` |
| Port API / web | 8000 / 8080 | 8001 / 8081 |
| Aplikasi HP | `com.visiontech.vms_mobile` "Visiontech" | `com.visiontech.vms_mobile.beta` "Visiontech Beta" |
| Kanal pembaruan APK | `rilis/android` (stable) | `rilis/android` milik beta (kanal beta) |

Satu skrip `deploy/autodeploy.sh` untuk keduanya; beda lewat `<folder>/deploy.env`
(`VMS_ENV_NAME`, `VMS_DEPLOY_BRANCH`, `VMS_CONTAINER_PREFIX`, `VMS_IMAGE_PREFIX`, `VMS_API_PORT`, `VMS_WEB_PORT`,
`VMS_DB_CONTAINER`, `VMS_PUBLIC_URL`). APK beta ditandatangani **kunci rilis yang sama** dengan prod
(`keystore/vms-release-2.jks`) tetapi paket `.beta`, jadi bisa terpasang berdampingan.

## Skema V2 di DB baru (beta, prod, CI)
`db/06_master_schema_v2.sql` → `db/08_master_v2_tambahan.sql` (idempoten) → `migration_v3` (dijalankan API saat
start & oleh `autodeploy.sh`). Rantai alembic V1 tidak dipakai lagi. Skrip: `scripts/siapkan_db_v2.sh`.

## Migrasi data produksi V1 → V2 (`scripts/migrasi_v1_ke_v2.py`)
Sumber `vms_db_prod/visiontech_db` (skema `vms`) **hanya dibaca**; tujuan DB V2 baru yang kosong; satu transaksi.
Ketetapan pemilik: 3 divisi lapangan di kantor Pekanbaru — CCTV & ACS (PM RAMADANI), Wall Display (PM HANDOKO),
OM satu orang (Ade Candra). Karyawan unit "CCTV & ACS" → CCTV, "Wall Display" → Wall Display, unit kantor lain tanpa
divisi lapangan. Kata sandi (argon2id) tetap, berkas MinIO tetap (storage key sama). Sesi tidak dipindah (login ulang).

Latihan 2026-10-22 di `vms_db_test` (salinan prod): 38 karyawan & akun, 3 divisi, 2 kantor, 54 dokumen, 140 berkas,
19 aset, 12 absensi, 12 data wajah — cocok dengan sumber.

## Urutan cutover (tanpa downtime panjang)
1. **Beta dulu:** siapkan `vms_db_beta` + MinIO beta (salin bucket prod), DB `vms_beta` dari salinan prod lewat skrip
   migrasi, jalankan stack beta, uji web & HP beta.
2. **Prod:** backup `visiontech_db` (tetap disimpan, tidak dihapus) → `siapkan_db_v2.sh vms_db_prod vms_v2 vms_app`
   → migrasi data → ubah `DATABASE_URL`/`MIGRATION_DATABASE_URL` di `api.env` ke `vms_v2` → merge `beta` → `prod`
   (autodeploy membangun & memeriksa kesehatan). **Rollback:** kembalikan `api.env` ke `visiontech_db` & deploy
   commit lama — data V1 tidak pernah diubah.
3. Build APK prod dengan versi lebih tinggi dari `1.1.0+2` agar pembaruan otomatis jalan.

## Catatan
- `SEED_DEMO_MEDIA` harus mati di beta & prod (bawaan mati).
- Peran Sutono (OPS) tetap Operational Manager tanpa divisi — konfirmasi pemilik.
