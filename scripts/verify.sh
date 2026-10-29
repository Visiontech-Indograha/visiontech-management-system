#!/usr/bin/env bash
# Verifikasi cepat di disk kerja (bukan salinan bersih; untuk itu pakai verify-branch.sh).
#   bash scripts/verify.sh [api|web|mobile|all]   (bawaan: all)
# Output tiap langkah dipangkas; ringkasan LULUS/GAGAL di akhir. Log penuh: .local_tests/verify.log
set -u
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT" || exit 1
what="${1:-all}"
mkdir -p .local_tests
log=".local_tests/verify.log"; : > "$log"
fail=0
PY="api/.venv/Scripts/python.exe"; [ -x "$PY" ] || PY="api/.venv/bin/python"
FLUTTER="$HOME/flutter/bin/flutter.bat"; [ -f "$FLUTTER" ] || FLUTTER=flutter

step() { # step <nama> <direktori> <perintah...>
  local name="$1" dir="$2"; shift 2
  echo "== $name" >> "$log"
  if (cd "$dir" && "$@") >> "$log" 2>&1; then echo "  ok     $name"; else echo "  GAGAL  $name"; tail -n 15 "$log" | sed 's/^/         /'; fail=1; fi
}

# Versi SemVer konsisten (VERSION = api/VERSION = web/package.json = mobile/pubspec.yaml).
step "versi konsisten" . bash scripts/versi.sh

if [ "$what" = api ] || [ "$what" = all ]; then
  step "api ruff" api "../$PY" -m ruff check app tests
  step "api mypy" api "../$PY" -m mypy
  step "api pytest" api "../$PY" -m pytest -n 4 -q
fi

if [ "$what" = web ] || [ "$what" = all ]; then
  step "web tsc" web npx tsc -b
  step "web lint" web npm run -s lint
  step "web vitest" web npx vitest run
  # Tipe web harus sama dengan OpenAPI API saat ini (tanpa perubahan setelah regenerasi).
  step "web apiTypes sinkron" . bash -c "(cd web && npm run -s gen:api:export && npm run -s gen:api) && git diff --quiet -- web/openapi.json web/src/lib/apiTypes.ts"
fi

if [ "$what" = mobile ] || [ "$what" = all ]; then
  step "mobile analyze" mobile "$FLUTTER" analyze
  step "mobile test" mobile "$FLUTTER" test
fi

[ $fail -eq 0 ] && echo "LULUS" || { echo "GAGAL (log: $log)"; exit 1; }
