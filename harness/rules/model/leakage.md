---
description: Leakage inspection contract — temporal boundary, target leakage, group leakage checklists for any training pipeline
paths:
  - "**/train*.py"
  - "**/split*.py"
  - "**/feature*.py"
  - "experiments/**"
  - "notebooks/**"
---

# Leakage Inspection

Model-domain agents (`ramo-model-design`, `ramo-model-implement`, `ramo-model-verify`) also cite this file by
path in their prompts.

## Principle

Leakage is the highest-frequency silent failure in DS work: the pipeline runs, the metric looks
great, and the result is fiction. Leakage checks are therefore a **declared checklist** the plan
must answer and verification must re-run — never an implicit "we were careful".

## HARD Rules

- **[HARD] The plan states the split boundary and the leakage checklist answers before
  training.**
  WHY: a split designed after feature computation inherits whatever leakage the features
  already baked in. Enforced by `plan-rubric.md` (ramo-plan-evaluator REJECT condition).
- **[HARD] `split_boundary` is recorded in the training envelope.**
  WHY: without the recorded boundary, no reviewer can re-check temporal soundness.
  Enforced by `subagent_stop.py::check_evidence` + run gate (model-training required key,
  `.claude/schema/harness.json`).
- **[HARD] ramo-model-verify re-checks the checklist independently; implement's own claim never
  substitutes.**
  WHY: the agent that built the features is structurally blind to its own leakage.
  Enforced by verify team composition: the implement agent is never seated on the
  verification team, and the `leak.*` items in `verify-rubric.md`, filled by
  @ramo-model-verify, require the checklist to be re-answered independently.

## Checklist

### Temporal boundary
- Every feature is computable strictly before the prediction time (no post-outcome fields).
- Aggregation windows end at or before the split boundary; no future rows leak into
  train-side aggregates.
- Label window and feature window do not overlap.

### Target leakage
- No feature is a proxy or descendant of the label (post-outcome status fields, columns
  populated by the outcome process).
- Encodings/statistics computed on the full dataset (target encoding, global means,
  normalization) are fit on train only.

### Group leakage
- Entities (vendor, trip, zone-day) do not appear on both sides of the split when the task
  requires entity-level generalization; state the grouping key of the split.
- Duplicate or near-duplicate rows are deduplicated before splitting.

## Incorrect / Correct

```python
# Incorrect — scaler fit on the full frame before the split (target-side statistics leak)
scaler.fit(df[features]); train, test = split(df)

# Correct — split first, fit on train only, record the boundary
train, test = temporal_split(df, boundary="2023-01-22")   # → envelope split_boundary
scaler.fit(train[features])
```
