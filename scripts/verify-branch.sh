#!/usr/bin/env bash
# Verifikasi branch dari SALINAN BERSIH (git archive) — bukan dari disk kerja pembuatnya.
# Pakai:  scripts/verify-branch.sh <branch> web            → npm ci, lint, typecheck, test
#         scripts/verify-branch.sh <branch> api [uji...]   → ruff, mypy, pytest (uji yang disebut)
# Hasil akhir satu baris: LULUS / GAGAL + ringkasan. Log lengkap di .local_tests/verify-<branch>.log
set -u
branch="$1"; kind="$2"; shift 2
root="$(git rev-parse --show-toplevel)"
safe="$(echo "$branch" | tr '/' '-')"
log="$root/.local_tests/verify-$safe.log"
work="$(mktemp -d)"
mkdir -p "$root/.local_tests"
: > "$log"
fail=0

step() { echo "== $*" >> "$log"; "$@" >> "$log" 2>&1 || { echo "GAGAL: $*" >> "$log"; fail=1; }; }

# Aturan bersama: CHANGELOG tidak boleh ditulis ulang utuh / rusak penyandiannya.
changed=$(git diff --numstat "origin/development...$branch" -- CHANGELOG.md | awk '{print $1+$2}')
mojibake=$(git show "$branch:CHANGELOG.md" 2>/dev/null | grep -c 'â€' || true)
if [ "${changed:-0}" -gt 40 ] || [ "${mojibake:-0}" -gt 0 ]; then
  echo "CHANGELOG mencurigakan: $changed baris berubah, $mojibake mojibake" >> "$log"; fail=1
fi

if [ "$kind" = "web" ]; then
  git archive "$branch" web | tar -x -C "$work"
  cd "$work/web" || exit 2
  step npm ci --no-audit --no-fund --loglevel=error
  step npm run -s lint
  step npm run -s typecheck
  step npx vitest run
  summary=$(grep -E "Tests +[0-9]+" "$log" | tail -1)
else
  git archive "$branch" api | tar -x -C "$work"
  cp "$root/api/.env" "$work/api/.env" 2>/dev/null
  cd "$work/api" || exit 2
  venv="$root/api/.venv/Scripts"
  step "$venv/ruff" check app tests
  step env PYTHONPATH=. "$venv/python" -m mypy
  step env PYTHONPATH=. "$venv/python" -m pytest -q -p no:warnings "${@:-tests}"
  summary=$(grep -E "[0-9]+ (passed|failed)" "$log" | tail -1)
fi

rm -rf "$work"
if [ "$fail" -eq 0 ]; then echo "LULUS  $branch ($kind) — $summary"; else echo "GAGAL  $branch ($kind) — $summary — lihat $log"; fi
exit $fail
