#!/usr/bin/env bash
# Sanitasi data biometrik mentah (`face_embedding` di tabel `employee`) sesuai amanat UU PDP No. 27/2022.
# Memastikan data biometrik tidak bocor saat cadangan dipulihkan ke lingkungan non-produksi (uji/analisis).
# Pemakaian:
#   1. Cek jumlah data biometrik aktif:
#      sanitasi-dump-biometrik.sh --cek [CONTAINER] [DB_NAME]
#   2. Sanitasi langsung basis data berjalan:
#      sanitasi-dump-biometrik.sh --db [CONTAINER] [DB_NAME]
#   3. Sanitasi berkas dump mandiri lewat kontainer Postgres sementara (--network none):
#      sanitasi-dump-biometrik.sh --berkas <input.dump> <output_sanitasi.dump>
set -euo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
[ -f "$BASE/deploy.env" ] && . "$BASE/deploy.env"
DB_CT="${VMS_DB_CONTAINER:-vms_db_prod}"
DB_NAME=""

if [ -f "$BASE/api.env" ]; then
  DB_NAME=$(grep -E '^DATABASE_URL=' "$BASE/api.env" | sed -E 's#.*/([A-Za-z0-9_]+)(\?.*)?$#\1#' || true)
fi

MODE="${1:-}"

tampilkan_bantuan() {
  echo "Pemakaian:"
  echo "  $0 --cek [CONTAINER] [DB_NAME]                     # Hitung baris biometrik"
  echo "  $0 --db [CONTAINER] [DB_NAME]                      # Bersihkan face_embedding di DB aktif"
  echo "  $0 --berkas <input.dump> <output_sanitasi.dump>    # Buat salinan dump bersih biometrik"
  exit 1
}

[ -n "$MODE" ] || tampilkan_bantuan

case "$MODE" in
  --cek)
    CT="${2:-$DB_CT}"
    DB="${3:-$DB_NAME}"
    [ -n "$DB" ] || { echo "Nama DB wajib diisi atau disetel di api.env" >&2; exit 2; }
    echo "Memeriksa biometrik di kontainer $CT, DB $DB..."
    n=$(docker exec "$CT" sh -c "psql -U \"\$POSTGRES_USER\" -d '$DB' -Atc \"SELECT count(*) FROM employee WHERE face_embedding IS NOT NULL;\"" 2>/dev/null || echo "0")
    echo "Jumlah baris employee dengan face_embedding terisi: $n"
    ;;

  --db)
    CT="${2:-$DB_CT}"
    DB="${3:-$DB_NAME}"
    [ -n "$DB" ] || { echo "Nama DB wajib diisi atau disetel di api.env" >&2; exit 2; }
    echo "PERINGATAN: Membersihkan face_embedding di kontainer $CT, DB $DB..."
    n_awal=$(docker exec "$CT" sh -c "psql -U \"\$POSTGRES_USER\" -d '$DB' -Atc \"SELECT count(*) FROM employee WHERE face_embedding IS NOT NULL;\"" 2>/dev/null || echo "0")
    docker exec "$CT" sh -c "psql -U \"\$POSTGRES_USER\" -d '$DB' -c \"UPDATE employee SET face_embedding = NULL WHERE face_embedding IS NOT NULL;\""
    echo "Sanitasi berhasil. Baris dibersihkan: $n_awal"
    ;;

  --berkas)
    IN="${2:-}"
    OUT="${3:-}"
    [ -n "$IN" ] && [ -n "$OUT" ] || { echo "Format: $0 --berkas <input.dump> <output.dump>" >&2; exit 2; }
    [ -s "$IN" ] || { echo "Berkas masukan tidak ditemukan: $IN" >&2; exit 2; }
    
    TMP_CT="vms_sanitize_tmp_$$"
    TMP_PW="sanitize_pw_$$"
    IMAGE="${VMS_PG_IMAGE:-postgres:18-alpine}"
    if docker inspect "$DB_CT" >/dev/null 2>&1; then
      IMAGE=$(docker inspect -f '{{.Config.Image}}' "$DB_CT")
    fi

    echo "Menjalankan Postgres sementara ($IMAGE, --network none)..."
    docker run -d --name "$TMP_CT" --network none --memory 512m -e POSTGRES_PASSWORD="$TMP_PW" "$IMAGE" >/dev/null
    cleanup() { docker rm -f "$TMP_CT" >/dev/null 2>&1 || true; }
    trap cleanup EXIT

    echo "Menunggu Postgres siap..."
    for _ in $(seq 1 30); do
      if docker exec "$TMP_CT" pg_isready -U postgres >/dev/null 2>&1; then break; fi
      sleep 1
    done

    echo "Memulihkan berkas masukan ke basis data sementara..."
    docker exec -i "$TMP_CT" pg_restore -U postgres -d postgres < "$IN" 2>/dev/null || true

    echo "Membersihkan face_embedding..."
    docker exec "$TMP_CT" psql -U postgres -d postgres -c "UPDATE employee SET face_embedding = NULL WHERE face_embedding IS NOT NULL;" >/dev/null 2>&1 || true

    echo "Mengekspor ulang dump tersanitasi ke $OUT..."
    docker exec "$TMP_CT" pg_dump -U postgres -d postgres -Fc > "$OUT"
    [ -s "$OUT" ] || { echo "Gagal mengekspor dump sanitasi" >&2; exit 3; }

    echo "Sanitasi dump selesai: $OUT ($(stat -c %s "$OUT") bita)"
    ;;

  *)
    tampilkan_bantuan
    ;;
esac
