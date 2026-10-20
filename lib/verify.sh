#!/usr/bin/env bash
# lib/verify.sh - checks the seeded target against MANIFEST (same file seed.sh reads).
# Exit contract: 0 = complete, 1 = missing items (each one listed; no silent skip).

# verify_target <payload_dir(harness)> <target_root>
verify_target() {
  local payload_dir="$1" target_root="$2"
  local manifest="$payload_dir/MANIFEST"
  [[ -f "$manifest" ]] || { error "MANIFEST not found: $manifest"; return 1; }

  local rel missing=() checked=0
  while IFS= read -r rel; do
    checked=$((checked + 1))
    case "$rel" in
      CLAUDE.md)
        if [[ ! -f "$target_root/CLAUDE.md" ]] || ! grep -q "BEGIN RAMO-HARNESS" "$target_root/CLAUDE.md"; then
          missing+=("CLAUDE.md marker block in $target_root/CLAUDE.md")
        fi ;;
      settings.hooks.json)
        if ! python3 - "$target_root/.claude/settings.json" "$payload_dir/settings.hooks.json" <<'PY'
import json, pathlib, sys
target, fragment = sys.argv[1], sys.argv[2]
try:
    settings = json.load(open(target))
except Exception:
    sys.exit(1)
frag = json.load(open(fragment))
registered = {
    hook.get("command")
    for groups in settings.get("hooks", {}).values()
    for group in groups
    for hook in group.get("hooks", [])
}
wanted = {
    hook.get("command")
    for groups in frag.get("hooks", {}).values()
    for group in groups
    for hook in group.get("hooks", [])
}
sys.exit(0 if wanted <= registered else 1)
PY
        then
          missing+=("hook registrations in $target_root/.claude/settings.json")
        fi ;;
      VERSION)
        [[ -f "$target_root/.claude/hooks/ramo/.seed-info" ]] || missing+=(".claude/hooks/ramo/.seed-info") ;;
      *)
        [[ -f "$target_root/.claude/$rel" ]] || missing+=(".claude/$rel") ;;
    esac
  done < <(manifest_entries "$manifest")

  [[ -d "$target_root/.ramo" ]] || missing+=(".ramo/ state directory")

  if [[ ${#missing[@]} -gt 0 ]]; then
    error "verify FAILED: ${#missing[@]} missing item(s) of $checked checked:"
    local m; for m in "${missing[@]}"; do printf '  - %s\n' "$m" >&2; done
    return 1
  fi
  info "verify OK ($checked MANIFEST entries checked)"
  return 0
}
