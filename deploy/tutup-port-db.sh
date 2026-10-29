#!/usr/bin/env bash
# Ikat port DB produksi (5433) ke 127.0.0.1 agar tidak terbuka ke LAN. Aplikasi, backup, dan deploy memakai jaringan Docker
# (db:5432) atau `docker exec`, jadi tidak terpengaruh. DB restart beberapa detik: jalankan di jam sepi.
#   bash ~/deploy/vms-mvp/src/deploy/tutup-port-db.sh --cek   # hanya melihat keadaan
#   bash ~/deploy/vms-mvp/src/deploy/tutup-port-db.sh --ya    # menerapkan (cadangan berkas compose dibuat dulu)
# Berkas compose DB produksi: ~/deploy/visiontech/docker-compose.prod.yml (+ docker-compose.minio.prod.yml).
set -uo pipefail
MODE="${1:---cek}"
[ "$MODE" = "--cek" ] || [ "$MODE" = "--ya" ] || { echo "Pemakaian: $0 --cek|--ya" >&2; exit 2; }
DIR="${VMS_DB_COMPOSE_DIR:-$HOME/deploy/visiontech}"
cd "$DIR" || { echo "$DIR tidak ada" >&2; exit 1; }
F=(-f docker-compose.prod.yml -f docker-compose.minio.prod.yml)
ready() { curl -s -o /dev/null -w '%{http_code}' localhost:"${API_PORT:-8000}"/ready; }

echo "== sekarang: pendengar :5433 = $(ss -tln | awk '$4 ~ /:5433$/ {print $4}' | tr '\n' ' ')  | /ready=$(ready)"
if grep -q '^      - "127.0.0.1:5433:5432"' docker-compose.prod.yml; then echo "Sudah terikat 127.0.0.1 (tidak ada yang diubah)."; exit 0; fi
grep -q '^      - "5433:5432"' docker-compose.prod.yml || { echo "Baris port 5433 tidak ditemukan; periksa manual." >&2; exit 3; }
[ "$MODE" = "--cek" ] && { echo "Akan mengubah '5433:5432' → '127.0.0.1:5433:5432' lalu membuat ulang kontainer db."; exit 0; }

BAK="docker-compose.prod.yml.bak-$(date +%Y%m%d-%H%M)"
cp -p docker-compose.prod.yml "$BAK"
sed -i 's|^      - "5433:5432"|      - "127.0.0.1:5433:5432"|' docker-compose.prod.yml
if ! docker compose "${F[@]}" config -q; then echo "compose tidak valid, dipulihkan" >&2; cp -p "$BAK" docker-compose.prod.yml; exit 4; fi
docker compose "${F[@]}" up -d --no-deps db 2>&1 | tail -n 3
for _ in $(seq 1 30); do [ "$(docker inspect -f '{{.State.Health.Status}}' vms_db_prod 2>/dev/null)" = healthy ] && break; sleep 2; done
sleep 5
echo "== sesudah: pendengar :5433 = $(ss -tln | awk '$4 ~ /:5433$/ {print $4}' | tr '\n' ' ')  | db=$(docker inspect -f '{{.State.Health.Status}}' vms_db_prod) | /ready=$(ready)"
[ "$(ready)" = 200 ] || { echo "PERINGATAN: /ready belum 200. Pulihkan: cp -p $DIR/$BAK $DIR/docker-compose.prod.yml && docker compose ${F[*]} up -d --no-deps db" >&2; exit 5; }
echo "Selesai. Cadangan: $DIR/$BAK"
