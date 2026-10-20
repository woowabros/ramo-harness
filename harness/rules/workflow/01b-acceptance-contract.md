---
description: How a machine judges each execution row without the plan predicting its values — the row-to-unit mapping derived from the Task cell, the unit's optional Checks line, the §5 `validity` block for model plans, evidence invariants that hold for every plan, the parse-time BLOCKED list, the row evidence record, and what the implementer is never shown. Parsed by `.claude/skills/ramo-run/scripts/acceptance.py`
paths:
  - ".ramo/plans/*.md"
  - ".ramo/todo/**"
---

# Row Check Contract

`01a-execution-structure.md` says what each row is and who builds it. This file says how a
machine decides the row was built as planned. In earlier versions the only machine-readable parts of a
plan were the six-column table, `[CP]`, and the presence of `Gate:` lines: whether a row met its
plan was a model reading prose, and a row reporting `quality_checks: 0/0` passed run's gate in a
test drive until a person asked again.

**A plan declares what is built and how it is measured, never what the values will be.** An
earlier draft asked each row for evidence expectations (an exact literal, a regex, an integer range).
They were withdrawn in the same release for three measured reasons: relayed to the implementer
they became the target the row was built to, an author with nothing to predict wrote formal
patterns such as `~ .`, and a guess made before the data was seen outranked the data's own
answer.

One script, `.claude/skills/ramo-run/scripts/acceptance.py`, judges at three points: plan
Step 2b (`parse`), run Step 3f (`check`), verify Gate 3 (`recheck`, and `check --stage verify`
after a Fix round). Vocabulary and ceilings are single-sourced in
`.claude/schema/harness.json` `plan_blocks`, `envelope.evidence.key_formats`, and `limits`;
this file restates none of the lists.

## Row mapping

Each implementation row maps to one change unit, read from what the plan already carries.

| Row field | Read from |
|---|---|
| `unit` | the one `U{n}` token in the row's `Task` cell, resolved against a `### U{n}` heading |
| `binding` | that unit's `- **Binding decisions:** D1, D3` line (or `none`), each id resolved against a `\| D{n} \|` row of §1 |
| `checks` | that unit's optional `- **Checks:**` line (next section) |

A `Domain: docs` row and a `Type: other` row are exempt: they need no unit token, and a token
they carry is used when it resolves. Several rows may name the same unit; each then runs that
unit's checks.

**The mapping is not a seventh column.** The six-column header is frozen and the parser matches it
literally, and a frontmatter field is pinned the same way, so the mapping is derived from the Task cell and the
unit's own lines instead.

## Unit checks

```markdown
### U1. 데이터셋 구축

- **Binding decisions:** D1
- **Checks:** `uv run pytest tests/test_trip_dataset.py`, `uv run python -m sql.lint sql/trip_dataset.sql`
```

Each backticked command on the line is one check, and **exit 0 within
`limits.run_row_check_command_max_seconds` is the only pass signal**. There is no output pattern
to match and no per-command budget: a check says how the unit is exercised, never what it will
print. A command known to run longer than the ceiling belongs in the plan's verification
commands, not here.

A check command is plain under `workflow/12-subagent-bash-hygiene.md` and never a SQL CLI in
command position. The parser imports the grammar and the CLI name set from `pre_bash.py` rather
than copying them, so a check the parser accepts is a command the hook lets the main session run.

The line is optional. A unit with no check still passes the parser; `plan-rubric.md`
`verify.commands` and `verify.files` score whether its verification is concrete, and the
invariants below still judge its evidence.

## Validity

A plan with a `model-training` row carries exactly one fenced `validity` block in §5; a plan
without one carries none. It is the measurement design, declared before the run: what the
verify validity seat recomputes against, so every value names something on disk or in the
prediction file. Grammar is the envelope's YAML-lite: `key: value`, `- item` (one per line),
two-space nesting, `#` comment lines; flow syntax (`[a, b]`, `{k: v}`) is rejected with
"write one `- item` per line".

| Key | Required | Value |
|---|---|---|
| `metric` | yes | a `plan_blocks.validity.standard_metrics` name, or any name plus `metric_definition` |
| `metric_direction` | yes | `lower_better` or `higher_better` |
| `slices` | yes | slice **column names** in the prediction file, one per item |
| `baseline` | yes | a prediction-file column name or a numeric literal |
| `split_boundary`, `seed` | yes | per `key_formats`; `seed` is an integer |
| `wall_minutes` | yes | the training row's wall-clock budget, whole minutes. A budget, not a prediction: it only sets the record's `over_budget` mark |
| `anchor` | yes | the prediction-anchor column |
| `label_window` | yes | `<start col>..<end col>` or a stated period |
| `predictions` | yes | disk path of the row-level prediction file; must appear in some row's `Deliverable` |
| `prediction_columns` | yes | the file's columns: `y_true`, `y_pred`, and the baseline column when `baseline` is a column |
| `features` | yes | the feature-list file (one feature per line: name then transform); in some `Deliverable`, and the input `feature_spec` is recomputed from |
| `group_key` | when the split is grouped | the group column |
| `timestamp_column` | no | input to the temporal-boundary scan; absent means that scan is NOT-RUN |
| `forbidden_columns` | no | eda leakage candidates and post-anchor fields; `plan-rubric.md` `eval.validity-declared` fails a plan that leaves it empty while its eda artifact lists candidates |
| `feature_sample` | no | a labelled feature sample for the target probe; absent means NOT-RUN |
| `metric_definition` | when `metric` is not standard | a committed `module:function` |
| `min_n`, `metric_tolerance` | no | defaults `limits.verify_slice_min_n`, `limits.verify_metric_tolerance` |

The prediction file needs to exist on disk, not in git: `experiments/*/artifacts/` is ignored
by design. The envelope's `artifacts` list records its sha256 so verify can tell it read the
same bytes the row produced.

```validity
metric: mae
metric_direction: lower_better
slices:
  - borough
  - hour_bucket
baseline: baseline_pred
split_boundary: 2023-01-22
seed: 42
wall_minutes: 20
anchor: tpep_pickup_datetime
label_window: tpep_pickup_datetime..tpep_dropoff_datetime
predictions: experiments/2026-09-24-trip-duration/artifacts/predictions.parquet
prediction_columns:
  - y_true
  - y_pred
  - baseline_pred
features: experiments/2026-09-24-trip-duration/features.txt
forbidden_columns:
  - tpep_dropoff_datetime
  - trip_distance
  - fare_amount
```

## Evidence invariants

A row's envelope evidence is judged by rules that hold for every plan, so no author has to
predict them. Each rule's text lives beside its key in `key_formats.<key>._invariant`.

| Key | Invariant |
|---|---|
| every key the row's `Type` requires | present and non-empty (re-checked by the script: a background spawn bypasses the SubagentStop hook) |
| `quality_checks` | `<passed>/<declared>` with passed == declared and declared > 0 |
| `row_reconciliation` | both sides equal as integers after removing thousands commas |
| `data_snapshot` | no floating reference (`key_formats.data_snapshot.floating_refs`) |
| `query_hash` | matches its pattern and is a prefix of the digest recomputed from the row's `.sql` deliverables |
| `feature_spec` | matches its pattern and is a prefix of the digest recomputed from validity `features` |
| `seed`, `split_boundary` | on a `model-training` row, equal to the validity block's values |
| `dataset_tables` | contains every workspace table in the row's `Deliverable` |

The `0/0` that motivated the contract fails the second row with no plan expectation at all.

- **[HARD] A row is judged by its deliverables, its unit checks, and these invariants — never
  by a value the plan predicted.**
  WHY: a predicted value is a target once the implementer can see it, and a guess once it
  cannot; neither measures whether the row was built right. An invariant is true of every
  correct row regardless of what the data turned out to be. Enforced by `acceptance.py check`
  and `recheck`, which judge each invariant above as its own cell — mechanical.

## Parse-time validations

`acceptance.py parse --plan <file>` prints nothing and exits 0 on a conforming plan. Otherwise it
prints one English line per defect, `row {n} | {key} | {reason}` (`row -` for plan-level
defects), and exits 1.

- At least one Execution Structure row; a `Deliverable` cell backticks every path or none.
- Every non-exempt row's `Task` cell names exactly one `U{n}` ("Task cell names exactly one
  U{n}"), and that unit has a `### U{n}` heading.
- The unit carries a `Binding decisions:` line whose ids resolve, or `none`.
- A `Checks:` line backticks each command; each command is plain and names no SQL CLI.
- No `Checks` or `Binding decisions` line goes unread: one that is misspelled, repeated within
  its unit, or outside any `### U{n}` unit is a defect, never silently dropped. Fenced code is
  skipped, so a `# ` comment in a code excerpt does not end the unit.
- `validity` exists iff a model row exists; required keys are present; `seed` and `wall_minutes`
  are integers; `predictions` and `features` appear in a `Deliverable`; `metric` is standard or
  defined; slices are column names; `prediction_columns` carries the required columns; no flow
  syntax.

- **[HARD] A plan reaches review only after `parse` is silent.**
  WHY: Class-A review seats hold no Bash and cannot run the parser, so a malformed plan they
  score as fine would first fail at run time, after the review budget was spent on it. Enforced
  by `acceptance.py parse` (mechanical: every listed class is a defect line) and the plan
  skill's Step 2b gate (model-discipline grade for the step being run).

- **[HARD] The script has a kill switch declared in the schema.** `scripts.acceptance.kill_switch`
  set to `false` makes `parse`, `check`, and `recheck` print `gate_disabled` and exit 0. `check`
  then writes no record, so run updates the tracker alone and notes `gate_disabled` in the Task
  Log.
  WHY: one parser gates plan, run, and verify, so a parser defect would stop all three stages at
  once, and editing a seeded script in place turns it into a user-modified file that later
  installs skip (`lib/seed.sh` no-clobber). Implemented in `acceptance.py` (the switch is read
  before any command judges).

## Row evidence record

The stage that ran the implementer writes one JSON record per row at
`.ramo/todo/{plan-stem}-evidence/row-{nn}.json`, pass or fail: `ramo-run` Step 3f, and
`ramo-verify` after a Fix round. Its required fields and readers are listed in
`.claude/schema/harness.json` `state_records.row_evidence`. The tracker frontmatter stays the
state of record (`common/state-discipline.md`); the record is a derived handoff, and a `done`
tracker row without a PASS record is BLOCKED, never reconciled by guessing.

The record stores what a check returned, never its output: exit code, seconds, whether it
passed, and the sha256 of the full output. The full stdout stays in session scratch, because a
check's output may carry values the PII rule forbids in `.ramo/` (`common/untrusted-data-boundary.md`).
Each judged evidence item keeps its recomputed digest in the record, where verify reads it.

## Not shown to the implementer

The implementer sees the row's task, its unit's Checks commands, and its binding decisions:
that is the work. It is never shown how the row is judged.

- The delegation prompt (run Step 3d) and the Fix prompt (verify Step 7) carry no acceptance
  criteria.
- A failure line says what is wrong — `row 1 | evidence.query_hash | does not re-derive from the
  row's SQL deliverables` — and never the value that would pass. A recomputed digest in a RETRY
  line could be copied into the next envelope, and the recompute would then prove nothing.
- The verify fidelity matrix and validity checklists (`verify-rubric.md`) are never relayed to
  the implementer either. Unit checks are visible and can themselves be built to; these hidden
  cells are what judge the gap between passing a check and doing the work.

- **[HARD] Nothing an implementer reads carries the judgment criteria.**
  WHY: an agent shown its checks scores near-perfectly while an audit of the same work finds
  much of it hollow, because the checks become the target. Failure lines are built in `acceptance.py`
  without expected values or digests — mechanical; the prompts carrying no criteria is
  model-discipline grade, reviewed at verify.

## What the row check does not judge

The row check decides whether a row's recorded values are internally sound. It does not decide
whether the code computes what the unit says, whether the method was substituted, or whether a
validation claim holds; those are the verify seats' cells (`verify-rubric.md`). A green row
check is necessary for a verify PASS, never sufficient.

## See Also

- `01a-execution-structure.md` — the six-column table the mapping reads
- `01-plan.md` — §5 and §6, where the validity block and the unit lines sit in a plan
- `plan-rubric.md` — `eval.validity-declared`, `verify.commands`
- `12-subagent-bash-hygiene.md` — the allow-grammar a check command obeys
