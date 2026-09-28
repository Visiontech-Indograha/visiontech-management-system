#!/usr/bin/env bash
# Backup DB VMS (R-20): pg_dump basis data yang DIPAKAI API (dibaca dari api.env, bukan POSTGRES_DB
# kontainer — keduanya berbeda di server ini) → berkas lokal → unggah ke MinIO bucket `vms-backups`.
# Retensi: 7 berkas lokal, 30 hari di MinIO. Dipanggil cron harian dan oleh autodeploy.sh.
# Pemakaian: backup.sh [label]   → mencetak nama berkas; kode keluar ≠ 0 bila gagal.
set -euo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
LABEL="${1:-harian}"
cd "$BASE"
mkdir -p backups

DB=$(grep -E '^DATABASE_URL=' api.env | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
[ -n "$DB" ] || { echo "Nama DB tidak ditemukan di api.env" >&2; exit 2; }
FILE="backups/$DB-$LABEL-$(date +%Y%m%d-%H%M%S).dump"

docker exec vms_db_prod sh -c "pg_dump -U \"\$POSTGRES_USER\" -d '$DB' -Fc" > "$FILE"
[ -s "$FILE" ] || { echo "Backup kosong: $FILE" >&2; exit 3; }

# Unggah lewat kontainer API (klien MinIO & kredensialnya sudah ada di sana).
docker exec -i -e OBJ="$(basename "$FILE")" vms_api python -c '
import io, os, sys
from datetime import datetime, timedelta, timezone
from minio import Minio
from app.core.config import settings as s
data = sys.stdin.buffer.read()
host = s.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
c = Minio(host, access_key=s.MINIO_ACCESS_KEY, secret_key=s.MINIO_SECRET_KEY, secure=s.MINIO_SECURE)
b = "vms-backups"
if not c.bucket_exists(b):
    c.make_bucket(b)
c.put_object(b, os.environ["OBJ"], io.BytesIO(data), len(data), content_type="application/octet-stream")
cut = datetime.now(timezone.utc) - timedelta(days=30)
for o in c.list_objects(b):
    if o.last_modified and o.last_modified < cut:
        c.remove_object(b, o.object_name)
print("minio:", b + "/" + os.environ["OBJ"], len(data), "bita")
' < "$FILE" || { echo "Unggah MinIO gagal" >&2; exit 4; }

ls -1t backups/*.dump | tail -n +8 | xargs -r rm -f
echo "$FILE"
