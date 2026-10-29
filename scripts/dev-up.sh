#!/usr/bin/env bash
# Siapkan lingkungan DEV penuh di PC sendiri (tanpa bergantung pada server): DB + MinIO lokal, skema, migrasi, .env.
#   bash scripts/dev-up.sh            # sekali jalan; aman diulang (tidak menimpa data/.env yang ada)
#   bash scripts/dev-up.sh --wajah    # sekaligus catat cara menyalakan face-service lokal (opsional)
# Lalu: bash scripts/api-lokal.sh  ·  cd web && npm run dev
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"
DOCKER=${DOCKER:-docker}; command -v "$DOCKER" >/dev/null || DOCKER="/c/Users/ageng/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
PY="api/.venv/Scripts/python.exe"; [ -x "$PY" ] || PY="api/.venv/bin/python"

echo "== Kontainer dev (DB, DB uji, MinIO)"
for svc in vms-dev-db vms-test-db; do      # kontainer lama (dibuat tangan/proyek lain) dinyalakan apa adanya, tidak dibuat ulang
  if "$DOCKER" container inspect "$svc" >/dev/null 2>&1; then "$DOCKER" start "$svc" >/dev/null; else "$DOCKER" compose -f docker-compose.dev-db.yml up -d "$svc"; fi
done
"$DOCKER" compose -f docker-compose.dev-db.yml up -d vms-dev-minio
for i in $(seq 1 30); do
  "$DOCKER" exec vms-dev-db pg_isready -U postgres -d vms_dev >/dev/null 2>&1 && break; sleep 1
done

echo "== Skema (hanya bila DB masih kosong)"
n=$("$DOCKER" exec vms-dev-db psql -U postgres -d vms_dev -Atc "select count(*) from pg_tables where schemaname='public'")
if [ "${n:-0}" = "0" ]; then
  for f in 06_master_schema_v2 07_master_seed_v2 08_master_v2_tambahan; do
    "$DOCKER" exec -i vms-dev-db psql -U postgres -d vms_dev -v ON_ERROR_STOP=1 -q < "db/$f.sql"
  done
  echo "skema dipasang"
else echo "skema sudah ada ($n tabel), dilewati"; fi

echo "== api/.env"
if [ ! -f api/.env ]; then
  cp api/.env.example api/.env
  k1=$(openssl rand -hex 32); k2=$(openssl rand -hex 32)
  sed -i "s|^JWT_PRIVATE_KEY_HEX=.*|JWT_PRIVATE_KEY_HEX=$k1|;s|^DOC_SIGNING_KEY_HEX=.*|DOC_SIGNING_KEY_HEX=$k2|" api/.env
  echo "api/.env dibuat (kunci acak khusus dev)"
else echo "api/.env sudah ada, dibiarkan"; fi

echo "== Migrasi Alembic"
(cd api && "${PY#api/}" -m alembic -c alembic.ini upgrade head 2>&1 | tail -n 2)

echo "== Selesai"
echo "  API   : bash scripts/api-lokal.sh   (http://127.0.0.1:8010)"
echo "  Web   : cd web && npm run dev"
echo "  MinIO : http://127.0.0.1:19001  (vmsdev / vmsdev-secret)"
echo "  Seed akun uji (opsional): cd api && ${PY#api/} ../scripts/seed_uji_lokal.py --ya-hapus-semua"
if [ "${1:-}" = "--wajah" ]; then
  echo "  Wajah : jalankan face-service lokal (lihat face-service/README.md), set FACE_SERVICE_TOKEN di api/.env, lalu"
  echo "          ubah FACE_ENROLLMENT_REQUIRED=true bila ingin mewajibkan pendaftaran wajah."
fi
