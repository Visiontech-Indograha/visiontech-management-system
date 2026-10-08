#!/usr/bin/env bash
# Mengalihkan koneksi API produksi ke peran runtime `vms_api` agar RLS benar-benar berlaku (P9-2, Alembic 0024).
# Temuan 2026-10-08: API tersambung sebagai `vms_app` = superuser + pemilik tabel, sehingga RLS terlewati.
#
# Jalankan dari komputer pemilik SETELAH rilis yang memuat migrasi 0024_runtime_role ter-deploy (peran sudah ada):
#   ssh ageng@192.168.88.160 "bash -s" < deploy/pakai-peran-runtime.sh             # pakai vms_api
#   ssh ageng@192.168.88.160 "bash -s -- kembalikan" < deploy/pakai-peran-runtime.sh # rollback ke URL lama
#
# Yang dikerjakan (mode pakai):
#   1. periksa: api.env ada, peran vms_api ada & bukan superuser, alembic di 0024 atau lebih baru
#   2. salin api.env → api.env.sebelum-vms_api.<waktu> (chmod 600) — bahan rollback
#   3. sandi acak baru untuk vms_api (dibuat & dipakai di server, TIDAK pernah dicetak)
#   4. api.env: MIGRATION_DATABASE_URL = URL lama (pemilik, untuk alembic), DATABASE_URL = URL yang sama dengan vms_api
#   5. buat ulang kontainer api; /ready harus 200 dan API harus tersambung sebagai vms_api — gagal → rollback otomatis
set -euo pipefail
BASE="$HOME/deploy/vms-mvp"
cd "$BASE"
MODE="${1:-pakai}"
ENV_FILE=api.env

recreate_and_wait() {
  docker compose up -d --force-recreate api >/dev/null
  for _ in $(seq 1 24); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)" = 200 ] && return 0
    sleep 5
  done
  return 1
}

restore_latest() {
  local backup
  backup=$(ls -1t api.env.sebelum-vms_api.* 2>/dev/null | head -1 || true)
  [ -n "$backup" ] || { echo "GAGAL: tidak ada salinan api.env.sebelum-vms_api.*"; exit 1; }
  cp -p "$backup" "$ENV_FILE"
  echo "   api.env dikembalikan dari $backup"
  recreate_and_wait && echo "   api /ready: $(curl -s localhost:8000/ready)" || echo "PERINGATAN: /ready belum 200"
}

if [ "$MODE" = kembalikan ]; then
  echo "== rollback: kembali ke koneksi sebelum vms_api"
  restore_latest
  exit 0
fi

echo "== 1/5 pemeriksaan"
[ -f "$ENV_FILE" ] || { echo "GAGAL: $BASE/$ENV_FILE tidak ada"; exit 1; }
OLD_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)
[ -n "$OLD_URL" ] || { echo "GAGAL: DATABASE_URL tidak ada di api.env"; exit 1; }
DB_NAME=$(printf '%s' "$OLD_URL" | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
case "$OLD_URL" in
  *://vms_api:*) echo "   API sudah memakai vms_api — tidak ada yang diubah"; exit 0 ;;
esac
psql_owner() { docker exec -i vms_db_prod sh -c "psql -v ON_ERROR_STOP=1 -qAt -U \"\$POSTGRES_USER\" -d '$DB_NAME'"; }
ROLE=$(echo "SELECT rolsuper::text || ' ' || rolbypassrls::text FROM pg_roles WHERE rolname = 'vms_api';" | psql_owner)
[ "$ROLE" = "false false" ] || { echo "GAGAL: peran vms_api belum ada / tidak aman ($ROLE) — deploy rilis berisi 0024 dulu"; exit 1; }
REV=$(docker exec vms_api alembic current 2>/dev/null | tail -1)
case "$REV" in
  0024_runtime_role*|0025*|0026*|0027*|0028*|0029*|003*) echo "   alembic: $REV" ;;
  *) echo "GAGAL: alembic belum di 0024 ($REV)"; exit 1 ;;
esac
echo "   peran vms_api siap (bukan superuser, tanpa BYPASSRLS)"

echo "== 2/5 salinan api.env"
BACKUP="api.env.sebelum-vms_api.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$BACKUP" && chmod 600 "$BACKUP"
echo "   $BACKUP"

echo "== 3/5 sandi baru vms_api (tidak dicetak)"
PW=$(openssl rand -hex 24)
printf "ALTER ROLE vms_api WITH LOGIN PASSWORD '%s';\n" "$PW" | psql_owner
echo "   disetel"

echo "== 4/5 api.env"
OLD_URL="$OLD_URL" PW="$PW" python3 - "$ENV_FILE" <<'PY'
import os, re, sys
path = sys.argv[1]
old, pw = os.environ["OLD_URL"], os.environ["PW"]
new = re.sub(r"://[^:@/]+:[^@]*@", f"://vms_api:{pw}@", old, count=1)
assert new != old, "format DATABASE_URL tidak dikenali"
lines = [l for l in open(path, encoding="utf-8").read().splitlines() if not l.startswith("MIGRATION_DATABASE_URL=")]
lines = [f"DATABASE_URL={new}" if l.startswith("DATABASE_URL=") else l for l in lines]
lines.append(f"MIGRATION_DATABASE_URL={old}")
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
unset PW
chmod 600 "$ENV_FILE"
echo "   DATABASE_URL → vms_api; MIGRATION_DATABASE_URL → pemilik (alembic)"

echo "== 5/5 buat ulang api dan periksa"
if ! recreate_and_wait; then
  echo "GAGAL: /ready tidak 200 — rollback otomatis"
  restore_latest
  exit 1
fi
WHO=$(docker exec vms_api python -c "
import asyncio, asyncpg
from app.core.config import settings
async def m():
    c = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''))
    r = await c.fetchrow('SELECT current_user AS u, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user')
    print(r['u'], r['rolsuper'], r['rolbypassrls'])
    await c.close()
asyncio.run(m())")
if [ "$WHO" != "vms_api False False" ]; then
  echo "GAGAL: API tersambung sebagai '$WHO' — rollback otomatis"
  restore_latest
  exit 1
fi
echo "   api /ready: $(curl -s localhost:8000/ready)"
echo "   API tersambung sebagai vms_api (RLS berlaku)"
echo "SELESAI. Uji login web & HP, absen, buka SK. Ada masalah → jalankan mode 'kembalikan'."
