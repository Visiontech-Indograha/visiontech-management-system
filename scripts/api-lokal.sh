#!/usr/bin/env bash
# Jalankan API lokal (dev) dengan muat-ulang otomatis. Port bawaan 8010 (web dev mem-proxy ke sini lewat
# web/.env.development.local; APK beta lewat `adb reverse`). Ubah dengan API_PORT=....
#   bash scripts/api-lokal.sh
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT/api"
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
exec "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "${API_PORT:-8010}"
