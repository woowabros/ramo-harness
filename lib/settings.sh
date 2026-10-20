#!/usr/bin/env bash
# lib/settings.sh - merges the hooks/env/permissions/statusLine fragment into .claude/settings.json.
# Merge, never overwrite: user entries are preserved; identical hook entries are
# deduped by (event, matcher, command) and allow rules by string, so re-running init stays
# idempotent.
# statusLine is a single value rather than a list, so the same never-overwrite rule that
# guards env applies to it: a repository that already has one keeps it, and we say so.

# merge_settings <fragment.json> <target settings.json>
merge_settings() {
  local fragment="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  python3 - "$fragment" "$target" <<'PY'
import json, pathlib, sys

fragment_path, target_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
fragment = json.loads(fragment_path.read_text())
settings = json.loads(target_path.read_text()) if target_path.exists() else {}

changed = False

hooks = settings.setdefault("hooks", {})
for event, frag_groups in fragment.get("hooks", {}).items():
    groups = hooks.setdefault(event, [])
    existing = {
        (group.get("matcher"), hook.get("command"))
        for group in groups
        for hook in group.get("hooks", [])
    }
    for frag_group in frag_groups:
        matcher = frag_group.get("matcher")
        wanted = [h for h in frag_group.get("hooks", [])
                  if (matcher, h.get("command")) not in existing]
        if wanted:
            group = dict(frag_group)
            group["hooks"] = wanted
            groups.append(group)
            changed = True

env = settings.setdefault("env", {})
for key, value in fragment.get("env", {}).items():
    if key not in env:  # never overwrite a user-set value
        env[key] = value
        changed = True

# Allow rules are appended after the user's own, only when missing. The fragment carries one
# rule, for the data access adapter: background sub-agents call it through Bash, and a
# permission prompt they cannot render reads as a hang (rules/workflow/12-subagent-bash-hygiene.md).
frag_allow = fragment.get("permissions", {}).get("allow", [])
if frag_allow:
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for rule in frag_allow:
        if rule not in allow:
            allow.append(rule)
            changed = True

# A statusLine already in the target belongs to the user (a personal script, a plugin's).
# Replacing it would take away something they chose, and unlike hooks there is no list to
# append to, so the only safe move is to leave it and report that we did.
notes = []
frag_status = fragment.get("statusLine")
if frag_status is not None:
    if "statusLine" not in settings:
        settings["statusLine"] = frag_status
        changed = True
    elif settings["statusLine"] != frag_status:
        notes.append("settings: statusLine kept (yours); ramo's is at "
                     ".claude/statusline-ramo.py if you want to switch")

if changed or not target_path.exists():
    target_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    print("settings: merged")
else:
    print("settings: unchanged")
for note in notes:
    print(note)
PY
}

# remove_settings <fragment.json> <target settings.json>
# Uninstall counterpart. Known limit: removal matches by
# string equality, so a user entry identical to ours is removed too.
remove_settings() {
  local fragment="$1" target="$2"
  [[ -f "$target" ]] || return 0
  python3 - "$fragment" "$target" <<'PY'
import json, pathlib, sys

fragment_path, target_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
fragment = json.loads(fragment_path.read_text())
settings = json.loads(target_path.read_text())

frag_commands = {
    hook.get("command")
    for groups in fragment.get("hooks", {}).values()
    for group in groups
    for hook in group.get("hooks", [])
}

hooks = settings.get("hooks", {})
for event in list(hooks):
    kept_groups = []
    for group in hooks[event]:
        remaining = [h for h in group.get("hooks", []) if h.get("command") not in frag_commands]
        if remaining:
            group = dict(group)
            group["hooks"] = remaining
            kept_groups.append(group)
    if kept_groups:
        hooks[event] = kept_groups
    else:
        del hooks[event]

env = settings.get("env", {})
for key, value in fragment.get("env", {}).items():
    if env.get(key) == value:
        del env[key]

permissions = settings.get("permissions", {})
allow = permissions.get("allow")
if isinstance(allow, list):
    frag_allow = set(fragment.get("permissions", {}).get("allow", []))
    permissions["allow"] = [rule for rule in allow if rule not in frag_allow]
    if not permissions["allow"]:
        del permissions["allow"]
    if not permissions:
        del settings["permissions"]

if fragment.get("statusLine") is not None \
        and settings.get("statusLine") == fragment["statusLine"]:
    del settings["statusLine"]

target_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
print("settings: ramo entries removed")
PY
}
