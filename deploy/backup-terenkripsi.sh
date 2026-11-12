#!/usr/bin/env bash
# Cadangan TERENKRIPSI (age) DB + MinIO untuk ditarik (PULL) oleh Windows 'pobonguar'. Lihat docs/CADANGAN-WINDOWS.md.
# Hanya kunci PUBLIK age di server ini; kunci privat TIDAK pernah ada di sini. Semua dialirkan (stream): tanpa
# berkas polos untuk DB, RAM tambahan ~puluhan MB (aman di 4 GB).
# Pemakaian: backup-terenkripsi.sh [db|minio|semua]   (kode keluar != 0 bila ada yang gagal)
#   VMS_DEPLOY_DIR       : folder deploy lingkungan ini (bawaan ~/deploy/vms-mvp); deploy.env dibaca bila ada.
#   VMS_BACKUP_NAME      : awalan nama (prod/beta). WAJIB berbeda per lingkungan.
#   VMS_BACKUP_DIR       : folder kerja polos (mirror MinIO, status tar) - TIDAK boleh terlihat oleh backup-reader.
#   VMS_ENC_DIR          : folder keluaran terenkripsi (bawaan /srv/vms-cadangan/$NAME), dibaca backup-reader.
#   VMS_AGE_RECIPIENTS   : berkas kunci publik age, satu per baris (bawaan $BASE/age-recipients.txt).
#   VMS_ENC_KEEP_DAYS    : retensi lokal hari (bawaan 3).
#   VMS_FULL_DOW         : hari penuh mingguan MinIO, 1=Senin..7=Minggu (bawaan 7); selain itu inkremental.
# Keluaran per lari (berkas diberi nama setelah selesai; .manifest ditulis TERAKHIR = tanda sah):
#   <NAME>-db-<stempel>.dump.age | <NAME>-minio-<stempel>-full|inc.tar.age  + .sha256 + .manifest
set -euo pipefail
umask 077
MODE="${1:-semua}"
BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE"
[ -f deploy.env ] && . ./deploy.env
NAME="${VMS_BACKUP_NAME:?Setel VMS_BACKUP_NAME (prod atau beta)}"
BKDIR="${VMS_BACKUP_DIR:-backups}"
ENC="${VMS_ENC_DIR:-/srv/vms-cadangan/$NAME}"
RECIP="${VMS_AGE_RECIPIENTS:-$BASE/age-recipients.txt}"
KEEP="${VMS_ENC_KEEP_DAYS:-3}"
FULL_DOW="${VMS_FULL_DOW:-7}"
DB_CONTAINER="${VMS_DB_CONTAINER:-vms_db_prod}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BKDIR" "$ENC"

command -v age >/dev/null || { echo "age belum terpasang (apt install age)" >&2; exit 2; }
[ -s "$RECIP" ] || { echo "Berkas kunci publik tidak ada/kosong: $RECIP" >&2; exit 2; }
# Pengaman: jangan pernah jalan bila ada kunci privat di berkas penerima.
if grep -q 'AGE-SECRET-KEY' "$RECIP"; then echo "BERBAHAYA: kunci PRIVAT ada di $RECIP; hapus." >&2; exit 2; fi
grep -qE '^age1[a-z0-9]+$' "$RECIP" || { echo "Tidak ada baris kunci publik age1... di $RECIP" >&2; exit 2; }
RECIP_CLEAN="$(mktemp)"
grep -E '^age1[a-z0-9]+$' "$RECIP" > "$RECIP_CLEAN"
trap 'rm -f "$RECIP_CLEAN" "$ENC"/*.partial 2>/dev/null || true' EXIT

# selesaikan <berkas.age> <jenis> <objek> <bita-sumber>: sha256 + manifest (terakhir), izin baca grup.
selesaikan() {
  local f="$1" jenis="$2" objek="$3" sumber="$4" b h
  b="$(basename "$f")"
  h="$(cd "$ENC" && sha256sum "$b")"
  echo "$h" > "$f.sha256"
  {
    echo "nama=$NAME"; echo "jenis=$jenis"; echo "berkas=$b"; echo "waktu=$(date -Is)"
    echo "versi=$(cat "$BASE/VERSION" 2>/dev/null || echo ?)"
    echo "ukuran_age=$(stat -c %s "$f")"; echo "sumber_bita=$sumber"; echo "objek=$objek"
    echo "sha256=${h%% *}"
  } > "$f.manifest.partial"
  mv "$f.manifest.partial" "$f.manifest"
  chmod 640 "$f" "$f.sha256" "$f.manifest" 2>/dev/null || true
  echo "OK $b"
}

cadangan_db() {
  local DB out ukuran dump_extra=""
  DB=$(grep -E '^DATABASE_URL=' api.env | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#')
  [ -n "$DB" ] || { echo "Nama DB tidak ditemukan di api.env" >&2; return 2; }
  out="$ENC/$NAME-db-$STAMP.dump.age"
  if [ "${VMS_BACKUP_EXCLUDE_BIOMETRIC:-0}" = 1 ] || [ "${VMS_BACKUP_SANITIZE_PDP:-0}" = 1 ]; then
    dump_extra="--exclude-table-data='*.employee'"
  fi
  docker exec "$DB_CONTAINER" sh -c "pg_dump -U \"\$POSTGRES_USER\" -d '$DB' -Fc $dump_extra" | age -R "$RECIP_CLEAN" > "$out.partial"
  [ -s "$out.partial" ] || { echo "Cadangan DB kosong" >&2; return 3; }
  mv "$out.partial" "$out"
  ukuran=$(docker exec "$DB_CONTAINER" sh -c "psql -U \"\$POSTGRES_USER\" -d '$DB' -Atc \"select pg_database_size('$DB')\"" 2>/dev/null || echo 0)
  selesaikan "$out" db 1 "$ukuran"
}

cadangan_minio() {
  local src="$BKDIR/$NAME-berkas" snar="$BKDIR/.$NAME-minio.snar" jenis out n s
  # 1) Salinan kerja HARUS menghormati penghapusan (--remove), supaya berkas terhapus tidak abadi.
  VMS_MINIO_REMOVE=1 VMS_BACKUP_DIR="$BKDIR" VMS_BACKUP_NAME="$NAME" bash "$(dirname "$0")/backup-minio.sh" "enkripsi" >/dev/null
  [ -d "$src" ] || { echo "Salinan kerja MinIO tidak ada: $src" >&2; return 3; }
  jenis=inc
  if [ "$(date +%u)" = "$FULL_DOW" ] || [ ! -s "$snar" ]; then jenis=full; fi
  rm -f "$snar.baru"
  if [ "$jenis" = inc ]; then cp -f "$snar" "$snar.baru"; fi
  out="$ENC/$NAME-minio-$STAMP-$jenis.tar.age"
  # 2) tar GNU inkremental (--listed-incremental mencatat penghapusan) -> age; tanpa kompresi (WebP/PDF sudah padat).
  tar --create --listed-incremental="$snar.baru" -C "$src" . | age -R "$RECIP_CLEAN" > "$out.partial"
  [ -s "$out.partial" ] || { echo "Arsip MinIO kosong" >&2; rm -f "$snar.baru"; return 3; }
  mv "$out.partial" "$out"
  mv -f "$snar.baru" "$snar"
  n=$(find "$src" -type f | wc -l | tr -d ' ')
  s=$(du -sb "$src" | cut -f1)
  selesaikan "$out" "minio-$jenis" "$n" "$s"
}

rotasi_lokal() {
  find "$ENC" -maxdepth 1 -type f -name "$NAME-*" -mtime "+$((KEEP - 1))" -delete 2>/dev/null || true
}

rc=0
case "$MODE" in
  db) cadangan_db || rc=$? ;;
  minio) cadangan_minio || rc=$? ;;
  semua) cadangan_db || rc=$?; cadangan_minio || rc=$? ;;
  *) echo "Mode: db|minio|semua" >&2; exit 64 ;;
esac
if [ "$rc" = 0 ]; then rotasi_lokal; fi
exit "$rc"
