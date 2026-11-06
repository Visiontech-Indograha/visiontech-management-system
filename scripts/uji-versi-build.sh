#!/usr/bin/env bash
# Uji nomor build mobile di scripts/versi.sh (tanpa Docker/DB): repo git sementara berriwayat pendek.
set -u
SRC=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cd "$T" && git init -q . && git config user.email t@t && git config user.name t
mkdir -p scripts api web mobile
cp "$SRC/scripts/versi.sh" scripts/
echo 1.7.0 > VERSION; echo 1.5.0 > api/VERSION
printf '{\n  "name": "w",\n  "version": "1.5.0",\n  "lockfileVersion": 3\n}\n' > web/package.json
echo "version: 1.6.0+1723" > mobile/pubspec.yaml; echo 1723 > mobile/BUILD-LANTAI.txt
git add . && git commit -qm a
gagal=0
b() { sed -n 's/^version: .*+//p' mobile/pubspec.yaml; }
cek() { if [ "$2" = "$3" ]; then echo "ok     $1"; else echo "GAGAL  $1 (dapat $2, harus $3)"; gagal=1; fi; }
bash scripts/versi.sh --tulis >/dev/null 2>&1
cek "riwayat 1 commit, versi baru: 1723 -> 1724 (bukan turun)" "$(b)" 1724
bash scripts/versi.sh --tulis >/dev/null 2>&1
cek "idempoten: tulis ulang versi sama tetap 1724" "$(b)" 1724
echo 1.7.1 > VERSION; bash scripts/versi.sh --tulis >/dev/null 2>&1
cek "versi baru 1.7.1 naik minimal 1 -> 1725" "$(b)" 1725
cek "lantai ikut diperbarui" "$(cat mobile/BUILD-LANTAI.txt)" 1725
sed -i 's/+1725/+1612/' mobile/pubspec.yaml
bash scripts/versi.sh >/dev/null 2>&1; r=$?
cek "cek konsistensi GAGAL bila build < lantai" "$r" 1
bash scripts/versi.sh --tulis >/dev/null 2>&1
cek "tulis memulihkan build ke lantai (1725)" "$(b)" 1725
bash scripts/versi.sh >/dev/null 2>&1
cek "cek konsistensi lulus setelah dipulihkan" "$?" 0
[ $gagal -eq 0 ] && echo "LULUS uji versi-build" || { echo "GAGAL uji versi-build"; exit 1; }
