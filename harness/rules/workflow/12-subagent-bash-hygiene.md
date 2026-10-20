---
description: Sub-agent Bash command hygiene SSOT — allow-grammar, Class A/B/C enforcement table, rewrite cookbook
---

# Sub-Agent Bash Command Hygiene

**SSOT for sub-agent Bash command hygiene.** Loaded globally (no `paths:`): it governs how
sub-agents *shape* Bash commands, a concern not tied to which files are edited. Agent and skill
files that declare `Bash` **cite** this file by path and MUST NOT restate the allow-grammar or
the class table.

## Why

Claude Code's permission engine never auto-approves a Bash command containing shell expansion
or control flow, regardless of any `settings.json` allowlist entry. On a background-spawned
sub-agent the resulting approval prompt has nowhere to render — the sub-agent appears to hang,
and the orchestrator burns a retry slot on a command that was never going to execute in that
form. No allowlist widening fixes this: the expansion/control-flow check runs before allowlist
matching.

## Allow-grammar (SSOT definition)

A sub-agent Bash command is **plain** if and only if it contains **none** of the following:

- `$` (any use — variable expansion, `$(...)`, arithmetic `$((...))`)
- backtick (`` ` ``)
- `<(` or `>(` (process substitution)
- `<<` (heredoc)
- a word-boundary occurrence of `for`, `while`, `until`, `do`, `done`, or `cd`

Pipelines (`|`) and `&&`/`;` chains **of plain commands** are fine — only the tokens above trip
the gate. `git log --oneline | head -20` is plain; `for f in *.py; do rg TODO "$f"; done` is not.

## Agent Class Table (v0 roster)

Roster assignments are single-sourced in `.claude/schema/harness.json` (`agents.roster[*].bash_class`).

| Class | Agents | Enforcement |
|-------|--------|-------------|
| A — full deny | ramo-plan-evaluator, ramo-critique, ramo-audit, ramo-model-design, ramo-wiki-writer, ramo-wiki-reviewer, ramo-wiki-reader, ramo-research-reader | Bash denied outright by `pre_bash.py::main`, regardless of command content — reviewers and the model designer have no legitimate shell need, and the research reader handles fetched web text, where a shell is the widest injection blast radius |
| B — hygiene-gated | ramo-plan-writer, ramo-plan-improver, ramo-explore, ramo-data-explore, ramo-model-explore, ramo-data-design, ramo-data-verify, ramo-model-verify | Allow-grammar enforced by `pre_bash.py::NOT_PLAIN` deny: plain commands pass to normal permission evaluation; non-plain commands are denied with rewrite guidance. ramo-data-design holds Bash only for the data access adapter's metadata and `explain` commands (`.claude/rules/data/warehouse-access.md`); that limit is stated in its agent file and is model discipline |
| C — write agents | ramo-data-implement, ramo-model-implement, ramo-doc-writer | Guidance only — the hook does not intervene; heredoc patterns stay legal |

## HARD Rules

- **[HARD] Class-B agents write single plain commands only.**
  WHY: a non-plain command from a background sub-agent produces an invisible permission prompt
  and a false hang. Enforced by `pre_bash.py::NOT_PLAIN` (deny with rewrite guidance).
- **[HARD] Agent/skill `.md` files MUST NOT embed command templates containing `${`, `$(`, or
  backticks for Class-A or Class-B agents.**
  WHY: a shell-expansion template baked into a prompt reproduces the hang deterministically on
  every invocation. Model-discipline grade, reviewed whenever an agent or skill file changes; a
  template that slips through is still denied at run time by `pre_bash.py::NOT_PLAIN` for
  Class B, which turns the hang into a visible block.
- **[HARD] Every Bash-declaring agent `.md` cites this file by path** in its constraints —
  never restates the allow-grammar or class table inline.
  WHY: a restated table drifts from the SSOT the hook actually enforces — several agent files
  had already lost `until`/`do`/`done` and bare `$` from their inline copies. Model-discipline
  grade, reviewed whenever an agent file changes.

## Rewrite Cookbook

| Forbidden form | Plain replacement |
|-----------------|--------------------|
| `for f in *.py; do rg TODO "$f"; done` | One `rg TODO` across the glob, or one Grep tool call per file |
| `diff <(cmd1) <(cmd2)` | Write each output to a real temp file, then `diff file1 file2` |
| `cd apps/x && pytest tests/` | `pytest apps/x/tests/` — pass the path as an argument |
| `echo ${RAMO_DOCUMENTATION_LANGUAGE:-ko}` | `printenv RAMO_DOCUMENTATION_LANGUAGE` |
| `cat "$(git rev-parse --show-toplevel)/CLAUDE.md"` | Run `git rev-parse --show-toplevel` alone, read the output, then Read the literal path |

## Enforcement Layers

| Layer | Mechanism | Precedence |
|-------|-----------|------------|
| 1 — agent tools | The agent's own `tools:` frontmatter. A Class-A agent simply has no `Bash`. | Structural; nothing to bypass |
| 2 — hook | `pre_bash.py` applies the Class-A full deny and the Class-B allow-grammar deny on every sub-agent `Bash` PreToolUse call. A `deny` decision always wins over any `settings.json` allow entry. | Mechanical, grade 1 |
| 3 — this rule | The HARD rules above, cited by every Bash-declaring agent, keep the violation from being written into a prompt at all. | Model discipline, grade 3 |

Layer 3 is the primary control and layer 2 is the backstop, not the other way round.

The allow-grammar above is judged on the **original command text**, heredocs included: a `<<`
in a Class-B command is a Class-B violation whether or not its body would run. The SQL gates in
the same handler read a rewritten form instead (`pre_bash.py::strip_heredoc_bodies` and
`::strip_quoted_literals`), because those gates ask what a statement *is* rather than what a
command *contains*. The two readings are deliberately different and neither is a relaxation of
the other.

### Kill Switch

`RAMO_BASH_GATE_ENABLED=false` disables `pre_bash.py` entirely for the session — every class,
every pattern, pass-through with a `gate_disabled` log entry.

WHY a blocking gate needs one: this gate has already misfired. In integration testing it denied
a run of legitimate Class-B commands because this rule and the handler disagreed about pipes,
and the only remedy available was editing the handler in place — which breaks `ramo verify`
(the manifest check) for every consumer repository. The requirement is generalized in
`workflow/08-hook-conventions.md`.

Disabling the gate does not relax the HARD rules above; it removes the mechanical backstop
while model discipline still applies.

## See Also

- `common/output-contract.md` — the `<ramo>` contract sub-agents owe regardless of Bash denial.
- `common/state-discipline.md` — the mtime-query ban `pre_bash.py` also enforces.
- `workflow/08-hook-conventions.md` — hook authoring SSOT, including the kill-switch requirement.
