---
description: Workflow state discipline — .ramo/ layout, frontmatter as state, no mtime queries, missing file = BLOCKED
---

# State Discipline

Loaded globally (no `paths:`): every workflow step reads or writes state, so this contract
cannot be scoped to particular files.

Workflow state lives **outside the session**, on disk, under `.ramo/`. State is YAML
frontmatter in markdown files — human-readable and hand-fixable.

## Layout

| Directory | Contents | Written by |
|-----------|----------|-----------|
| `.ramo/plans/` | plan documents (frontmatter `status:` is the state) | plan skill, ramo-plan-writer/improver |
| `.ramo/todo/` | run's materialized task tracker; per-row evidence records `{plan-stem}-evidence/row-{nn}.json` (schema `state_records.row_evidence`) | run skill (records also by verify after a Fix round) |
| `.ramo/interviews/` | interview outputs (volatile input to eda and plan) | interview skill |
| `.ramo/eda/` | exploration findings: feature candidates with measurements, leakage candidates (volatile input to plan) | eda skill |
| `.ramo/diagnoses/` | slice error decomposition, cause hypotheses, ranked next-experiment candidates (volatile input to the next plan) | diagnose skill |
| `.ramo/research/` | research run state `{run}.md` (questions, curated sources and their topics, per-source status) and reader reports `{run}/{batch}.md`; the committed result is `docs/research/<topic>/README.md` | research skill |
| `.ramo/context/` | session context notes, stage reports, `promotion-candidates.md` (run/verify append, doc consumes) | skills |
| `.ramo/logs/` | hook logs (0600, key-names-only) | hook handlers |

`.ramo/` is gitignored: it is **intentionally volatile** workflow state. Durable knowledge is
promoted to `docs/` by the doc skill. `.ramo/` paths are therefore banned as SoT evidence
(`common/sot-authoring.md` SOT-1).

## HARD Rules

- **[HARD] Never use mtime to find state** (`ls -t | head -1` and equivalents).
  WHY: mtime is not state — `git checkout`, opening a file, or editor autosave changes it.
  Query `status:` frontmatter instead. Enforced by `pre_bash.py::MTIME_GUESS` (exit 2) for the
  mtime-ordering `ls` flag family when the same command names a `.ramo/` path — mechanical
  grade. Every other mtime-ordering form (`find -newer`, `stat` on mtime) is model-discipline
  grade.
- **[HARD] Missing state file = BLOCKED, never silently create or guess.**
  WHY: a silently recreated file hides that state was lost, and downstream steps then run
  against fabricated state. Enforced by each workflow skill's Step 0 — model-discipline grade,
  no mechanical check.
- **[HARD] `status:` values form a closed set**: `draft | active | done | superseded`.
  A value outside the set = BLOCKED. Enforced by each workflow skill's Step 0 —
  model-discipline grade, no mechanical check on `.ramo/` frontmatter.

## Write Discipline

- **Single writer**: one file has one writing skill at a time. Skills update state at step
  boundaries; hooks only observe, never write state.
- **JSON records are derived handoffs**: a row evidence record is written through
  `acceptance.py::write_record` (temp file, then `os.replace`). The tracker frontmatter and its
  row `Status` stay the state of record; a `done` row with no PASS record, or a record ahead of
  its tracker, is BLOCKED ("state inconsistent"), never reconciled by guessing.
- **Atomic rename**: write to a temp file in the same directory, then `os.replace` /
  `mv -f` over the target. A torn frontmatter is worse than a stale one.
- **The harness assumes a single session** per repository working on `.ramo/` state.
  Concurrent-session detection is out of scope; do not build partial locking.

## Resume Contract (dual path)

1. `SessionStart` hook injects a summary of the `status: active` plan (primary path).
2. Every workflow skill's Step 0 reads `.ramo/` directly (survives hook death).

Both paths read the same frontmatter; neither uses mtime.

## Incorrect / Correct

```bash
# Incorrect — mtime guessing
ls -t .ramo/plans/ | head -1

# Correct — state query (frontmatter), explicit failure
grep -l "^status: active" .ramo/plans/*.md   # 0 matches → BLOCKED, ask the user
```
