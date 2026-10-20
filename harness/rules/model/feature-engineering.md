---
description: Feature work as a task, not only as a hazard — which transforms each model family needs, the derivation types to consider, and the rule that an all-exclusions feature verdict is a defect
paths:
  - "**/feature*.py"
  - "**/train*.py"
  - "**/model*.py"
  - "experiments/**"
  - "notebooks/**"
---

# Feature Engineering

The rest of this rule library mentions feature transforms only to forbid them: fit on train
only, never import a fitted scaler across the boundary. Nothing said to *do* the work. The
observed consequence was an experiment that judged several columns out of scope, added zero
derived features, and reported a negative result — with nobody having asked for more features.
An agent that is never told a thing is a job will treat it as a hazard to avoid.

This file is the other half. `model/leakage.md` stays the checklist; this is the task.

## Which transforms the model actually needs

Applying an unnecessary transform is a defect too, not free insurance: it costs code, it costs a
fitted object to carry to serving, and it hides what the model is really using.

| Family | Needs | Does not need |
|---|---|---|
| Tree ensembles (LightGBM, XGBoost, RF) | native categorical handling or an ordinal map; monotonic constraints where domain says so | scaling, one-hot for high-cardinality categories, normality transforms |
| Linear / GLM | one-hot, scaling, monotone transforms of skewed inputs, explicit interaction terms | native categorical handling |
| Neural | scaling, embeddings for high-cardinality categories | tree-style splits |

State the family first, then the transform list follows from it. A plan that one-hot encodes for
a gradient-boosted tree has not thought about the model.

## The feature table carries the column's state

A hypothesis and a transform describe what you intend to do with a column. They do not say
whether the column can carry it. Three measured values decide that, and they belong in the table
next to the hypothesis rather than in prose somewhere else.

| 피처 | 가설 | 변환 | 이 계열에 필요? | 결측률 | 처리 | 값 종류 |
|---|---|---|---|---|---|---|
| `{column}` | {why it should predict} | {transform or `없음`} | {필요·불필요} | {measured %} | {drop row / impute with what / native null} | {cardinality, or range} |

- **결측률** is measured on the same sample the eda stage used, not estimated. A column at 40%
  null is a different feature from the same column at 4%.
- **처리** follows from that rate and the family: tree ensembles take nulls natively, a linear
  model needs a decision, and a rate high enough to bias the population is a `D`-row question,
  not a table cell.
- **값 종류** is cardinality for a categorical column and range for a continuous one. It is what
  says whether an encoding is even possible: a 40,000-level categorical cannot be one-hot
  encoded, and that fact has to be visible before the transform column claims it will be.

## The transform walk

Once the family is fixed, walk that family's Needs and Does not need lists one row at a time.

| 변환 | 필요 여부 | 사유 |
|---|---|---|
| {transform from the family's row} | 필요 / 불필요 | {why, in one line} |

## Derivation types to consider

Walk the list; for each, either name a candidate or say why the data cannot support one. The
point is that the list was walked, not that every row produces a feature.

| Type | Example shape | Watch for |
|---|---|---|
| Ratio | two observed quantities divided | denominators that can be zero or near-zero |
| Interaction | product or conjunction of two columns | one of the pair being post-anchor |
| Lag / recency | value at a previous event, time since last event | the window reaching past the anchor |
| Aggregate | count, mean, or median over a past window at some grain | the window's end boundary; the grain's minimum sample |
| Missingness indicator | "this was null" as its own column | nullness that encodes the outcome |

Two hazards run across all five and both have produced real defects.

- **Circularity**: a derivation whose input is another model's output. It predicts the other
  model, not the outcome, and it moves whenever that model is retrained.
- **Leakage**: any window, join, or fitted statistic that sees data unavailable at the
  prediction anchor. `model/leakage.md` is the checklist.

## HARD Rules

- **[HARD] A feature verdict made entirely of exclusions is a defect, and the plan says what
  was tried instead.**
  Deciding what not to use is half the work; a plan whose feature section contains only
  removals has not done the other half. Scored by `plan-rubric.md` `feat.table` and
  `feat.derivation`, and at verification time by `verify-rubric.md` `fid.no-substitution`.
  WHY: this is the observed failure, not a hypothetical. Only exclusions, zero additions, a
  negative result, and no record that adding any was considered. Model-discipline grade at
  authoring time; the rubric items are the review-time seat.
- **[HARD] Declare the model family before the transform list, and justify any transform the
  family does not need.**
  WHY: the transform list is derived from the family. Without the family stated, a reviewer
  cannot tell a deliberate choice from a copied notebook cell. Enforced at review time by
  `plan-rubric.md` `feat.table` — model-discipline grade.
- **[HARD] Every feature row carries its measured null rate, the handling that rate implies, and
  its value kinds.**
  WHY: an observed plan carried a long feature list with a hypothesis and a transform each and
  no state column, so no seat could tell a usable column from an unusable one, and every review
  seat raised nothing about the feature space because nothing in the format asked them to. An estimated rate does not satisfy this: the number has to come off the sample the eda
  stage measured. Scored by `plan-rubric.md` `feat.state` — model-discipline grade, no mechanical
  check (no gate can tell a measured percentage from an invented one).
- **[HARD] After the family is fixed, walk that family's transform list one row at a time and
  record needed or not needed with the reason.**
  WHY: the family's row above says which transforms it needs, and the failure mode is silence —
  a plan that lists two transforms it happens to have thought of and never says whether the other
  four were considered. A walk makes the omissions visible as rows; prose makes them invisible.
  The walk is also what catches the reverse defect, an unnecessary transform applied as insurance.
  Scored by `plan-rubric.md` `feat.transform-walk` — model-discipline grade.
- **[HARD] Every declared transform exists in the code, and every fitted one is fitted on train
  only.**
  WHY: a feature table in a plan that the code does not implement is worse than no table, since
  review reads the table and believes it. Enforced by `verify-rubric.md` `fid.no-substitution`
  (the transform list) and `leak.fit-on-train` (train-only fits) reading the changed feature code — model-discipline grade, no mechanical check.

## Where a derived value is computed

Both layers legitimately derive values, and the boundary is one question:
`common/architectural-boundaries.md` (Where a Derived Value Belongs). Heavy aggregation in SQL
is normal; a fitted transform in SQL is leakage.

## See Also

- `model/leakage.md` — the checklist every derivation above must clear.
- `model/eval-metric-slice.md` — how a feature's effect gets reported.
- `common/architectural-boundaries.md` — which layer computes what.
