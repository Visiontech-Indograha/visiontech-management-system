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
WEBHOOK_DEPLOY="${DISCORD_WEBHOOK_DEPLOY:-}"
WEBHOOK_BUILD="${DISCORD_WEBHOOK_BUILD:-${DISCORD_WEBHOOK_DIGEST:-${DISCORD_WEBHOOK_4:-}}}"

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
# discord JUDUL WARNA DESKRIPSI [LAMPIRAN] [TARGET_WEBHOOK] — kolom lewat env FIELDS: "Nama|inline(1/0)|Nilai" dipisah $F.
discord() {
  local body code target_hook
  body=$(mktemp)
  target_hook="${5:-$WEBHOOK_DEPLOY}"
  if [ -z "$target_hook" ]; then
    echo "discord: webhook tidak dikonfigurasi, dilewati" >&2
    rm -f "$body"
    return 0
  fi
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
    code=$(curl -s -o /dev/null -w '%{http_code}' -F "payload_json=<$body" -F "file=@$4;type=text/plain" "$target_hook")
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "@$body" "$target_hook")
  fi
  case "$code" in 2*) ;; *)                      # cadangan: tanpa lampiran, tetap kabari
    echo "discord gagal ($code), kirim ulang tanpa lampiran" >&2
    curl -s -o /dev/null -H 'Content-Type: application/json' --data-binary "@$body" "$target_hook" ;;
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
  git -C src checkout -q --force "$NEW" && rm -rf api web face && cp -a src/api src/web . && cp -a src/face-service face || exit 11
  rm -f api/.env web/.env
  step "Build image (docker compose build)"
  docker compose --progress=plain build 2>&1 || exit 12
  step "Backup database (DB aplikasi → lokal + MinIO vms-backups)"
  ./backup.sh "pra-deploy-$SHORT" || exit 13
  step "Jalankan kontainer baru (up -d)"
  # Compose dapat mempertahankan kontainer lama bila isi image baru identik (mis. commit hanya docs),
  # padahal pemeriksaan di bawah sengaja mewajibkan ID image hasil build terbaru.
  docker compose up -d --force-recreate 2>&1 || exit 14
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

# Build aplikasi mobile Android (bila ada perubahan di mobile/) dan laporkan ke webhook ke-4
build_mobile() {
  local mobile_src="$BASE/src/mobile"
  local rilis_dir="$BASE/rilis/android"
  local mobile_log="$LOGDIR/mobile-build-$STAMP.log"
  local t_mb0
  t_mb0=$(date +%s)

  [ -d "$mobile_src" ] || return 0

  local touched=0
  if [ -n "$OLD" ]; then
    if git -C "$BASE/src" diff --name-only "$OLD" "$NEW" | grep -q '^mobile/'; then
      touched=1
    fi
  else
    touched=1
  fi
  [ "${FORCE_BUILD_MOBILE:-0}" = "1" ] && touched=1

  if [ "$touched" -eq 0 ]; then
    echo "Tidak ada perubahan pada mobile/, build aplikasi mobile dilewati."
    return 0
  fi

  step "Build aplikasi mobile Android"

  local flutter_bin=""
  if [ -n "${FLUTTER:-}" ] && [ -x "${FLUTTER:-}" ]; then
    flutter_bin="$FLUTTER"
  elif command -v flutter >/dev/null 2>&1; then
    flutter_bin="flutter"
  elif [ -x "$HOME/flutter/bin/flutter" ]; then
    flutter_bin="$HOME/flutter/bin/flutter"
  fi

  if [ -z "$flutter_bin" ]; then
    echo "PERINGATAN: Flutter SDK tidak ditemukan di server ($BASE)." | tee -a "$mobile_log"
    if [ -n "$WEBHOOK_BUILD" ]; then
      FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Status|1|Flutter SDK Belum Terpasang" \
      discord "⚠️ Build Aplikasi Mobile Dilewati — $SHORT" 16753920 \
"Perubahan pada \`mobile/\` terdeteksi di commit ini, tetapi Flutter SDK belum terpasang di host server (\`$BASE\`).
Silakan pasang Flutter SDK di server atau bangun rilis dari laptop dengan \`scripts/rilis-apk.bat bangun\` lalu kirim." "" "$WEBHOOK_BUILD"
    fi
    return 0
  fi

  local pubspec="$mobile_src/pubspec.yaml"
  [ -f "$pubspec" ] || { echo "pubspec.yaml tidak ditemukan" | tee -a "$mobile_log"; return 0; }

  local ver name build
  ver=$(sed -n 's/^version:[[:space:]]*\([0-9][0-9.]*+[0-9][0-9]*\).*/\1/p' "$pubspec")
  name=${ver%+*}; build=${ver#*+}
  if [ -z "$name" ] || [ -z "$build" ]; then
    echo "Format versi di pubspec.yaml tidak valid: $ver" | tee -a "$mobile_log"
    return 0
  fi

  local key_props="$mobile_src/android/key.properties"
  if [ ! -f "$key_props" ] && [ -f "$BASE/keystore/key.properties" ]; then
    cp "$BASE/keystore/key.properties" "$key_props"
  fi

  local extra_args=""
  if [ ! -f "$key_props" ]; then
    echo "PERINGATAN: key.properties tidak ditemukan di server, mencoba build dengan debug signing." | tee -a "$mobile_log"
    extra_args="-PallowDebugSigning=true"
  fi

  mkdir -p "$rilis_dir"
  local build_ok=0
  (
    cd "$mobile_src" || exit 1
    "$flutter_bin" pub get || exit 31
    "$flutter_bin" build apk --release --split-per-abi --target-platform android-arm,android-arm64 \
      --build-name "$name" --build-number "$build" -Pforce-version-code-ignoring-abi=true \
      --dart-define=API_BASE_URL="$APP_URL" $extra_args || exit 32
    "$flutter_bin" build apk --release --target-platform android-arm,android-arm64 \
      --build-name "$name" --build-number "$build" \
      --dart-define=API_BASE_URL="$APP_URL" $extra_args || exit 33
  ) > "$mobile_log" 2>&1 && build_ok=1

  local dur_build
  dur_build=$(( $(date +%s) - t_mb0 ))

  if [ "$build_ok" -eq 1 ]; then
    local apk_outputs="$mobile_src/build/app/outputs/flutter-apk"
    local files_json="" sep="" list_msg=""

    for apk in "$apk_outputs"/app-*-release.apk; do
      [ -f "$apk" ] || continue
      local abi dest sha size
      abi=$(basename "$apk" | sed 's/^app-\(.*\)-release\.apk$/\1/')
      dest="vms-$name-$build-$abi.apk"
      cp "$apk" "$rilis_dir/$dest"
      sha=$(sha256sum "$rilis_dir/$dest" | cut -d' ' -f1)
      size=$(stat -c %s "$rilis_dir/$dest")
      files_json+="$sep    {\"abi\": \"$abi\", \"name\": \"$dest\", \"sha256\": \"$sha\", \"size\": $size}"
      sep=$',\n'
      list_msg+="• \`$dest\` ($(( size / 1048576 )) MB)\n"
    done

    local uni_apk="$apk_outputs/app-release.apk"
    if [ -f "$uni_apk" ]; then
      local uni_dest="vms-$name-$build-universal.apk"
      cp "$uni_apk" "$rilis_dir/$uni_dest"
      local uni_sha uni_size
      uni_sha=$(sha256sum "$rilis_dir/$uni_dest" | cut -d' ' -f1)
      uni_size=$(stat -c %s "$rilis_dir/$uni_dest")
      files_json+="$sep    {\"abi\": \"universal\", \"name\": \"$uni_dest\", \"sha256\": \"$uni_sha\", \"size\": $uni_size}"
      list_msg+="• \`$uni_dest\` (Full Universal, $(( uni_size / 1048576 )) MB)\n"
    fi

    cat > "$rilis_dir/latest.json.tmp" <<EOF
{
  "package": "com.visiontech.vms_mobile",
  "version_name": "$name",
  "build": $build,
  "min_build": 1,
  "released_at": "$(date +%Y-%m-%dT%H:%M:%S%:z)",
  "notes": ["Build otomatis dari deploy server commit $SHORT"],
  "files": [
$files_json
  ]
}
EOF
    mv "$rilis_dir/latest.json.tmp" "$rilis_dir/latest.json"

    if [ -n "$WEBHOOK_BUILD" ]; then
      FIELDS="Versi|1|\`$name+$build\`${F}Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Durasi|1|$(dur "$dur_build")\
${F}Berkas APK|0|${list_msg}" \
      discord "📱 Build Aplikasi Mobile Berhasil — v$name+$build" 3066993 \
"**$SUBJECT**

Aplikasi Android versi **$name** (build $build) berhasil dibangun dan diterbitkan di portal.
Tersedia berkas arsitektur terpisah (split-per-ABI) dan berkas universal full version.

🔗 $APP_URL" "" "$WEBHOOK_BUILD"
    fi
  else
    if [ -n "$WEBHOOK_BUILD" ]; then
      FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Durasi|1|$(dur "$dur_build")" \
      discord "🔴 Build Aplikasi Mobile GAGAL — $SHORT" 15158332 \
"**$SUBJECT**

Build Flutter Android gagal pada tahap kompilasi.

\`\`\`
$(tail -20 "$mobile_log" | cut -c1-150)
\`\`\`
📎 Log build lengkap terlampir." "$mobile_log" "$WEBHOOK_BUILD"
    fi
  fi
}

build_mobile
