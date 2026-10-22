#!/usr/bin/env bash
# Pasang lingkungan BETA (docs/40) di server — kembar prod, data & jaringan terpisah. PROD HANYA DIBACA.
#
#   ./pasang-beta.sh siapkan   # folder, kredensial baru, DB & MinIO beta, env aplikasi, cron, Tailscale
#   ./pasang-beta.sh data      # (setelah deploy beta pertama) salin data prod V1 → DB beta V2, lalu berkas
#   ./pasang-beta.sh berkas    # hanya salin ulang berkas MinIO prod → beta
#
# Aman diulang: berkas rahasia yang sudah ada tidak ditimpa; DB beta tidak diisi ulang bila sudah berisi.
set -euo pipefail

PROD="${VMS_PROD_DIR:-$HOME/deploy/vms-mvp}"
BETA="${VMS_BETA_DIR:-$HOME/deploy/vms-beta}"
REPO="${VMS_DEPLOY_REPO:-git@github-vms:Visiontech-Indograha/visiontech-management-system.git}"
BETA_URL="${VMS_BETA_URL:-https://visiontech-bar.tail827174.ts.net:10000}"
rand() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
val() { grep -E "^$1=" "$2" | head -1 | cut -d= -f2-; }

siapkan() {
  mkdir -p "$BETA"/{backups,logs,rilis/android,keystore}
  cd "$BETA"
  [ -d src/.git ] || git clone -q --branch beta "$REPO" src
  git -C src fetch -q origin beta && git -C src checkout -q --force origin/beta
  cp src/deploy/beta/compose.yml compose.yml
  cp src/deploy/beta/compose.infra.yml compose.infra.yml

  if [ ! -f infra.env ]; then
    umask 077
    cat > infra.env <<EOF
POSTGRES_USER=vms_app
POSTGRES_PASSWORD=$(rand 24)
POSTGRES_DB=vms_beta
MINIO_ROOT_USER=vmsbeta
MINIO_ROOT_PASSWORD=$(rand 24)
EOF
    echo "infra.env dibuat (kredensial baru, beda dari prod)"
  fi
  docker compose -f compose.infra.yml up -d
  for _ in $(seq 60); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' vms_db_beta 2>/dev/null)" = healthy ] && break; sleep 2
  done

  # Skema V2 di DB beta (sekali; DB dibuat oleh POSTGRES_DB saat kontainer pertama kali jalan).
  if ! docker exec vms_db_beta psql -U vms_app -d vms_beta -Atc "select 1 from pg_tables where tablename='employee'" | grep -q 1; then
    for f in 06_master_schema_v2.sql 08_master_v2_tambahan.sql; do
      docker exec -i vms_db_beta psql -U vms_app -d vms_beta -q -v ON_ERROR_STOP=1 < "src/db/$f"
      echo "skema beta: $f"
    done
  fi

  local pg_pw minio_user minio_pw face_token
  pg_pw=$(val POSTGRES_PASSWORD infra.env); minio_user=$(val MINIO_ROOT_USER infra.env)
  minio_pw=$(val MINIO_ROOT_PASSWORD infra.env)
  if [ ! -f api.env ]; then
    umask 077
    face_token=$(rand 32)
    # Template = api.env prod (pengaturan sama), lalu semua koneksi & rahasia diganti milik beta.
    grep -vE "^(DATABASE_URL|MIGRATION_DATABASE_URL|MINIO_ENDPOINT|MINIO_ACCESS_KEY|MINIO_SECRET_KEY|MINIO_PUBLIC_URL|PUBLIC_VERIFY_URL|JWT_PRIVATE_KEY_HEX|JWT_KID|FACE_SERVICE_URL|FACE_SERVICE_TOKEN)=" "$PROD/api.env" > api.env
    cat >> api.env <<EOF
DATABASE_URL=postgresql+asyncpg://vms_app:${pg_pw}@db:5432/vms_beta
MIGRATION_DATABASE_URL=postgresql+asyncpg://vms_app:${pg_pw}@db:5432/vms_beta
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=${minio_user}
MINIO_SECRET_KEY=${minio_pw}
MINIO_PUBLIC_URL=${BETA_URL}
PUBLIC_VERIFY_URL=${BETA_URL}/verify
JWT_PRIVATE_KEY_HEX=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_KID=jwt-beta-1
FACE_SERVICE_URL=http://face:8001
FACE_SERVICE_TOKEN=${face_token}
EOF
    sed -E "s/^FACE_SERVICE_TOKEN=.*/FACE_SERVICE_TOKEN=${face_token}/" "$PROD/face.env" > face.env
    echo "api.env & face.env beta dibuat"
  fi
  [ -f notify.env ] || cp "$PROD/notify.env" notify.env           # webhook Discord sama; judul ditandai [beta]
  [ -f keystore/key.properties ] || cp -a "$PROD/keystore/." keystore/   # kunci tanda tangan APK sama dengan prod
  cat > deploy.env <<EOF
VMS_ENV_NAME=beta
VMS_DEPLOY_BRANCH=beta
VMS_CONTAINER_PREFIX=vms_beta
VMS_IMAGE_PREFIX=vms-beta
VMS_API_PORT=8001
VMS_WEB_PORT=8081
VMS_DB_CONTAINER=vms_db_beta
VMS_PUBLIC_URL=${BETA_URL}
EOF
  cp src/deploy/autodeploy.sh src/deploy/backup.sh .
  chmod +x autodeploy.sh backup.sh

  # Akses: web beta khusus tailnet (:8444), API beta publik untuk HP (Funnel :10000). Prod tidak diubah.
  sudo -n tailscale serve --bg --https=8444 http://127.0.0.1:8081 >/dev/null 2>&1 \
    || tailscale serve --bg --https=8444 http://127.0.0.1:8081 || echo "PERHATIAN: atur tailscale serve 8444 manual"
  sudo -n tailscale funnel --bg --https=10000 http://127.0.0.1:8001 >/dev/null 2>&1 \
    || tailscale funnel --bg --https=10000 http://127.0.0.1:8001 || echo "PERHATIAN: atur tailscale funnel 10000 manual"

  local line="* * * * * VMS_DEPLOY_DIR=$BETA $BETA/autodeploy.sh >> $BETA/logs/cron.log 2>&1"
  ( crontab -l 2>/dev/null | grep -vF "$BETA/autodeploy.sh"; echo "$line"
    echo "45 1 * * * VMS_DEPLOY_DIR=$BETA $BETA/backup.sh harian >> $BETA/logs/backup.log 2>&1" ) | sort -u | crontab -
  echo "beta siap: push ke branch 'beta' → autodeploy beta (cron). Lalu jalankan: $0 data"
}

data() {
  cd "$BETA"
  local prod_db_name beta_pw
  prod_db_name=$(val DATABASE_URL "$PROD/api.env" | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
  beta_pw=$(val POSTGRES_PASSWORD infra.env)
  # 1) Dump prod (pg_dump = hanya membaca, lewat soket kontainer) → DB sementara `sumber_v1` di kontainer BETA.
  #    Superuser beta melewati RLS V1, jadi semua baris terbaca tanpa memakai kredensial prod.
  docker exec vms_db_beta psql -U vms_app -d postgres -q -c "DROP DATABASE IF EXISTS sumber_v1" -c "CREATE DATABASE sumber_v1"
  docker exec vms_db_prod sh -c "pg_dump -U \"\$POSTGRES_USER\" -d '$prod_db_name' -Fc" \
    | docker exec -i vms_db_beta pg_restore -U vms_app -d sumber_v1 --no-owner --no-acl
  # 2) sumber_v1 (V1) → vms_beta (V2); skrip menolak bila beta sudah berisi karyawan.
  docker run --rm --network host -v "$BETA/src/scripts:/s:ro" \
    -e SUMBER_DSN="postgresql://vms_app:${beta_pw}@127.0.0.1:5435/sumber_v1" \
    -e TUJUAN_DSN="postgresql://vms_app:${beta_pw}@127.0.0.1:5435/vms_beta" \
    vms-beta-api python /s/migrasi_v1_ke_v2.py
  docker exec vms_db_beta psql -U vms_app -d postgres -q -c "DROP DATABASE sumber_v1"
  berkas
}

berkas() {
  cd "$BETA"
  local prod_minio_key prod_minio_secret minio_user minio_pw
  # 3) Berkas prod → MinIO beta (salinan; prod hanya dibaca).
  prod_minio_key=$(val MINIO_ACCESS_KEY "$PROD/api.env"); prod_minio_secret=$(val MINIO_SECRET_KEY "$PROD/api.env")
  minio_user=$(val MINIO_ROOT_USER infra.env); minio_pw=$(val MINIO_ROOT_PASSWORD infra.env)
  # Klien MinIO Python dari image API beta (image `mc` resmi kini butuh login registri).
  docker run --rm --network host -e PK="$prod_minio_key" -e PS="$prod_minio_secret" -e BK="$minio_user" \
    -e BS="$minio_pw" --entrypoint python vms-beta-api -c '
import io, os
from minio import Minio
prod = Minio("127.0.0.1:9000", access_key=os.environ["PK"], secret_key=os.environ["PS"], secure=False)
beta = Minio("127.0.0.1:9002", access_key=os.environ["BK"], secret_key=os.environ["BS"], secure=False)
for bucket in ("vms-files", "vms-bucket"):
    if not beta.bucket_exists(bucket):
        beta.make_bucket(bucket)
    n = 0
    for obj in prod.list_objects(bucket, recursive=True):
        resp = prod.get_object(bucket, obj.object_name)
        try:
            data = resp.read()
        finally:
            resp.close(); resp.release_conn()
        beta.put_object(bucket, obj.object_name, io.BytesIO(data), len(data),
                        content_type=obj.content_type or "application/octet-stream")
        n += 1
    print(f"{bucket}: {n} berkas disalin")
'
  docker restart vms_beta_api >/dev/null
  echo "berkas beta selesai (salinan MinIO prod saat ini)"
}

case "${1:-}" in
  siapkan) siapkan ;;
  data) data ;;
  berkas) berkas ;;
  *) echo "pakai: $0 siapkan | data" >&2; exit 2 ;;
esac
