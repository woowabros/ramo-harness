#!/usr/bin/env bash
# lib/seed.sh - seeds the payload into a target repo's .claude/ from MANIFEST.
# MANIFEST is the single source of the seed list; verify.sh reads the same file.
# No-clobber contract: never overwrite a file the user modified; list it as a conflict.

# Special payload entries (everything else maps to .claude/<relpath>):
#   CLAUDE.md           -> marker-block merge into <target>/CLAUDE.md
#   settings.hooks.json -> JSON merge into <target>/.claude/settings.json (lib/settings.sh)
#   VERSION             -> recorded in .claude/hooks/ramo/.seed-info (not copied verbatim)

RAMO_MARKER_BEGIN="<!-- BEGIN RAMO-HARNESS (managed by 'ramo init'; do not edit inside) -->"
RAMO_MARKER_END="<!-- END RAMO-HARNESS -->"

SEED_CONFLICTS=()
SEED_COPIED=0
SEED_IDENTICAL=0
# Relpaths ramo owns after this run (freshly copied or already identical to payload).
# `ramo update` reads these back out of .seed-info to tell an untouched file from a user
# edit; a path left out of SEED_OWNED (a no-clobber conflict) gets no ownership record.
SEED_OWNED=()

_files_identical() { cmp -s "$1" "$2"; }

_seed_plain_file() {
  local src="$1" dst="$2" rel="$3"
  if [[ -f "$dst" ]]; then
    if _files_identical "$src" "$dst"; then
      SEED_IDENTICAL=$((SEED_IDENTICAL + 1))
      SEED_OWNED+=("$rel")
    else
      SEED_CONFLICTS+=("$dst (kept local version; payload differs)")
    fi
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp -p "$src" "$dst"
  SEED_COPIED=$((SEED_COPIED + 1))
  SEED_OWNED+=("$rel")
}

# Replace (or append) the ramo-owned marker block. The block itself is ramo-owned,
# so rewriting it is idempotent and is not a clobber of user content.
_seed_claude_md() {
  local src="$1" target_file="$2"
  python3 - "$src" "$target_file" "$RAMO_MARKER_BEGIN" "$RAMO_MARKER_END" <<'PY'
import sys, pathlib
src, target, begin, end = sys.argv[1:5]
block = f"{begin}\n{pathlib.Path(src).read_text()}\n{end}\n"
path = pathlib.Path(target)
if path.exists():
    text = path.read_text()
    if begin in text and end in text:
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
        new = head + block.rstrip("\n") + tail
    else:
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        new = text + sep + block
else:
    new = block
if not path.exists() or path.read_text() != new:
    path.write_text(new)
    print("merged")
else:
    print("unchanged")
PY
}

_write_seed_info() {
  local payload_dir="$1" target_root="$2"
  local info_dir="$target_root/.claude/hooks/ramo"
  mkdir -p "$info_dir"
  python3 - "$payload_dir" "$info_dir/.seed-info" "${SEED_OWNED[*]:-}" <<'PY'
import hashlib, pathlib, sys
payload, out, owned = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
version = (payload / "VERSION").read_text().strip() if (payload / "VERSION").exists() else "unknown"
manifest = payload / "MANIFEST"
sha16 = hashlib.sha256(manifest.read_bytes()).hexdigest()[:16] if manifest.exists() else "missing"
lines = [f"version={version}", f"manifest_sha16={sha16}"]
for rel in sorted(set(p for p in owned.split() if p)):
    f = payload / rel
    if f.is_file():
        lines.append(f"file:{rel}=" + hashlib.sha256(f.read_bytes()).hexdigest())
out.write_text("\n".join(lines) + "\n")
PY
}

_seed_state_dir() {
  local target_root="$1" d
  # Keep in step with the Layout table in rules/common/state-discipline.md; a stage whose
  # directory is missing here has nowhere to land its output on a fresh install.
  for d in plans todo interviews eda diagnoses research context logs; do mkdir -p "$target_root/.ramo/$d"; done
  # Ignore what the harness itself produces or lays out, and only that. Two classes:
  #   by-products of what we seed -- the state dir, the handler bytecode cache, the agent
  #     memory store the `memory: project` agents write;
  #   directories our own layout rule defines as binary-bearing -- experiments/*/data/ holds
  #     extraction output and experiments/*/artifacts/ holds model dumps (common/naming.md,
  #     common/architectural-boundaries.md state ownership). experiments/*/reports/ stays
  #     tracked: metric and slice reports are the evidence, and they are text.
  # Still no blanket rule. `__pycache__/` or `*.parquet` across the tree would be the harness
  # legislating the consumer's repo, which is a line we hold (a consumer repository had large
  # parquet files and a model dump untracked; the fix is naming our own layout, not
  # claiming every large file in someone else's repo).
  local gi="$target_root/.gitignore" entry
  for entry in '.ramo/' '.claude/hooks/ramo/handlers/__pycache__/' '.claude/agent-memory/' \
               '.claude/hooks/ramo/.backup/' 'experiments/*/data/' 'experiments/*/artifacts/'; do
    if [[ ! -f "$gi" ]] || ! grep -qxF "$entry" "$gi"; then
      printf '%s\n' "$entry" >> "$gi"
    fi
  done
}

# seed_payload <payload_dir(harness)> <target_root>
seed_payload() {
  local payload_dir="$1" target_root="$2"
  local manifest="$payload_dir/MANIFEST"
  SEED_CONFLICTS=(); SEED_COPIED=0; SEED_IDENTICAL=0; SEED_OWNED=()

  [[ -f "$manifest" ]] || { error "MANIFEST not found: $manifest"; return 1; }

  # Fail fast on payload gaps: every MANIFEST entry must exist. No silent skip.
  local rel missing=()
  while IFS= read -r rel; do
    [[ -f "$payload_dir/$rel" ]] || missing+=("$rel")
  done < <(manifest_entries "$manifest")
  if [[ ${#missing[@]} -gt 0 ]]; then
    error "payload is missing ${#missing[@]} MANIFEST entry(ies); aborting before partial install:"
    local m; for m in "${missing[@]}"; do printf '  - %s\n' "$m" >&2; done
    return 1
  fi

  while IFS= read -r rel; do
    case "$rel" in
      CLAUDE.md)           _seed_claude_md "$payload_dir/CLAUDE.md" "$target_root/CLAUDE.md" >/dev/null ;;
      settings.hooks.json) merge_settings "$payload_dir/settings.hooks.json" "$target_root/.claude/settings.json" ;;
      VERSION)             : ;;  # recorded via .seed-info below
      *)                   _seed_plain_file "$payload_dir/$rel" "$target_root/.claude/$rel" "$rel" ;;
    esac
  done < <(manifest_entries "$manifest")

  _write_seed_info "$payload_dir" "$target_root"
  _seed_state_dir "$target_root"

  info "seeded: $SEED_COPIED new, $SEED_IDENTICAL identical (skipped)"
  if [[ ${#SEED_CONFLICTS[@]} -gt 0 ]]; then
    warn "no-clobber conflicts (${#SEED_CONFLICTS[@]}): local versions kept"
    local c; for c in "${SEED_CONFLICTS[@]}"; do printf '  - %s\n' "$c" >&2; done
  fi
  return 0
}
