# Skema basis data VMS

PostgreSQL 18 + PostGIS 3.6 + pgvector (citra dibangun dari `db/Dockerfile`, sama untuk compose, CI, dan produksi).
Perubahan skema berikutnya lewat Alembic V2 (`api/alembic_v2/`), bukan mengubah berkas di sini.

| Berkas | Isi |
|---|---|
| `06_master_schema_v2.sql` | Skema dasar V2: tabel, enum, indeks, partisi log bulanan, soft delete |
| `07_master_seed_v2.sql` | Data uji realistis (hanya dev/uji, jangan di produksi) |
| `08_master_v2_tambahan.sql` | Tambahan master data (klien, proyek, jabatan, cuti, biaya). Idempoten |

Urutan pasang: `06` → `08` → `alembic_v2 upgrade head`. `07` opsional untuk data uji.
