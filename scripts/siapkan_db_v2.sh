#!/usr/bin/env bash
# Siapkan basis data Master Schema V2 BARU di kontainer PostgreSQL (docs/40): buat DB → db/06 → db/08.
# Migrasi perubahan aplikasi dikelola Alembic dan dijalankan saat deploy.
#
#   scripts/siapkan_db_v2.sh <kontainer_db> <nama_db_baru> <pemilik>
#   contoh latihan : scripts/siapkan_db_v2.sh vms_db_test latih_v2 vms_app
#   contoh beta    : scripts/siapkan_db_v2.sh vms_db_beta vms_beta vms_app
#
# Menolak bila DB sudah ada (tidak pernah menimpa data). Dijalankan di server (butuh docker).
set -euo pipefail
CONTAINER="${1:?kontainer db}"; DB="${2:?nama db}"; OWNER="${3:?pemilik}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ADMIN_USER="$(docker exec "$CONTAINER" sh -c 'echo $POSTGRES_USER')"

if docker exec "$CONTAINER" psql -U "$ADMIN_USER" -d postgres -Atc "select 1 from pg_database where datname='$DB'" | grep -q 1; then
  echo "DB '$DB' sudah ada di $CONTAINER — dibatalkan (hapus manual bila memang ingin mengulang)." >&2
  exit 2
fi
docker exec "$CONTAINER" psql -U "$ADMIN_USER" -d postgres -q -c "CREATE DATABASE \"$DB\" OWNER \"$OWNER\""
for f in 06_master_schema_v2.sql 08_master_v2_tambahan.sql; do
  docker exec -i "$CONTAINER" psql -U "$OWNER" -d "$DB" -q -v ON_ERROR_STOP=1 < "$HERE/db/$f"
  echo "terpasang: $f"
done
echo "DB '$DB' siap; Alembic V2 akan memvalidasi baseline dan menerapkan pembaruan saat deploy."
