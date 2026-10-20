#!/usr/bin/env bash
# Shim that forwards Claude Code hook events to seeded python3 handlers. No logic here.
#
# Placement: <repo>/.claude/hooks/ramo/ramo-hook.sh
# Invocation: settings.json registers each event as `ramo-hook.sh <handler-key>` where
# <handler-key> is one of session_start / pre_bash / post_write / subagent_stop.
# SSOT for events and handler names: .claude/schema/harness.json (hooks section).
# Judgments this file locks in:
#   - Hook logic lives in seeded python3 stdlib handlers (handlers/<key>.py); the shim
#     only dispatches. Bundled one-file binaries were rejected: their startup cost alone
#     put every hook call past a second
#   - No branching and no JSON parsing in shell; never call jq — hooks run on every tool
#     call, so process startup cost multiplies across the session
#   - The event->handler mapping lives in settings.json (the registration site), not here
#   - Handler absent => exit 0 silently. A lost event beats a blocked session
#
# Exit codes: 0 pass / 2 block (stderr feeds the model) / anything else fail-open.

set -uo pipefail

HANDLER="$(dirname "$0")/handlers/$1.py"

[ -f "$HANDLER" ] || exit 0

exec python3 "$HANDLER" "${@:2}"
