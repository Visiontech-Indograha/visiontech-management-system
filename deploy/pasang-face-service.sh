#!/usr/bin/env bash
# Memasang layanan wajah (face-service) di server VMS, SEKALI. Aman dijalankan ulang (idempoten).
#
# Jalankan dari komputer pemilik (CMD/PowerShell Windows):
#   ssh ageng@192.168.88.160 "bash -s" < deploy\pasang-face-service.sh
# Menyalakan juga kewajiban daftar wajah setelah login (bila layanan sudah terbukti sehat):
#   ssh ageng@192.168.88.160 "WAJIB_DAFTAR=ya bash -s" < deploy\pasang-face-service.sh
#
# Yang dikerjakan:
#   1. cadangkan compose.yml, api.env, autodeploy.sh
#   2. buat face.env (token acak) dan isi FACE_SERVICE_URL/TOKEN di api.env
#   3. tambah service `face` ke compose.yml (jaringan internal, TANPA port, batas memori)
#   4. ubah autodeploy.sh agar ikut menyalin face-service dari repo (pembaruan berikutnya otomatis)
#   5. build citra (model dibakukan ke citra), nyalakan `face`, nyalakan ulang `api` agar membaca env baru
#   6. cek: /health face dari kontainer api, dan /ready api
set -euo pipefail
BASE="$HOME/deploy/vms-mvp"
cd "$BASE"
STAMP=$(date +%Y%m%d-%H%M%S)
echo "== 1/6 cadangan ($STAMP)"
cp -p compose.yml "compose.yml.bak-face-$STAMP"
cp -p api.env "api.env.bak-face-$STAMP"
cp -p autodeploy.sh "autodeploy.sh.bak-face-$STAMP"

echo "== 2/6 rahasia dan env"
if [ ! -f face.env ]; then
  umask 077
  printf 'FACE_SERVICE_TOKEN=%s\nFACE_MAX_CONCURRENCY=2\n' "$(head -c 32 /dev/urandom | base64 | tr -d '/+=\n' | cut -c1-40)" > face.env
fi
chmod 600 face.env
TOKEN=$(grep '^FACE_SERVICE_TOKEN=' face.env | cut -d= -f2-)
grep -q '^FACE_SERVICE_URL=' api.env || echo 'FACE_SERVICE_URL=http://face:8001' >> api.env
if grep -q '^FACE_SERVICE_TOKEN=' api.env; then
  sed -i "s|^FACE_SERVICE_TOKEN=.*|FACE_SERVICE_TOKEN=$TOKEN|" api.env
else
  echo "FACE_SERVICE_TOKEN=$TOKEN" >> api.env
fi
if [ "${WAJIB_DAFTAR:-}" = "ya" ]; then
  grep -q '^FACE_ENROLLMENT_REQUIRED=' api.env && sed -i 's|^FACE_ENROLLMENT_REQUIRED=.*|FACE_ENROLLMENT_REQUIRED=true|' api.env \
    || echo 'FACE_ENROLLMENT_REQUIRED=true' >> api.env
  echo "   FACE_ENROLLMENT_REQUIRED=true (wajib daftar wajah setelah login)"
fi

echo "== 3/6 compose.yml"
python3 - <<'PY'
import re
p = "compose.yml"
s = open(p).read()
if re.search(r"^  face:", s, re.M):
    print("   service face sudah ada, dilewati")
else:
    block = """  face:
    build: ./face
    image: vms-mvp-face
    container_name: vms_face
    env_file: ./face.env
    mem_limit: 1200m
    restart: unless-stopped
    networks:
      vmsnet:
        aliases: [face]
"""
    i = s.rindex("\nnetworks:\n")
    s = s[: i + 1] + block + s[i + 1 :]
    # API menunggu face agar urutan nyala rapi (tidak wajib sehat).
    open(p, "w").write(s)
    print("   service face ditambahkan")
PY

echo "== 4/6 autodeploy.sh ikut menyalin face-service"
if grep -q 'cp -a src/face-service face' autodeploy.sh; then
  echo "   sudah"
else
  sed -i 's#rm -rf api web \&\& cp -a src/api src/web \. #rm -rf api web face \&\& cp -a src/api src/web . \&\& cp -a src/face-service face #' autodeploy.sh
  grep -q 'cp -a src/face-service face' autodeploy.sh || { echo "GAGAL mengubah autodeploy.sh"; exit 1; }
  echo "   diubah"
fi

echo "== 5/6 build dan nyalakan (unduh model ±124 MB, beberapa menit)"
SRC_HEAD=$(git -C src rev-parse --short HEAD)
rm -rf face && cp -a src/face-service face
docker compose build face
docker compose up -d face
sleep 5
docker compose up -d --force-recreate api   # buat ulang api agar membaca api.env baru

echo "== 6/6 pemeriksaan"
ok=0
for i in $(seq 1 30); do
  if docker exec vms_api python -c "import urllib.request,sys; sys.exit(0 if b'ok' in urllib.request.urlopen('http://face:8001/health').read() else 1)" 2>/dev/null; then ok=1; break; fi
  sleep 5
done
[ "$ok" = 1 ] && echo "   face /health: ok (dari kontainer api)" || { echo "   face BELUM sehat. Lihat: docker logs vms_face"; exit 1; }
for i in $(seq 1 12); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/ready)" = 200 ] && break; sleep 5
done
echo "   api /ready: $(curl -s localhost:8000/ready)"
docker ps --format '   {{.Names}}  {{.Status}}' | grep -E 'vms_(api|web|face)'
docker stats --no-stream --format '   memori {{.Name}}: {{.MemUsage}}' vms_face vms_api
echo "SELESAI (kode sumber: $SRC_HEAD)."
