#!/usr/bin/env bash
# APK "Visiontech Beta" untuk uji lokal (Rencana Kerja v3, T1).
# Terpasang berdampingan dengan aplikasi prod (applicationId .beta), mengarah ke API laptop lewat
# `adb reverse`, tanpa pemeriksaan pembaruan. Tidak pernah dikirim ke server.
#
#   bash scripts/bangun-beta.sh [--tanpa-pasang]
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
MOBILE="$ROOT/mobile"
FLUTTER="${FLUTTER:-$(command -v flutter || echo "$HOME/flutter/bin/flutter.bat")}"
SDK="${ANDROID_HOME:-${LOCALAPPDATA:-$HOME/AppData/Local}/Android/Sdk}"
ADB="$SDK/platform-tools/adb"; [ -f "$ADB.exe" ] && ADB="$ADB.exe"
PASANG=1; [ "${1:-}" = "--tanpa-pasang" ] && PASANG=0
API_PORT="${API_PORT:-8010}"   # port API di laptop (scripts/api-lokal.sh); HP tetap memanggil 127.0.0.1:8000

if [ "$PASANG" = 1 ]; then
  "$ADB" reverse tcp:8000 "tcp:$API_PORT"
fi

(cd "$MOBILE" && VMS_BETA=1 "$FLUTTER" build apk --release --split-per-abi -PallowDebugSigning=true \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=VMS_BETA=true \
  --dart-define=UPDATE_CHANNEL=beta)

OUT="$MOBILE/build/beta"; mkdir -p "$OUT"
SRC=$(ls "$MOBILE"/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk)
APK="$OUT/visiontech-beta-$(date +%Y%m%d-%H%M).apk"
cp "$SRC" "$APK"

[ "$PASANG" = 1 ] && "$ADB" install -r "$APK"
echo "== APK beta: $APK"
echo "== Ingat: 'adb reverse' hilang bila kabel dicabut; jalankan ulang: adb reverse tcp:8000 tcp:$API_PORT"
