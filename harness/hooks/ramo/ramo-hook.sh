#!/usr/bin/env bash
# ramo-hook.sh - dispatch-only shim; the handler name comes from settings.json registration.
# Missing handler or python3 => exit 0: losing one event beats blocking the session.
set -uo pipefail
H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/handlers/${1:?handler name required}.py"
{ [ -f "$H" ] && command -v python3 >/dev/null 2>&1; } || exit 0
exec python3 "$H" "${@:2}"
