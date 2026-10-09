#!/usr/bin/env bash
# Mode pengembangan di HP (debug + hot reload) untuk merapikan tampilan tanpa build APK ulang.
# Terpasang sebagai "Visiontech Beta" (.beta), memanggil API laptop lewat `adb reverse` (port API_PORT, bawaan 8010).
#   bash scripts/hp-dev.sh [serial-hp]
# Di terminal ini:  r = hot reload (perubahan tampilan langsung tampil)  ·  R = hot restart  ·  q = keluar.
# Di VS Code/Android Studio (Flutter extension) hot reload otomatis setiap berkas disimpan.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
FLUTTER="${FLUTTER:-$(command -v flutter || echo "$HOME/flutter/bin/flutter.bat")}"
SDK="${ANDROID_HOME:-${LOCALAPPDATA:-$HOME/AppData/Local}/Android/Sdk}"
ADB="$SDK/platform-tools/adb"; [ -f "$ADB.exe" ] && ADB="$ADB.exe"
API_PORT="${API_PORT:-8010}"
DEVICE="${1:-$("$ADB" devices | awk 'NR>1 && $2=="device" && $1 !~ /^emulator/ {print $1; exit}')}"
[ -n "$DEVICE" ] || { echo "GAGAL: HP tidak terdeteksi (cek kabel & USB debugging)" >&2; exit 1; }

"$ADB" -s "$DEVICE" reverse tcp:8000 "tcp:$API_PORT"
echo "== HP $DEVICE → API laptop port $API_PORT. Tekan r untuk hot reload."
cd "$ROOT/mobile"
VMS_BETA=1 exec "$FLUTTER" run -d "$DEVICE" \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=VMS_BETA=true \
  --dart-define=UPDATE_CHANNEL=beta
