---
description: The plan-to-run machine handoff — frozen Execution Structure column contract, `[CP]` marking criteria, and the domain delegation map. The half of the plan format `ramo-run` parses, split from `01-plan.md` which is written for the person.
paths:
  - ".ramo/plans/*.md"
  - ".ramo/todo/**"
---

# Plan Execution Interface

`01-plan.md` opens by saying a plan has two readers who need different things. This file is the
machine reader's half: what `ramo-run` parses, and the two contracts that decide what it does
with each row. `01-plan.md` keeps everything written for the person.

Splitting them was not cosmetic. Both halves sat in one file past the rule line ceiling of
the time (`.claude/schema/harness.json` `limits.rule_max_lines`, since raised), and the
responsibility boundary the file already articulated in its own opening paragraph is where it
wanted to come apart.

## Execution Structure

After the change units, provide phases ordered by dependency. The task table is the
machine-readable handoff consumed by `ramo-run` — the 6-column contract below is frozen and
parsed mechanically; do not rename, add, or drop columns.

```markdown
# Execution Structure

## Phase 1 — {outcome}

| # | Task | Domain | Type | Dependencies | Deliverable |
|---|------|--------|------|--------------|-------------|
| 1 [CP] | {decision-stating slice naming change unit + files} | data | data-extraction | — | `sql/...`, `.ramo/...` |

Gate: {observable condition that ends this phase}
```

Column contract (parser-facing):

| Column | Allowed values / format |
|---|---|
| `#` | integer task id, unique across all phases; optional ` [CP]` suffix marks critical path (criteria below) |
| `Task` | free text naming **exactly one** change unit token `U{n}` (docs and `other` rows exempt) plus concrete files/symbols; states a decision already made, never a goal restatement |
| `Domain` | `data` \| `model` \| `docs` (closed set; any other value is a visible BLOCKED in ramo-run, never a silent fallback). **Not the same set as the schema's `domains` registry** — `docs` is a deliverable kind, owns no evidence contract, and has no `rules/docs/` |
| `Type` | the task type declared by this row's domain, or `other` — drives the evidence gate. Closed set: `data-extraction` \| `dataset-build` \| `data-analysis` (data) \| `model-training` (model) \| `code-change` (code, contract-only in this version) \| `other` (belongs to no registered domain; requires nothing, so declaring it for work that does belong to one empties the gate). SSOT: `.claude/schema/harness.json` `domains.<name>.evidence` |
| `Dependencies` | comma-separated task ids, or `—` |
| `Deliverable` | exact output file paths/artifacts; backticked paths are the list `acceptance.py` reads, and the single list of what the row produces |

- Every phase ends with one `Gate:` line naming its observable pass condition.
- Split cross-domain work into separate rows; group independent tasks in the same phase.
- The first task is the thinnest end-to-end slice piercing the highest-risk integration point.
- A one-row table means the plan itself is unnecessary — say so instead of writing it.

**Each row's acceptance is derived, not written in a column or a block.** The `Task` cell's
`U{n}` maps the row to its change unit; that unit's `Binding decisions:` and `Checks:` lines are
the row's binding and its check commands, and a model plan's §5 carries a `validity` block. The
derivation is specified in `01b-acceptance-contract.md`; the `Type` column decides which
evidence keys the row owes.

## Marking `[CP]`

> **`[CP]` is not `CP-`.** This page's `[CP]` is a **row marker** on the execution table
> meaning critical path, and it triggers a human briefing. The `CP-` in `CP-P0-001` is a
> **ticket prefix** meaning consensus-derived at the plan stage
> (`.claude/rules/workflow/09-ticket-schema.md` Prefix Table). Same two letters, unrelated
> machines: a row is marked, a ticket is numbered. A real user read one as the other, which is
> why both pages now say so; renaming either is deferred because the marker is part of
> the frozen column contract above.

`[CP]` triggers the design briefing (`.claude/skills/ramo-run/rules/human-gates.md` gate 1,
before the row is delegated), so which rows carry it decides where a person gets to look. Mark a
row when **any** holds; the shared reason is that no later row re-asks the question.

| Criterion | Example |
|---|---|
| Its output feeds every downstream row | dataset, split, feature table |
| It fixes a contract others build against | schema, interface, boundary, naming |
| It embeds a judgement nothing revisits | prediction anchor, label definition, feature semantics, split boundary, exclusion predicate |
| It is the thinnest end-to-end slice | the first task, per the Core Quality Contract |

`[CP]` is **not** "hard" or "long": a 400-line mechanical transform with one consumer is not
critical path, and a three-line predicate deciding which rows exist is. Under-marking is the
failure that matters, since an unmarked row is decided and built with nobody outside the agent
seeing it, while over-marking costs one briefing the user can wave through. When genuinely
unsure, mark it. Scored by `plan-rubric.md` `exec.cp-marking`.

## Delegation and Domain Mapping

Agents must exist in the roster (`.claude/schema/harness.json` `agents.roster`); do not invent names.

| Domain | Implement agent | Verify agent (verify stage) |
|--------|-----------------|------------------------------|
| data | @ramo-data-implement | @ramo-data-verify |
| model | @ramo-model-implement | @ramo-model-verify |
| docs | @ramo-doc-writer | — |

**Why there is no `Mode` column any more.** It carried the choice between a single delegation
and a per-task design-critique-implement-verify cycle, and an earlier version removed the second: the design
belongs to §1's 선결 결정 table, and re-deciding it per task cost several spawns each while its
redesign budget was spent in full on two tasks in one cycle. A column whose only legal value is
`B` states nothing, and `01-plan.md` forbids keeping a section that has nothing to report — the
same applies to a column. What the cycle bought is kept in `ramo-run`: the design briefing and
the query gate (`.claude/skills/ramo-run/rules/human-gates.md`), the per-row named check, and
the verify stage that follows.

## See Also

- `01-plan.md` — the authoring half: quality contract, change units, verification, risks
- `01b-acceptance-contract.md` — the per-row acceptance block keyed to this table's row ids
- `plan-rubric.md` — scores this contract as dimension 4 (Execution Handoff)
- `.claude/skills/ramo-run/SKILL.md` — the parser that consumes it
