#!/usr/bin/env bash
# lib/preflight.sh - environment checks for `ramo init`.
# Every unmet requirement is reported with a concrete reason; silent progress is forbidden.
# Overridable for tests: RAMO_CLAUDE_BIN, RAMO_MIN_CLAUDE, RAMO_BIN_DIR, RAMO_SKIP_PATH_CHECK.

PREFLIGHT_BLOCKED=()
PREFLIGHT_WARNINGS=()

_pf_block() { PREFLIGHT_BLOCKED+=("$1"); }
_pf_warn()  { PREFLIGHT_WARNINGS+=("$1"); }

_pf_check_git_repo() {
  local target="$1"
  if ! resolve_project_root "$target" >/dev/null; then
    _pf_block "not a git work tree (checked with 'git rev-parse --show-toplevel' in $target)"
  fi
}

_pf_check_python3() {
  local schema_file="$1" min
  if ! command -v python3 >/dev/null 2>&1; then
    _pf_block "python3 not found on PATH (hook handlers are python3 stdlib scripts)"
    return
  fi
  min=$(schema_get "$schema_file" "python.handler_min_version" 2>/dev/null) || min="3.9"
  if ! python3 - "$min" <<'PY'
import sys
major, minor = (int(x) for x in sys.argv[1].split(".")[:2])
sys.exit(0 if sys.version_info >= (major, minor) else 1)
PY
  then
    _pf_block "python3 $(python3 -V 2>&1 | cut -d' ' -f2) < required $min (harness/schema/harness.json python.handler_min_version)"
  fi
}

_pf_check_claude() {
  local bin="${RAMO_CLAUDE_BIN:-claude}" min="${RAMO_MIN_CLAUDE:-2.0.0}" ver
  if ! command -v "$bin" >/dev/null 2>&1; then
    _pf_block "Claude Code CLI '$bin' not found on PATH"
    return
  fi
  ver=$("$bin" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  if [[ -z "$ver" ]]; then
    _pf_block "could not parse '$bin --version' output"
    return
  fi
  if ! python3 - "$ver" "$min" <<'PY'
import sys
cur = tuple(int(x) for x in sys.argv[1].split("."))
req = tuple(int(x) for x in sys.argv[2].split("."))
sys.exit(0 if cur >= req else 1)
PY
  then
    _pf_block "Claude Code $ver < required $min (version-based SubagentStop support probe)"
  fi
}

# The ramo CLI must be callable by name for `ramo update` and `ramo verify` later. Asking the
# shell (command -v) instead of matching one directory honours a RAMO_BIN_DIR install.
_pf_check_cli_on_path() {
  [[ "${RAMO_SKIP_PATH_CHECK:-0}" == "1" ]] && return
  command -v ramo >/dev/null 2>&1 && return
  _pf_block "the ramo CLI is not on PATH (install.sh puts it in ${RAMO_BIN_DIR:-\$HOME/.local/bin}; add that directory to PATH)"
}

# The data stages read tables through the data access adapter, which reads ramo-data.json at
# the project root. The file is the user's (git-tracked, never seeded), so its absence is a
# warning: the non-data stages work without it.
_pf_check_data_config() {
  local target="$1" root
  root="$(resolve_project_root "$target" 2>/dev/null)" || root="$target"
  [[ -f "$root/ramo-data.json" ]] && return 0
  _pf_warn "no ramo-data.json at $root; the data stages need it to read tables (example: .claude/rules/data/engines/duckdb.md after init)"
}

# run_preflight <target-repo-dir> <schema-file>
# Prints a BLOCKED report and returns 1 when any hard requirement is unmet.
run_preflight() {
  local target="$1" schema_file="$2"
  PREFLIGHT_BLOCKED=(); PREFLIGHT_WARNINGS=()

  _pf_check_git_repo "$target"
  _pf_check_python3 "$schema_file"
  _pf_check_claude
  _pf_check_cli_on_path
  _pf_check_data_config "$target"

  local w
  for w in ${PREFLIGHT_WARNINGS[@]+"${PREFLIGHT_WARNINGS[@]}"}; do warn "$w"; done
  if [[ ${#PREFLIGHT_BLOCKED[@]} -gt 0 ]]; then
    error "preflight BLOCKED (${#PREFLIGHT_BLOCKED[@]} unmet requirement(s)):"
    local b
    for b in "${PREFLIGHT_BLOCKED[@]}"; do printf '  - %s\n' "$b" >&2; done
    return 1
  fi
  info "preflight OK"
  return 0
}
