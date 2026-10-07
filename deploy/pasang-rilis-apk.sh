#!/usr/bin/env bash
# Menyiapkan folder rilis APK (pembaruan otomatis aplikasi HP, docs/32) di server VMS, SEKALI. Aman dijalankan ulang.
#
# Jalankan dari komputer pemilik (CMD/PowerShell Windows), SETELAH rilis API yang memuat /app/android/* ter-deploy:
#   ssh ageng@192.168.88.160 "bash -s" < deploy\pasang-rilis-apk.sh
#
# Yang dikerjakan:
#   1. buat folder ~/deploy/vms-mvp/rilis/android (diisi skrip scripts/rilis-apk.sh dari laptop)
#   2. tulis compose.override.yml: folder itu di-mount READ-ONLY ke vms_api sebagai /srv/rilis + APP_RELEASE_DIR.
#      compose.yml dan api.env TIDAK disentuh; autodeploy (docker compose tanpa -f) otomatis membaca override.
#      Bila sudah ada override lain → berhenti (tidak pernah menimpa berkas yang tidak dikenal).
#   3. pastikan `docker compose config` memuat mount itu
#   4. buat ulang kontainer api, cek /ready dan /api/v1/app/android/update
set -euo pipefail
BASE="$HOME/deploy/vms-mvp"
cd "$BASE"
MARK="# vms: rilis-apk (deploy/pasang-rilis-apk.sh)"

echo "== 1/4 folder rilis"
mkdir -p rilis/android
chmod 755 rilis rilis/android
echo "   $BASE/rilis/android"

echo "== 2/4 compose.override.yml"
if [ -f compose.override.yml ]; then
  if grep -qF "$MARK" compose.override.yml; then
    echo "   sudah ada, dilewati"
  else
    echo "GAGAL: compose.override.yml sudah ada dan bukan buatan skrip ini — gabungkan manual (lihat docs/32)."
    exit 1
  fi
else
  cat > compose.override.yml <<EOF
$MARK
# Folder rilis APK dibaca API (read-only). Dihapus = fitur pembaruan otomatis mati (API menjawab UP_TO_DATE).
services:
  api:
    volumes:
      - ./rilis:/srv/rilis:ro
    environment:
      APP_RELEASE_DIR: /srv/rilis
EOF
  echo "   dibuat"
fi

echo "== 3/4 validasi compose"
docker compose config >/tmp/vms-compose-config.txt
grep -q "/srv/rilis" /tmp/vms-compose-config.txt || { echo "GAGAL: mount /srv/rilis tidak terbaca compose"; exit 1; }
grep -q "read_only: true" /tmp/vms-compose-config.txt || { echo "GAGAL: mount tidak read-only"; exit 1; }
rm -f /tmp/vms-compose-config.txt
echo "   mount /srv/rilis (read-only) terbaca"

echo "== 4/4 buat ulang api dan periksa"
docker compose up -d --force-recreate api
for i in $(seq 1 24); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)" = 200 ] && break; sleep 5
done
echo "   api /ready: $(curl -s localhost:8000/ready)"
code=$(curl -s -o /tmp/vms-update.json -w '%{http_code}' 'localhost:8000/api/v1/app/android/update?build=0')
if [ "$code" = 200 ]; then
  echo "   /app/android/update: $(cat /tmp/vms-update.json)"
else
  echo "   PERINGATAN: /app/android/update = $code (API versi lama? deploy rilis yang memuat fitur ini dulu)"
fi
rm -f /tmp/vms-update.json
docker exec vms_api sh -c 'test -d /srv/rilis/android && echo "   folder terlihat dari kontainer: /srv/rilis/android"'
echo "SELESAI. Terbitkan APK dari laptop: scripts\\rilis-apk.bat bangun lalu scripts\\rilis-apk.bat kirim"
