#!/usr/bin/env bash
# lib/common.sh - shared helpers: logging, project root resolution, payload resolution.
# Sourced by bin/ramo and install.sh. No side effects besides variable defaults.

set -uo pipefail

if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BOLD='\033[1m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BOLD=''; NC=''
fi

info()  { printf "%b\n" "${GREEN}[ramo]${NC} $*"; }
warn()  { printf "%b\n" "${YELLOW}[ramo] WARN:${NC} $*" >&2; }
error() { printf "%b\n" "${RED}[ramo] ERROR:${NC} $*" >&2; }
die()   { error "$*"; exit 1; }

# Resolve the project root of the repo we are seeding into.
# Uses --show-toplevel: seeded assets (.claude/) are committed content, and a linked
# worktree is an independent checkout that needs its own copy on its own branch.
# --git-common-dir would resolve a worktree to the MAIN checkout and install the
# harness where nobody is working (observed in testing).
resolve_project_root() {
  local top
  top=$(git -C "${1:-.}" rev-parse --show-toplevel 2>/dev/null) || return 1
  # bare repos have no work tree and are not seedable
  [[ -n "$top" && -d "$top" ]] || return 1
  printf '%s\n' "$top"
}

# Resolve where the payload (harness/, which contains schema/) lives.
# Priority: RAMO_HOME env > script-relative repo checkout > installed default.
resolve_ramo_home() {
  if [[ -n "${RAMO_HOME:-}" ]]; then
    printf '%s\n' "$RAMO_HOME"; return 0
  fi
  local script_root
  script_root=$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")/.." && pwd)
  if [[ -d "$script_root/harness" && -f "$script_root/harness/schema/harness.json" ]]; then
    printf '%s\n' "$script_root"; return 0
  fi
  printf '%s\n' "$HOME/.local/share/ramo/current"
}

# Read a value out of harness/schema/harness.json with python3 (stdlib only).
schema_get() {
  local schema_file="$1" expr="$2"
  python3 - "$schema_file" "$expr" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
node = data
for key in sys.argv[2].split("."):
    node = node[key]
print(node)
PY
}

manifest_entries() {
  # MANIFEST: one payload-relative path per line, '#' comments allowed.
  grep -v '^#' "$1" | grep -v '^[[:space:]]*$'
}

# sha256_file <path> - prints the sha256 hex digest (python3 stdlib; no external dependency).
sha256_file() {
  python3 - "$1" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
}
