---
title: Error Diagnosis Template
impact: HIGH
tags: template, diagnosis, analysis, error-analysis, next-experiment
---

## Error Diagnosis Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

Diagnoses live in `docs/analysis/` and are the durable form of the error analysis: where the
model was wrong, why, and what to try next. The volatile working record is `.ramo/diagnoses/`.

This template exists because of a gap observed during testing. A model card's answer to "what
should the next experiment do" was one line listing three options with no evidence behind any of
them, while the material for a real answer was already in hand: every slice cell negative, an
advantage on sparse zones, a label-selection bias with the same sign across every borough and
hour band, and a small shortfall. The synthesis was missing, not the data. The numbers in the
example below are illustrative.

**Incorrect (a verdict with no decomposition and no ranked next step):**

```markdown
---
title: Trip duration model diagnosis
---

MAE 4.7 vs target 4.5. Model underperforms. Consider adding features or trying another model.
```

**Correct (full template):**

```markdown
---
type: Error Diagnosis
title: 운행시간 모델 v1 오차 진단
description: 슬라이스별 오차 분해와 다음 실험 후보 순위
category: analysis
status: stable
created: 2026-08-26
updated: 2026-08-26
tags: trip-duration, error-analysis, slice
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-26T09:00:00Z }
relates-to: experiments/2026-08-24-trip-duration/reports/metrics.md
depends-on: docs/model/trip-duration-baseline.md
---

# 운행시간 모델 v1 오차 진단

## 목표 대비 결과

| 항목 | 값 |
|---|---|
| 주지표 | MAE 4.7분 |
| 목표 | 4.5분 (베이스라인 5.0분 대비 10% 개선) |
| 달성 | 6% 개선 (부족분 0.2분) |

## 슬라이스 오차 분해

| 슬라이스 | n | MAE | 전체 대비 | 편향(mean d) |
|---|---|---|---|---|
| 16~19시 | 175,000 | 5.9 | +26% | -1.6 |
| 공항 트립 (JFK/LGA/EWR) | 70,000 | 7.5 | +60% | -2.1 |
| Brooklyn | 10,000 | 5.6 | +19% | -1.2 |
| 희소 zone | 1,500 | 4.2 | -11% | -0.4 |

- 20셀(borough 5 × 시간대 4) 전량이 음의 편향임. 모델이 체계적으로 과소예측하며 슬라이스 하나의 문제가 아님
- 희소 zone 에서 모델이 베이스라인 대비 10% 우위이므로 일반화는 되고 있음

## 원인 가설

| # | 가설 | 근거 | 강도 | 반증 조건 |
|---|---|---|---|---|
| H1 | 라벨 선택 편향: 학습 표본에서만 180분 초과 트립을 걸러 학습 라벨이 평가 라벨보다 짧게 치우침 | 평가 라벨 평균이 학습 라벨보다 약 2분 길고, 그 차이가 5 borough·4 시간대 전부 같은 부호 | 높음 | 걸러진 트립을 학습에 되돌려도 음의 편향이 그대로면 기각 |
| H2 | 피크 시간대 혼잡 정보 부재 | 16~19시 MAE 가 +26%, 시간대·요일 혼잡 피처 없음 | 중간 | 혼잡 피처 추가 후 그 슬라이스 개선 없으면 기각 |

가설마다 **반증 조건**을 적음. 반증할 방법이 없는 가설은 가설이 아니라 서술임.

## 다음 실험 후보 (순위)

| # | 후보 | 표적 슬라이스 | 기대 효과 | 비용 | 근거 |
|---|---|---|---|---|---|
| 1 | 라벨 필터 재검토 (H1) | 전체 | 부족분 0.2분을 넘길 유일한 후보 | 재추출 필요, 1~2일 | 20셀 전량 음의 편향이 단일 원인을 가리킴 |
| 2 | 시간대·요일 혼잡 피처 추가 (H2) | 16~19시, 공항 트립 | 해당 슬라이스 10~15% | 재추출 불필요, 1일 | 그 슬라이스만 +20% 이상 |
| 3 | 모델 계열 교체 | 전체 | 불명 | 1일 | 근거 없음 (현 오차는 계열보다 라벨·피처에서 옴) |

순위는 기대 효과가 아니라 **부족분을 닫을 가능성**으로 정함. 3번을 목록에 남긴 이유는
기각 근거를 남기기 위함이며, 근거 없는 후보를 상위에 두지 않음.

## 확인 필요 사항

- 180분 초과 트립이 실제 장거리 운행인지 미터 미종료 같은 기록 오류인지 가를 컬럼을 아직 못 찾음

## 다음 플랜으로 넘기는 것

`parent`: 이 실험의 플랜 파일명 / `change`: 후보 1(라벨 필터 재검토) /
`objective`: MAE, 부모값 4.7
```

Required sections: 목표 대비 결과, 슬라이스 오차 분해, 원인 가설, 다음 실험 후보, 확인 필요
사항, 다음 플랜으로 넘기는 것.

- **Every hypothesis carries a falsification condition.** A hypothesis nothing can refute is a
  description wearing a hypothesis's clothes, and it will survive every future cycle unchanged.
- **Candidates are ranked by their chance of closing the gap**, not by expected effect size. A
  candidate with no evidence stays in the table with its reason, so the next cycle does not
  re-propose it.
- Aggregate-only reporting never passes here either
  (`.claude/rules/model/eval-metric-slice.md`): the decomposition is the document.
