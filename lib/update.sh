#!/usr/bin/env bash
# lib/update.sh - refreshes a seeded target's .claude/ from a newer payload.
# Two separate questions per file, and conflating them is what made the plan useless:
#   1. is it ramo's?  current SHA matches its `.seed-info` record; anything else is a user
#      edit, preserved and reported as a conflict
#   2. does it change?  current SHA differs from the new payload's
# A file that is ramo's but already byte-identical to the new payload is UNCHANGED: it stays
# owned (its `.seed-info` record is rewritten) and is never written, backed up, or listed.
# Backed by a timestamped backup and per-file atomic writes so a mid-run failure rolls back
# to the pre-update state.

UPDATE_REPLACED=()
UPDATE_ADDED=()
UPDATE_CONFLICTS=()
UPDATE_UNCHANGED=()
UPDATE_APPLIED=()

# A self-hosting checkout (this repo) has harness/MANIFEST at its own root. Seeding the
# install payload over it would revert its own working tree to the installed release.
_update_is_self_host() { [[ -f "$1/harness/MANIFEST" ]]; }

_read_seed_file_sha() {
  local seed_info="$1" rel="$2" line
  [[ -f "$seed_info" ]] || return 1
  line=$(grep -F "file:$rel=" "$seed_info" 2>/dev/null | tail -1)
  [[ -n "$line" ]] || return 1
  printf '%s\n' "${line#file:$rel=}"
}

# _atomic_write <src> <dst> - copy via temp file + rename in dst's own directory.
_atomic_write() {
  local src="$1" dst="$2" tmp
  mkdir -p "$(dirname "$dst")" || return 1
  tmp="$dst.ramo-update.tmp.$$"
  cp -p "$src" "$tmp" || { rm -f "$tmp"; return 1; }
  mv -f "$tmp" "$dst" || { rm -f "$tmp"; return 1; }
}

# _classify_update <payload_dir> <target_root> - fills UPDATE_REPLACED/ADDED/UNCHANGED/CONFLICTS.
_classify_update() {
  local payload_dir="$1" target_root="$2" manifest="$1/MANIFEST"
  local seed_info="$target_root/.claude/hooks/ramo/.seed-info"
  UPDATE_REPLACED=(); UPDATE_ADDED=(); UPDATE_CONFLICTS=(); UPDATE_UNCHANGED=()
  local rel dst current recorded new_sha
  while IFS= read -r rel; do
    case "$rel" in
      CLAUDE.md|settings.hooks.json|VERSION) continue ;;  # already idempotent merges
    esac
    dst="$target_root/.claude/$rel"
    if [[ ! -f "$dst" ]]; then
      UPDATE_ADDED+=("$rel")
      continue
    fi
    current=$(sha256_file "$dst")
    new_sha=$(sha256_file "$payload_dir/$rel")
    if [[ "$current" == "$new_sha" ]]; then
      # Already what the new payload holds. Nothing to write, and it is ours either way:
      # an edit that happens to equal the new bytes is indistinguishable from no edit.
      UPDATE_UNCHANGED+=("$rel")
      continue
    fi
    if recorded=$(_read_seed_file_sha "$seed_info" "$rel"); then
      if [[ "$current" == "$recorded" ]]; then UPDATE_REPLACED+=("$rel"); else UPDATE_CONFLICTS+=("$rel"); fi
    else
      # No per-file record (seeded before per-file records shipped) and the content differs
      # from the new payload: ownership is unproven, so the no-clobber default applies.
      UPDATE_CONFLICTS+=("$rel")
    fi
  done < <(manifest_entries "$manifest")
}

_report_update_plan() {
  info "update plan: ${#UPDATE_REPLACED[@]} to replace, ${#UPDATE_ADDED[@]} to add, ${#UPDATE_UNCHANGED[@]} already current, ${#UPDATE_CONFLICTS[@]} locally modified (kept)"
  # Only what changes is listed. Listing every owned file is what stopped this preview from
  # telling a one-file fix from a full rewrite, which is why a person reads it at all.
  local r
  for r in ${UPDATE_REPLACED[@]+"${UPDATE_REPLACED[@]}"}; do printf '  replace: %s\n' "$r"; done
  for r in ${UPDATE_ADDED[@]+"${UPDATE_ADDED[@]}"}; do printf '  add:     %s\n' "$r"; done
  for r in ${UPDATE_CONFLICTS[@]+"${UPDATE_CONFLICTS[@]}"}; do printf '  keep:    %s (locally modified)\n' "$r" >&2; done
}

_write_update_seed_info() {
  local payload_dir="$1" seed_info="$2"
  local owned="${UPDATE_REPLACED[*]:-} ${UPDATE_ADDED[*]:-} ${UPDATE_UNCHANGED[*]:-}"
  python3 - "$payload_dir" "$seed_info" "$owned" <<'PY'
import hashlib, pathlib, sys
payload, out, owned = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
version = (payload / "VERSION").read_text().strip() if (payload / "VERSION").exists() else "unknown"
manifest_sha16 = hashlib.sha256((payload / "MANIFEST").read_bytes()).hexdigest()[:16]
lines = [f"version={version}", f"manifest_sha16={manifest_sha16}"]
for rel in sorted(set(p for p in owned.split() if p)):
    f = payload / rel
    if f.is_file():
        lines.append(f"file:{rel}=" + hashlib.sha256(f.read_bytes()).hexdigest())
pathlib.Path(out).write_text("\n".join(lines) + "\n")
PY
}

# _rollback_update <backup_dir> <claude_dir> - undo everything recorded in UPDATE_APPLIED.
_rollback_update() {
  local backup_dir="$1" claude_dir="$2" entry rel action
  for entry in ${UPDATE_APPLIED[@]+"${UPDATE_APPLIED[@]}"}; do
    rel="${entry%:*}"; action="${entry##*:}"
    if [[ "$action" == "replaced" ]]; then
      cp -p "$backup_dir/$rel" "$claude_dir/$rel"
    else
      rm -f "$claude_dir/$rel"
    fi
  done
}

# update_payload <payload_dir(harness)> <target_root> <dry_run:0|1>
update_payload() {
  local payload_dir="$1" target_root="$2" dry_run="${3:-0}"
  local claude_dir="$target_root/.claude"
  local seed_info="$claude_dir/hooks/ramo/.seed-info"
  local manifest="$payload_dir/MANIFEST"

  [[ -f "$manifest" ]] || { error "MANIFEST not found: $manifest"; return 1; }
  if _update_is_self_host "$target_root"; then
    error "refusing to update a self-hosting checkout (harness/MANIFEST found at $target_root); this would revert its own dev payload"
    return 1
  fi
  [[ -f "$seed_info" ]] || { error "target is not seeded (missing $seed_info); run 'ramo init' first"; return 1; }

  _classify_update "$payload_dir" "$target_root"

  if [[ "$dry_run" == "1" ]]; then
    _report_update_plan
    return 0
  fi

  if [[ ${#UPDATE_REPLACED[@]} -eq 0 && ${#UPDATE_ADDED[@]} -eq 0 ]]; then
    # Nothing to write, but the record still needs the new version and manifest digest:
    # a release that changes only unseeded files (lib/, bin/) would otherwise leave the
    # target reporting the version it was seeded with.
    _write_update_seed_info "$payload_dir" "$seed_info"
    info "update: already current (${#UPDATE_UNCHANGED[@]} file(s) unchanged, ${#UPDATE_CONFLICTS[@]} locally modified kept)"
    return 0
  fi

  local ts backup_dir rel dst ok=1
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  backup_dir="$claude_dir/hooks/ramo/.backup/$ts"
  mkdir -p "$backup_dir" || { error "cannot create backup dir $backup_dir"; return 1; }
  cp -p "$seed_info" "$backup_dir/.seed-info" 2>/dev/null || true

  UPDATE_APPLIED=()
  for rel in ${UPDATE_REPLACED[@]+"${UPDATE_REPLACED[@]}"}; do
    dst="$claude_dir/$rel"
    mkdir -p "$backup_dir/$(dirname "$rel")"
    cp -p "$dst" "$backup_dir/$rel" || { ok=0; break; }
    _atomic_write "$payload_dir/$rel" "$dst" || { ok=0; break; }
    UPDATE_APPLIED+=("$rel:replaced")
  done

  if [[ $ok -eq 1 ]]; then
    for rel in ${UPDATE_ADDED[@]+"${UPDATE_ADDED[@]}"}; do
      dst="$claude_dir/$rel"
      _atomic_write "$payload_dir/$rel" "$dst" || { ok=0; break; }
      UPDATE_APPLIED+=("$rel:added")
    done
  fi

  if [[ $ok -eq 0 ]]; then
    error "update failed writing $rel; rolling back ${#UPDATE_APPLIED[@]} already-applied change(s)"
    _rollback_update "$backup_dir" "$claude_dir"
    return 1
  fi

  _write_update_seed_info "$payload_dir" "$seed_info"

  info "update: ${#UPDATE_REPLACED[@]} replaced, ${#UPDATE_ADDED[@]} added, ${#UPDATE_UNCHANGED[@]} already current, ${#UPDATE_CONFLICTS[@]} kept (locally modified). backup: $backup_dir"
  if [[ ${#UPDATE_CONFLICTS[@]} -gt 0 ]]; then
    warn "kept ${#UPDATE_CONFLICTS[@]} locally modified file(s) (not overwritten):"
    local c; for c in "${UPDATE_CONFLICTS[@]}"; do printf '  - %s\n' "$c" >&2; done
  fi
  return 0
}
