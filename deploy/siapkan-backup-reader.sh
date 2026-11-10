#!/usr/bin/env bash
# Siapkan pengguna `backup-reader` (HANYA-BACA, SFTP terkurung) agar Windows 'pobonguar' bisa menarik cadangan.
# Idempoten; jalankan sebagai root: sudo bash siapkan-backup-reader.sh <berkas-kunci-publik-ssh-windows.pub> [pengguna-penulis]
#   - Tanpa shell, tanpa sandi, hanya `internal-sftp -R` (baca saja), chroot ke /srv/vms-cadangan, tanpa forwarding.
#   - Kunci dibatasi: restrict + from=<IP Tailscale pobonguar> (ubah lewat VMS_READER_FROM).
#   - Cadangan ditulis oleh pengguna penulis (bawaan $SUDO_USER) ke /srv/vms-cadangan/{prod,beta}.
# Membatalkan: lihat bagian Rollback di docs/CADANGAN-WINDOWS.md.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Jalankan sebagai root (sudo)." >&2; exit 2; }
PUB="${1:?Pakai: siapkan-backup-reader.sh <kunci.pub> [penulis]}"
WRITER="${2:-${SUDO_USER:-}}"
[ -n "$WRITER" ] && id "$WRITER" >/dev/null 2>&1 || { echo "Pengguna penulis tidak valid: '$WRITER'" >&2; exit 2; }
FROM="${VMS_READER_FROM:-100.94.81.43}"
ROOT=/srv/vms-cadangan
KEYS=/etc/ssh/backup-reader.authorized_keys
CONF=/etc/ssh/sshd_config.d/50-backup-reader.conf
[ -r "$PUB" ] || { echo "Tidak bisa membaca $PUB" >&2; exit 2; }
if grep -q 'PRIVATE KEY' "$PUB"; then echo "Itu kunci PRIVAT. Berikan berkas .pub." >&2; exit 2; fi
grep -qE '^ssh-(ed25519|rsa) ' "$PUB" || { echo "Format .pub tidak dikenal (pakai ssh-ed25519)." >&2; exit 2; }

getent group vms-cadangan >/dev/null || groupadd --system vms-cadangan
id backup-reader >/dev/null 2>&1 || useradd --system --gid vms-cadangan --home-dir "$ROOT" --shell /usr/sbin/nologin --no-create-home backup-reader
usermod -g vms-cadangan -d "$ROOT" -s /usr/sbin/nologin backup-reader
passwd -l backup-reader >/dev/null 2>&1 || true

# Akar chroot WAJIB milik root dan tidak dapat ditulis siapa pun selain root.
mkdir -p "$ROOT/prod" "$ROOT/beta"
chown root:root "$ROOT"; chmod 755 "$ROOT"
for d in prod beta; do chown "$WRITER:vms-cadangan" "$ROOT/$d"; chmod 750 "$ROOT/$d"; done
# Berkas baru dibuat penulis dengan umask 077 lalu chmod 640 oleh skrip cadangan (grup vms-cadangan membaca).
# setgid agar berkas baru ikut grup vms-cadangan.
chmod g+s "$ROOT/prod" "$ROOT/beta"

# Satu kunci, dibatasi sumber. 'restrict' mematikan pty, forwarding, agent, X11.
{
  echo "# dikelola siapkan-backup-reader.sh"
  while read -r tipe kunci _; do
    case "$tipe" in ssh-ed25519|ssh-rsa) echo "restrict,from=\"$FROM\" $tipe $kunci backup-reader@pobonguar" ;; esac
  done < "$PUB"
} > "$KEYS.baru"
chown root:root "$KEYS.baru"; chmod 644 "$KEYS.baru"; mv -f "$KEYS.baru" "$KEYS"

mkdir -p /etc/ssh/sshd_config.d
grep -Eqs '^\s*Include\s+/etc/ssh/sshd_config\.d/' /etc/ssh/sshd_config || echo "PERINGATAN: sshd_config tidak meng-Include sshd_config.d; tambahkan manual." >&2
[ -f "$CONF" ] && cp -a "$CONF" "$CONF.bak.$(date +%Y%m%d-%H%M%S)"
cat > "$CONF" <<EOT
Match User backup-reader
    AuthorizedKeysFile $KEYS
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    AllowTcpForwarding no
    X11Forwarding no
    PermitTTY no
    PermitTunnel no
    ChrootDirectory $ROOT
    ForceCommand internal-sftp -R
EOT
sshd -t || { echo "sshd -t gagal; konfigurasi TIDAK dimuat. Periksa $CONF" >&2; exit 3; }
systemctl reload ssh 2>/dev/null || systemctl reload sshd
echo "OK: backup-reader siap. Uji dari Windows: sftp -i <kunci> backup-reader@<ip-tailscale-visiontech-bar>"
