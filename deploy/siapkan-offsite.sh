#!/usr/bin/env bash
# Pasang backup luar-server dalam dua fase. Dijalankan DI SERVER (~/deploy/vms-mvp), oleh pemilik.
#   Fase 1: bash siapkan-offsite.sh siapkan <user@host-tujuan> <folder-tujuan>
#           → membuat kunci SSH khusus, offsite.env, mencatat host tujuan; mencetak 1 baris kunci publik
#             yang harus Anda tambahkan ke ~/.ssh/authorized_keys di mesin tujuan (+ perintah membuat foldernya).
#   Fase 2: bash siapkan-offsite.sh pasang
#           → uji coba kering, salinan nyata + verifikasi ukuran, lalu memasang cron harian 01:45.
# Tujuan disarankan lewat Tailscale (100.x) agar tidak membuka port. Tujuan butuh: sshd, rsync, folder tulis.
set -euo pipefail
BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"; cd "$BASE"
KEY="$HOME/.ssh/vms_offsite"
case "${1:-}" in
  siapkan)
    HOST="${2:?pemakai@host tujuan}"; DIR="${3:?folder tujuan, mis. /srv/backup/vms}"
    mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
    [ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C "vms-offsite@$(hostname)" -f "$KEY"
    h="${HOST#*@}"
    ssh-keyscan -T 10 -H "$h" 2>/dev/null >> "$HOME/.ssh/known_hosts" || true
    grep -q . "$HOME/.ssh/known_hosts" || { echo "Host $h tidak terjangkau (ssh-keyscan kosong)." >&2; exit 2; }
    umask 077
    printf 'OFFSITE_HOST=%s\nOFFSITE_DIR=%s\nOFFSITE_KEY=%s\nOFFSITE_KEEP_DAYS=30\n' "$HOST" "$DIR" "$KEY" > offsite.env
    chmod 600 offsite.env
    echo "== offsite.env dibuat. Di MESIN TUJUAN ($HOST) jalankan:"
    echo "   mkdir -p '$DIR' && chmod 700 '$DIR'"
    echo "   echo '$(cat "$KEY.pub")' >> ~/.ssh/authorized_keys"
    echo "== Lalu di server ini: bash siapkan-offsite.sh pasang"
    ;;
  pasang)
    [ -f offsite.env ] || { echo "Jalankan fase 'siapkan' dulu." >&2; exit 2; }
    ls backups/*.dump >/dev/null 2>&1 || ./backup.sh manual-offsite
    ./backup-offsite.sh --coba
    ./backup-offsite.sh
    LINE="45 1 * * * $BASE/backup-offsite.sh >> $BASE/logs/offsite.log 2>&1"
    ( crontab -l 2>/dev/null | grep -vF "backup-offsite.sh"; echo "$LINE" ) | crontab -
    echo "== cron terpasang: $LINE"
    echo "== healthcheck.sh memberi alert bila salinan luar-server > 26 jam."
    ;;
  *) echo "Pemakaian: $0 siapkan <user@host> <folder> | pasang" >&2; exit 2 ;;
esac
