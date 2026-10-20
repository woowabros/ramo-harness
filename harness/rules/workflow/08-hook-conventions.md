---
description: Hook authoring SSOT — single dispatch shim, logic-free shell, stdlib-only handlers, per-handler tests, and the payload-citation/MANIFEST lockstep that keeps seeded assets readable
---

# Hook Conventions

Loaded globally (no `paths:`): hooks are the only mechanical enforcement the harness has, and
their contract governs how every handler is written and shipped, not which files are edited.

An earlier version of these conventions assumed handlers bundled as binaries; this one is
written for the seeded-payload model (stdlib python3 handlers copied into the consumer
repository). HARD 5 below is the rule whose absence let the seeded-path regression class below
reappear.

## Architecture

```text
settings.json  ->  ramo-hook.sh <handler-name>  ->  handlers/<handler-name>.py
   (registration)      (dispatch only)                (all judgment)
```

Event-to-handler mapping lives in `settings.hooks.json` registration arguments, never in shell
branching. Four events are registered: `SessionStart`, `PreToolUse` (Bash),
`PostToolUse` (Write|Edit), `SubagentStop`.

## Response Protocol (3 channels)

| Exit | Meaning | Channel |
|------|---------|---------|
| `0` | pass | stdout is injected into session context on `SessionStart` |
| `2` | block | stderr is returned to the caller as the reason |
| other | fail-open | treated as pass; never blocks the session |

`PostToolUse` warnings use `hookSpecificOutput.additionalContext` (JSON, exit 0), never exit 2
— the tool already ran, and exit 2 there pollutes the blocked-event signal.

## HARD Rules

- **[HARD] All hook dispatch goes through the single shim `hooks/ramo/ramo-hook.sh`.**
  No other shell script may be registered as a hook handler.
  WHY: multiple entry points make the dispatch path unauditable and the seeded file set
  ambiguous. Held by `harness/settings.hooks.json`, which registers every event through the
  one shim, and by `harness/MANIFEST`, which carries one shim entry; no shipped test checks
  it, so a change to either file is reviewed against this rule.

- **[HARD] The shim contains no logic.** Path resolution, an existence guard, and `exec` only.
  No JSON parsing, no event branching, no `jq`.
  WHY: shell is the layer with the worst failure diagnostics and no test harness; every
  judgment belongs in Python where it can be unit-tested. The ceiling is
  `.claude/schema/harness.json` `limits.shim_max_lines`; no shipped check measures it, so the
  shim is reviewed against it whenever it changes.

- **[HARD] Handlers are python3 stdlib only.** No third-party imports in
  `hooks/ramo/handlers/**`.
  WHY: handlers run on every matching tool call in a consumer repository that has no
  guaranteed virtualenv; an import error becomes a session-wide failure. Model discipline
  plus review: no shipped test parses the handlers' imports, so check every import against
  the interpreter's stdlib (`sys.stdlib_module_names`) when a handler changes.

- **[HARD] Every handler ships with tests in the same change.** A new handler without a
  matching test in the repository's test suite is incomplete.
  WHY: a hook that never fires is indistinguishable from a hook that passes; an earlier
  version shipped a status-routing handler that fired zero times and nobody noticed. The
  payload ships no hook test suite, so this is held by review: the change that adds a
  handler also adds the test that feeds it a payload and asserts its exit code.

- **[HARD] Every path a seeded asset cites MUST be added to `harness/MANIFEST` in the same
  change that introduces the citation.**
  WHY: a consumer repository receives only what MANIFEST lists. An asset citing a path that
  was never seeded produces a silent degradation, not an error — the agent reads nothing and
  falls back to a conservative default. This exact class shipped twice: once as data files a
  bundled binary never collected, and again when many seeded assets cited
  `schema/harness.json` while MANIFEST omitted it (`verify` silently pinned its fix budget to
  one round). Enforced in part by `scripts/gen-manifest.sh --check`, which `install.sh` runs
  and which fails when MANIFEST and the `harness/` tree disagree. Whether a cited path lies
  inside `harness/` at all is not checked mechanically; it is reviewed with the citation.

- **[HARD] A blocking gate MUST have an environment kill switch, and its name is declared in
  `.claude/schema/harness.json` (`hooks.events.<event>.kill_switch`), not only in the handler.**
  A handler that can deny tool calls reads that single `RAMO_*_ENABLED` variable and passes
  everything through when it is set to `false`.
  WHY: gates misfire. `pre_bash.py` denied legitimate Class-B commands in integration testing
  because the rule and the implementation disagreed, and the only remedy was editing the
  handler in place — which breaks `ramo verify` for every consumer.
  A name that lives only as a Python constant cannot be checked against the rule that promises
  it, and this is not hypothetical: `subagent_stop.py` shipped as a blocking gate with no switch
  at all, and the omission was invisible until the schema field made it a missing key. Every
  blocking gate's message also names its own switch, so a false positive shows the way out on
  the same screen rather than sending someone to find this file. Held today by both blocking
  handlers (`pre_bash.py` and `subagent_stop.py` each read the `GATE_ENV` their schema entry
  names, and `pre_bash.py`'s `block()` prints it); no shipped test compares the schema field
  with the handler, so a new blocking handler is reviewed against this rule.

## Logging Contract

Handlers log through `_common.log_event`. Log records carry **key names only** by default —
never values, paths, command text, or output previews — and the log file is created `0600`.

**[HARD] The one opt-in exception is `RAMO_HOOK_LOG_VERBOSE=true`.** When set, a
handler may pass `verbose_extra` to `log_event`, and its content lands under the record's
`verbose` key — currently only `pre_bash.py`'s `block()`, which logs the denied command
text. Default is unset (`false`), which preserves the original key-names-only behavior
byte-for-byte.
WHY: key-names-only made post-hoc audit of an individual block impossible — it had been
recorded as a known limitation rather than an accepted design. The
trade-off itself does not change (a session that never sets the variable gets exactly the
old privacy stance); what changes is that a team that needs to audit *why* a specific
command was blocked now has a documented, explicit way to opt in, rather than editing the
handler to add ad hoc logging. Held by `_common.log_event`, the only log writer: it drops
`verbose_extra` unless the variable is set and opens the file `0600` in both modes. No shipped
test asserts it, so a change to `log_event` is reviewed against this contract.

## Adding a New Handler

1. Write `hooks/ramo/handlers/<name>.py` (stdlib only, `main()` returning an exit code).
2. Add its tests to the repository's test suite, including the failure path (HARD 4).
3. Register the event in `harness/settings.hooks.json` with `<name>` as the shim argument.
4. Regenerate `harness/MANIFEST` (`scripts/gen-manifest.sh`).
5. If the handler blocks, add its kill switch, declare it in the schema, and name it in the
   block message (HARD 6).
6. If the handler cites any seeded path, confirm that path is in MANIFEST (HARD 5).

Declaring an event for observability only (no judgment) still requires steps 1-4; a handler
that always returns 0 is legitimate, a registered event with no handler is not.

## Incorrect / Correct

```bash
# Incorrect — event branching in the shim
case "$1" in SessionStart) exec python3 handlers/session_start.py ;; esac

# Correct — the handler name is the registration argument; the shim never decides
exec python3 "$H" "${@:2}"
```

## See Also

- `common/output-contract.md` — the envelope contract `subagent_stop.py` enforces.
- `workflow/12-subagent-bash-hygiene.md` — the allow-grammar `pre_bash.py` enforces.
- `common/state-discipline.md` — the no-mtime rule `pre_bash.py` also enforces.
