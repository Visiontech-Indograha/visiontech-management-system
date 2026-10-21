#!/usr/bin/env bash
# Jaga sambungan HP uji ↔ API lokal: tiap beberapa detik pastikan HP (USB atau debugging nirkabel) tersambung dan
# `adb reverse tcp:<port HP> tcp:<port API>` aktif. HP yang tidur / kabel goyang / Wi-Fi berpindah tersambung lagi
# otomatis tanpa perintah manual.
#
#   bash scripts/adb-jaga.sh                 # port 8000 → 8000, cek tiap 5 detik
#   API_PORT=8010 bash scripts/adb-jaga.sh   # HP 8000 → API laptop 8010
set -u
ADB="${ADB:-$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe}"
[ -x "$ADB" ] || ADB="$(command -v adb)"
PHONE_PORT="${PHONE_PORT:-8000}"
API_PORT="${API_PORT:-8000}"
INTERVAL="${INTERVAL:-5}"

log() { echo "[$(date +%H:%M:%S)] $*"; }

while true; do
  # Debugging nirkabel: sambungkan ulang ke alamat yang diiklankan HP (port berubah tiap Wi-Fi/restart).
  for target in $("$ADB" mdns services 2>/dev/null | awk '/_adb-tls-connect/ {print $3}'); do
    "$ADB" devices | grep -q "^${target}[[:space:]]*device" || {
      "$ADB" connect "$target" >/dev/null 2>&1 && log "tersambung nirkabel $target"
    }
  done
  # Setiap HP fisik yang tersambung (bukan emulator): pasang ulang reverse bila hilang.
  for dev in $("$ADB" devices | awk 'NR>1 && $2=="device" && $1 !~ /^emulator-/ {print $1}'); do
    if ! "$ADB" -s "$dev" reverse --list 2>/dev/null | grep -q "tcp:${PHONE_PORT} tcp:${API_PORT}"; then
      "$ADB" -s "$dev" reverse "tcp:${PHONE_PORT}" "tcp:${API_PORT}" >/dev/null 2>&1 \
        && log "reverse aktif lagi di $dev (HP ${PHONE_PORT} → laptop ${API_PORT})"
    fi
  done
  sleep "$INTERVAL"
done
