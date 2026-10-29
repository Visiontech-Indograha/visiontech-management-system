#!/usr/bin/env bash
# Ikat port API (8000 prod, 8001 beta) dan MinIO prod (9000) ke localhost agar tidak terbuka ke LAN.
# Aman karena: Cloudflare Tunnel hanya ke localhost:8080, Tailscale Serve/Funnel hanya ke 127.0.0.1:{8000,8001,8080,8081},
# aplikasi/backup/deploy memakai jaringan Docker atau localhost. API juga diikat ke gerbang Docker (172.17.0.1) agar monitor
# Uptime Kuma (host.docker.internal) tetap bisa menjangkau; alamat itu tidak terjangkau dari LAN.
#   bash ~/deploy/vms-mvp/src/deploy/tutup-port-layanan.sh --cek    # hanya melihat
#   bash ~/deploy/vms-mvp/src/deploy/tutup-port-layanan.sh --ya     # menerapkan (cadangan compose dibuat; jam sepi, API restart ±10 dtk)
set -uo pipefail
MODE="${1:---cek}"
[ "$MODE" = "--cek" ] || [ "$MODE" = "--ya" ] || { echo "Pemakaian: $0 --cek|--ya" >&2; exit 2; }
GW=$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null); GW="${GW:-172.17.0.1}"
STAMP=$(date +%Y%m%d-%H%M)
rc=0

ubah() {   # ubah DIR BERKAS POLA GANTI "compose -f ..." LAYANAN CEK_URL
  local dir="$1" file="$2" from="$3" to="$4" cf="$5" svc="$6" url="$7"
  cd "$dir" || { echo "!! $dir tidak ada"; rc=1; return; }
  if grep -qF -- "$to" "$file"; then echo "ok   $dir/$file sudah terikat lokal"; return; fi
  grep -qF -- "$from" "$file" || { echo "!!   $dir/$file: baris '$from' tidak ditemukan (periksa manual)"; rc=1; return; }
  echo "ubah $dir/$file : $from  →  $to"
  [ "$MODE" = "--cek" ] && return
  cp -p "$file" "$file.bak-$STAMP"
  sed -i "s|$(printf '%s' "$from" | sed 's/[][\.*^$|/]/\&/g')|$to|" "$file"
  # shellcheck disable=SC2086
  if ! docker compose $cf config -q; then echo "!! compose tidak valid, dipulihkan"; cp -p "$file.bak-$STAMP" "$file"; rc=1; return; fi
  # shellcheck disable=SC2086
  docker compose $cf up -d --no-deps "$svc" 2>&1 | tail -n 2
  sleep 8
  [ -n "$url" ] && echo "     $svc: $(curl -s -o /dev/null -w '%{http_code}' "$url")"
}

echo "gerbang Docker: $GW | mode: $MODE"
ubah "$HOME/deploy/vms-mvp"  compose.yml 'ports: ["8000:8000"]'      "ports: [\"127.0.0.1:8000:8000\", \"$GW:8000:8000\"]" "" api "http://localhost:8000/ready"
ubah "$HOME/deploy/vms-beta" compose.yml 'ports: ["8001:8000"]'      "ports: [\"127.0.0.1:8001:8000\", \"$GW:8001:8000\"]" "" api "http://localhost:8001/ready"
ubah "$HOME/deploy/visiontech" docker-compose.minio.prod.yml '      - "9000:9000"' '      - "127.0.0.1:9000:9000"' "-f docker-compose.prod.yml -f docker-compose.minio.prod.yml" minio ""

echo "== pendengar sekarang"; ss -tln | awk '$4 ~ /:(8000|8001|9000)$/ {print "   "$4}' | sort -u
echo "== /ready prod=$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready) beta=$(curl -s -o /dev/null -w '%{http_code}' localhost:8001/ready)"
[ "$MODE" = "--ya" ] && echo "Cek monitor Uptime Kuma (harus tetap hijau). Pulihkan: salin berkas *.bak-$STAMP kembali lalu 'docker compose up -d --no-deps <layanan>'."
exit $rc
