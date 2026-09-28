#!/usr/bin/env bash
# Deploy otomatis VMS (R-20): setiap menit (cron) memeriksa branch `prod` di GitHub.
# Ada commit baru → build image → backup DB → up -d → migrasi → cek kesehatan,
# lalu lapor ke Discord #vms-deploy (mulai, berhasil/gagal + log build lengkap sebagai lampiran).
#
# Pasang di server (sekali): lihat deploy/README.md.
# Berkas di ~/deploy/vms-mvp: compose.yml, api.env, notify.env (DISCORD_WEBHOOK_DEPLOY=...), src/ (klon repo).
set -uo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
BRANCH="${VMS_DEPLOY_BRANCH:-prod}"
cd "$BASE" || exit 1
exec 9>"$BASE/.autodeploy.lock"
flock -n 9 || exit 0                       # deploy sebelumnya masih berjalan
# shellcheck disable=SC1091
source "$BASE/notify.env"

LOGDIR="$BASE/logs"; mkdir -p "$LOGDIR" backups
LAST_FILE="$BASE/.last-deployed"

REPO="${VMS_DEPLOY_REPO:-git@github-vms:consep33t/visiontech-management-system.git}"
if [ ! -d src/.git ]; then
  # Klon pertama: tandai `prod` saat ini sebagai sudah terpasang — yang dideploy hanya merge berikutnya.
  git clone -q --branch "$BRANCH" "$REPO" src || exit 1
  git -C src rev-parse HEAD > "$LAST_FILE"
fi
git -C src fetch -q origin "$BRANCH" || exit 1
NEW=$(git -C src rev-parse "origin/$BRANCH")
OLD=$(cat "$LAST_FILE" 2>/dev/null || echo "")
[ "$NEW" = "$OLD" ] && exit 0

STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$LOGDIR/deploy-$STAMP.log"
SHORT=${NEW:0:8}
SUBJECT=$(git -C src log -1 --format='%s' "$NEW")
AUTHOR=$(git -C src log -1 --format='%an' "$NEW")
if [ -n "$OLD" ]; then CHANGES=$(git -C src log --format='• %h %s' "$OLD..$NEW" | head -15); else CHANGES="• (deploy pertama)"; fi
T0=$(date +%s)

json() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }
discord() {  # $1 = judul, $2 = warna (desimal), $3 = isi, $4 = lampiran (opsional)
  local payload
  payload=$(printf '{"embeds":[{"title":%s,"color":%s,"description":%s,"footer":{"text":"vms-mvp · %s"}}]}' \
    "$(printf '%s' "$1" | json)" "$2" "$(printf '%s' "$3" | head -c 3900 | json)" "$(hostname)")
  local body code
  body=$(mktemp); printf '%s' "$payload" > "$body"
  # Isi dibaca dari berkas (`<`): pesan commit ber-`;` tidak lagi merusak argumen curl -F.
  if [ -n "${4:-}" ] && [ -f "$4" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' -F "payload_json=<$body" -F "file=@$4;type=text/plain" "$DISCORD_WEBHOOK_DEPLOY")
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "@$body" "$DISCORD_WEBHOOK_DEPLOY")
  fi
  case "$code" in 2*) ;; *)                      # cadangan: tanpa lampiran, tetap kabari
    echo "discord gagal ($code), kirim ulang tanpa lampiran" >&2
    curl -s -o /dev/null -H 'Content-Type: application/json' --data-binary "@$body" "$DISCORD_WEBHOOK_DEPLOY" ;;
  esac
  rm -f "$body"
}

step() { echo; echo "===== $(date '+%H:%M:%S') · $* ====="; }
fail() {
  local took=$(( $(date +%s) - T0 ))
  discord "🔴 Deploy GAGAL — $SHORT" 15158332 \
"**Tahap gagal:** $1
**Commit:** \`$SHORT\` $SUBJECT
**Oleh:** $AUTHOR · **Durasi:** ${took} dtk
Versi yang berjalan tetap versi sebelumnya (\`${OLD:0:8}\`) kecuali tahap gagal setelah *up*.

**Akhir log:**
\`\`\`
$(tail -25 "$LOG" | cut -c1-180)
\`\`\`
Log lengkap terlampir." "$LOG"
  exit 1
}

discord "🚀 Deploy dimulai — $SHORT" 3447003 \
"**Branch:** \`$BRANCH\` · **Commit:** \`$SHORT\`
**Pesan:** $SUBJECT
**Oleh:** $AUTHOR
**Perubahan:**
$CHANGES"

(
  step "Checkout $SHORT"
  git -C src checkout -q --force "$NEW" && rm -rf api web && cp -a src/api src/web . || exit 11
  rm -f api/.env web/.env
  step "Build image (docker compose build)"
  docker compose build --progress=plain 2>&1 || exit 12
  step "Backup database (DB aplikasi → lokal + MinIO vms-backups)"
  ./backup.sh "pra-deploy-$SHORT" || exit 13
  step "Jalankan kontainer baru (up -d)"
  docker compose up -d 2>&1 || exit 14
  sleep 8
  step "Migrasi database (alembic upgrade head)"
  docker exec vms_api alembic upgrade head 2>&1 || exit 15
  docker exec vms_api alembic current 2>&1 | tail -1
  step "Cek kesehatan"
  for i in $(seq 1 10); do
    a=$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/health)
    w=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/)
    [ "$a" = 200 ] && [ "$w" = 200 ] && break; sleep 3
  done
  echo "api=$a web=$w"
  [ "$a" = 200 ] && [ "$w" = 200 ] || exit 16
  docker image prune -f >/dev/null 2>&1
) > "$LOG" 2>&1
RC=$?
case $RC in
  0) ;;
  11) fail "checkout kode" ;; 12) fail "build image" ;; 13) fail "backup database" ;;
  14) fail "menjalankan kontainer" ;; 15) fail "migrasi database" ;; 16) fail "cek kesehatan (api/web tidak 200)" ;;
  *) fail "tidak dikenal (kode $RC)" ;;
esac

echo "$NEW" > "$LAST_FILE"
TOOK=$(( $(date +%s) - T0 ))
MIG=$(grep -E "Running upgrade" "$LOG" | sed 's/.*Running upgrade /• /' | cut -c1-120)
discord "✅ Deploy berhasil — $SHORT" 3066993 \
"**Commit:** \`$SHORT\` $SUBJECT
**Oleh:** $AUTHOR · **Durasi:** ${TOOK} dtk
**Migrasi:** ${MIG:-tidak ada migrasi baru}
**Versi DB:** $(grep -E '\(head\)' "$LOG" | tail -1)
**Kesehatan:** $(grep -E '^api=' "$LOG" | tail -1)
**Backup DB:** $(grep -E '^minio:' "$LOG" | tail -1)
Log build lengkap terlampir." "$LOG"
