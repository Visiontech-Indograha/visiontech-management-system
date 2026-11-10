#!/usr/bin/env bash
# Perkiraan ruang disk Windows untuk cadangan, dihitung dari ukuran SUMBER (dijalankan di server Linux, hanya baca).
# Pemakaian: perkiraan-disk-cadangan.sh <nama-kontainer-db-prod> <db-prod> <kontainer-db-beta> <db-beta> <folder-mirror-prod> <folder-mirror-beta>
# Bisa juga memberi ukuran langsung (bita) lewat env: DB_PROD DB_BETA MINIO_PROD MINIO_BETA CHURN (bawaan 0.02 = 2%/hari).
set -euo pipefail
dbsize() { docker exec "$1" sh -c "psql -U \"\$POSTGRES_USER\" -d '$2' -Atc \"select pg_database_size('$2')\""; }
DB_PROD="${DB_PROD:-$( [ -n "${1:-}" ] && dbsize "$1" "$2" || echo 0)}"
DB_BETA="${DB_BETA:-$( [ -n "${3:-}" ] && dbsize "$3" "$4" || echo 0)}"
MINIO_PROD="${MINIO_PROD:-$( [ -n "${5:-}" ] && du -sb "$5" | cut -f1 || echo 0)}"
MINIO_BETA="${MINIO_BETA:-$( [ -n "${6:-}" ] && du -sb "$6" | cut -f1 || echo 0)}"
CHURN="${CHURN:-0.02}"
awk -v dp="$DB_PROD" -v db="$DB_BETA" -v mp="$MINIO_PROD" -v mb="$MINIO_BETA" -v c="$CHURN" 'BEGIN{
  g=1073741824; k=0.35  # dump -Fc ~35% dari ukuran DB (konservatif; ukur nyata setelah malam pertama)
  dbp=dp*k; dbb=db*k
  # DB: 14 harian + 8 mingguan + 12 bulanan = 34 salinan penuh (puncak)
  dbtot=(dbp+dbb)*34
  # MinIO: 5-6 set mingguan (retensi 35 hari + set berjalan): tiap set = 1 penuh + 6 inkremental (churn*ukuran)
  set_p=mp*(1+6*c); set_b=mb*(1+6*c); miniotot=(set_p+set_b)*6
  tot=(dbtot+miniotot)*1.3  # +30% cadangan ruang kerja uji pulih/VSS
  printf "DB prod=%.2f GB, DB beta=%.2f GB, MinIO prod=%.2f GB, MinIO beta=%.2f GB, churn=%.0f%%/hari\n", dp/g,db/g,mp/g,mb/g,c*100
  printf "Dump DB per salinan (prod+beta) ~ %.2f GB x 34 salinan = %.2f GB\n",(dbp+dbb)/g,dbtot/g
  printf "MinIO: 6 set x (penuh + 6 inkremental) = %.2f GB\n",miniotot/g
  printf "TOTAL disarankan (x1.3) = %.2f GB\n",tot/g
  print "Rumus: TOTAL = 1.3 x [ 34 x 0.35 x (DBprod+DBbeta) + 6 x (1+6c) x (MinIOprod+MinIObeta) ]"
}'
