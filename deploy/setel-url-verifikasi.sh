#!/usr/bin/env bash
# Menyetel alamat di QR tanda tangan (PUBLIC_VERIFY_URL) ke domain publik portal. Aman dijalankan ulang.
# Temuan 2026-10-08: QR SK masih berisi alamat Tailscale, sehingga tidak bisa dibuka dari HP di luar Tailscale.
#
# Jalankan dari komputer pemilik (bash UCRT64, di folder repo):
#   ssh ageng@192.168.88.160 "bash -s" < deploy/setel-url-verifikasi.sh
#
# Yang dikerjakan:
#   1. api.env → PUBLIC_VERIFY_URL=https://portal.visiontechindo.com/verify (salinan api.env.sebelum-url-verifikasi.<waktu>)
#      Salinan rollback api.env.sebelum-vms_api.* ikut disamakan baris itu saja, agar `kembalikan` tidak membawa
#      alamat Tailscale kembali.
#   2. buat ulang kontainer api, cek /ready dan nilai yang dibaca API.
# QR dibuat ulang setiap SK/laporan dibuka atau diunduh, jadi dokumen lama ikut memakai alamat baru saat dibuka lagi.
set -euo pipefail
BASE="$HOME/deploy/vms-mvp"
cd "$BASE"
URL="${1:-https://portal.visiontechindo.com/verify}"
ENV_FILE=api.env

set_line() {  # set_line <berkas>: ganti/tambah baris PUBLIC_VERIFY_URL tanpa menyentuh baris lain
  local f="$1"
  if grep -q '^PUBLIC_VERIFY_URL=' "$f"; then
    sed -i "s#^PUBLIC_VERIFY_URL=.*#PUBLIC_VERIFY_URL=$URL#" "$f"
  else
    printf 'PUBLIC_VERIFY_URL=%s\n' "$URL" >> "$f"
  fi
}

echo "== 1/2 api.env"
[ -f "$ENV_FILE" ] || { echo "GAGAL: $BASE/$ENV_FILE tidak ada"; exit 1; }
OLD=$(grep -E '^PUBLIC_VERIFY_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)
echo "   sebelumnya: ${OLD:-<kosong: bawaan localhost>}"
if [ "$OLD" = "$URL" ]; then
  echo "   sudah benar — tidak ada yang diubah"
  exit 0
fi
BACKUP="api.env.sebelum-url-verifikasi.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$BACKUP" && chmod 600 "$BACKUP"
echo "   salinan: $BACKUP"
set_line "$ENV_FILE"
for b in api.env.sebelum-vms_api.*; do
  [ -f "$b" ] && set_line "$b" && echo "   disamakan: $b"
done
echo "   sekarang: $URL"

echo "== 2/2 buat ulang api dan periksa"
docker compose up -d --force-recreate api >/dev/null
for _ in $(seq 1 24); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)" = 200 ] && break
  sleep 5
done
echo "   api /ready: $(curl -s localhost:8000/ready)"
SEEN=$(docker exec vms_api python -c "from app.core.config import settings; print(settings.PUBLIC_VERIFY_URL)")
if [ "$SEEN" != "$URL" ]; then
  echo "GAGAL: API membaca '$SEEN' — periksa api.env (salinan: $BACKUP)"
  exit 1
fi
echo "SELESAI. Buka/unduh ulang SK, lalu scan QR-nya dari HP tanpa Tailscale."
