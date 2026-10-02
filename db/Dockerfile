# Basis data VMS: PostgreSQL 18 + PostGIS 3.6 + pgvector.
#
# Citra ini dipakai docker-compose.yml DAN CI (.github/workflows/ci.yml) supaya
# lingkungan pengembangan, CI, dan produksi benar-benar sama. Sebelumnya compose
# memakai postgis/postgis:16-3.4 tanpa pgvector, sehingga db/05_face.sql tidak
# pernah bisa dijalankan di luar CI.
#
# PostgreSQL 18 dipilih karena keputusan terkunci A-05, dan karena `uuidv7()`
# tersedia sebagai fungsi bawaan sejak PG18 — lihat migrasi new_id().
FROM postgis/postgis:18-3.6

# pgvector untuk pengenalan wajah (db/05_face.sql, embedding vector(512)).
# Paket berasal dari repositori PGDG yang sudah aktif di citra PostGIS.
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends postgresql-18-pgvector \
 && rm -rf /var/lib/apt/lists/*
