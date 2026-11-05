#!/usr/bin/env bash
# Versi tunggal (SemVer). Sumber: berkas VERSION di root repo.
#   bash scripts/versi.sh           cek: API, web, mobile harus sama dengan VERSION (galat bila beda / bukan X.Y.Z)
#   bash scripts/versi.sh --tulis   sinkronkan: api/VERSION (citra Docker api), web/package.json(+lock),
#                                   mobile/pubspec.yaml -> "version: X.Y.Z+BUILD" (BUILD = jumlah commit, selalu naik)
# Aturan kenaikan dan urutan rilis: docs/RILIS.md.
set -u
ROOT=$(git rev-parse --show-toplevel) || exit 1
cd "$ROOT" || exit 1
SEMVER='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'

v=$(tr -d '[:space:]' < VERSION 2>/dev/null)
if ! [[ $v =~ $SEMVER ]]; then
  echo "GAGAL: VERSION '${v:-<kosong/tak ada>}' bukan SemVer X.Y.Z"; exit 1
fi

if [ "${1:-}" = "--tulis" ]; then
  # BUILD = max(jumlah commit, build pubspec, lantai); versi X.Y.Z berubah -> minimal build sekarang + 1.
  # Idempoten: versi sama tidak menaikkan lagi. Riwayat pendek (worktree) tak boleh menurunkan build.
  cur=$(sed -n 's/^version: *\([0-9.]*\)+\([0-9]*\).*/\1 \2/p' mobile/pubspec.yaml | head -n 1)
  curv=${cur% *}; curb=${cur#* }; [ "$curb" = "$cur" ] && curb=0
  lantai=$(tr -d '[:space:]' < mobile/BUILD-LANTAI.txt 2>/dev/null); [[ $lantai =~ ^[0-9]+$ ]] || lantai=0
  build=$(git rev-list --count HEAD)
  for x in "$curb" "$lantai"; do [ "$x" -gt "$build" ] && build=$x; done
  if [ "$curv" != "$v" ] && [ "$build" -le "$curb" ]; then build=$((curb + 1)); fi
  printf '%s\n' "$build" > mobile/BUILD-LANTAI.txt
  printf '%s\n' "$v" > api/VERSION
  (cd web && npm version "$v" --no-git-tag-version --allow-same-version >/dev/null) || { echo "GAGAL: npm version"; exit 1; }
  sed -i "s/^version: .*/version: $v+$build/" mobile/pubspec.yaml
  echo "ok     versi $v disinkronkan (build mobile $build)"
  exit 0
fi

fail=0
cek() { # cek <nama> <nilai>
  if [ "$2" = "$v" ]; then echo "  ok     $1 $2"; else echo "  GAGAL  $1 '$2' != VERSION '$v'"; fail=1; fi
}
cek "api/VERSION" "$(tr -d '[:space:]' < api/VERSION 2>/dev/null)"
cek "web/package.json" "$(sed -n 's/^  "version": "\([^"]*\)".*/\1/p' web/package.json | head -n 1)"
pub=$(sed -n 's/^version: \(.*\)$/\1/p' mobile/pubspec.yaml | head -n 1 | tr -d '[:space:]')
cek "mobile/pubspec.yaml" "${pub%%+*}"
if ! [[ ${pub##*+} =~ ^[0-9]+$ ]] || [ "${pub##*+}" = "$pub" ]; then
  echo "  GAGAL  mobile build number '${pub}' harus X.Y.Z+N (N angka)"; fail=1
fi

lantai=$(tr -d '[:space:]' < mobile/BUILD-LANTAI.txt 2>/dev/null)
if ! [[ $lantai =~ ^[0-9]+$ ]]; then
  echo "  GAGAL  mobile/BUILD-LANTAI.txt harus berisi satu angka"; fail=1
elif [[ ${pub##*+} =~ ^[0-9]+$ ]] && [ "${pub##*+}" -lt "$lantai" ]; then
  echo "  GAGAL  build pubspec ${pub##*+} < lantai $lantai (Android menolak turun versi)"; fail=1
else echo "  ok     build ${pub##*+} >= lantai $lantai"; fi

if [ $fail -eq 0 ]; then echo "LULUS (versi $v)"; else echo "GAGAL: versi tak konsisten — jalankan: bash scripts/versi.sh --tulis"; exit 1; fi
