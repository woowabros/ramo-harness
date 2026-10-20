#!/usr/bin/env bash
# lib/fetch.sh - 배포 원격에서 최신 릴리스 태그를 찾아 받아 오는 함수 모음
# Sourced by bin/ramo. The channel is git itself: git reuses whatever credentials the person
# already used to install, so a private distribution repository works the same as a public one
# (an unauthenticated HTTP download from a private host is redirected to a login page instead).
# Shell does the git calls; every comparison is python3 stdlib, because version order is not
# string order (0.0.10 > 0.0.2).

# Default distribution remote. install.sh records the remote a checkout was cloned from, and that record
# wins over this default; set RAMO_DIST_REMOTE to your own fork or mirror to override both.
RAMO_DEFAULT_DIST_REMOTE="https://github.com/woowabros/ramo-harness.git"

# fetch_remote_url <share_root> - RAMO_DIST_REMOTE > <share_root>/source > built-in default.
fetch_remote_url() {
  local share_root="$1" recorded
  if [[ -n "${RAMO_DIST_REMOTE:-}" ]]; then
    printf '%s\n' "$RAMO_DIST_REMOTE"; return 0
  fi
  if [[ -f "$share_root/source" ]]; then
    recorded="$(head -1 "$share_root/source" | tr -d '[:space:]')"
    if [[ -n "$recorded" ]]; then printf '%s\n' "$recorded"; return 0; fi
  fi
  printf '%s\n' "$RAMO_DEFAULT_DIST_REMOTE"
}

# fetch_latest_version <url> - prints the highest X.Y.Z among the remote's vX.Y.Z tags.
# Pre-release and non-version tags are ignored. Returns 1 when the remote cannot be listed
# or carries no release tag.
fetch_latest_version() {
  local url="$1" refs
  refs="$(GIT_TERMINAL_PROMPT=0 git ls-remote --tags --refs -- "$url" 2>/dev/null)" || return 1
  printf '%s\n' "$refs" | python3 -c '
import re, sys
found = []
for line in sys.stdin:
    m = re.search(r"refs/tags/v(\d+)\.(\d+)\.(\d+)$", line.strip())
    if m:
        found.append(tuple(int(x) for x in m.groups()))
if not found:
    sys.exit(1)
print(".".join(str(x) for x in max(found)))
'
}

# fetch_version_exists <url> <version> - 0 when tag v<version> exists on the remote.
fetch_version_exists() {
  GIT_TERMINAL_PROMPT=0 git ls-remote --tags --refs --exit-code -- "$1" "refs/tags/v$2" >/dev/null 2>&1
}

# version_cmp <a> <b> - prints -1, 0 or 1 comparing two X.Y.Z strings numerically.
version_cmp() {
  python3 - "$1" "$2" <<'PY'
import sys
a, b = (tuple(int(x) for x in v.split("-")[0].split(".")) for v in sys.argv[1:3])
print((a > b) - (a < b))
PY
}

# fetch_release <url> <version> <dest> - shallow clone of tag v<version> into dest.
fetch_release() {
  GIT_TERMINAL_PROMPT=0 git -c advice.detachedHead=false clone -q --depth 1 \
    --branch "v$2" -- "$1" "$3" 2>/dev/null
}

# changelog_headings <changelog> <from> <to> - prints the `## <version>` headings a move from
# <from> to <to> crosses, newest first: (from, to] going up, (to, from] going down.
changelog_headings() {
  [[ -f "$1" ]] || return 0
  python3 - "$1" "$2" "$3" <<'PY'
import re, sys
path, a, b = sys.argv[1:4]
key = lambda v: tuple(int(x) for x in v.split("-")[0].split("."))
lo, hi = sorted((key(a), key(b)))
for line in open(path, encoding="utf-8"):
    m = re.match(r"## (\d+\.\d+\.\d+)\s*$", line)
    if m and lo < key(m.group(1)) <= hi:
        print("  - " + line.strip())
PY
}
