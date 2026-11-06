#!/usr/bin/env bash
# Mengaktifkan hook git proyek (.githooks/) untuk klon ini dan semua worktree-nya. Jalankan sekali:
#   bash scripts/pasang-hook.sh          (aktifkan)
#   bash scripts/pasang-hook.sh --lepas  (kembali ke hook bawaan git)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [ "${1:-}" = "--lepas" ]; then
  git config --unset core.hooksPath || true
  echo "Hook proyek dilepas."
  exit 0
fi
git config core.hooksPath .githooks
echo "Hook aktif: $(git config core.hooksPath)/pre-commit (ruff · dart analyze · eslint · cegah berkas rahasia) dan commit-msg (tolak atribusi AI)."
