#!/usr/bin/env bash
# scripts/gen-manifest.sh - (re)generates harness/MANIFEST from the payload tree.
# MANIFEST is the single source of the seed list (seed.sh and verify.sh read it);
# this script is the paired consistency check required for that dual bookkeeping.
# Usage: gen-manifest.sh [--check] [repo-root]   (--check: exit 1 if MANIFEST is stale)
set -uo pipefail

CHECK=0
ROOT=""
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    *) ROOT="$arg" ;;
  esac
done
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PAYLOAD="$ROOT/harness"
MANIFEST="$PAYLOAD/MANIFEST"
[[ -d "$PAYLOAD" ]] || { echo "[gen-manifest] payload dir not found: $PAYLOAD" >&2; exit 1; }

generated() {
  printf '# MANIFEST - seed list, single source for lib/seed.sh and lib/verify.sh.\n'
  printf '# Regenerate with scripts/gen-manifest.sh in the same commit as any payload change.\n'
  # __pycache__ is a byproduct of running the handlers, never seed payload: shipping it
  # would push stale bytecode into every consumer repository.
  (cd "$PAYLOAD" && /usr/bin/find . -type f ! -name MANIFEST ! -name '.DS_Store' \
     ! -path '*/__pycache__/*' | sed 's|^\./||' | LC_ALL=C sort)
}

if [[ "$CHECK" == "1" ]]; then
  [[ -f "$MANIFEST" ]] || { echo "[gen-manifest] MANIFEST missing" >&2; exit 1; }
  if ! diff <(generated | grep -v '^#') <(grep -v '^#' "$MANIFEST" | grep -v '^[[:space:]]*$') >/dev/null; then
    echo "[gen-manifest] MANIFEST is stale relative to harness/ tree:" >&2
    diff <(generated | grep -v '^#') <(grep -v '^#' "$MANIFEST" | grep -v '^[[:space:]]*$') >&2 || true
    exit 1
  fi
  exit 0
fi

generated > "$MANIFEST"
echo "[gen-manifest] wrote $MANIFEST ($(grep -cv '^#' "$MANIFEST") entries)"
