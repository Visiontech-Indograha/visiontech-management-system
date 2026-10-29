#!/usr/bin/env bash
# Pemeriksaan kesehatan server produksi. Dipanggil cron tiap 5 menit; alert Discord hanya saat keadaan BERUBAH
# (masalah baru / pulih), bukan tiap 5 menit.
#   */5 * * * * /home/ageng/deploy/vms-mvp/healthcheck.sh >> /home/ageng/deploy/vms-mvp/logs/healthcheck.log 2>&1
# Opsi: --cetak  → hanya mencetak hasil (tanpa kirim Discord, tanpa mengubah status).
# Kontainer yang sengaja dimatikan (mis. vms_beta_face): tulis namanya di berkas `healthcheck.skip` (satu per baris).
# Env (notify.env): DISCORD_WEBHOOK_ALERT (bawaan: DISCORD_WEBHOOK_DEPLOY), VMS_DEPLOY_DIR, API_PORT, WEB_PORT.
set -uo pipefail

BASE="${VMS_DEPLOY_DIR:-$HOME/deploy/vms-mvp}"
cd "$BASE" || { echo "healthcheck: $BASE tidak ada" >&2; exit 1; }
[ -f notify.env ] && . ./notify.env
HOOK="${DISCORD_WEBHOOK_ALERT:-${DISCORD_WEBHOOK_DEPLOY:-}}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-8080}"
API_CONTAINER="${VMS_CONTAINER_PREFIX:-vms}_api"
STATE=".healthcheck.state"
PRINT_ONLY=0
[ "${1:-}" = "--cetak" ] && PRINT_ONLY=1

problems=()
add() { problems+=("$1"); }

# 1. Kontainer berkebijakan restart (always/unless-stopped) harus berjalan — menangkap MinIO yang diam-diam mati.
while read -r name; do
  policy=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$name" 2>/dev/null)
  case "$policy" in always|unless-stopped) ;; *) continue ;; esac
  [ -f healthcheck.skip ] && grep -qxF "$name" healthcheck.skip && continue
  status=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null)
  [ "$status" = "running" ] || add "kontainer $name tidak berjalan ($status)"
  restarts=$(docker inspect -f '{{.RestartCount}}' "$name" 2>/dev/null || echo 0)
  [ "${restarts:-0}" -gt 3 ] && add "kontainer $name restart $restarts kali"
done < <(docker ps -a --format '{{.Names}}')

# 2. Endpoint HTTP
code() { curl -s -m 6 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo 000; }
[ "$(code "localhost:${API_PORT}/health")" = "200" ] || add "API /health tidak 200"
[ "$(code "localhost:${API_PORT}/ready")" = "200" ] || add "API /ready tidak 200 (DB?)"
[ "$(code "localhost:${WEB_PORT}/")" = "200" ] || add "web tidak 200"
[ "$(code "localhost:${WEB_PORT}/api/v1/auth/me")" = "401" ] || add "jalur proxy web→API tidak 401"

# 3. API dapat menjangkau penyimpanan objek (MinIO) — tanpanya unggah foto/dokumen dan backup gagal.
if ! docker exec "$API_CONTAINER" python -c 'import os,socket; h,p=os.environ["MINIO_ENDPOINT"].rsplit(":",1); socket.create_connection((h,int(p)),3)' >/dev/null 2>&1; then
  add "API tidak bisa menjangkau MinIO (unggah berkas & backup MinIO gagal)"
fi

# 4. Sumber daya
disk=$(df --output=pcent / | tail -n 1 | tr -dc '0-9')
[ "${disk:-0}" -ge 80 ] && add "disk / terpakai ${disk}%"
avail_mb=$(awk '/MemAvailable/ {printf "%d", $2/1024}' /proc/meminfo)
[ "${avail_mb:-9999}" -lt 400 ] && add "RAM tersedia ${avail_mb} MB (<400)"
swap_total=$(awk '/SwapTotal/ {print $2}' /proc/meminfo)
swap_free=$(awk '/SwapFree/ {print $2}' /proc/meminfo)
if [ "${swap_total:-0}" -gt 0 ]; then
  swap_used_pct=$(( (swap_total - swap_free) * 100 / swap_total ))
  [ "$swap_used_pct" -ge 60 ] && add "swap terpakai ${swap_used_pct}%"
fi

# 5. Umur backup: lokal dan luar-server (offsite) harus < 26 jam.
age_h() { [ -e "$1" ] && echo $(( ( $(date +%s) - $(stat -c %Y "$1") ) / 3600 )) || echo 9999; }
newest=$(ls -1t backups/*.dump 2>/dev/null | head -n 1)
[ -n "$newest" ] && [ "$(age_h "$newest")" -lt 26 ] || add "backup lokal terakhir lebih dari 26 jam"
if [ -f offsite.env ]; then
  [ "$(age_h .offsite.ok)" -lt 26 ] || add "backup luar-server terakhir lebih dari 26 jam"
fi

summary=""
for p in "${problems[@]:-}"; do [ -n "$p" ] && summary="${summary}- ${p}\n"; done

if [ "$PRINT_ONLY" = "1" ]; then
  if [ -z "$summary" ]; then echo "SEHAT"; else printf '%b' "MASALAH:\n$summary"; fi
  exit 0
fi

new_sig=$(printf '%b' "$summary" | md5sum | cut -d' ' -f1)
old_sig=$(cat "$STATE" 2>/dev/null || echo "")
[ "$new_sig" = "$old_sig" ] && exit 0
echo "$new_sig" > "$STATE"

if [ -n "$summary" ]; then
  text="🔴 **VMS produksi bermasalah** ($(hostname))\n${summary}"
elif [ -n "$old_sig" ]; then
  text="✅ **VMS produksi pulih** ($(hostname)) — semua pemeriksaan lolos."
else
  exit 0
fi
echo "$(date '+%F %T') $(printf '%b' "$text" | tr '\n' ' ')"
if [ -n "$HOOK" ]; then
  body=$(printf '%b' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}')
  curl -s -m 10 -o /dev/null -H 'Content-Type: application/json' -d "{\"content\":\"${body}\"}" "$HOOK" || true
fi
