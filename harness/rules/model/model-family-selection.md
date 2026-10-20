---
description: Default model family per problem case, the one-line record required when a default applies, and the single AskUserQuestion required when the plan deviates from it.
paths:
  - ".ramo/plans/*.md"
---

# Model Family Selection

The model family is a decision, and in the observed cycle nobody made it out loud. LightGBM
appeared in the plan's experiment-constants table as a value, was described hundreds of lines
later as "current evidence: 모델 계열은 LightGBM", and the user first saw it in a run briefing
for a row that also declared the feature set frozen. The interview had explicitly deferred the
choice to the plan; the plan received it as a fact.

Nothing was wrong with the choice. What was missing was the seat. This file is that seat: a
default per problem case so the common path costs nothing, and one question when the case is
not covered.

## Where the decision happens

`.claude/skills/ramo-plan/SKILL.md` Step 1b, immediately after exploration and before the plan
is written. That position is deliberate: exploration is where the evidence for the choice first
exists, and writing is where it would otherwise harden into a constant.

## Default table

Read down the Case column and stop at the first row that matches.

| Case | Default family | Alternative worth naming | Why this default |
|---|---|---|---|
| Tabular, supervised — any target shape (binary, multiclass, continuous) | Gradient-boosted trees, LightGBM by default | XGBoost when the team already runs it in production; CatBoost when categoricals dominate and are very high-cardinality | Handles categorical splits and missing values without preprocessing, trains fast enough to iterate several times a day, and gives per-feature importance the error analysis stage can read. One row covers every target shape because the target changes the loss, not the family |
| Time series, one target over time, multiple series or exogenous columns | The same trees, on lag and rolling features, as one global model across series | A neural forecaster (TFT, PatchTST, N-HiTS class) when there are many series, a long multi-step horizon, and rich covariates; a pretrained time-series foundation model (Chronos, TimesFM, Moirai class) for a zero-shot baseline when there is little history to train on | Warehouse data usually arrives as many series with exogenous columns, which is where a global tree model beats per-series fitting. Validation MUST split on time (`.claude/rules/model/leakage.md`) |
| Ranking or prioritisation, where the label is a relative order | LightGBM with a ranking objective | A classifier's score, sorted, when the order is only a by-product | The metric being optimised is the order itself, not a per-item value |
| Unstructured input — text, image, or an event sequence whose order carries signal | Fine-tune a pretrained encoder for that modality (for Korean text, a Korean-pretrained transformer encoder) | Frozen embeddings fed into the tabular model above, when labels are few or the embedding is one feature among many tabular ones | Pretraining is the part the team cannot reproduce from its own data volume. The frozen-embedding alternative is the cheaper half of the same idea and is often enough |
| Anything else | **no default** | — | Deviation path below |

"Anything else" is a real answer: censored or survival targets, causal effect estimation,
uplift, anomaly detection with no labels, and any target the team has not modelled before.

- **The table names families, never a loss, an objective, or a configuration.** Which objective
  a regression uses, how a ranking loss is parameterised, which checkpoint a fine-tune starts
  from, and every hyperparameter are a `model-training` row's business and belong to whoever
  runs that row. The seat this file creates is "was the family chosen or inherited", nothing
  finer.
- **Deep learning on tabular data is not a default and does not become one by being available.**
  On warehouse-shaped tabular data, boosted trees remain the standard to beat. Reach for a
  network on tabular input only for a reason that names itself: input with genuine sequence
  structure that aggregate features destroy, or an embedding that has to be shared across
  tasks. That reason is a deviation, so it takes the question below.
- A row's Alternative column is not a second default. It is the option to put in front of the
  user if the deviation path fires for a different reason.
- Model names in this table age faster than the cases do. A named alternative is a **class**,
  not a pinned choice: the case is what the row asserts, and the example is how it was best
  served when the row was written.
- **Adding or changing a row is a decision with evidence, not an edit.** A default is a claim
  about what works on this team's data; change it when an experiment says so, and say which one.

## When the default applies

- **[HARD] Record one line in the plan's §1 settled-decisions table, naming the case that
  matched:** `D{n} | 모델 계열: LightGBM (기본값 적용: 정형 지도학습 + 연속형 타깃) | ...`
  WHY: the line is what makes a wrong match visible. Without it the agent's judgement that the
  default fits is invisible, and an unstated match cannot be questioned — which is exactly the
  state the observed cycle was in, where the family read as a constant. One line costs nothing
  on the common path and is the only thing standing between "considered and confirmed" and
  "never asked". Enforced by `.claude/rules/workflow/01-plan.md` §1 and scored by
  `plan-rubric.md` `model.family`.
- No question is asked. The default path is silent by design; a confirmation prompt on the
  common case is the cost this table exists to avoid.

## When the plan deviates

- **[HARD] Ask exactly one `AskUserQuestion`, at Step 1b, before the plan is written.**
  Offer two or three real candidates with each one's cost, and name the recommended one with
  its reason. The form is governed by
  `.claude/skills/ramo-explain/rules/decision-block.md` — in particular, never invent a second
  option to fill the shape.
  WHY: the deviation is a judgement, so unlike a raw-SQL deviation it leaves no file for a hook
  to inspect; there is nothing for `post_write.py` to catch. Making it a question turns
  `AskUserQuestion` itself into the mechanism, which is why this rule can claim an enforcement
  grade at all. Enforced by `.claude/skills/ramo-plan/SKILL.md` Step 1b — model-discipline
  grade, with the user's answer as the durable trace.
- Record the answer as a `D`-row like any other settled decision, with the user as its basis.
- A deviation the user declines to decide does not become the agent's choice: the plan carries
  it as an unresolved assumption in §8 and says which change units it blocks.

## Recording the structure

The family is not the design. Choosing boosted trees leaves open whether one model predicts the
target or two stages predict a decomposition of it, and that second question changes the feature
set, the evaluation, and what a slice result means.

- **[HARD] The plan's §4 states the structure in the same place it states the family: `단일` on
  one line, or every stage with its own objective and how the stages connect.**
  WHY: the observed cycle's plan named the family in its model section and carried the two-stage
  decision as a user answer in a `D`-row hundreds of lines away, so no reviewer ever saw the
  family and the structure together and the structure was never reviewed as a design. Enforced by
  `.claude/rules/workflow/01-plan.md` §4 and scored by `plan-rubric.md` `model.architecture` —
  model-discipline grade, no mechanical check.
- **There is no default table for structure and there should not be one.** A default family is a
  claim about what works on warehouse-shaped tabular data, which generalizes; a default number of
  stages would be a claim about the target's decomposition, which does not. Single-stage is the
  thing to beat, and beating it is what the stage objectives have to argue.
- Multi-stage needs three lines, not a paragraph: what each stage predicts, what it hands the
  next one, and why the split beats predicting the target directly.

## What this rule is not

- Not a restriction on trying a second family inside one experiment. That is a change unit with
  its own row, and the comparison is the point.
- Not a gate on running a hyperparameter search. The plan does declare the search range, the
  selection method, and where the final values land (`.claude/rules/workflow/01-plan.md` §4,
  scored by `plan-rubric.md` `model.hyperparameters`), but which values win is the training
  row's business.
- Not a substitute for the feature table (`.claude/rules/model/feature-engineering.md`): the
  family decides which transforms are needed, so the family line goes above the feature table,
  not inside it.

## Incorrect / Correct

```text
# Incorrect — the family arrives as a constant, so nobody decided it
| 실험 상수 | 값 |
| 모델 | LightGBM, objective=l1, seed=42 |

# Correct — default path, one line, the matched case named (the loss is not this line's business)
| D4 | 모델 계열: LightGBM (기본값 적용: 정형 지도학습). 손실 함수는 U5 훈련 행에서 결정 | 타깃 분포 실측(꼬리 상위 1% 가 평균의 6배) | U2, U5, U6 |

# Correct — deviation path, one question, answer recorded as the basis
| D4 | 모델 계열: DeepSurv (타깃이 우측 절단(censored)이라 기본 표 미적용) | 사용자 결정(2026-08-31), 대안 Cox PH 는 시변 공변량 미지원 | U3, U6 |
```

## See Also

- `.claude/rules/model/INDEX.md` — registry row for this file
- `.claude/rules/model/feature-engineering.md` — the transform map the chosen family implies
- `.claude/rules/model/leakage.md` — the time-split requirement the time-series row cites
- `.claude/skills/ramo-explain/rules/decision-block.md` — the question form the deviation uses
