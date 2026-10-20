# Plan skeleton (`.ramo/plans/YYYY-MM-DD-slug.md`)

Master copy for @ramo-plan-writer. §0-§5 are fixed and keep these numbers and this order; §6-§8
are adaptive and the headings below are one workable grouping, not a contract. The normative spec
is `.claude/rules/workflow/01-plan.md` and the scoring pair is
`.claude/rules/workflow/plan-rubric.md`; on any disagreement those two win.

Body prose follows `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`); paths, symbols, commands, agent
names, and `Skill()` calls stay English. The Korean example cells below are illustrative.

Four em-dashes survive in the example block on purpose and they are the only ones: `N/A — reason`
is the literal string `.claude/rules/workflow/01-plan.md` §8 prescribes for a documentation or
rollback skip, and a bare `—` in the Dependencies column is the frozen table's own marker for
"no dependencies" (`.claude/rules/workflow/01a-execution-structure.md`). Both are contract
values, not prose, so they are not the em-dash a Korean deliverable avoids.

**Five lines before anything else.** Open the plan with a five-line summary: what is predicted,
off which data, with which change from the parent, what decides success, and what could
invalidate it. A reader who stops after five lines should still know whether to keep reading.

---

````markdown
---
type: plan
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
ticket: PROJ-123              # optional tracker key, or null when there is none
parent: null                  # or the previous plan's filename
change: null                  # the one atomic difference from the parent
objective: null               # metric name + the parent's value on it
generated: {by: ramo-plan-writer/claude, at: YYYY-MM-DDTHH:MM:SS+09:00}
---

# Plan: {구체적 성과}

{다섯 줄 요약}

## 0. 목적과 문제

**비즈니스 목적.** {누가 결과를 쓰고 어떤 결정을 바꾸며 지금은 무엇이 문제인가. 한 단락}

**예측 대상과 앵커.** {무엇을 예측하나} / 앵커: {이 시점 이후 값은 모델이 못 봄}

**타깃 분포** (표본: {윈도우·파티션·행수})

| 지표 | 값 |
|---|---|
| p50 | |
| p95 | |
| p99 | |
| 결측률 | |
| 꼬리 (상위 1% 대 평균) | |

**베이스라인.** {이겨야 하는 수치} (출처: {어디서 나온 값인가})

**목표 메트릭과 판정 조건.** {메트릭 이름} 이 {어떤 슬라이스에서 어떤 값}일 때 성공임

## 1. 선결 결정 (구현 전 확정, 재논의 대상 아님)

| ID | 결정 | 근거 | 확정 범위 |
|----|------|------|-----------|
| D1 | {사실로 진술한 결정} | {증거 또는 사용자 답} | {어느 변경 단위를 묶나} |
| D2 | {분할 경계 결정} | {증거} | U2 |
| D3 | {모델 계열 결정} | {증거} | U2 |

**범위 밖.** {드리프트가 그럴듯한 인접 작업의 경계}

**가정.** | 가정 | VERIFIED / UNVERIFIED | 근거 |

## 2. 데이터

| 테이블 | 파티션 범위 | 실측 행수 | 확인 경로 |
|---|---|---|---|

| 컬럼 | 출처 테이블 | 의미 |
|---|---|---|

**스냅샷.** {무엇을 고정하나} / 재획득: {나중에 어떻게 다시 얻나}

| 추출 행 | 기대 행수 범위 | 산출 grain | 비용 상한 |
|---|---|---|---|

## 3. 피처

**모델 계열.** {계열} (§4 D-row 참조)

| 피처 | 가설 | 변환 | 이 계열에 필요? | 결측률 | 처리 | 값 종류 |
|---|---|---|---|---|---|---|

**계열별 변환 순회** (`.claude/rules/model/feature-engineering.md` 의 계열 행)

| 변환 | 필요 여부 | 사유 |
|---|---|---|

**파생 유형 순회**

| 유형 | 후보 | 없으면 사유 |
|---|---|---|

**제외** | 컬럼 | 사유 |

**누수 검사.** {시간·타깃·그룹 각각 무엇을 확인하나}

## 4. 모델

**계열.** {계열} / **구조.** 단일 | 다단({단계 수})

| 단계 | 목표 | 다음 단계로 넘기는 것 |
|---|---|---|

**손실과 선택 절차.** {objective} / {승자를 무엇으로 고르나}

| 하이퍼파라미터 | 탐색 범위 | 선택 방법 | 최종값 기록 위치 |
|---|---|---|---|

**최단순 여부.** {parent: null 이면 계열의 가장 단순한 구성인가, 아니면 그렇지 않은 이유}

**예상 벽시계.** {학습 행마다 몇 분} (기계가 읽는 사본은 §5 validity 의 `wall_minutes` 하나)

**분할과 시드.** 분할 경계: {} / seed: {}

## 5. 평가

| 메트릭 | 슬라이스 | 판정 조건 |
|---|---|---|

**불확실성 보고.** {부트스트랩 구간 | 폴드 분산 | 시드 반복} 또는 `N/A — {사유}`

**validity 선언** (`model-training` 행이 있을 때만, `.claude/rules/workflow/01b-acceptance-contract.md`)

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

## 6. 변경 단위

### U1. {성과}

- **성과.** {바꿀 관측 가능한 동작}
- **현재 증거.** `file:line-range` / `file::symbol` + 필요할 때 최소 발췌
- **구현 형태.** {만들·고칠·지울 파일과 심볼, 제어·데이터 흐름, 경계 동작}
- **검증.** {검사 파일, 명명한 케이스, 명령, 현재 RED 간격}
- **재현성 의도.** task_type: {model-training | data-extraction | ... | code-change}
- **Binding decisions:** D1
- **Checks:** `uv run pytest tests/test_trip_extract.py`

### U2. {성과}

- **구현 형태.** {학습·평가 스크립트, 예측 파일과 피처 목록 파일 경로}
- **Binding decisions:** D2, D3
- **Checks:** `uv run pytest tests/test_trip_train.py`

## 7. 실행 구조와 검증

# Execution Structure

## Phase 1: {이름}

| # | Task | Domain | Type | Dependencies | Deliverable |
|---|------|--------|------|--------------|-------------|
| 1 [CP] | U1 {구체적 파일·심볼 조각} | data | data-extraction | — | `sql/trip_extract.sql` |

Gate: {통과를 뜻하는 관측 가능한 출력}

## Phase 2: {이름}

| # | Task | Domain | Type | Dependencies | Deliverable |
|---|------|--------|------|--------------|-------------|
| 2 | U2 {구체적 파일·심볼 조각} | model | model-training | 1 | `experiments/2026-09-24-trip-duration/train.py`, `experiments/2026-09-24-trip-duration/features.txt`, `experiments/2026-09-24-trip-duration/artifacts/predictions.parquet` |

Gate: {통과를 뜻하는 관측 가능한 출력}

**검증 명령.** | 명령 | 통과를 뜻하는 출력 | 자동 / 수동 |

**수용 기준** (배포·인계로 끝나는 계획만) | # | 기준 | 측정 방법 | 등급 |

## 8. 리스크와 확인 필요 사항

| 리스크 | 완화 |
|---|---|

**확인 필요 사항.** {사용자 확인이 필요한 미해결 고영향 가정}

**Documentation.** {진부해지는 정확한 docs/ 경로} 또는 `N/A — {사유}`

**Rollback.** {되돌리는 방법} 또는 `N/A — no deployment boundary`
````

---

## What the fixed top half buys

| Section | The question it answers | Rubric dimension |
|---|---|---|
| §0 | what are we predicting and why | 1 Problem and Objective |
| §1 | what is already decided and closed | 1 Problem and Objective |
| §2 | off which data, and what the extraction should produce | 2 Data and Tables |
| §3 | which features, in what state, with which transforms | 3 Feature Design |
| §4 | which model, in what structure, at what cost | 4 Model Design |
| §5 | what decides success, and how noise is separated from signal | 8 Verification and Reproducibility |

## Sections to omit rather than pad

- An empty §5 uncertainty line. Write `N/A — {사유}` or the method, never a blank cell.
- A §6 unit that restates §0-§5. Cite the section number instead.
- A risk table of generic risks. `plan-rubric.md` `risk.concrete` scores padding as a FAIL.
- `## 수용 기준` on a plan that ships nothing.
- A `validity` block on a plan with no `model-training` row (the parser rejects it).
- A `Checks:` line that cannot fail, or one that predicts a value. A check states how the unit
  is exercised (`exit 0` is the pass); what the values turn out to be is never written in advance.
