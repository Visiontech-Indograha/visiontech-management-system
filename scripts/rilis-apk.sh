#!/usr/bin/env bash
# Rilis aplikasi HP Android tanpa Play Store (docs/32). Dijalankan di LAPTOP pemilik (keystore tidak pernah ke server).
#
#   bash scripts/rilis-apk.sh bangun [--wajib] [--catatan "poin"]...   build + verifikasi + latest.json
#   bash scripts/rilis-apk.sh kirim [BUILD]                             unggah ke server (scp/ssh, kunci SSH pemilik)
#   bash scripts/rilis-apk.sh wajib BUILD                               wajibkan pembaruan ke ≥ BUILD tanpa build ulang
#   bash scripts/rilis-apk.sh status                                    rilis yang sedang terbit di portal
#
# Uji lokal (emulator + API :8000): `bangun --uji-lokal --build N [--wajib]` → APK ke http://127.0.0.1:8000,
# cleartext diizinkan, ditambah x86_64; hasil di mobile/build/rilis-uji/N (tidak pernah dikirim ke server).
#
# Versi rilis = `version:` di mobile/pubspec.yaml (mis. 1.1.0+2 → versionName 1.1.0, versionCode/build 2).
# Lingkungan (opsional): VMS_PORTAL, VMS_SERVER, FLUTTER, ANDROID_HOME, JAVA_HOME.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
MOBILE="$ROOT/mobile"
PORTAL="${VMS_PORTAL:-https://portal.visiontechindo.com}"
SERVER="${VMS_SERVER:-ageng@192.168.88.160}"
REMOTE_DIR="deploy/vms-mvp/rilis/android"          # relatif ke home pengguna di server
PACKAGE="com.visiontech.vms_mobile"
CERT_FILE="$ROOT/deploy/android-release-cert.sha256"

die() { echo "GAGAL: $*" >&2; exit 1; }
info() { echo "== $*"; }

tools() {
  FLUTTER="${FLUTTER:-$(command -v flutter || echo "$HOME/flutter/bin/flutter.bat")}"
  [ -e "$FLUTTER" ] || command -v "$FLUTTER" >/dev/null || die "flutter tidak ditemukan (set FLUTTER=…)"
  SDK="${ANDROID_HOME:-${LOCALAPPDATA:-$HOME/AppData/Local}/Android/Sdk}"
  BT=$(ls -d "$SDK"/build-tools/* 2>/dev/null | sort -V | tail -1)
  [ -n "$BT" ] || die "Android build-tools tidak ditemukan di $SDK"
  APKSIGNER="$BT/apksigner"; [ -f "$APKSIGNER.bat" ] && APKSIGNER="$APKSIGNER.bat"
  AAPT2="$BT/aapt2"; [ -f "$AAPT2.exe" ] && AAPT2="$AAPT2.exe"
  if [ -z "${JAVA_HOME:-}" ] && ! command -v java >/dev/null; then
    for j in "/c/Program Files/Android/Android Studio/jbr" "$HOME/AppData/Local/Programs/Android Studio/jbr"; do
      [ -d "$j" ] && export JAVA_HOME="$j" && break
    done
  fi
}

json_escape() { local s=${1//\\/\\\\}; s=${s//\"/\\\"}; printf '%s' "$s"; }

published() {   # <base-url> → "latest_build min_build" (0 1 bila belum ada rilis / API lama)
  local body
  body=$(curl -k -fsS --max-time 15 "$1/api/v1/app/android/update?build=0" 2>/dev/null || true)
  local latest min
  latest=$(printf '%s' "$body" | sed -n 's/.*"latest_build":\([0-9]*\).*/\1/p')
  min=$(printf '%s' "$body" | sed -n 's/.*"min_build":\([0-9]*\).*/\1/p')
  echo "${latest:-0} ${min:-1}"
}

cmd_bangun() {
  local wajib=0 uji=0 build_override="" notes=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --wajib) wajib=1 ;;
      --catatan) shift; notes+=("${1:?--catatan butuh teks}") ;;
      --uji-lokal) uji=1 ;;
      --build) shift; build_override="${1:?--build butuh angka}" ;;
      *) die "opsi tidak dikenal: $1" ;;
    esac
    shift
  done
  tools
  local ver name build api targets cleartext outroot
  ver=$(sed -n 's/^version:[[:space:]]*\([0-9][0-9.]*+[0-9][0-9]*\).*/\1/p' "$MOBILE/pubspec.yaml")
  [ -n "$ver" ] || die "version: di mobile/pubspec.yaml harus berbentuk X.Y.Z+N"
  name=${ver%+*}; build=${ver#*+}
  if [ "$uji" = 1 ]; then
    [ -n "$build_override" ] && build="$build_override"
    api="http://127.0.0.1:8000"; targets="android-arm,android-arm64,android-x64"; cleartext="-PallowCleartext=true"
    outroot="$MOBILE/build/rilis-uji"
  else
    [ -z "$build_override" ] || die "--build hanya untuk --uji-lokal; naikkan version di pubspec untuk rilis"
    [ -z "$(git status --porcelain)" ] || die "pohon kerja belum bersih — commit dulu agar APK = kode yang tercatat"
    git fetch -q origin prod || true
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/prod 2>/dev/null || echo x)" ] \
      || echo "PERINGATAN: HEAD bukan origin/prod — pastikan API di server sudah memuat perubahan yang dibutuhkan APK ini."
    api="https://portal.visiontechindo.com"; targets="android-arm,android-arm64,android-x64"; cleartext=""
    outroot="$MOBILE/build/rilis"
  fi
  [[ "$build" =~ ^[0-9]+$ ]] || die "nomor build tidak valid: $build"

  local base_url="$PORTAL"; [ "$uji" = 1 ] && base_url="$api"
  read -r cur_latest cur_min < <(published "$base_url")
  [ "$build" -gt "$cur_latest" ] || die "build $build tidak lebih tinggi dari yang terbit ($cur_latest) — naikkan +N di pubspec"
  local min_build=$cur_min; [ "$wajib" = 1 ] && min_build=$build

  info "build $name+$build → $api (target $targets)"
  rm -f "$MOBILE"/build/app/outputs/flutter-apk/app-*-release.apk "$MOBILE"/build/app/outputs/flutter-apk/app-release.apk
  (cd "$MOBILE" && "$FLUTTER" build apk --release --split-per-abi --target-platform "$targets" \
     --build-name "$name" --build-number "$build" -Pforce-version-code-ignoring-abi=true $cleartext \
     --dart-define=API_BASE_URL="$api")
  (cd "$MOBILE" && "$FLUTTER" build apk --release --target-platform "$targets" \
     --build-name "$name" --build-number "$build" $cleartext \
     --dart-define=API_BASE_URL="$api")

  local expected out files_json="" sep=""
  expected=$(tr -d '\r' < "$CERT_FILE" | grep -E '^[0-9a-f]{64}$' | head -1)
  out="$outroot/$build"; rm -rf "$out"; mkdir -p "$out"
  for apk in "$MOBILE"/build/app/outputs/flutter-apk/app-*-release.apk; do
    local abi badging digest dest sha size
    abi=$(basename "$apk" | sed 's/^app-\(.*\)-release\.apk$/\1/')
    badging=$("$AAPT2" dump badging "$apk" | head -1)
    [[ "$badging" == *"name='$PACKAGE'"* ]] || die "$abi: paket bukan $PACKAGE"
    [[ "$badging" == *"versionCode='$build'"* ]] || die "$abi: versionCode bukan $build ($badging)"
    [[ "$badging" == *"versionName='$name'"* ]] || die "$abi: versionName bukan $name"
    digest=$("$APKSIGNER" verify --print-certs "$apk" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | tr -d '\r')
    [ "$digest" = "$expected" ] || die "$abi: APK tidak bertanda kunci rilis Visiontech ($digest) — cek android/key.properties"
    dest="vms-$name-$build-$abi.apk"
    cp "$apk" "$out/$dest"
    sha=$(sha256sum < "$out/$dest" | cut -d' ' -f1); size=$(stat -c %s "$out/$dest")   # stdin: tanpa awalan "\" pada jalur ber-backslash
    files_json+="$sep    {\"abi\": \"$abi\", \"name\": \"$dest\", \"sha256\": \"$sha\", \"size\": $size}"; sep=$',\n'
    echo "   $dest  $(( size / 1048576 )) MB  sha256 ${sha:0:12}…  tanda tangan OK"
  done
  local uni_apk="$MOBILE/build/app/outputs/flutter-apk/app-release.apk"
  if [ -f "$uni_apk" ]; then
    local u_abi="universal" u_badging u_digest u_dest u_sha u_size
    u_badging=$("$AAPT2" dump badging "$uni_apk" | head -1)
    [[ "$u_badging" == *"name='$PACKAGE'"* ]] || die "universal: paket bukan $PACKAGE"
    [[ "$u_badging" == *"versionCode='$build'"* ]] || die "universal: versionCode bukan $build ($u_badging)"
    [[ "$u_badging" == *"versionName='$name'"* ]] || die "universal: versionName bukan $name"
    u_digest=$("$APKSIGNER" verify --print-certs "$uni_apk" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | tr -d '\r')
    [ "$u_digest" = "$expected" ] || die "universal: APK tidak bertanda kunci rilis Visiontech ($u_digest) — cek android/key.properties"
    u_dest="vms-$name-$build-universal.apk"
    cp "$uni_apk" "$out/$u_dest"
    u_sha=$(sha256sum < "$out/$u_dest" | cut -d' ' -f1); u_size=$(stat -c %s "$out/$u_dest")
    files_json+="$sep    {\"abi\": \"$u_abi\", \"name\": \"$u_dest\", \"sha256\": \"$u_sha\", \"size\": $u_size}"; sep=$',\n'
    echo "   $u_dest  $(( u_size / 1048576 )) MB  sha256 ${u_sha:0:12}…  tanda tangan OK (Universal)"
  fi
  [ -n "$files_json" ] || die "tidak ada APK hasil build"

  local notes_json="" n
  sep=""
  for n in "${notes[@]}"; do notes_json+="$sep\"$(json_escape "$n")\""; sep=", "; done
  cat > "$out/latest.json" <<EOF
{
  "package": "$PACKAGE",
  "version_name": "$name",
  "build": $build,
  "min_build": $min_build,
  "released_at": "$(date +%Y-%m-%dT%H:%M:%S%:z)",
  "notes": [$notes_json],
  "files": [
$files_json
  ]
}
EOF
  info "siap: $out (min_build $min_build$([ "$wajib" = 1 ] && echo ', WAJIB'))"
  [ "$uji" = 1 ] || echo "   lanjut: bash scripts/rilis-apk.sh kirim"
}

latest_out() { ls -d "$MOBILE"/build/rilis/*/ 2>/dev/null | sed 's#/$##' | sort -t/ -k1 -V | tail -1; }

cmd_kirim() {
  local out
  if [ -n "${1:-}" ]; then out="$MOBILE/build/rilis/$1"; else out=$(latest_out); fi
  [ -n "$out" ] && [ -f "$out/latest.json" ] || die "belum ada hasil 'bangun' (mobile/build/rilis/<build>)"
  info "kirim $(basename "$out") → $SERVER:~/$REMOTE_DIR"
  ssh "$SERVER" "test -d $REMOTE_DIR" || die "folder rilis belum ada di server — jalankan deploy/pasang-rilis-apk.sh dulu"
  scp -q "$out"/*.apk "$SERVER:$REMOTE_DIR/"                    # APK dulu …
  scp -q "$out/latest.json" "$SERVER:$REMOTE_DIR/latest.json.tmp"
  ssh "$SERVER" "mv $REMOTE_DIR/latest.json.tmp $REMOTE_DIR/latest.json"   # … manifest diganti atomik
  verify_public "$out"
}

verify_public() {
  local out=$1 build body
  build=$(sed -n 's/^  "build": \([0-9]*\),/\1/p' "$out/latest.json")
  for i in 1 2 3 4 5 6; do
    body=$(curl -k -fsS --max-time 15 "$PORTAL/api/v1/app/android/update?build=0" || true)
    [[ "$body" == *"\"latest_build\":$build"* ]] && break; sleep 5
  done
  [[ "$body" == *"\"latest_build\":$build"* ]] || die "portal belum menampilkan build $build: $body"
  for apk in "$out"/*.apk; do
    local name size remote
    name=$(basename "$apk"); size=$(stat -c %s "$apk")
    remote=$(curl -k -fsSI --max-time 30 "$PORTAL/api/v1/app/android/files/$name" | tr -d '\r' \
             | sed -n 's/^[Cc]ontent-[Ll]ength: //p' | tail -1)
    [ "$remote" = "$size" ] || die "$name di portal berukuran ${remote:-?}, harus $size"
    echo "   $PORTAL/api/v1/app/android/files/$name  OK"
  done
  info "terbit: build $build. HP memeriksa saat aplikasi dibuka/kembali aktif."
}

cmd_wajib() {
  local build=${1:?pakai: wajib BUILD}
  [[ "$build" =~ ^[0-9]+$ ]] || die "BUILD harus angka"
  ssh "$SERVER" "python3 - '$REMOTE_DIR/latest.json' '$build'" <<'PY'
import json, os, sys
path, build = sys.argv[1], int(sys.argv[2])
m = json.load(open(path, encoding="utf-8"))
if build > m["build"]:
    sys.exit(f"build {build} belum terbit (terbaru {m['build']})")
m["min_build"] = build
tmp = path + ".tmp"
json.dump(m, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
os.replace(tmp, path)
print(f"min_build = {build}: HP di bawah build {build} wajib memperbarui.")
PY
}

cmd_status() { curl -k -fsS --max-time 15 "$PORTAL/api/v1/app/android/update?build=0"; echo; }

case "${1:-}" in
  bangun) shift; cmd_bangun "$@" ;;
  kirim) shift; cmd_kirim "$@" ;;
  wajib) shift; cmd_wajib "$@" ;;
  status) cmd_status ;;
  *) sed -n '2,13p' "$0"; exit 1 ;;
esac
