#!/usr/bin/env bash
# Uji sebelum dipasang: sintaks nginx dengan variabel contoh (tanpa menyentuh server). Butuh docker di mesin yang menjalankan.
# Pakai: bash deploy/hikvision/uji-konfigurasi.sh [folder-konfigurasi]
set -euo pipefail
DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
HIK_BIND_IP=127.0.0.1 HIK_PORT=8088 HIK_IP_1=192.168.88.13 HIK_IP_2=192.168.88.12 \
  envsubst '${HIK_BIND_IP} ${HIK_PORT} ${HIK_IP_1} ${HIK_IP_2}' < "$DIR/nginx.conf.template" > "$TMP"
if ! command -v docker >/dev/null 2>&1; then echo "docker tidak ada: hanya templat dirender (tidak diuji nginx -t)"; exit 0; fi
docker run --rm -v "$TMP:/etc/nginx/nginx.conf:ro" nginx:1.27-alpine nginx -t
echo "LULUS: konfigurasi nginx valid"
