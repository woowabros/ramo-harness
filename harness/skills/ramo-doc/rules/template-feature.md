---
title: Feature Definition Template
impact: HIGH
tags: template, feature, leakage, computation-window
---

## Feature Definition Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

Feature docs live in `docs/feature/` and record what each feature means, over what window it is
computed, what makes it safe with respect to the prediction anchor, and — the part a later
experiment most needs and least able to re-derive — **which candidate columns were excluded and
why**.

That exclusion table is why this template exists. The doc trigger for feature work fires even
when the verdict was to exclude (`.claude/rules/workflow/05-doc.md` trigger 2), because the next
experiment will otherwise re-propose every rejected column and re-do the work that rejected it.

**Incorrect (names without definitions, no window, no anchor):**

```markdown
---
title: Trip duration features
---

Features: passenger_count, service_zone, vendor. Standard stuff.
```

**Correct (full template):**

```markdown
---
type: Feature Definition
title: 운행시간 모델 피처 정의
description: 피처별 의미·계산 윈도·누수 경계와 제외 판정
category: feature
status: stable
created: 2026-08-24
updated: 2026-08-26
tags: trip-duration, feature, leakage
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-26T09:00:00Z }
relates-to: src/trip_duration/features.py
depends-on: docs/data/trips-snapshot.md, docs/analysis/trip-duration-eda.md
---

# 운행시간 모델 피처 정의

## 예측 앵커

승차 시각(`tpep_pickup_datetime`). 이 시점에 알려진 값만 피처가 될 수 있고, 아래 모든 윈도는
이 앵커를 기준으로 닫힘.

## 피처

| 피처 | 의미 | 계산 윈도 | 유도 유형 | 앵커 안전성 근거 |
|---|---|---|---|---|
| `zone_duration_median_28d` | 승차 zone 의 최근 28일 운행시간 중앙값 | 앵커 -28d ~ 앵커(배타) | 롤링 집계 | 윈도가 앵커 직전에 닫힘. 앵커 이후 트립 미포함 |
| `service_zone` | 승차 zone 의 서비스 구역 (Yellow Zone, Boro Zone, Airports) | 앵커 시점 스냅샷 | 조인 유도 | zone lookup 은 트립과 무관한 정적 테이블 |
| `hour_of_day` | 앵커의 시(현지 시각) | 앵커 시점 | 시간 파트 | 앵커 자체에서 계산 |

- 컬럼명은 `{entity}_{aggregation}_{window}` (`.claude/rules/common/naming.md`)
- 유도 유형은 `.claude/rules/model/feature-engineering.md` 의 분류를 씀. 전부 한 유형에
  몰려 있으면 나머지 유형을 검토하지 않았다는 신호임

## 적합 변환 (train 에서만 적합)

| 변환 | 대상 | 적합 범위 | 이유 |
|---|---|---|---|
| 목표 인코딩 | `PULocationID` | train 분할만 | 전체에 적합하면 valid/test 로 라벨 정보가 새어감 |

**추출(SQL)과 적합 변환(python)의 경계**: 라벨이나 train 분포를 봐야 만들어지는 값은 적합
변환이고 train 에서만 적합함 (`.claude/rules/common/architectural-boundaries.md`).

## 누수 경계 검사

| 검사 | 방법 | 결과 |
|---|---|---|
| 시간 경계 | 각 피처 윈도의 상한이 앵커 이전인지 SQL 로 확인 | 통과 (3/3) |
| 타깃 누수 | 타깃 파생 컬럼이 피처에 없는지 대조 | 통과 |
| 그룹 누수 | 같은 승차 zone 이 train/valid 양쪽에 있는지 | **있음 (의도적).** zone 단위 일반화가 목표가 아니므로 허용하고 여기 적음 |

## 제외 판정

| 후보 | 제외 사유 | 다시 볼 조건 |
|---|---|---|
| `trip_distance` | 하차 후 확정됨 (누수) | 없음. 구조적으로 불가 |
| `passenger_count` | 상관 0.03, 결측 2% | 결측이 개선되면 재검토 |
| `store_and_fwd_flag` | 표본 거의 전체에서 같은 값 | 미터 전송 방식이 바뀌면 |

**다시 볼 조건**을 적는 것이 이 표의 값어치임. 사유만 적으면 다음 사람이 같은 후보를 같은
근거로 다시 제안함.

## 확인 필요 사항

- `zone_duration_median_28d` 는 희소 zone(28일 동안 트립이 적은 zone)에서 결측이며, 현재 전역
  중앙값으로 대치함. 그 대치가 희소 zone 예측을 편향시키는지 측정 못 함
```

Required sections: 예측 앵커, 피처, 적합 변환, 누수 경계 검사, 제외 판정, 확인 필요 사항.

- The anchor section comes first: without it every window claim below is unfalsifiable.
- An exclusion table with reasons but no re-examination conditions is half a record.
- An intentional leakage (a group appearing on both sides of a split by design) is written down
  as intentional, with the reason. Silence there reads as an oversight to the next reviewer.
