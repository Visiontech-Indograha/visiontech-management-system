#!/usr/bin/env bash
# Saklar wajib-daftar-wajah (FACE_ENROLLMENT_REQUIRED) lewat berkas env API. Rencana Kerja v3, T3.
#   bash scripts/saklar-wajah.sh on|off|status [berkas-env]     (bawaan: api/.env)
# on  = absen HP & gerbang menu ditolak tanpa wajah terdaftar (bawaan aplikasi).
# off = dimatikan, untuk lingkungan yang face-service-nya belum terpasang.
# Setelah mengubah, restart API. Skrip tidak pernah mencetak isi berkas, hanya nilai saklar ini.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
AKSI="${1:-status}"
FILE="${2:-$ROOT/api/.env}"
KEY=FACE_ENROLLMENT_REQUIRED
[ -f "$FILE" ] || { echo "GAGAL: $FILE tidak ada" >&2; exit 1; }
case "$AKSI" in
  on|off)
    NILAI=true; [ "$AKSI" = off ] && NILAI=false
    if grep -q "^$KEY=" "$FILE"; then sed -i "s|^$KEY=.*|$KEY=$NILAI|" "$FILE"; else printf '\n%s=%s\n' "$KEY" "$NILAI" >> "$FILE"; fi
    echo "$KEY=$NILAI di $FILE — restart API agar berlaku." ;;
  status)
    if grep -q "^$KEY=" "$FILE"; then grep "^$KEY=" "$FILE"; else echo "$KEY tidak diset (bawaan aplikasi: true)"; fi ;;
  *) echo "pemakaian: saklar-wajah.sh on|off|status [berkas-env]" >&2; exit 2 ;;
esac
