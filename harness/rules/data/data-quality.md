---
description: Standard data-quality check classes for an extracted dataset — counts, source reconciliation, label bounds, column set, point-in-time window, split separation, sample determinism, null rates, independent recomputation; plus what makes a check able to fail
paths:
  - "**/*.sql"
  - "**/extract*.py"
  - "**/*dataset*.py"
  - "**/check*.py"
  - "notebooks/**"
---

# Data Quality Checks

A dataset is not done when it exists; it is done when a named check says what it is. This file
is the standard list of check classes so a plan does not reinvent it per experiment, and so
`ramo-data-verify` has something to run rather than something to judge.

Declare the checks in the plan, by id, with the expected value. Report every one with its
measured value. "Checks pass" without the numbers is not a report
(`common/explanation-style.md` rule 5).

## The classes

Each row is a class, not a fixture. Instantiate the ones the dataset admits and say in the plan
why any is not applicable — an omitted class with no reason is the gap this list exists to close.

| Class | What it asserts | Reads |
|---|---|---|
| `rows` | Row count and every declared split's count match the plan's quota | the artifact |
| `population` | The artifact's population equals the source predicate's count | the source |
| `label-bounds` | Zero rows outside the declared label range | the artifact |
| `label-moments` | Label mean/median/spread equal the values pinned at snapshot time | the artifact |
| `column-set` | Feature columns are exactly the declared set; intersection with the forbidden list is empty | the artifact |
| `window` | Every aggregate's window ends at or before the prediction anchor (`model/leakage.md`) | source + artifact |
| `split-separation` | Split keys do not intersect at the split grain | the artifact |
| `sample-determinism` | Re-running the selection reproduces the same rowset hash | source + artifact |
| `null-rate` | Null share per column is within a threshold set from measurement, not from taste | the artifact |
| `recompute` | At least one derived column, recomputed independently, matches the artifact | source + artifact |

## HARD Rules

- **[HARD] A check whose expected value is a snapshot-pinned literal states the snapshot it was
  pinned to, and is re-measured when that snapshot changes.**
  WHY: source tables get rewritten. A pinned moment or count then fails against a dataset that
  has nothing wrong with it, and the failure looks like a defect in the work rather than in the
  expectation. Re-measuring is the fix; loosening the tolerance until it passes destroys the
  check. Enforced at review time by `.claude/rules/workflow/verify-rubric.md` `dq.checks` and stop S2 of `04-verify.md` — model-discipline
  grade, no mechanical check.
- **[HARD] Every check must be able to fail, and the plan says how that was established.**
  A positive control (a row or a column deliberately violating the assertion) or a mutation of
  the check's own recipe is the evidence. A check nobody has seen fail is indistinguishable from
  a check that cannot.
  WHY: this harness has already shipped a validator with no caller and a hook that fired zero
  times; both looked like coverage. Model-discipline grade.
- **[HARD] Split the suite by what it reads.** Checks that read only the artifact run without
  warehouse access; checks that reconcile against the source need it. Say which is which.
  WHY: a suite that needs the warehouse to answer anything cannot run while the warehouse is
  unreachable or unconfigured (`data/warehouse-access.md` Precondition), so the artifact-only
  half becomes unavailable for no reason. Model-discipline grade.
- **[HARD] A failing check is a `RETRY` with the measured value, never a relaxed threshold.**
  WHY: the only thing a widened tolerance proves is that someone widened it. Enforced by the
  scope guard in `.claude/rules/workflow/03-run.md` and at review time by
  `.claude/rules/workflow/verify-rubric.md` — model-discipline grade.

## Incorrect / Correct

```text
# Incorrect — a report that cannot be checked
"데이터 품질 검증 완료, 모든 체크 통과"

# Correct — class, expected, measured, and where it read from
"rows: 1,000,000 기대 / 1,000,000 실측 (artifact)
 population: 3,066,718 기대 / 3,066,718 실측 (source, snapshot pickup_date=2023-01-01..01-31)
 null-rate: 임계 3% 기대 / 최대 2.3% 실측 (artifact)"
```

## See Also

- `data/dataset-materialization.md` — building the artifact these checks read.
- `data/table-pitfalls.md` — the traps that make a plausible check pass on wrong data.
- `model/leakage.md` — the window and anchor rules the `window` class enforces.
