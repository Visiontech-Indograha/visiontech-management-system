#!/usr/bin/env bash
# Menyetel alamat publik yang dibagikan API ke browser/HP ke domain portal. Aman dijalankan ulang.
# Temuan 2026-10-08: QR SK masih berisi alamat Tailscale, dan pratinjau berkas ("Berkas saya") tidak tampil di luar
# Tailscale. Keduanya diisi dari api.env:
#   PUBLIC_VERIFY_URL → isi QR tanda tangan       = https://portal.visiontechindo.com/verify
#   MINIO_PUBLIC_URL  → host URL berkas presigned = https://portal.visiontechindo.com (Caddy: /vms-files/* → MinIO)
#
# Jalankan dari komputer pemilik (bash UCRT64, di folder repo):
#   ssh ageng@192.168.88.160 "bash -s" < deploy/setel-url-verifikasi.sh
#
# Yang dikerjakan:
#   1. api.env → kedua baris di atas (salinan api.env.sebelum-url-verifikasi.<waktu>). Salinan rollback
#      api.env.sebelum-vms_api.* ikut disamakan baris itu saja, agar `kembalikan` tidak membawa alamat Tailscale kembali.
#   2. buat ulang kontainer api, cek /ready dan nilai yang benar-benar dibaca API.
# QR & URL berkas dibuat ulang setiap dokumen dibuka, jadi dokumen lama ikut memakai alamat baru saat dibuka lagi.
set -euo pipefail
BASE="$HOME/deploy/vms-mvp"
cd "$BASE"
DOMAIN="${1:-https://portal.visiontechindo.com}"
ENV_FILE=api.env
WANT="PUBLIC_VERIFY_URL=$DOMAIN/verify
MINIO_PUBLIC_URL=$DOMAIN"

set_line() {  # set_line <berkas> <KUNCI> <nilai>: ganti/tambah satu baris tanpa menyentuh baris lain
  local f="$1" k="$2" v="$3"
  if grep -q "^$k=" "$f"; then
    sed -i "s#^$k=.*#$k=$v#" "$f"
  else
    printf '%s=%s\n' "$k" "$v" >> "$f"
  fi
}

echo "== 1/2 api.env"
[ -f "$ENV_FILE" ] || { echo "GAGAL: $BASE/$ENV_FILE tidak ada"; exit 1; }
CHANGED=0
while IFS='=' read -r k v; do
  old=$(grep -E "^$k=" "$ENV_FILE" | head -1 | cut -d= -f2- || true)
  echo "   $k sebelumnya: ${old:-<kosong>}"
  [ "$old" = "$v" ] || CHANGED=1
done <<< "$WANT"
if [ "$CHANGED" = 0 ]; then
  echo "   sudah benar — tidak ada yang diubah"
  exit 0
fi
BACKUP="api.env.sebelum-url-verifikasi.$(date +%Y%m%d-%H%M%S)"
cp -p "$ENV_FILE" "$BACKUP" && chmod 600 "$BACKUP"
echo "   salinan: $BACKUP"
while IFS='=' read -r k v; do
  set_line "$ENV_FILE" "$k" "$v"
  for b in api.env.sebelum-vms_api.*; do
    [ -f "$b" ] && set_line "$b" "$k" "$v"
  done
  echo "   $k sekarang: $v"
done <<< "$WANT"

echo "== 2/2 buat ulang api dan periksa"
docker compose up -d --force-recreate api >/dev/null
for _ in $(seq 1 24); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)" = 200 ] && break
  sleep 5
done
echo "   api /ready: $(curl -s localhost:8000/ready)"
SEEN=$(docker exec vms_api python -c "from app.core.config import settings as s
print(f'PUBLIC_VERIFY_URL={s.PUBLIC_VERIFY_URL}'); print(f'MINIO_PUBLIC_URL={s.MINIO_PUBLIC_URL}')")
if [ "$SEEN" != "$WANT" ]; then
  echo "GAGAL: API membaca nilai lain — periksa api.env (salinan: $BACKUP)"
  echo "$SEEN" | sed 's/^/   /'
  exit 1
fi
echo "SELESAI. Buka ulang 'Berkas saya' dan SK, lalu scan QR dari HP tanpa Tailscale."
