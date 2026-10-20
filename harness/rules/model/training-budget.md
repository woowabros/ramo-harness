---
description: Training budget discipline — early stopping declares its improvement tolerance, wall-clock is derived from a measured per-iteration cost, the first fit leaves a loss curve, and search and confirmation carry separate budgets
paths:
  - "**/train*.py"
  - "**/*model*.py"
  - "experiments/**"
  - "notebooks/**"
---

# Training Budget

A budget line that states a ceiling and nothing else is not a budget: it is a ceiling, and the
run will spend it. This file is what `.claude/rules/workflow/01-plan.md` §4 requires beside the
ceiling, and what `.claude/rules/workflow/plan-rubric.md` `model.budget` scores.

## Why this file exists (illustrative values)

A plan wrote `n_estimators <= 3000, early stopping 100` and read as safe: the ceiling is an
upper bound, early stopping decides the real number. It does not, because LightGBM's
`early_stopping(stopping_rounds=N)` defaults its improvement tolerance `min_delta` to `0.0`.
On a validation set of a few hundred thousand rows a 1e-6 improvement is always available, the
patience counter resets forever, and the ceiling becomes the effective value.

Every fit in that experiment landed within a few trees of the 3,000 ceiling, across every
objective and seed. At a few minutes per fit, the grid spent hours on pure training.

Re-scoring the same validation set at increasing `num_iteration` on the trained model shows the
shape (illustrative values):

| Trees | valid MAE | vs 3000 | fit cost |
|---|---|---|---|
| 100 | 4.07 | +1.8% | ~8s |
| 250 | 4.03 | +0.8% | ~20s |
| 500 | 4.02 | +0.5% | ~40s |
| 1000 | 4.01 | +0.3% | ~80s |
| 2000 | 4.00 | +0.1% | ~170s |
| 3000 | 4.00 | — | ~250s |

500 trees cost about half a percent of the metric for one sixth of the time, and the last 500
trees bought almost nothing for about 40 seconds. The model was not slow — under 100ms per tree
over a few million rows is normal — it built six times more trees than the result needed.

## HARD Rules

- **[HARD] A plan that declares early stopping states its improvement tolerance beside the
  ceiling. A stopping rule with no stated tolerance is a declaration that the ceiling is the
  budget, and the plan says so in those words rather than implying otherwise.**
  WHY: the case above. The default tolerance is zero in a widely used boosting library, so
  the natural reading of a stopping rule ("it will stop early") is false by default and nothing
  in the plan or the rules said so. Writing the tolerance also forces the author to decide what
  counts as an improvement worth paying for, which is the decision the budget is about.
  Enforced at review time by `.claude/rules/workflow/plan-rubric.md` `model.budget` (FAIL when
  early stopping is declared with no tolerance) — model-discipline grade for the number chosen.

- **[HARD] The expected wall-clock of a `model-training` row is derived as expected iterations
  times a measured per-iteration cost, and the plan shows both factors.**
  WHY: a per-row total states what the author hopes, and the two factors state what the author
  measured. Only the factored form survives contact with a surprise: when that experiment ran
  long, the total said nothing while the factors would have said immediately that the iteration
  count, not the per-iteration cost, was the problem. The per-iteration cost comes from the
  smoke fit `.claude/rules/data/dataset-materialization.md` already requires before a full run,
  so the number is in hand before the plan is written. Enforced by
  `.claude/rules/workflow/01-plan.md` §4 and scored by `plan-rubric.md` `model.budget` —
  model-discipline grade, no mechanical check.

- **[HARD] The first fit of an experiment writes its loss-versus-iteration curve to a committed
  artifact.**
  WHY: the table above was produced *after* the experiment, by reloading the model and rescoring
  at successive `num_iteration` values. Everything it settled — that the ceiling was six times
  too high, and that the tail failure was structural rather than a budget shortfall — was
  available from the first fit at no extra cost. Recording it there turns a post-hoc
  investigation into a glance. Committed matters: an uncommitted curve cannot be cited as
  evidence later (`.claude/rules/common/sot-authoring.md` SOT-1). Enforced by
  `.claude/rules/workflow/verify-rubric.md` `budget.declared` when the curve is a declared
  deliverable — model-discipline grade, no mechanical check.

## Search budget and confirmation budget are separate

A grid search ranks configurations; a confirmation run produces the artifact. They do not need
the same budget, and giving them the same one spends the confirmation budget once per grid cell.

| Stage | Ceiling | Tolerance | What it has to be good enough for |
|---|---|---|---|
| Search | low, enough to separate configurations | loose | ordering the candidates correctly |
| Confirmation | the real ceiling | tight | the number that goes in the report |

Refit only the winner at the confirmation budget. This is not always available: when the ranking
itself inverts between budgets, say so and run the grid at the full budget with the cost stated.
The inversion is a finding worth recording, not a reason to skip the split silently.

## What this does not govern

Hyperparameter *values* (`.claude/rules/model/model-family-selection.md` and the plan's §4
search range) and evaluation slices (`.claude/rules/model/eval-metric-slice.md`). This file is
about how much compute a declared configuration is allowed to consume and how that number is
arrived at.

A budget overrun is also not automatically a defect. `ramo-run` flags a measured wall-clock
past twice the plan's expectation, and the honest response is sometimes to record the new
per-iteration cost and move on.

## See Also

- `.claude/rules/workflow/01-plan.md` — §4, where the budget is declared.
- `.claude/rules/workflow/plan-rubric.md` — `model.budget`, which scores it.
- `.claude/rules/model/eval-metric-slice.md` — what the trained model must then report.
