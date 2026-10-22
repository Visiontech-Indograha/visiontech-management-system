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
# Lingkungan (docs/40): prod & beta memakai skrip yang sama, beda variabel di <BASE>/deploy.env.
#   prod: vms_api/vms_web, port 8000/8080, kanal APK stable · beta: vms_beta_api/…, port 8001/8081, kanal beta.
[ -f "${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}/deploy.env" ] && . "${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}/deploy.env"
BRANCH="${VMS_DEPLOY_BRANCH:-$BRANCH}"
ENV_NAME="${VMS_ENV_NAME:-prod}"                 # prod | beta (judul Discord, kanal APK)
PFX="${VMS_CONTAINER_PREFIX:-vms}"              # vms_api / vms_beta_api
IMG="${VMS_IMAGE_PREFIX:-vms-mvp}"              # vms-mvp-api / vms-beta-api
API_PORT="${VMS_API_PORT:-8000}"
WEB_PORT="${VMS_WEB_PORT:-8080}"
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

# Menunggu sampai benar-benar siap, bukan sekadar `sleep`: insiden 2026-10-13 menunjukkan
# `sleep 8` lolos padahal API belum bisa mencapai DB (host salah parse → socket.gaierror),
# sehingga kegagalan baru muncul sebagai traceback di tengah tahap migrasi. Menunggu juga
# mencegah deploy gagal saat DB/MinIO lambat siap (mis. setelah host reboot).
wait_api_reaches_db() {                       # → 0 bila API benar-benar tersambung ke basis data
  local i
  for i in $(seq 1 12); do                    # maks ±60 dtk
    if docker exec ${PFX}_api python -c "
import asyncio, asyncpg
from app.core.config import settings
async def main():
    conn = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''), timeout=5)
    await conn.close()
asyncio.run(main())" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  return 1
}

wait_api_reaches_minio() {                    # → 0 bila API benar-benar bisa memakai MinIO
  local i
  for i in $(seq 1 6); do                     # maks ±30 dtk
    if docker exec ${PFX}_api python -c "
from minio import Minio
from app.core.config import settings as s
host = s.MINIO_ENDPOINT.replace('http://', '').replace('https://', '')
Minio(host, access_key=s.MINIO_ACCESS_KEY, secret_key=s.MINIO_SECRET_KEY,
      secure=s.MINIO_SECURE).list_buckets()" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  return 1
}

# Menerjemahkan kegagalan di atas menjadi kalimat yang menunjuk berkas & nilai yang salah,
# bukan sekadar traceback — supaya log Discord langsung memberi arah perbaikan.
db_hint() {
  echo "API tidak bisa mencapai basis data lewat DATABASE_URL di api.env."
  echo "Periksa sandi yang memuat karakter khusus (@ : / #) — WAJIB di-URL-encode ('@' → '%40')."
  echo "Pastikan port untuk host kontainer (vms_db_prod) adalah 5432, BUKAN 5433 (port host)."
  docker exec ${PFX}_api python -c "
import os
from sqlalchemy.engine import make_url
for key in ('DATABASE_URL', 'MIGRATION_DATABASE_URL'):
    value = os.environ.get(key, '')
    if not value:
        continue
    url = make_url(value)
    print(f'  {key}: user={url.username!r} host={url.host!r} port={url.port!r} db={url.database!r}')
    if '@' in (url.host or ''):
        print(f'  -> {key} SALAH BENTUK: sandi belum di-URL-encode.')
    if url.host in ('vms_db_prod', 'vms_db') and url.port == 5433:
        print(f'  -> {key} SALAH PORT: gunakan 5432 untuk koneksi internal kontainer, bukan 5433.')
" 2>&1 || true
  echo "Lalu: docker compose up -d --force-recreate api dan periksa /ready."
}

minio_hint() {
  echo "API tidak bisa memakai MinIO dengan MINIO_ACCESS_KEY / MINIO_SECRET_KEY di api.env."
  echo "Kredensial itu tidak dikenal MinIO — pakai service account yang valid"
  echo "(mis. dari /home/ageng/deploy/visiontech/.env: S3_ACCESS_KEY / S3_SECRET_KEY)."
}
fail() {
  FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Durasi|1|$(dur $(( $(date +%s) - T0 )))\
${F}Versi berjalan|0|\`${OLD:0:8}\` (sebelumnya) — kecuali tahap gagal setelah kontainer dinyalakan\
${F}Tahapan|0|$(stage_times)" \
  discord "🔴 [$ENV_NAME] Deploy GAGAL — $1" 15158332 \
"**$SUBJECT**

\`\`\`
$(tail -20 "$LOG" | cut -c1-150)
\`\`\`
📎 Log lengkap terlampir." "$LOG"
  rm -f "$STAGES"
  exit 1
}

FIELDS="Branch|1|\`$BRANCH\`${F}Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR" \
discord "🚀 [$ENV_NAME] Deploy dimulai — $SHORT" 3447003 \
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
  step "Jalankan kontainer baru (up -d)"
  # Compose dapat mempertahankan kontainer lama bila isi image baru identik (mis. commit hanya docs),
  # padahal pemeriksaan di bawah sengaja mewajibkan ID image hasil build terbaru.
  # Dijalankan SEBELUM backup & migrasi supaya pemeriksaan berikutnya memakai api.env yang baru —
  # kalau tidak, perbaikan api.env baru terbaca pada deploy setelahnya (jebakan insiden 2026-10-13).
  docker compose up -d --force-recreate 2>&1 || exit 14
  step "Tunggu API tersambung ke basis data (maks 60 dtk)"
  wait_api_reaches_db || { db_hint; exit 17; }
  step "Tunggu API tersambung ke MinIO (maks 30 dtk)"
  wait_api_reaches_minio || { minio_hint; exit 18; }
  step "Backup database (DB aplikasi → lokal + MinIO vms-backups)"
  ./backup.sh "pra-deploy-$SHORT" || exit 13
  step "Migrasi database (Master Schema V2: migration_v3, idempoten)"
  # V2 tidak memakai rantai alembic V1 (skema = db/06 + DDL idempoten di app/database/migration_v3.py).
  docker exec ${PFX}_api python -c "
import asyncio
from app.database.migration_v3 import apply_v3_migrations
asyncio.run(apply_v3_migrations())
print('migrasi V2: selesai')" 2>&1 || exit 15
  step "Cek siap pakai (api, basis data, web, jalur /api, 3x berturut-turut)"
  ok=0
  for i in $(seq 1 24); do                     # maks ±2 menit
    a=$(curl -s -o /dev/null -w '%{http_code}' localhost:${API_PORT}/health)
    r=$(curl -s -o /dev/null -w '%{http_code}' localhost:${API_PORT}/ready)
    w=$(curl -s -o /dev/null -w '%{http_code}' localhost:${WEB_PORT}/)
    p=$(curl -s -o /dev/null -w '%{http_code}' localhost:${WEB_PORT}/api/v1/auth/me)
    run=$(docker inspect -f '{{.State.Running}}' ${PFX}_api ${PFX}_web 2>/dev/null | sort -u | tr '\n' ' ')
    if [ "$a" = 200 ] && [ "$r" = 200 ] && [ "$w" = 200 ] && [ "$p" = 401 ] && [ "$run" = "true " ]; then
      ok=$((ok+1)); [ "$ok" -ge 3 ] && break
    else ok=0; fi
    sleep 5
  done
  echo "api=$a db=$([ "$r" = 200 ] && echo ok || echo "GAGAL($r)") web=$w jalur_api=$p stabil=$ok/3"
  [ "$ok" -ge 3 ] || exit 16
  for c in api web; do                           # pastikan yang berjalan memang image hasil build ini
    [ "$(docker inspect -f '{{.Image}}' ${PFX}_$c)" = "$(docker image inspect -f '{{.Id}}' ${IMG}-$c)" ] || { echo "${PFX}_$c bukan image terbaru"; exit 16; }
  done
  echo "image=terbaru"
  docker image prune -f >/dev/null 2>&1
) > "$LOG" 2>&1
RC=$?
case $RC in
  0) ;;
  11) fail "checkout kode" ;; 12) fail "build image" ;; 13) fail "backup database" ;;
  14) fail "menjalankan kontainer" ;; 15) fail "migrasi database" ;; 16) fail "cek siap pakai (server belum sehat/stabil)" ;;
  17) fail "API tidak bisa mencapai basis data" ;; 18) fail "API tidak bisa mencapai MinIO" ;;
  *) fail "tidak dikenal (kode $RC)" ;;
esac

echo "$NEW" > "$LAST_FILE"
TOOK=$(( $(date +%s) - T0 ))
MIG=$(grep -E "^migrasi V2:" "$LOG" | tail -1)
HEALTH=$(grep -E '^api=' "$LOG" | tail -1)
BACKUP=$(grep -E '^minio:' "$LOG" | tail -1 | sed -E 's/^minio: *//')
FIELDS="Commit|1|[\`$SHORT\`]($GH_URL/commit/$NEW)${F}Oleh|1|$AUTHOR${F}Total waktu|1|$(dur "$TOOK")\
${F}Kesehatan|0|\`$HEALTH\`\
${F}Basis data|0|${MIG:-—}\
${F}Backup sebelum deploy|0|\`${BACKUP:-—}\`\
${F}Tahapan|0|$(stage_times)" \
discord "✅ [$ENV_NAME] Siap dipakai — $SHORT" 3066993 \
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

  # Beta: paket .beta ("Visiontech Beta", terpasang berdampingan dengan prod) & kanal pembaruan beta.
  local beta_args=""
  if [ "$ENV_NAME" = "beta" ]; then
    export VMS_BETA=1
    beta_args="--dart-define=VMS_BETA=true --dart-define=UPDATE_CHANNEL=beta"
  fi

  mkdir -p "$rilis_dir"
  local build_ok=0
  (
    cd "$mobile_src" || exit 1
    "$flutter_bin" pub get || exit 31
    "$flutter_bin" build apk --release --split-per-abi --target-platform android-arm,android-arm64 \
      --build-name "$name" --build-number "$build" -Pforce-version-code-ignoring-abi=true \
      --dart-define=API_BASE_URL="$APP_URL" $beta_args $extra_args || exit 32
    "$flutter_bin" build apk --release --target-platform android-arm,android-arm64 \
      --build-name "$name" --build-number "$build" \
      --dart-define=API_BASE_URL="$APP_URL" $beta_args $extra_args || exit 33
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
