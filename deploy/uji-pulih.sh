#!/usr/bin/env bash
# Uji pulih TERISOLASI: dump DB terbaru -> Postgres sementara (tanpa jaringan/port/volume), lalu cocokkan
# hitungan berkas hasil backup-minio.sh dengan manifest terbarunya. Tidak menyentuh DB/MinIO sumber (hanya baca
# berkas cadangan). Aman di beta; di prod cukup jalankan dengan folder cadangan prod (tetap hanya membaca).
# Pemakaian: uji-pulih.sh      (kode keluar 0 = lulus)
#   VMS_DEPLOY_DIR, VMS_BACKUP_DIR, VMS_BACKUP_NAME : sama dengan backup.sh/backup-minio.sh.
#   VMS_PG_IMAGE : citra Postgres sementara (bawaan: citra kontainer ${VMS_DB_CONTAINER}).
set -euo pipefail
BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE"
[ -f deploy.env ] && . ./deploy.env
BKDIR="${VMS_BACKUP_DIR:-backups}"
BKNAME="${VMS_BACKUP_NAME:-}"
DB_CT="${VMS_DB_CONTAINER:-vms_db_prod}"
TMP_CT="vms_uji_pulih_$$"
cleanup() { docker rm -f "$TMP_CT" >/dev/null 2>&1 || true; }
trap cleanup EXIT
GAGAL=0

if [ -n "$BKNAME" ]; then DUMP=$(ls -1t "$BKDIR/$BKNAME"-*.dump 2>/dev/null | head -n 1 || true); else DUMP=$(ls -1t "$BKDIR"/*.dump 2>/dev/null | head -n 1 || true); fi
[ -n "$DUMP" ] && [ -s "$DUMP" ] || { echo "GAGAL: tidak ada dump di $BKDIR" >&2; exit 1; }
echo "dump: $DUMP"
IMAGE="${VMS_PG_IMAGE:-$(docker inspect -f '{{.Config.Image}}' "$DB_CT")}"
docker run -d --name "$TMP_CT" --network none --memory 512m -e POSTGRES_PASSWORD=uji "$IMAGE" >/dev/null
for _ in $(seq 1 30); do docker exec "$TMP_CT" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
docker exec "$TMP_CT" createdb -U postgres uji
if docker exec -i "$TMP_CT" pg_restore -U postgres -d uji --no-owner --no-privileges --exit-on-error < "$DUMP" 2>/tmp/uji-pulih.err; then
  echo "LULUS pg_restore tanpa galat"
else
  echo "GAGAL pg_restore (lihat /tmp/uji-pulih.err)"; GAGAL=1
fi
TABEL=$(docker exec "$TMP_CT" psql -U postgres -d uji -qAtX -c "select count(*) from information_schema.tables where table_schema='public'")
echo "tabel publik terpulih: $TABEL"
[ "${TABEL:-0}" -gt 0 ] || { echo "GAGAL: tidak ada tabel"; GAGAL=1; }
docker exec "$TMP_CT" psql -U postgres -d uji -qAtX -c "select relname||' '||n_live_tup from pg_stat_user_tables order by n_live_tup desc limit 10" || true

# Berkas: bandingkan hitungan objek di salinan dengan manifest terbaru.
MAN=$(ls -1t "$BKDIR/${BKNAME:-prod}"-berkas-*.manifest 2>/dev/null | head -n 1 || true)
if [ -n "$MAN" ]; then
  DEST="$BKDIR/${BKNAME:-prod}-berkas"
  while read -r b objek _; do
    want=${objek#objek=}; have=$(find "$DEST/$b" -type f 2>/dev/null | wc -l | tr -d ' ')
    # Salinan boleh >= manifest (objek baru sesudahnya); kurang = hilang.
    if [ "$have" -ge "$want" ]; then echo "LULUS $b: $have objek (manifest $want)"; else echo "GAGAL $b: $have < $want"; GAGAL=1; fi
  done < "$MAN"
else
  echo "PERINGATAN: manifest berkas tidak ada (jalankan backup-minio.sh dulu)"; GAGAL=1
fi
[ "$GAGAL" = 0 ] && echo "UJI PULIH LULUS" || { echo "UJI PULIH GAGAL"; exit 1; }
