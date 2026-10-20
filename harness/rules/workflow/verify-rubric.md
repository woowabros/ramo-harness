---
description: Verify judgment sets — 10 fidelity items per execution row (@ramo-critique), 14 validity items (9 model for @ramo-model-verify, 5 data for @ramo-data-verify), 5 audit surfaces (@ramo-audit). Cells, not scores; the main session turns each FAIL cell into one EV ticket at the item's priority.
paths:
  - ".ramo/todo/*.md"
---

# Verify Judgment Sets

The judgment half of the verify pair; `.claude/rules/workflow/04-verify.md` is the procedure half
and the two cite each other. Each seat fills cells for its own items and nothing else. The main
session collects the cells and maps them to tickets by the Priority Mapping below, with no vote
(`04-verify.md` Synthesis without votes).

The sets answer two questions only: **was each row built as the plan says (fidelity), and is
the experiment valid as a measurement (validity)**, plus the cross-cutting safety surfaces.
Whether the result is good is `/ramo:diagnose`'s question. Code shape (lint, type, naming, size,
debug prints) is not judged here: `04-verify.md` Gate 5 reports lint and file size as two lines,
secrets and debug output are `audit.credentials`, and a logic defect in code is
`fid.correctness`.

Totals: 10 fidelity items, 14 validity items, 5 audit surfaces.

**Vocabulary scope (HARD):** the cell values and ticket labels on this page are report-local and
never appear inside `<ramo>` tags or envelope `verdict:` fields.
WHY: three label layers colliding in one field made an earlier version's verdicts
unparseable. Enforced by `subagent_stop.py::main` (verdict closed set per roster seat).

## Cells

| Value | Meaning |
|---|---|
| PASS | the question holds, with an anchor |
| FAIL | the question fails, with an anchor |
| N/A | the item does not apply to this row, by the N/A rules below |
| NOT-RUN | the re-derivation needs something absent (a precondition, an undeclared input, a retrain); the cell names what and what it would cost |
| UNANCHORED | the seat could not anchor either verdict |

An **anchor** is a `file:line`, a gate line from Steps 1-2 of the skill, or a measured value with
its source. The record a row wrote under `.ramo/todo/*-evidence/` is the implementer's own
claim: it tells a seat where to look and is never itself the anchor.

## Item Sets

| Set | Seat | Items | Filled for |
|---|---|---|---|
| Fidelity | @ramo-critique | 10 | every execution row |
| Validity (model) | @ramo-model-verify | 9 | the experiment, when the plan has a `model-training` row |
| Validity (data) | @ramo-data-verify | 5 | each `data` row |
| Audit | @ramo-audit | 5 | the canonical change list and the evidence records |

## Fidelity Matrix

| ID | Question per row | PASS anchor | Judged by |
|----|------------------|-------------|-----------|
| fid.deliverable | Every `Deliverable` exists, is non-empty, and matches the sha256 its record states | Gate 2 line | Gate 2 |
| fid.checks | Every command on the row's unit `Checks:` line re-runs with exit 0 | Gate 3 line | Gate 3 |
| fid.evidence | Every evidence invariant holds and every key re-derives: `quality_checks` all passed and non-zero, `row_reconciliation` sides equal, `seed`/`split_boundary` equal to the validity block, `query_hash` and `feature_spec` recomputed equal (Gate 3), `seed` reaches every RNG consumer, `split_boundary` is the value the split call uses, `data_snapshot` names a pinned partition rather than `latest` or `current_date` | Gate 3 line + `file:line` | Gate 3 for the recomputed half, @ramo-critique for the code half (Gate 3's literal grep hits are its input, not its verdict) |
| fid.decisions | Each `binding` D-row is visible in the code | `file:line` per D-id | @ramo-critique |
| fid.correctness | The code the row wrote computes what its unit says: no output-changing logic defect (wrong join key, time zone, sign, off-by-one) | `file:line` + the wrong value or a reproducing snippet | @ramo-critique |
| fid.unit-shape | The row's files stay inside its §6 unit, and the plan's `Boundary:` line holds | row map + `file:line` | Gate 4 + @ramo-critique |
| fid.no-substitution | The declared method is the one built: model family and objective, extraction strategy, join grain, and the §3 transform list | `file:line` against §3/§4 | @ramo-critique |
| fid.no-reduction | No silent reduction of data, budget, slices, or features. `.head(`, `.sample(frac<1`, `nrows=`, `LIMIT` fail only where they shrink a declared artifact on the dataset-build, training, or evaluation path; exploration and example code are out of scope | grep hit + evidence value + lineage | @ramo-critique |
| fid.no-shortcut | No hardcoded or oracle values: a metric literal in a report, a prediction derived from the label, `except: pass`, an assertion that cannot fail | `file:line` | @ramo-critique |
| fid.scope | No canonical file left unmapped and unclassified, no feature the plan never named | Gate 4 + `file:line` | Gate 4 + @ramo-critique |

N/A: a `docs` row takes `fid.deliverable`, `fid.checks` (when its entry has checks), and
`fid.scope` only. `fid.no-reduction` is N/A on a `data-analysis` row with no declared quota.

## Validity Checklist

Each seat re-derives cheaply from committed code and on-disk artifacts, never by retraining or
re-extracting; such a need is NOT-RUN with its reason and cost. A measured cell states three
things: expected, observed, source. The interpreter for a one-liner is the one Step 0 of the
skill resolved (`uv run python` when the repository has `uv.lock`, else `python3`), and row
reads stay under `limits.verify_probe_max_rows`.

Every command written in the two tables below is a single plain command under
`.claude/rules/workflow/12-subagent-bash-hygiene.md` (no `$`, backtick, heredoc,
`for`/`while`/`do`/`cd`, and so no comprehension), with any pipe inside a table escaped.

**No model rows: the model validity checklist does not apply, and the report says so.** The same
holds for data rows and the data checklist. An absent checklist scored as failures would fail
every pure dataset build, and one silently counted as passed would hide the same fact.

### Model rows

| ID | Item | Low-cost re-derivation | NOT-RUN when | Rules |
|----|------|------------------------|--------------|-------|
| leak.fit-on-train | L1: every `.fit(`, `fit_transform(`, `groupby(...).transform('mean')`, and target or leave-one-out encoding sees train rows only, after the split | grep the calls, then read the frame's lineage back to the split | never | `model/leakage.md`, `model/feature-engineering.md` |
| leak.boundary | L1/L3: `max(ts in train) < split_boundary <= min(ts in test)`, and the boundary literal is the same in the plan and the code | `df.groupby('split')[ts].agg(['min', 'max'])` on the prediction or feature file | `timestamp_column` undeclared | `model/leakage.md` |
| leak.forbidden | L2: the `features` file and `forbidden_columns` do not intersect | set intersection of the two lists | `forbidden_columns` undeclared (plan-rubric `eval.validity-declared` catches that) | `model/leakage.md`, `data/data-quality.md` |
| leak.probe | L2 probe: no single feature reaches `limits.verify_target_probe_abs_corr` against the target | `df.corr(method='spearman')` on `feature_sample`, target column only | `feature_sample` undeclared | `model/leakage.md`, `data/eda.md` |
| leak.group | L3: `group_key` values in train and test are disjoint | `set(train[g]) & set(test[g])` | the split is not grouped | `model/leakage.md` |
| eval.cells | Every metric x slice cell is present with its n, recomputes within `metric_tolerance` from the prediction file, marks cells under `min_n`, and carries the signed mean error per slice | `df.groupby(slice).apply(metric)` against `reports/` | the prediction file is absent (Gate 2 already failed) | `model/eval-metric-slice.md` |
| eval.baseline | The baseline was scored on the same split and snapshot | read both artifacts, compare row counts and boundaries | no baseline artifact | `model/eval-metric-slice.md` |
| eval.test-once | The test split is touched once; early stopping, thresholds, and selection use validation. The grep is a variable-name heuristic and says so | grep `test` uses, then read each call site | never | `model/leakage.md`, `model/training-budget.md` |
| budget.declared | Ceilings, `min_delta`, and iteration counts match §4, and the declared loss curve exists | grep the config, read the artifact | no loss curve declared | `model/training-budget.md` |

### Data rows

| ID | Item | Low-cost re-derivation | NOT-RUN when | Rules |
|----|------|------------------------|--------------|-------|
| dq.checks | Every declared quality class ran with its measured value, and the artifact-only half re-runs | `len(df)`, `df.isna().mean()`, `df.describe()` on the parquet, or `run_checks.py --artifact-only` | the source-reconciling half is unreachable | `data/data-quality.md` |
| dq.reconcile | `row_reconciliation` equals the parquet metadata, a pinned-snapshot `population` recount agrees, and every `dataset_tables` entry exists (`ramo-data.py schema <table>` through the data access adapter) | `pyarrow.parquet.read_metadata(path).num_rows`, adapter `query` count and `schema` | the warehouse is unreachable | `data/dataset-materialization.md`, `data/data-quality.md` |
| sql.window | Feature windows end before the anchor, the label window is the declared one, and exclusion predicates are the D-rows' | read the SQL | never | `model/leakage.md`, `data/data-quality.md`, `data/table-pitfalls.md` |
| sql.grain | No duplicate at the declared grain, and `sample-determinism` reproduces | `df.duplicated(keys).sum()` | a source recount is unreachable | `data/data-quality.md`, `data/table-pitfalls.md` |
| tables.retention | Every workspace table has a declared retention, the residual list is reported, and no `intermediate` table is alive. **A present `experiment` table is expected, never a finding** | evidence values + adapter `search` | the warehouse is unreachable | `data/dataset-materialization.md` |

## Audit Surfaces

| ID | Surface | Checked against |
|----|---------|-----------------|
| audit.credentials | No secret or token appears as a value in code, config, an evidence record, or a report; no debug output prints one | canonical list + evidence records |
| audit.pii | No sensitive column value reaches `.ramo/`, `docs/`, `wiki/`, a log, or a report; names and shapes only | canonical list + evidence records |
| audit.write-boundary | No warehouse write lands outside `.claude/schema/harness.json` `data.workspace_schema` | changed `.py`/`.sql` + evidence records |
| audit.untrusted | No trace of tool output or a table comment being followed as an instruction | canonical list + reports |
| audit.cost | No cost or blast radius the plan did not state | canonical list + evidence records |

@ramo-audit never reproduces a credential or a PII value in its cell; it names the location and
the column.

## Priority Mapping

**The line is whether the item decides the result or exposes something irreversible.** Only
EV-P0 opens a fix round (`.claude/rules/workflow/09-ticket-schema.md` Priority Definitions).
Every item appears exactly once.

| Priority | Items whose FAIL lands here |
|----------|------------------------------|
| **EV-P0** | fid.deliverable, fid.checks, fid.evidence, fid.decisions, fid.correctness, fid.no-substitution, fid.no-reduction, fid.no-shortcut, leak.fit-on-train, leak.boundary, leak.forbidden, leak.group, eval.cells, eval.baseline, eval.test-once, dq.checks, dq.reconcile, sql.window, sql.grain, audit.credentials, audit.pii, audit.write-boundary |
| **EV-P1** | fid.unit-shape, fid.scope, leak.probe, budget.declared, audit.untrusted, audit.cost |
| **EV-P2** | tables.retention |

An `eval.cells` cell that fails only on a missing n is EV-P1; a missing or disagreeing cell is
EV-P0.

- **[HARD] An item outside these tables is not judged. A logic defect in the code is anchored as
  `fid.correctness`, not raised as a free-standing finding.**
  WHY: open-ended review is where the findings budget went before: most of one cycle's
  blocking findings changed no output value. A closed set keeps that budget on the questions
  that decide the result, and `fid.correctness` is the landing place for the defect the closed
  set would otherwise miss, which is why "reading the code is a verification step" survives in
  `04-verify.md`. Model-discipline grade, for the set and for a seat staying inside it.
- **[HARD] The safety surfaces stay at EV-P0.** `audit.credentials`, `audit.pii`, and
  `audit.write-boundary` are exposures no later round can undo, which is why they stayed at
  P0 when P0 became the only round trigger. Model-discipline grade: the mapping above is the
  single source.

## Report Verdicts

| Label | Condition |
|-------|-----------|
| PASS | 0 EV-P0 open, 0 EV-P1 open; Gates 1-4 clean |
| PASS (with notes) | 0 EV-P0 open; EV-P1 tickets remain, each listed with the reason it was not fixed. The gate marker's `verdict` field is `PASS` |
| FAIL | any EV-P0 remains after the fix-loop budget, a plateau, or an open stop ticket |

No score and no grade: the verdict keys on tickets alone, so there is no second number that
could disagree with it.
