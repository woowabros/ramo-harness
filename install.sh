#!/usr/bin/env bash
# install.sh - installs the ramo harness from a local clone (pure bash).
# Default: copy payload to ~/.local/share/ramo/<version>/ and the CLI to ~/.local/bin/ramo
#   (RAMO_INSTALL_ROOT and RAMO_BIN_DIR override the two locations).
# --target <dir>: seed straight into <dir> from this checkout (self-consumption; skips
#   preflight because it needs no CLI).
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_DIR/lib/common.sh"

TARGET=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="${2:?--target requires a directory}"; shift 2 ;;
    -h|--help) echo "Usage: ./install.sh [--target <dir>]"; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

PAYLOAD="$REPO_DIR/harness"
MANIFEST="$PAYLOAD/MANIFEST"
[[ -f "$MANIFEST" ]] || die "MANIFEST not found: $MANIFEST"

# Fail fast: MANIFEST must match the payload tree exactly (no silent skip).
"$REPO_DIR/scripts/gen-manifest.sh" --check "$REPO_DIR" \
  || die "MANIFEST is stale. Run scripts/gen-manifest.sh and commit it with the payload change."
missing=()
while IFS= read -r rel; do
  [[ -f "$PAYLOAD/$rel" ]] || missing+=("$rel")
done < <(manifest_entries "$MANIFEST")
if [[ ${#missing[@]} -gt 0 ]]; then
  error "payload is missing ${#missing[@]} MANIFEST entry(ies):"
  for m in "${missing[@]}"; do printf '  - %s\n' "$m" >&2; done
  exit 1
fi

if [[ -n "$TARGET" ]]; then
  # Self-consumption mode: seed directly from this checkout.
  source "$REPO_DIR/lib/settings.sh"
  source "$REPO_DIR/lib/seed.sh"
  source "$REPO_DIR/lib/verify.sh"
  target_root="$(resolve_project_root "$TARGET")" || die "--target $TARGET is not a git repository"
  info "seeding from checkout into $target_root"
  seed_payload "$PAYLOAD" "$target_root" || exit 1
  verify_target "$PAYLOAD" "$target_root" || exit 1
  exit 0
fi

VERSION="$(cat "$PAYLOAD/VERSION")"
SHARE_ROOT="${RAMO_INSTALL_ROOT:-$HOME/.local/share/ramo}"
DEST="$SHARE_ROOT/$VERSION"
BIN_DIR="${RAMO_BIN_DIR:-$HOME/.local/bin}"

info "installing ramo $VERSION"
rm -rf "$DEST"
mkdir -p "$DEST" "$BIN_DIR"
cp -R "$PAYLOAD" "$DEST/harness"
cp -R "$REPO_DIR/lib" "$DEST/lib"
ln -sfn "$DEST" "$SHARE_ROOT/current"
install -m 755 "$REPO_DIR/bin/ramo" "$BIN_DIR/ramo"

# Record where `ramo update` fetches from, so later updates reuse the URL (and with it the
# credentials) this install came through: RAMO_DIST_REMOTE when set, else this clone's origin.
source_url="${RAMO_DIST_REMOTE:-}"
if [[ -z "$source_url" ]]; then
  source_url="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
fi
if [[ -n "$source_url" ]]; then
  printf '%s\n' "$source_url" > "$SHARE_ROOT/source.tmp.$$" && mv -f "$SHARE_ROOT/source.tmp.$$" "$SHARE_ROOT/source"
fi

info "installed: $BIN_DIR/ramo -> payload $SHARE_ROOT/current"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) warn "$BIN_DIR is not on PATH; add it before running 'ramo init'" ;;
esac
info "next: cd <your-repo> && ramo init   (later updates: ramo update)"
