---
description: Evaluation metric and slice discipline — declared slices are mandatory; a single aggregate number never passes
paths:
  - "**/eval*.py"
  - "**/train*.py"
  - "**/*model*.py"
  - "experiments/**"
  - "notebooks/**"
---

# Evaluation Metric and Slice Discipline

Model-domain agents (`ramo-model-design`, `ramo-model-implement`, `ramo-model-verify`) also cite this file by
path in their prompts — design-stage work has no matching file open.

## Principle

An aggregate metric hides exactly the failures that matter. Evaluation is designed **before**
training: the plan declares the metric set, the slice set, and the baseline; verification checks
against that declaration, not against whatever numbers the run happened to produce.

## HARD Rules

- **[HARD] The plan declares metrics, slices, and baseline before training starts.**
  WHY: metrics chosen after seeing results are selection bias in institutional form.
  Enforced by `plan-rubric.md` (reproducibility/evaluation dimension — ramo-plan-evaluator REJECT
  condition).
- **[HARD] Evaluation reports every declared slice; a missing slice is a FAIL, not a gap.**
  WHY: aggregate-only reporting is how a model that fails an entire region or segment ships.
  Enforced by the `eval.cells` item of `verify-rubric.md` — EV-P0 for a missing cell, so a
  missing slice fails verification whatever else passes.
- **[HARD] Compare against the declared baseline, not against zero.**
  WHY: "0.83 AUC" is uninterpretable without the baseline's number on the same split.
  Enforced by the `eval.baseline` item of `verify-rubric.md`.

## Slice Declaration Format

Declared in the plan's evaluation section; consumed by ramo-model-verify:

```markdown
| Slice | Definition | Why it can diverge |
|-------|------------|--------------------|
| borough | per pickup borough | density/traffic regimes differ |
| sparse_zone | pickup zones in the bottom trip-count bucket | cold-start behavior |
| daypart | peak / off-peak | congestion asymmetry |
```

Minimum: one business-critical categorical slice and one temporal slice. "No meaningful slice
exists" must be argued in the plan and approved in review — silence is not approval.

## Practices

- Report each metric per slice with sample counts; flag slices with n below a stated floor.
- Metric numbers cite their split and snapshot (`data_snapshot`, `split_boundary` from the
  envelope) so any number can be traced to the data it was computed on.
- Prefer a small declared metric set over a dashboard dump; every reported number needs an
  interpretation against baseline and expectation (`common/explanation-style.md` rule 5).
