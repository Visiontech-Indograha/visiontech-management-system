#!/usr/bin/env bash
# Salin backup DB ke mesin/NAS lain lewat rsync + SSH (disarankan lewat Tailscale). Jalankan SETELAH backup.sh:
#   45 1 * * * /home/ageng/deploy/vms-mvp/backup-offsite.sh >> /home/ageng/deploy/vms-mvp/logs/offsite.log 2>&1
# Konfigurasi di `offsite.env` (chmod 600, tidak di Git):
#   OFFSITE_HOST=backup@100.x.y.z        # tujuan (Tailscale)
#   OFFSITE_DIR=/srv/backup/vms          # folder tujuan di mesin itu
#   OFFSITE_KEY=$HOME/.ssh/vms_offsite   # kunci SSH khusus (ed25519), hanya untuk rsync di tujuan
#   OFFSITE_KEEP_DAYS=30                 # retensi di tujuan
# Opsi: --coba  → rsync --dry-run (tidak mengubah apa pun).
set -euo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE"
[ -f offsite.env ] || { echo "offsite.env tidak ada — lihat komentar di atas." >&2; exit 2; }
# shellcheck disable=SC1091
. ./offsite.env
: "${OFFSITE_HOST:?isi OFFSITE_HOST}" "${OFFSITE_DIR:?isi OFFSITE_DIR}" "${OFFSITE_KEY:?isi OFFSITE_KEY}"
KEEP="${OFFSITE_KEEP_DAYS:-30}"
DRY=""
[ "${1:-}" = "--coba" ] && DRY="--dry-run"

ls backups/*.dump >/dev/null 2>&1 || { echo "Tidak ada backup lokal untuk disalin." >&2; exit 3; }
SSH="ssh -i $OFFSITE_KEY -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=yes"

rsync -a --partial --chmod=F600 $DRY -e "$SSH" backups/*.dump "$OFFSITE_HOST:$OFFSITE_DIR/"

if [ -z "$DRY" ]; then
  # Verifikasi ukuran berkas terbaru sama di tujuan, baru catat berhasil.
  newest=$(ls -1t backups/*.dump | head -n 1)
  local_size=$(stat -c %s "$newest")
  remote_size=$($SSH "$OFFSITE_HOST" "stat -c %s '$OFFSITE_DIR/$(basename "$newest")'")
  [ "$local_size" = "$remote_size" ] || { echo "Ukuran berbeda: lokal $local_size, tujuan $remote_size" >&2; exit 4; }
  $SSH "$OFFSITE_HOST" "find '$OFFSITE_DIR' -name '*.dump' -mtime +$KEEP -delete" || true
  touch .offsite.ok
  echo "$(date '+%F %T') offsite OK: $(basename "$newest") ($local_size bita)"
fi
