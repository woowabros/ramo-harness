---
title: Model Card Template
impact: HIGH
tags: template, model-card, model, evaluation
---

## Model Card Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

Model cards live in `docs/model/` and are the durable record of what a model is for,
what it was trained on, how it was evaluated (including slices), and how to reproduce
it. The reproducibility section mirrors the harness envelope keys
(`seed` / `split_boundary` / `data_snapshot`) so a reader can go from card to rerun
without archaeology. Slice reporting follows
`.claude/rules/model/eval-metric-slice.md` — a single aggregate number is not an
evaluation. The numbers in the example below are illustrative.

**Incorrect (aggregate-only, no data provenance, no reproducibility):**

```markdown
---
title: Trip Duration Model
---

LightGBM model, MAE 4.6 minutes. Works well.
```

**Correct (full template):**

```markdown
---
type: Model Card
title: Trip Duration Model v2
category: model
status: stable
created: 2026-08-20
updated: 2026-08-21
tags: trip-duration, lightgbm, regression
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-21T04:12:00Z }
relates-to: src/trip_duration/train.py
depends-on: docs/data/trips-snapshot.md
stale_after: 2026-11-21
---

# Trip Duration Model v2

## Intended Use

What the model predicts, for whom, at what cadence — and explicit out-of-scope uses.

## 모델

| Item | Value |
|---|---|
| 계열 | LightGBM (gradient-boosted trees) |
| 구조 | 단일 |
| 입력 피처 수 | 19 |
| `feature_spec` | `sha256:3f9a…` (`artifacts/feature_spec.json`) |

| 하이퍼파라미터 | 탐색 범위 | 선택 방법 | 최종값 | 출처 파일 |
|---|---|---|---|---|
| `num_leaves` | 31, 63, 127 | valid MAE 최소 | 63 | `configs/v2.yaml` |
| `learning_rate` | 0.03, 0.05, 0.1 | 같음 | 0.05 | 같음 |
| `alpha` (quantile) | 0.75 ~ 0.95, 0.05 간격 | valid 판정 조건 만족 중 MAE 최소 | 0.85 | `artifacts/selection_seed42.json` |

| 학습 설정 | Value |
|---|---|
| 손실 | `regression_l1` |
| 조기 종료 | valid MAE, 50 rounds |
| 반복 수 | 1,000 상한, 최적 412 |
| 실측 벽시계 | 18분 (계획 예상 20분) |

## Training Data

| Item | Value |
|---|---|
| Dataset | [Yellow Trips Snapshot](../data/trips-snapshot.md) |
| Snapshot | `tlc.yellow_trips/month=2023-01` |
| Split | temporal, `split_boundary: 2023-01-22` (`adr/001-temporal-split-policy.md`) |
| Label | `trip_duration_min` = dropoff − pickup, in minutes |

## Evaluation

| Metric | Overall | sparse-zone slice | airport slice |
|--------|---------|-------------------|---------------|
| MAE (min) | 4.6 | 4.4 | 7.2 |
| P90 absolute error (min) | 10.5 | 10.0 | 16.0 |

| Item | Value |
|---|---|
| 베이스라인 | MAE 4.7 (직전 챔피언 v1) |
| 불확실성 보고 | 부트스트랩 95% 구간 1,000회 (seed 42), MAE 4.6 [4.55, 4.65] |

Baseline comparison and the required slices declared in the experiment plan. Source
artifact for every number (committed eval report path). **An aggregate with no interval is not
a result**: a difference that cannot be told from noise is not a difference
(`.claude/rules/workflow/plan-rubric.md` `eval.variance`).

## Reproducibility

| Key | Value |
|---|---|
| seed | 42 |
| split_boundary | 2023-01-22 |
| data_snapshot | `tlc.yellow_trips/month=2023-01` |
| training entry | `uv run python -m trip_duration.train --config configs/v2.yaml` |

## Limitations and Risks

Known failure modes, under-represented slices, drift sensitivity, and any leakage checks
performed (`.claude/rules/model/leakage.md`).

## Serving

Where and how the model is served, input contract, and rollback procedure — or
`N/A — offline experiment only`.

## 다음 시도 후보

| # | 후보 | 표적 슬라이스 | 기대 효과 | 근거 |
|---|---|---|---|---|
| 1 | 라벨 필터 재검토 | 전체 | 부족분 0.1분을 닫을 유일한 후보 | 20셀 전량 음의 편향 |
| 2 | 시간대·요일 혼잡 피처 추가 | 16~19시, 공항 트립 | 해당 슬라이스 10~15% | 그 슬라이스만 MAE +20% 이상 |

진단이 있으면 그 순위와 근거를 본문으로 옮겨 적음(`docs/analysis/` 의 진단 문서를
`depends-on` 으로 걸되, `.ramo/diagnoses/` 경로는 인용하지 않음 (gitignore 대상이므로
SOT-1 위반). 진단이 없으면 `N/A: 진단 미실시` 라고 적고, 옵션 나열로 대체하지 않음.

## 확인 필요 사항

측정하지 못한 것, 근거가 얕은 채로 남긴 판단.

## Changelog

| Date | Change | Breaking |
|------|--------|----------|
| 2026-08-21 | v2 promoted to champion | Yes |
| 2026-08-20 | Initial card | No |
```

Required sections, in this order: Intended Use, **모델**, Training Data, Evaluation,
Reproducibility, Limitations and Risks, Serving, **다음 시도 후보**, **확인 필요 사항**,
Changelog. `N/A — reason` for genuinely inapplicable sections, never silent omission.

- **`## 모델` is required and it comes second, before Training Data.** It carries the family,
  the structure (단일 or the stages), the hyperparameter table (search range, selection method,
  final value, source file), the training settings including the measured wall-clock, and the
  input feature count with its `feature_spec`.
  WHY: Mitchell et al.'s original opens with Model Details and an earlier version of this
  template dropped it, so it asked for everything about a model except the model. Observed
  consequence: a card produced in testing named its family nowhere in the body (it survived only
  in a frontmatter tag), carried `seed` and two values buried in a Limitations sentence as its
  entire hyperparameter record, and put its design under `## Reproducibility` three heading
  levels deep, past the middle of the document. Nothing was withheld deliberately; the card
  answered the questions it was asked.
  The hyperparameter table's four columns are the ones a reader needs to rerun or challenge the
  choice: a final value alone cannot be challenged, because nothing says what it beat.
  Model-discipline grade: the required-section list and the example block both carry the
  section and its four hyperparameter columns, and `ramo-doc-writer`'s section walk applies
  them; nothing mechanical checks a written card.

- **다음 시도 후보 is required, and a bare list of options does not satisfy it.** Observed
  during testing: a model card's answer to "what would make this better" was one line naming
  three options (add features / change family / revisit the success criterion) with no evidence
  behind any of them, while the material for a real answer was already in hand — every slice
  cell negative, a label bias with the same sign across every borough and hour band, a small
  shortfall against the target. The template's own source (Mitchell et al.) is about reproducibility and
  transparency, so iteration design is outside its scope; this section is the addition that
  makes the card useful to the next experiment rather than only to an auditor.

**Incorrect — the design sits under Reproducibility, three levels deep:**

```markdown
## Reproducibility

| Key | Value |
|---|---|
| seed | 42 |

### 설계
2단 구조임. 1단은 이진 분류기, 2단은 회귀 2종.
```

Problems: the one section a reader opens a model card for is at depth 3, past the middle of
the document, inside a section about something else. The family is not named anywhere in the
body, and `num_leaves` and `learning_rate` appear nowhere at all. Depth hid it and the required
section list never asked for it (`.claude/rules/common/doc-readability.md` R3).

**Correct:** `## 모델` at depth 2, second section, with the four-column hyperparameter table.

Reference: [Mitchell et al., Model Cards for Model Reporting (2019)](https://arxiv.org/abs/1810.03993)
