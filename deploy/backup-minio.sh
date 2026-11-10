#!/usr/bin/env bash
# Cadangan BERKAS (bucket MinIO) VMS: `mc mirror` satu arah ke folder cadangan, per lingkungan.
# Aman: sumber tidak pernah dihapus/diubah (mirror tanpa --remove), idempoten (hanya salin yang baru/berubah),
# ringan (satu kontainer mc sementara, tanpa port, ~30-60 MB), rahasia tidak dicetak/tidak ada di argumen.
# Pemakaian: backup-minio.sh [label]   (kode keluar != 0 bila gagal; mencetak folder hasil)
#   VMS_DEPLOY_DIR      : folder deploy (bawaan ~/deploy/vms-mvp), deploy.env dibaca bila ada.
#   VMS_MINIO_CT        : nama kontainer MinIO (bawaan ${VMS_CONTAINER_PREFIX:-vms}_minio).
#   VMS_BACKUP_DIR/NAME : sama dengan backup.sh (bawaan "backups" dan nama DB/prod).
#   VMS_MINIO_BUCKETS   : daftar bucket dipisah spasi (bawaan: semua kecuali vms-backups).
#   VMS_MINIO_KEEP      : jumlah rekaman manifest yang disimpan (bawaan 14).
#   VMS_MINIO_REMOVE=1  : salinan juga menghapus berkas yang sudah dihapus di sumber (dipakai backup-terenkripsi.sh).
#   VMS_MC_IMAGE        : citra mc (bawaan quay.io/minio/mc, SEBAIKNYA dipin ke digest).
# Hasil: $BKDIR/<NAME>-berkas/<bucket>/... (salinan terkini) + <NAME>-berkas-<stempel>.manifest (hitungan objek/bita).
set -euo pipefail
BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
LABEL="${1:-harian}"
cd "$BASE"
[ -f deploy.env ] && . ./deploy.env
MINIO_CT="${VMS_MINIO_CT:-${VMS_CONTAINER_PREFIX:-vms}_minio}"
MC_IMAGE="${VMS_MC_IMAGE:-quay.io/minio/mc:latest}"
BKDIR="${VMS_BACKUP_DIR:-backups}"
BKNAME="${VMS_BACKUP_NAME:-prod}"
KEEP="${VMS_MINIO_KEEP:-14}"
mkdir -p "$BKDIR"
DEST="$(cd "$BKDIR" && pwd)/$BKNAME-berkas"

manifest_retention() { ls -1t "$BKDIR/$BKNAME"-berkas-*.manifest 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f || true; }
[ "${VMS_BACKUP_SOURCE_ONLY:-}" = 1 ] && return 0
trap manifest_retention EXIT

docker inspect "$MINIO_CT" >/dev/null 2>&1 || { echo "Kontainer MinIO '$MINIO_CT' tidak ada (setel VMS_MINIO_CT)" >&2; exit 2; }
# Kredensial dibaca dari lingkungan kontainer MinIO dan dioper lewat NAMA variabel (nilai tak masuk argumen/log).
MC_HOST_src="http://$(docker exec "$MINIO_CT" printenv MINIO_ROOT_USER):$(docker exec "$MINIO_CT" printenv MINIO_ROOT_PASSWORD)@localhost:9000"
export MC_HOST_src
mc() { docker run --rm --network "container:$MINIO_CT" -e MC_HOST_src -v "$DEST:/backup" --memory 128m "$MC_IMAGE" "$@"; }
mkdir -p "$DEST"

BUCKETS="${VMS_MINIO_BUCKETS:-}"
if [ -z "$BUCKETS" ]; then
  BUCKETS=$(mc ls src 2>/dev/null | awk '{print $NF}' | tr -d '/' | grep -v '^vms-backups$' || true)
fi
[ -n "$BUCKETS" ] || { echo "Tidak ada bucket untuk dicadangkan" >&2; exit 3; }

MAN="$BKDIR/$BKNAME-berkas-$(date +%Y%m%d-%H%M%S).manifest"
: > "$MAN"
for b in $BUCKETS; do
  mc mirror --overwrite ${VMS_MINIO_REMOVE:+--remove} --quiet "src/$b" "/backup/$b" >&2 || { echo "Mirror bucket $b gagal" >&2; rm -f "$MAN"; exit 4; }
  n=$(find "$DEST/$b" -type f | wc -l | tr -d ' ')
  s=$(du -sb "$DEST/$b" 2>/dev/null | cut -f1)
  echo "$b objek=$n bita=${s:-0} label=$LABEL" >> "$MAN"
done
cat "$MAN"
echo "$DEST"
