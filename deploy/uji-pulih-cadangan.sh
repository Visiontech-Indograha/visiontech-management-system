#!/usr/bin/env bash
# P9-5 · Uji pemulihan cadangan SUNGGUHAN ke basis data kosong, di server (data asli tidak pernah keluar server).
#
# Jalankan dari komputer pemilik (bash UCRT64, di folder repo):
#   ssh ageng@192.168.88.160 "bash -s" < deploy/uji-pulih-cadangan.sh
#
# Yang dikerjakan (prod hanya DIBACA; tidak ada yang diubah selain menambah satu cadangan):
#   1. buat cadangan baru lewat backup.sh yang sama dengan cron/autodeploy (label uji-pulih) → lokal + MinIO
#   2. unduh salinan MinIO-nya, cocokkan SHA-256 dengan berkas lokal (salinan di MinIO memang bisa dipakai)
#   3. nyalakan Postgres SEMENTARA (citra sama dengan vms_db_prod, tanpa jaringan, tanpa port, tanpa volume tetap)
#   4. pg_restore salinan MinIO ke basis data kosong; catat lamanya; galat pemulihan harus 0
#   5. bandingkan dengan prod: jumlah baris per tabel, versi alembic, tabel ber-RLS, fungsi SECURITY DEFINER
#   6. hapus kontainer sementara (juga saat gagal)
# Keluaran hanya nama tabel & angka — tidak ada isi data.
set -euo pipefail
# Variabel VMS_* hanya untuk menguji skrip ini di komputer developer terhadap DB uji (data sintetis).
BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE"
DB_CT="${VMS_DB_CT:-vms_db_prod}"
API_CT="${VMS_API_CT:-vms_api}"
TMP_CT=vms_db_uji_pulih
WORK=$(mktemp -d)
cleanup() { docker rm -f "$TMP_CT" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

DB=$(grep -E '^DATABASE_URL=' api.env | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
OWNER=$(docker exec "$DB_CT" printenv POSTGRES_USER || echo postgres)
IMAGE=$(docker inspect -f '{{.Config.Image}}' "$DB_CT")
psql_prod() { docker exec -i "$DB_CT" psql -v ON_ERROR_STOP=1 -qAtX -U "$OWNER" -d "$DB"; }
psql_tmp() { docker exec -i "$TMP_CT" psql -v ON_ERROR_STOP=1 -qAtX -U "$OWNER" -d "$DB"; }

echo "== 1/6 cadangan baru (backup.sh, sama dengan cron)"
FILE=$(./backup.sh uji-pulih | tail -1)
[ -s "$FILE" ] || { echo "GAGAL: berkas cadangan tidak ada"; exit 1; }
LOCAL_SHA=$(sha256sum "$FILE" | cut -d' ' -f1)
echo "   $FILE ($(du -h "$FILE" | cut -f1))"

echo "== 2/6 unduh salinan MinIO & cocokkan SHA-256"
if [ "${VMS_SKIP_MINIO:-0}" = 1 ]; then cp "$FILE" "$WORK/minio.dump"; else  # hanya uji lokal
docker exec -e OBJ="$(basename "$FILE")" "$API_CT" python -c '
import os, sys
from minio import Minio
from app.core.config import settings as s
host = s.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
c = Minio(host, access_key=s.MINIO_ACCESS_KEY, secret_key=s.MINIO_SECRET_KEY, secure=s.MINIO_SECURE)
r = c.get_object("vms-backups", os.environ["OBJ"])
sys.stdout.buffer.write(r.read()); r.close(); r.release_conn()
' > "$WORK/minio.dump"
fi
MINIO_SHA=$(sha256sum "$WORK/minio.dump" | cut -d' ' -f1)
[ "$MINIO_SHA" = "$LOCAL_SHA" ] || { echo "GAGAL: salinan MinIO berbeda dari berkas lokal"; exit 1; }
echo "   cocok ($LOCAL_SHA)"

echo "== 3/6 Postgres sementara ($IMAGE, tanpa jaringan)"
TMP_PW=$(openssl rand -hex 16)   # sandi kontainer sementara; tidak pernah dicetak
docker run -d --name "$TMP_CT" --network none -e POSTGRES_USER="$OWNER" -e POSTGRES_PASSWORD="$TMP_PW" "$IMAGE" >/dev/null
# Selama inisialisasi citra resmi menyalakan server sementara (hanya soket), lalu menyalakan ulang. TCP lokal baru
# menerima koneksi setelah server sungguhan siap — itu yang ditunggu (maks. 180 detik).
READY=0
for _ in $(seq 1 180); do
  if docker exec -e PGPASSWORD="$TMP_PW" "$TMP_CT" psql -h 127.0.0.1 -U "$OWNER" -d postgres -qAtXc 'SELECT 1' >/dev/null 2>&1; then
    READY=1; break
  fi
  [ "$(docker inspect -f '{{.State.Running}}' "$TMP_CT" 2>/dev/null)" = true ] || break
  sleep 1
done
if [ "$READY" != 1 ]; then
  echo "GAGAL: Postgres sementara tidak siap. Log terakhir:"
  docker logs --tail 15 "$TMP_CT" 2>&1 | cut -c1-200 | sed 's/^/   /'
  exit 1
fi
docker exec "$TMP_CT" createdb -U "$OWNER" "$DB"
# Peran yang disebut GRANT di cadangan; tanpa sandi & tanpa login (peran berlaku per klaster, tidak ikut pg_dump).
for r in $(echo "SELECT rolname FROM pg_roles WHERE rolname LIKE 'vms\_%' AND rolname <> '$OWNER';" | psql_prod); do
  echo "CREATE ROLE $r NOLOGIN;" | docker exec -i "$TMP_CT" psql -qAtX -U "$OWNER" -d postgres >/dev/null
done
echo "   siap"

echo "== 4/6 pg_restore salinan MinIO ke basis data kosong"
START=$(date +%s)
set +e
docker exec -i "$TMP_CT" pg_restore -U "$OWNER" -d "$DB" < "$WORK/minio.dump" 2> "$WORK/restore.err"
RC=$?
set -e
DUR=$(( $(date +%s) - START ))
ERRS=$(grep -c '^pg_restore: error' "$WORK/restore.err" || true)
echo "   selesai dalam ${DUR} detik, kode $RC, galat $ERRS"
if [ "$ERRS" != 0 ]; then
  grep '^pg_restore: error' "$WORK/restore.err" | cut -c1-200 | head -10
  echo "GAGAL: pemulihan bergalat"
  exit 1
fi

echo "== 5/6 bandingkan dengan prod"
COUNT_SQL="SELECT string_agg(format('SELECT %L, count(*) FROM vms.%I', c.relname, c.relname), ' UNION ALL ' ORDER BY c.relname)
             FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'vms' AND c.relkind IN ('r', 'p') AND NOT c.relispartition;"
Q=$(echo "$COUNT_SQL" | psql_prod)
echo "$Q;" | psql_prod | sort > "$WORK/prod.txt"
echo "$Q;" | psql_tmp | sort > "$WORK/pulih.txt"
AV=$(echo "SELECT quote_ident(n.nspname) || '.alembic_version' FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'alembic_version' ORDER BY n.nspname <> 'vms' LIMIT 1;" | psql_prod)
ALEMBIC_SQL="SELECT 'alembic', 'tidak ada'"
[ -n "$AV" ] && ALEMBIC_SQL="SELECT 'alembic', version_num FROM $AV"
META="$ALEMBIC_SQL
      UNION ALL SELECT 'tabel_rls', count(*)::text FROM pg_class WHERE relnamespace = 'vms'::regnamespace AND relrowsecurity
      UNION ALL SELECT 'fungsi_definer', count(*)::text FROM pg_proc WHERE pronamespace = 'vms'::regnamespace AND prosecdef
      UNION ALL SELECT 'partisi', count(*)::text FROM pg_class WHERE relnamespace = 'vms'::regnamespace AND relispartition;"
echo "$META" | psql_prod > "$WORK/prod.meta"
echo "$META" | psql_tmp > "$WORK/pulih.meta"
TABLES=$(wc -l < "$WORK/prod.txt")
ROWS=$(awk -F'|' '{s+=$2} END {print s}' "$WORK/pulih.txt")
echo "   $TABLES tabel, $ROWS baris dipulihkan"
paste -d'|' "$WORK/prod.meta" "$WORK/pulih.meta" | awk -F'|' '{printf "   %-15s prod=%s pulih=%s %s\n", $1, $2, $4, ($2==$4?"ok":"BEDA")}'
DIFF=$(join -t'|' "$WORK/prod.txt" "$WORK/pulih.txt" | awk -F'|' '$2 != $3 {printf "   %s: prod=%s pulih=%s\n", $1, $2, $3}')
META_DIFF=$(diff -q "$WORK/prod.meta" "$WORK/pulih.meta" >/dev/null || echo beda)
if [ -n "$DIFF" ]; then
  echo "   tabel yang berbeda (wajar bila ada tulisan baru selama uji; ulangi saat sepi bila banyak):"
  echo "$DIFF"
fi

echo "== 6/6 bersihkan kontainer sementara"
cleanup
trap - EXIT
echo "   dihapus"
if [ -n "$META_DIFF" ]; then
  echo "GAGAL: skema/versi hasil pulih berbeda dari prod"
  exit 1
fi
echo "SELESAI. Cadangan $FILE pulih ke basis data kosong dalam ${DUR} detik (salinan MinIO, SHA-256 cocok)."
