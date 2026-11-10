#!/usr/bin/env bash
# Mengalihkan koneksi API ke peran runtime `vms_api` (non-superuser, NOBYPASSRLS) agar RLS kelak berlaku.
# Temuan 2026-10-08: API tersambung sebagai `vms_app` = superuser + pemilik tabel, sehingga RLS terlewati.
# Peran dibuat/diselaraskan oleh deploy/peran-runtime.sql (idempoten), BUKAN migrasi Alembic.
#
# Mode (argumen pertama), dijalankan di server dari komputer pemilik:
#   ssh ageng@192.168.88.160 "bash -s -- cek"        < deploy/pakai-peran-runtime.sh   # hanya baca, tidak mengubah
#   ssh ageng@192.168.88.160 "bash -s -- terapkan"   < deploy/pakai-peran-runtime.sh   # (nama lama: pakai)
#   ssh ageng@192.168.88.160 "bash -s -- kembalikan" < deploy/pakai-peran-runtime.sh   # rollback ke api.env lama
# Variabel env: VMS_DIR (default ~/deploy/vms-mvp), VMS_DB_CONTAINER (default vms_db_prod),
#               VMS_API_CONTAINER (default vms_api), VMS_PORT (default 8000), VMS_OWNERS (default "vms_migrator,vms_app").
#
# terapkan: (1) periksa api.env & DB (2) salin api.env -> api.env.sebelum-vms_api.<waktu> (chmod 600)
#   (3) jalankan peran-runtime.sql dengan sandi acak (dibuat & dipakai di server, TIDAK pernah dicetak)
#   (4) api.env: MIGRATION_DATABASE_URL = URL lama (pemilik), DATABASE_URL = URL yang sama dengan vms_api
#   (5) buat ulang kontainer api; /ready harus 200 dan API tersambung sebagai vms_api, jika tidak rollback otomatis.
# Cadangan DB WAJIB dibuat pemilik sebelum `terapkan` (deploy/backup.sh); lihat deploy/PERAN-RUNTIME.md.
set -euo pipefail
BASE="${VMS_DIR:-$HOME/deploy/vms-mvp}"
DB_CTR="${VMS_DB_CONTAINER:-vms_db_prod}"
API_CTR="${VMS_API_CONTAINER:-vms_api}"
PORT="${VMS_PORT:-8000}"
OWNERS="${VMS_OWNERS:-vms_migrator,vms_app}"
cd "$BASE"
MODE="${1:-cek}"
ENV_FILE=api.env
SQL_FILE="$BASE/peran-runtime.sql"

recreate_and_wait() {
  docker compose up -d --force-recreate api >/dev/null
  for _ in $(seq 1 24); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "localhost:$PORT/ready")" = 200 ] && return 0
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
  recreate_and_wait && echo "   api /ready: $(curl -s "localhost:$PORT/ready")" || echo "PERINGATAN: /ready belum 200"
}

if [ "$MODE" = kembalikan ]; then
  echo "== rollback: kembali ke koneksi sebelum vms_api"
  restore_latest
  exit 0
fi
case "$MODE" in cek|terapkan|pakai) ;; *) echo "Mode tidak dikenal: $MODE (cek|terapkan|kembalikan)"; exit 2 ;; esac

echo "== 1 pemeriksaan ($MODE)"
[ -f "$ENV_FILE" ] || { echo "GAGAL: $BASE/$ENV_FILE tidak ada"; exit 1; }
OLD_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)
[ -n "$OLD_URL" ] || { echo "GAGAL: DATABASE_URL tidak ada di api.env"; exit 1; }
DB_NAME=$(printf '%s' "$OLD_URL" | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
CUR_USER=$(printf '%s' "$OLD_URL" | sed -E 's#^[^:]+://([^:@]+).*#\1#')
psql_owner() { docker exec -i "$DB_CTR" sh -c "psql -v ON_ERROR_STOP=1 -qAt -U \"\$POSTGRES_USER\" -d '$DB_NAME'"; }
echo "   DATABASE_URL sekarang memakai peran: $CUR_USER (db $DB_NAME)"
echo "SELECT rolname || ' super=' || rolsuper::text || ' bypassrls=' || rolbypassrls::text || ' login=' || rolcanlogin::text FROM pg_roles WHERE rolname IN ('vms_api','vms_app','vms_migrator','vms_readonly') ORDER BY 1;" | psql_owner | sed 's/^/   peran: /'
echo "SELECT 'policy RLS: ' || count(*) FROM pg_policies;" | psql_owner | sed 's/^/   /'
ROLE=$(echo "SELECT rolsuper::text || ' ' || rolbypassrls::text FROM pg_roles WHERE rolname = 'vms_api';" | psql_owner)
if [ -n "$ROLE" ] && [ "$ROLE" != "false false" ]; then
  echo "GAGAL: peran vms_api ada tetapi tidak aman ($ROLE) — jalankan mode terapkan untuk menyelaraskan, atau perbaiki manual"
  [ "$MODE" = cek ] || exit 1
fi
[ -n "$ROLE" ] && echo "   vms_api: ada, bukan superuser, tanpa BYPASSRLS" || echo "   vms_api: BELUM ada (dibuat oleh mode terapkan)"
REV=$(docker exec "$API_CTR" alembic current 2>/dev/null | tail -1 || true)
echo "   alembic: ${REV:-tidak terbaca}"
case "$CUR_USER" in
  vms_api) echo "   API sudah memakai vms_api"; [ "$MODE" = cek ] || { echo "   tidak ada yang diubah"; exit 0; } ;;
  *) echo "   API BELUM memakai vms_api (peran $CUR_USER)" ;;
esac
if [ "$MODE" = cek ]; then echo "Mode cek selesai (tidak ada perubahan)."; exit 0; fi
[ -f "$SQL_FILE" ] || { echo "GAGAL: $SQL_FILE tidak ada (salin deploy/peran-runtime.sql ke $BASE/ lebih dulu)"; exit 1; }

echo "== 2 salinan api.env"
BACKUP="api.env.sebelum-vms_api.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$BACKUP" && chmod 600 "$BACKUP"
echo "   $BACKUP"

echo "== 3 peran vms_api + hak minimal (sandi baru tidak dicetak)"
PW=$(openssl rand -hex 24)
docker exec -i -e VMS_API_PASSWORD="$PW" "$DB_CTR" sh -c "psql -v ON_ERROR_STOP=1 -q -U \"\$POSTGRES_USER\" -d '$DB_NAME' -v owners='$OWNERS'" < "$SQL_FILE" >/dev/null
echo "   disetel"

echo "== 4 api.env"
OLD_URL="$OLD_URL" PW="$PW" python3 - "$ENV_FILE" <<'PY'
import os, sys, urllib.parse

path = sys.argv[1]
old, pw = os.environ["OLD_URL"], os.environ["PW"]


def split_userinfo(url):
    """Pisahkan URL pada '@' TERAKHIR — itu pemisah userinfo/host yang sebenarnya.

    Sandi boleh memuat '@' (insiden 2026-10-13: sandi 'P@ss...' ditulis mentah sehingga
    SQLAlchemy membaca '@' pertama, host jadi 'ss...@vms_db_prod', API mati socket.gaierror).
    """
    head, sep, rest = url.partition("://")
    assert sep, "format DATABASE_URL tidak dikenali (tanpa '://')"
    at = rest.rfind("@")
    assert at != -1, "format DATABASE_URL tidak dikenali (tanpa '@')"
    user, colon, secret = rest[:at].partition(":")
    assert colon, "format DATABASE_URL tidak dikenali (userinfo tanpa ':')"
    return head, user, secret, rest[at + 1:]


def build(head, user, secret, hostpart):
    """Sandi & user WAJIB di-encode; tanpa ini '@' di sandi merusak parsing host."""
    return f"{head}://{urllib.parse.quote(user, safe='')}:{urllib.parse.quote(secret, safe='')}@{hostpart}"


def verify(url, expect_user, expect_secret):
    parsed = urllib.parse.urlsplit(url.replace("+asyncpg", ""))
    # urlsplit mengembalikan userinfo MASIH ter-encode, jadi harus di-unquote dulu —
    # tanpa ini pemeriksaan selalu gagal walau URL-nya benar (uji 2026-10-13).
    got_user = urllib.parse.unquote(parsed.username or "")
    got_secret = urllib.parse.unquote(parsed.password or "")
    assert got_user == expect_user, f"user salah: {got_user!r}"
    assert got_secret == expect_secret, "sandi tidak utuh setelah di-encode"
    assert "@" not in (parsed.hostname or ""), f"host salah bentuk: {parsed.hostname!r}"
    assert parsed.hostname and parsed.path.lstrip("/"), "host/nama basis data kosong"
    return parsed.hostname


head, old_user, old_secret, hostpart = split_userinfo(old)
hostpart = hostpart.replace("vms_db_prod:5433", "vms_db_prod:5432").replace("vms_db:5433", "vms_db:5432")
new = build(head, "vms_api", pw, hostpart)
migration = build(head, old_user, old_secret, hostpart)   # alembic: peran pemilik, sandi ikut di-encode
assert new != old, "format DATABASE_URL tidak dikenali"

host = verify(new, "vms_api", pw)
verify(migration, old_user, old_secret)

lines = [l for l in open(path, encoding="utf-8").read().splitlines() if not l.startswith("MIGRATION_DATABASE_URL=")]
lines = [f"DATABASE_URL={new}" if l.startswith("DATABASE_URL=") else l for l in lines]
lines.append(f"MIGRATION_DATABASE_URL={migration}")
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"   host terverifikasi: {host} (sandi ter-encode, '@' tidak merusak parsing)")
PY
unset PW
chmod 600 "$ENV_FILE"
echo "   DATABASE_URL -> vms_api; MIGRATION_DATABASE_URL -> pemilik (alembic)"

echo "== 5 buat ulang api dan periksa"
if ! recreate_and_wait; then
  echo "GAGAL: /ready tidak 200 — rollback otomatis"
  restore_latest
  exit 1
fi
WHO=$(docker exec "$API_CTR" python -c "
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
echo "   api /ready: $(curl -s "localhost:$PORT/ready")"
echo "   API tersambung sebagai vms_api (non-superuser, tanpa BYPASSRLS)"
echo "SELESAI. Uji login web & HP, absen, buka SK. Ada masalah -> jalankan mode 'kembalikan'."
