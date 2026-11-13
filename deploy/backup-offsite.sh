#!/usr/bin/env bash
# Salin backup DB ke mesin/NAS lain lewat rsync + SSH (disarankan lewat Tailscale). Jalankan SETELAH backup.sh:
#   45 1 * * * /home/ageng/deploy/vms-mvp/backup-offsite.sh >> /home/ageng/deploy/vms-mvp/logs/offsite.log 2>&1
# Kepatuhan UU PDP No. 27/2022: cadangan yang dikirim ke luar server WAJIB terenkripsi `age`.
# Kunci publik age dibaca dari `age-recipients.txt` atau $VMS_AGE_RECIPIENTS.
# Konfigurasi di `offsite.env` (chmod 600, tidak di Git):
#   OFFSITE_HOST=backup@100.x.y.z        # tujuan (Tailscale)
#   OFFSITE_DIR=/srv/backup/vms          # folder tujuan di mesin itu
#   OFFSITE_KEY=$HOME/.ssh/vms_offsite   # kunci SSH khusus (ed25519), hanya untuk rsync di tujuan
#   OFFSITE_KEEP_DAYS=30                 # retensi di tujuan (maks 35 hari untuk PDP)
# Opsi: --coba  → rsync --dry-run (tidak mengubah apa pun).
set -euo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE"
[ -f deploy.env ] && . ./deploy.env
BK="${VMS_BACKUP_DIR:-backups}"
RECIP="${VMS_AGE_RECIPIENTS:-$BASE/age-recipients.txt}"
[ -f offsite.env ] || { echo "offsite.env tidak ada — lihat komentar di atas." >&2; exit 2; }
# shellcheck disable=SC1091
. ./offsite.env
: "${OFFSITE_HOST:?isi OFFSITE_HOST}" "${OFFSITE_DIR:?isi OFFSITE_DIR}" "${OFFSITE_KEY:?isi OFFSITE_KEY}"
KEEP="${OFFSITE_KEEP_DAYS:-30}"
DRY=""
[ "${1:-}" = "--coba" ] && DRY="--dry-run"

# Cek apakah ada berkas cadangan (.age atau .dump)
HAS_AGE=0
HAS_DUMP=0
if ls "$BK"/*.age >/dev/null 2>&1; then HAS_AGE=1; fi
if ls "$BK"/*.dump >/dev/null 2>&1; then HAS_DUMP=1; fi

if [ "$HAS_AGE" = 0 ] && [ "$HAS_DUMP" = 0 ]; then
  echo "Tidak ada backup lokal (.age atau .dump) untuk disalin di $BK." >&2
  exit 3
fi

# Bila ada .dump polos, enkripsi dengan age sebelum dikirim ke luar server
if [ "$HAS_DUMP" = 1 ]; then
  if command -v age >/dev/null 2>&1 && [ -s "$RECIP" ] && ! grep -q 'AGE-SECRET-KEY' "$RECIP"; then
    RECIP_CLEAN="$(mktemp)"
    grep -E '^age1[a-z0-9]+$' "$RECIP" > "$RECIP_CLEAN" || true
    if [ -s "$RECIP_CLEAN" ]; then
      for d in "$BK"/*.dump; do
        [ -f "$d" ] || continue
        if [ ! -f "$d.age" ] || [ "$d" -nt "$d.age" ]; then
          age -R "$RECIP_CLEAN" "$d" > "$d.age.tmp"
          mv "$d.age.tmp" "$d.age"
          (cd "$BK" && sha256sum "$(basename "$d.age")" > "$(basename "$d.age").sha256")
        fi
      done
      HAS_AGE=1
    fi
    rm -f "$RECIP_CLEAN"
  fi
fi

# Pengaman PDP: tolak pengiriman berkas polos (.dump) jika belum terenkripsi age,
# kecuali diizinkan secara eksplisit lewat VMS_ALLOW_UNENCRYPTED_OFFSITE=1 (hanya untuk lab dev).
PATTERNS=()
if [ "$HAS_AGE" = 1 ]; then
  for f in "$BK"/*.age; do [ -e "$f" ] && PATTERNS+=("$f"); done
  for f in "$BK"/*.sha256; do [ -e "$f" ] && PATTERNS+=("$f"); done
  for f in "$BK"/*.manifest; do [ -e "$f" ] && PATTERNS+=("$f"); done
elif [ "${VMS_ALLOW_UNENCRYPTED_OFFSITE:-0}" = 1 ]; then
  echo "PERINGATAN: Mengirim cadangan polos tanpa enkripsi age (VMS_ALLOW_UNENCRYPTED_OFFSITE=1)." >&2
  for f in "$BK"/*.dump; do [ -e "$f" ] && PATTERNS+=("$f"); done
else
  echo "KEPATUHAN PDP: Cadangan DB yang dikirim ke luar server WAJIB terenkripsi age." >&2
  echo "Pasang kunci publik penerima di age-recipients.txt atau setel VMS_AGE_RECIPIENTS." >&2
  echo "Untuk pengujian darurat dev, setel VMS_ALLOW_UNENCRYPTED_OFFSITE=1." >&2
  exit 2
fi

SSH="ssh -i $OFFSITE_KEY -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=yes"

rsync -a --partial --chmod=F600 $DRY -e "$SSH" "${PATTERNS[@]}" "$OFFSITE_HOST:$OFFSITE_DIR/"

if [ -z "$DRY" ]; then
  # Verifikasi ukuran berkas terbaru sama di tujuan, baru catat berhasil.
  newest=$(ls -1t "${PATTERNS[@]}" | head -n 1)
  local_size=$(stat -c %s "$newest")
  remote_size=$($SSH "$OFFSITE_HOST" "stat -c %s '$OFFSITE_DIR/$(basename "$newest")'")
  [ "$local_size" = "$remote_size" ] || { echo "Ukuran berbeda: lokal $local_size, tujuan $remote_size" >&2; exit 4; }
  $SSH "$OFFSITE_HOST" "find '$OFFSITE_DIR' \( -name '*.age' -o -name '*.dump' -o -name '*.sha256' -o -name '*.manifest' \) -mtime +$KEEP -delete" || true
  touch .offsite.ok
  echo "$(date '+%F %T') offsite OK: $(basename "$newest") ($local_size bita)"
fi
