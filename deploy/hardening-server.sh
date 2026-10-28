#!/usr/bin/env bash
# Pengerasan server (SSH, firewall, pembaruan otomatis). PERLU root — dijalankan PEMILIK, bukan otomatis.
#   sudo bash deploy/hardening-server.sh --cek    → hanya menampilkan keadaan sekarang vs yang diinginkan (aman)
#   sudo bash deploy/hardening-server.sh --ya     → menerapkan
# SEBELUM --ya: buka SATU sesi SSH lagi dan biarkan terbuka; uji login kunci dari sesi baru sebelum menutup yang lama.
# Catatan penting: port yang DIPUBLIKASIKAN Docker (-p) melewati ufw. Kecuali dibatasi, DB/MinIO tetap terbuka —
# ikat ke 127.0.0.1 di compose (mis. "127.0.0.1:5433:5432"). Skrip ini hanya memeriksa dan memperingatkan.
set -uo pipefail

MODE="${1:---cek}"
[ "$MODE" = "--cek" ] || [ "$MODE" = "--ya" ] || { echo "Pemakaian: $0 --cek|--ya" >&2; exit 2; }
[ "$(id -u)" = "0" ] || { echo "Jalankan dengan sudo." >&2; exit 2; }

DROPIN=/etc/ssh/sshd_config.d/99-vms-hardening.conf
WANT_SSHD='PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 30'

say() { printf '%s\n' "$*"; }

say "== SSH (efektif sekarang)"
sshd -T 2>/dev/null | grep -E '^(permitrootlogin|passwordauthentication|x11forwarding|maxauthtries) ' || say "(sshd -T gagal)"

say "== Kunci yang terdaftar (periksa; cabut yang tak dikenal)"
for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
  [ -f "$f" ] && { say "$f:"; awk '{print "  " $1, $NF}' "$f"; }
done

say "== Port mendengar di semua alamat"
ss -tlnH | awk '$4 ~ /^(0\.0\.0\.0|\*|\[::\]):/ {print "  " $4}' | sort -u

say "== Port Docker terbuka ke semua alamat (melewati ufw)"
docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E '0\.0\.0\.0:' | sed 's/^/  /' || true

say "== Paket"
for p in ufw fail2ban unattended-upgrades; do
  if dpkg -s "$p" >/dev/null 2>&1; then say "  $p: terpasang"; else say "  $p: BELUM"; fi
done

[ "$MODE" = "--cek" ] && { say; say "Mode --cek selesai; tidak ada yang diubah."; exit 0; }

say; say "== MENERAPKAN"
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ufw fail2ban unattended-upgrades

printf '%s\n' "$WANT_SSHD" > "$DROPIN"
if sshd -t; then
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
  say "SSH dikeraskan ($DROPIN). Uji login kunci dari sesi BARU sekarang."
else
  rm -f "$DROPIN"
  say "sshd -t gagal; perubahan SSH dibatalkan." >&2
  exit 3
fi

systemctl enable --now fail2ban >/dev/null 2>&1
systemctl enable --now unattended-upgrades >/dev/null 2>&1

# Firewall: tolak semua masuk kecuali SSH, web, dan seluruh lalu lintas Tailscale.
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw allow "${WEB_PORT:-8080}/tcp" >/dev/null
ufw allow "${API_PORT:-8000}/tcp" >/dev/null
ip link show tailscale0 >/dev/null 2>&1 && ufw allow in on tailscale0 >/dev/null
ufw --force enable >/dev/null
ufw status verbose | sed 's/^/  /'

say; say "Selesai. LANGKAH BERIKUT (manual): ikat port DB/MinIO di compose ke 127.0.0.1 agar tidak terbuka ke jaringan."
