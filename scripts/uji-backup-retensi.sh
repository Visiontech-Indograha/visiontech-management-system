#!/usr/bin/env bash
# Tes logika penamaan & retensi deploy/backup.sh pada folder sementara (tanpa Docker/DB/MinIO).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
GAGAL=0
cek() { if [ "$2" = "$3" ]; then echo "LULUS $1"; else echo "GAGAL $1 (dapat '$2', harapan '$3')"; GAGAL=1; fi; }
mk() { # mk <dir> <awalan> <jumlah>
  mkdir -p "$1"; local i
  for i in $(seq 1 "$3"); do f="$1/$2-harian-20261001-0000$(printf %02d "$i").dump"; echo x > "$f"; touch -d "${4:-2026-10-01} 00:00:$(printf %02d "$i")" "$f"; done
}
muat() { ( export VMS_DEPLOY_DIR="$T" VMS_BACKUP_SOURCE_ONLY=1 "$@"; mkdir -p "$T"; cd "$T"; DB=${DB:-vms_v2}; source "$ROOT/deploy/backup.sh" harian; eval "$CMD" ); }

# 1. bawaan: semua *.dump dihitung, 7 terbaru; nama = DB-label-stempel
mk "$T/backups" vms_v2 10
CMD='backup_retention; ls backups | wc -l' ; cek "bawaan retensi 7" "$(DB=vms_v2 muat | tail -1 | tr -d ' ')" 7
CMD='backup_file_name vms_v2 pra-deploy-abc'; cek "bawaan nama" "$(DB=vms_v2 muat | sed -E 's/[0-9]{8}-[0-9]{6}/STAMP/')" "backups/vms_v2-pra-deploy-abc-STAMP.dump"

# 2. dua lingkungan satu folder; berkas lama (nama DB) tetap dihitung
rm -rf "$T/backups"; D="$T/bersama"
mk "$D" prod 4; mk "$D" beta 9; mk "$D" vms_v2 5 2026-09-01   # 5 berkas nama lama prod (lebih tua)
export_env='VMS_BACKUP_DIR='"$D"
CMD='backup_retention; ls '"$D"'/beta-* | wc -l'; cek "beta aman saat retensi prod" "$(DB=vms_v2 VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=prod muat | tail -1 | tr -d ' ')" 9
CMD='ls '"$D"'/prod-* | wc -l'; cek "berkas prod baru utuh" "$(DB=vms_v2 VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=prod muat | tail -1 | tr -d ' ')" 4
CMD='ls '"$D"'/vms_v2-* | wc -l'; cek "nama lama: 3 terbaru dipertahankan" "$(DB=vms_v2 VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=prod muat | tail -1 | tr -d ' ')" 3
CMD='backup_retention; ls '"$D"'/prod-* '"$D"'/vms_v2-* | wc -l'; cek "prod tidak disentuh retensi beta" "$(DB=vms_beta VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=beta muat | tail -1 | tr -d ' ')" 7
CMD='ls '"$D"'/beta-* | wc -l'; cek "beta dipangkas ke 7" "$(DB=vms_beta VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=beta muat | tail -1 | tr -d ' ')" 7
CMD='backup_file_name beta pra-deploy-abc'; cek "nama berawalan" "$(DB=vms_beta VMS_BACKUP_DIR=$D VMS_BACKUP_NAME=beta muat | sed -E 's/[0-9]{8}-[0-9]{6}/STAMP/')" "$D/beta-pra-deploy-abc-STAMP.dump"
[ "$GAGAL" = 0 ] && echo "SEMUA LULUS" || { echo "ADA GAGAL"; exit 1; }
