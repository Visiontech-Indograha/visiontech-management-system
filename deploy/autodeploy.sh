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

REPO="${VMS_DEPLOY_REPO:-git@github-vms:Visiontech-Indograha/visiontech-management-system.git}"
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

GH_URL="${VMS_GITHUB_URL:-https://github.com/Visiontech-Indograha/visiontech-management-system}"
APP_URL="${VMS_PUBLIC_URL:-https://visiontech-bar.tail827174.ts.net}"
STAGES="$LOGDIR/.stages-$STAMP"; : > "$STAGES"

F=$'\036'                                      # pemisah antarkolom embed (nilai boleh berisi baris baru)
# discord JUDUL WARNA DESKRIPSI [LAMPIRAN] — kolom lewat env FIELDS: "Nama|inline(1/0)|Nilai" dipisah $F.
discord() {
  local body code
  body=$(mktemp)
  TITLE="$1" COLOR="$2" DESC="$3" URL="$GH_URL/commit/$NEW" HOST="$(hostname)" FIELDS="${FIELDS:-}" \
  python3 - > "$body" <<'PY'
import json, os
fields = []
for rec in os.environ["FIELDS"].split("\x1e"):
    if rec.count("|") < 2:
        continue
    name, inline, value = rec.strip().split("|", 2)
    fields.append({"name": name[:250], "value": (value.strip() or "—")[:1000], "inline": inline != "0"})
embed = {
    "title": os.environ["TITLE"][:250], "url": os.environ["URL"], "color": int(os.environ["COLOR"]),
    "description": os.environ["DESC"][:3900], "fields": fields[:25],
    "footer": {"text": f"vms-mvp · {os.environ['HOST']}"},
    "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
}
print(json.dumps({"embeds": [embed]}))
PY
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

# Durasi tiap tahap dari penanda waktu yang ditulis step().
stage_times() {
  awk -F'|' -v end="$(date +%s)" '{n[NR]=$1; t[NR]=$2} END {for (i=1;i<=NR;i++) {e=(i<NR)?t[i+1]:end; printf "`%3ss` %s\n", e-t[i], n[i]}}' "$STAGES"
}
dur() { local s=$1; [ "$s" -ge 60 ] && printf '%d mnt %02d dtk' $((s/60)) $((s%60)) || printf '%d dtk' "$s"; }

step() { echo; echo "===== $(date '+%H:%M:%S') · $* ====="; echo "$*|$(date +%s)" >> "$STAGES"; }
fail() {
  FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Durasi|1|$(dur $(( $(date +%s) - T0 )))\
${F}Versi berjalan|0|\`${OLD:0:8}\` (sebelumnya) — kecuali tahap gagal setelah kontainer dinyalakan\
${F}Tahapan|0|$(stage_times)" \
  discord "🔴 Deploy GAGAL — $1" 15158332 \
"**$SUBJECT**

\`\`\`
$(tail -20 "$LOG" | cut -c1-150)
\`\`\`
📎 Log lengkap terlampir." "$LOG"
  rm -f "$STAGES"
  exit 1
}

FIELDS="Branch|1|\`$BRANCH\`${F}Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR" \
discord "🚀 Deploy dimulai — $SHORT" 3447003 \
"**$SUBJECT**

**Perubahan yang ikut:**
$CHANGES

⏳ Build → backup → nyalakan → migrasi → cek siap pakai. Kabar berikutnya menyusul."

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
  step "Cek siap pakai (api, basis data, web, jalur /api, 3x berturut-turut)"
  ok=0
  for i in $(seq 1 24); do                     # maks ±2 menit
    a=$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/health)
    r=$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)
    w=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/)
    p=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/api/v1/auth/me)
    run=$(docker inspect -f '{{.State.Running}}' vms_api vms_web 2>/dev/null | sort -u | tr '\n' ' ')
    if [ "$a" = 200 ] && [ "$r" = 200 ] && [ "$w" = 200 ] && [ "$p" = 401 ] && [ "$run" = "true " ]; then
      ok=$((ok+1)); [ "$ok" -ge 3 ] && break
    else ok=0; fi
    sleep 5
  done
  echo "api=$a db=$([ "$r" = 200 ] && echo ok || echo "GAGAL($r)") web=$w jalur_api=$p stabil=$ok/3"
  [ "$ok" -ge 3 ] || exit 16
  for c in api web; do                           # pastikan yang berjalan memang image hasil build ini
    [ "$(docker inspect -f '{{.Image}}' vms_$c)" = "$(docker image inspect -f '{{.Id}}' vms-mvp-$c)" ] || { echo "vms_$c bukan image terbaru"; exit 16; }
  done
  echo "image=terbaru"
  docker image prune -f >/dev/null 2>&1
) > "$LOG" 2>&1
RC=$?
case $RC in
  0) ;;
  11) fail "checkout kode" ;; 12) fail "build image" ;; 13) fail "backup database" ;;
  14) fail "menjalankan kontainer" ;; 15) fail "migrasi database" ;; 16) fail "cek siap pakai (server belum sehat/stabil)" ;;
  *) fail "tidak dikenal (kode $RC)" ;;
esac

echo "$NEW" > "$LAST_FILE"
TOOK=$(( $(date +%s) - T0 ))
MIG=$(grep -E "Running upgrade" "$LOG" | sed 's/.*Running upgrade /• /' | cut -c1-120)
HEALTH=$(grep -E '^api=' "$LOG" | tail -1)
BACKUP=$(grep -E '^minio:' "$LOG" | tail -1 | sed -E 's/^minio: *//')
FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Total waktu|1|$(dur "$TOOK")\
${F}Kesehatan|0|\`$HEALTH\`\
${F}Basis data|0|${MIG:-Tidak ada migrasi baru} · versi \`$(grep -E '\(head\)' "$LOG" | tail -1 | cut -d' ' -f1)\`\
${F}Backup sebelum deploy|0|\`${BACKUP:-—}\`\
${F}Tahapan|0|$(stage_times)" \
discord "✅ Siap dipakai — $SHORT" 3066993 \
"**$SUBJECT**

Server sudah lolos cek siap pakai (API, basis data, web, dan jalur \`/api\` sehat 3× berturut-turut; kontainer memakai image terbaru).
🔗 $APP_URL

📎 Log build lengkap terlampir." "$LOG"
rm -f "$STAGES"
