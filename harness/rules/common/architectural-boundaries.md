---
description: DS layer ownership and dependency direction — which layer may read or write what, and where each artifact lives. Cited by the plan skill's boundary reconciliation step
paths:
  - "**/*.py"
  - "**/*.sql"
  - "**/*.ipynb"
---

# Architectural Boundaries (DS)

The layer stack here is the DS pipeline, not a web stack. Repository-layout and immutability
concerns of a web codebase do not apply; layer ownership and dependency direction are what
carry over, and they carry over intact.

This file is the procedure source for the boundary reconciliation step in
`.claude/skills/ramo-plan/SKILL.md` (cite by path; do not inline this table into a plan).

## Layer Ownership

| Layer | Owns | Reads | Writes |
|-------|------|-------|--------|
| source | warehouse tables owned by other teams | — | **never** (read-only, always) |
| extraction | snapshot queries and their outputs | source | `experiments/{exp}/data/`, declared snapshot paths, the workspace schema |
| feature | feature definitions and computation | extraction outputs | feature tables/files under the experiment |
| training | split design, model fitting | feature outputs | `experiments/{exp}/artifacts/` |
| evaluation | metrics, slices, baseline comparison | feature outputs + artifacts | `experiments/{exp}/reports/` |
| serving | batch/online serving of a promoted model | artifacts + feature outputs | its own serving target |

## Where a Derived Value Belongs

The extraction and feature layers both compute derived values, and the split between them is
the one boundary people get wrong in both directions. One question decides it:

> **Does producing this value require looking at the training labels, or at the training set's
> distribution?**

| Answer | Layer | Task type | Examples |
|---|---|---|---|
| No — it is a deterministic function of what is observable at the prediction anchor | extraction, in SQL | `dataset-build` | rolling aggregates, medians over a past window, time-of-day and weekday parts, join-derived attributes, ratios of two observed columns |
| Yes — it must be *fitted*, and fitted on train only | feature/training, in python | `model-training` | category encodings, scalers, imputers computed from train, target encoding, anything whose parameters come from the data |

The two compose rather than compete. `dataset-build` records the column set it produced
(`quality_checks` `column-set` class); `model-training` records `feature_spec`, a digest of the
columns it consumed from that dataset **plus** the fitted transforms it added. So the dataset's
columns are an input to the model's evidence key, not a rival claim on the same work.

Two consequences worth stating, because both were observed.

- **Heavy aggregation belongs in SQL and that is not a boundary violation.** A rolling median
  over a million rows computed in python is waste, not discipline. The earlier reading of these
  rules pushed derivation out of extraction and the result was dozens of derived expressions
  living in the extraction SQL with no rule acknowledging them.
- **A fitted transform in SQL is leakage, not an optimization.** The same statement that reads
  train and test cannot fit on train only. `model/leakage.md` is the checklist either side runs.

## Dependency Direction

Dependencies point **downstream only**:

```text
source -> extraction -> feature -> training -> evaluation -> serving
```

Violations to flag, each a concrete failure mode rather than a style complaint:

| Violation | Why it breaks |
|-----------|---------------|
| training reads a source table directly, skipping extraction | the run has no `data_snapshot` and is unreproducible |
| evaluation imports training internals (fitted scaler, in-memory split) | the metric measures the fit, not the model; a rerun cannot reproduce it |
| feature computation reads the label window | target leakage (`.claude/rules/model/leakage.md`) |
| serving recomputes features with different code than training | training/serving skew, invisible until production |
| extraction writes back to a source table | mutates data another team owns |

## State Ownership

Every produced artifact has exactly one owning layer and one location.

| Artifact | Owner | Location |
|----------|-------|----------|
| snapshot | extraction | declared snapshot path, named per `common/naming.md` |
| workspace table | extraction | the workspace schema, target qualified `<schema>.<name>` (`<catalog>.<schema>.<name>` on an engine with catalogs) |
| feature table | feature | inside the experiment directory |
| model artifact | training | `experiments/{exp}/artifacts/` |
| metric/slice report | evaluation | `experiments/{exp}/reports/` |
| durable conclusion | doc stage | `docs/` (promoted, not left in the experiment) |

## HARD Rules

- **[HARD] Source data is read-only; warehouse writes land only in the workspace schema**
  named by `.claude/schema/harness.json` (`data.workspace_schema`). No other table is written
  from any layer.
  WHY: blast radius differs by target. Mutating shared source data has no rollback and damages
  another team's work, while a table in the workspace schema is disposable by construction —
  a rule banning both bans the dataset step itself, which is what the earlier wording did.
  Enforced by `_common.py::sql_writes_confined_to_workspace`, reached from the shell by
  `pre_bash.py::names_sql_cli` and from authored files by `post_write.py::main`. A statement
  sent from inside a script is invisible to both; that half is covered at review time by
  `.claude/rules/data/warehouse-access.md` and the `audit.write-boundary` item of
  `.claude/rules/workflow/verify-rubric.md` — model-discipline grade.
- **[HARD] A change unit that crosses a layer boundary states the direction and the reason.**
  WHY: a boundary crossing is sometimes correct and sometimes leakage; the difference is only
  visible when it is stated. Enforced at review time by `plan-rubric.md` `shape.pattern` and
  `snapshot.lineage`, and by the boundary step in `.claude/skills/ramo-plan/SKILL.md`.
- **[HARD] Derived artifacts land inside their experiment directory or in the workspace
  schema.** Those are the only two destinations before the doc stage promotes anything, and a
  workspace table is declared in the plan's Deliverable column like any other artifact.
  WHY: scattered outputs make an experiment unrepeatable and uncleanable, but a warehouse
  dataset is not a file, and demanding that it live under the experiment directory is what put
  the dataset step outside the rules entirely. Enforced at review time by the `fid.scope`
  item of `.claude/rules/workflow/verify-rubric.md` (canonical change list mapped to the plan's
  rows and Deliverable paths) — model-discipline grade, no mechanical check.

## Classification (used by the plan boundary step)

Classify every change unit as exactly one of:

- `conforms` — no boundary or ownership issue.
- `intentional-deviation` — a boundary is crossed on purpose; the rationale is stated inline.
- `unresolved-conflict` — a violation, ownership ambiguity, or unstated crossing.

Only `unresolved-conflict` is P0 and escalates to the user. When every unit conforms, the plan
body carries exactly one line: `Boundary: conforms`. Do not expand this into a section with
nothing to report.

## Incorrect / Correct

```python
# Incorrect — training reads the warehouse directly; no snapshot exists to record
df = con.execute("select * from tlc.yellow_trips where pickup_date >= '2023-01-01'").df()

# Correct — training reads the extraction output; the snapshot name is the recorded key
df = pd.read_parquet("experiments/2026-09-24-trip-duration/data/yellow_trips_20230201.parquet")
```

## See Also

- `common/naming.md` — the naming these locations and artifacts follow.
- `model/leakage.md` — the leakage checks the feature/training boundary protects.
- `data/warehouse-access.md` — the two sanctioned routes and which one may write.
