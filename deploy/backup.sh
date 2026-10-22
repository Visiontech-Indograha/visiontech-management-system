#!/usr/bin/env bash
# Backup DB VMS (R-20): pg_dump basis data yang DIPAKAI API (dibaca dari api.env, bukan POSTGRES_DB
# kontainer — keduanya berbeda di server ini) → berkas lokal → unggah ke MinIO bucket `vms-backups`.
# Retensi: 7 berkas lokal, 30 hari di MinIO. Dipanggil cron harian dan oleh autodeploy.sh.
# Pemakaian: backup.sh [label]   → mencetak nama berkas; kode keluar ≠ 0 bila gagal.
set -euo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
LABEL="${1:-harian}"
cd "$BASE"
# prod/beta (docs/40): kontainer DB & API dari deploy.env; bawaan = prod.
[ -f deploy.env ] && . ./deploy.env
DB_CONTAINER="${VMS_DB_CONTAINER:-vms_db_prod}"
API_CONTAINER="${VMS_CONTAINER_PREFIX:-vms}_api"
mkdir -p backups

# Retensi WAJIB jalan walau unggah MinIO gagal: tanpa trap, `exit 4` di bawah melewati baris ini
# dan dump menumpuk tanpa batas (insiden 2026-10-13: 12 dump @1.9 MB dalam 12 menit).
retention() { ls -1t backups/*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f || true; }
trap retention EXIT

DB=$(grep -E '^DATABASE_URL=' api.env | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
[ -n "$DB" ] || { echo "Nama DB tidak ditemukan di api.env" >&2; exit 2; }
FILE="backups/$DB-$LABEL-$(date +%Y%m%d-%H%M%S).dump"

docker exec "$DB_CONTAINER" sh -c "pg_dump -U \"\$POSTGRES_USER\" -d '$DB' -Fc" > "$FILE"
[ -s "$FILE" ] || { echo "Backup kosong: $FILE" >&2; exit 3; }

# Unggah lewat kontainer API (klien MinIO & kredensialnya sudah ada di sana).
# Kegagalan autentikasi dicetak sebagai instruksi perbaikan, bukan traceback Python: insiden
# 2026-10-13 menghabiskan berjam-jam karena hanya terlihat "InvalidAccessKeyId" tanpa petunjuk.
docker exec -i -e OBJ="$(basename "$FILE")" "$API_CONTAINER" python -c '
import io, os, sys
from datetime import datetime, timedelta, timezone

from minio import Minio
from minio.error import S3Error

from app.core.config import settings as s

data = sys.stdin.buffer.read()
host = s.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
bucket = "vms-backups"

try:
    client = Minio(host, access_key=s.MINIO_ACCESS_KEY, secret_key=s.MINIO_SECRET_KEY, secure=s.MINIO_SECURE)
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, os.environ["OBJ"], io.BytesIO(data), len(data),
                      content_type="application/octet-stream")
except S3Error as exc:
    if exc.code in ("InvalidAccessKeyId", "SignatureDoesNotMatch", "AccessDenied"):
        print(f"Kredensial MinIO DITOLAK ({exc.code}).", file=sys.stderr)
        print(f"  endpoint : {s.MINIO_ENDPOINT} (host {host})", file=sys.stderr)
        print(f"  access key yang dipakai: {s.MINIO_ACCESS_KEY!r}", file=sys.stderr)
        print("  access key ini tidak dikenal MinIO. Perbaiki api.env:", file=sys.stderr)
        print("    1. Ambil kredensial service account MinIO yang valid, mis. dari", file=sys.stderr)
        print("       /home/ageng/deploy/visiontech/.env -> S3_ACCESS_KEY / S3_SECRET_KEY", file=sys.stderr)
        print("    2. Setel MINIO_ACCESS_KEY / MINIO_SECRET_KEY di api.env", file=sys.stderr)
        print("    3. docker compose up -d --force-recreate api", file=sys.stderr)
        print("    4. Uji ulang: ./backup.sh uji", file=sys.stderr)
    else:
        print(f"Unggah MinIO gagal ({exc.code}): {exc.message}", file=sys.stderr)
    sys.exit(4)
except Exception as exc:
    print(f"Tidak bisa menghubungi MinIO di {host}: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(4)

cut = datetime.now(timezone.utc) - timedelta(days=30)
for obj in client.list_objects(bucket):
    if obj.last_modified and obj.last_modified < cut:
        client.remove_object(bucket, obj.object_name)
print("minio:", bucket + "/" + os.environ["OBJ"], len(data), "bita")
' < "$FILE" || { echo "Unggah MinIO gagal — lihat petunjuk di atas" >&2; exit 4; }

echo "$FILE"
