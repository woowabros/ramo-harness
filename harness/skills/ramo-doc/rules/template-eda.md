---
title: EDA Findings Template
impact: HIGH
tags: template, eda, analysis, feature-candidate
---

## EDA Findings Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

EDA conclusions live in `docs/analysis/` and record what the data exploration established:
which columns relate to the target, how strongly, on what sample, and which strong columns are
leakage candidates rather than features. The volatile working record is `.ramo/eda/`; this is
the promoted version, so every number arrives with the sample that produced it and every path
is committed (`.claude/skills/ramo-doc/rules/quality-durable-evidence.md`).

The section this document exists for is **확인 필요 사항**. An exploration that answered
everything did not explore. The numbers in the example below are illustrative.

**Incorrect (a number with no denominator, and no leakage judgement):**

```markdown
---
title: Trip duration EDA
---

trip_duration_min correlates with RatecodeID (0.4). Also trip_distance is very strong (0.8),
use it.
```

**Correct (full template):**

```markdown
---
type: EDA Findings
title: 운행시간 피처 후보 탐색
description: 운행시간 타깃에 대한 후보 컬럼 상관·커버리지 측정과 누수 후보 판정
category: analysis
status: stable
created: 2026-08-20
updated: 2026-08-21
tags: trip-duration, feature-candidate, correlation
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-21T04:12:00Z }
relates-to: sql/trip_duration_profile.sql
depends-on: docs/data/trips-snapshot.md
---

# 운행시간 피처 후보 탐색

## 타깃과 예측 시점

측정 대상 타깃의 정의, 그리고 **예측 앵커**(무엇이 알려진 시점에 예측하는가). 앵커가
없으면 아래 누수 판정이 성립하지 않으므로 이 절이 먼저임.

## 표본 정의

| 항목 | 값 |
|---|---|
| 파티션 범위 | `pickup_date` 2023-01-01 ~ 01-31 |
| 행 수 | 3,062,468 (원본 3,066,766) |
| 제외 | 월 범위 밖 pickup 48, 음수·0 운행시간 1,121, 180분 초과 운행 3,048, 주행 거리 100마일 초과 88 (합계 0.2% 미만) |

아래 모든 수치는 이 표본에서 나옴. 표본이 다른 수치는 그 자리에 따로 적음.

## 피처 후보

| 컬럼 | 출처 테이블 | 측정 | 커버리지 | 근거 강도 | 판단 |
|---|---|---|---|---|---|
| `RatecodeID` | `tlc.yellow_trips` | 그룹 평균차 20분 (공항 정액 코드) | null 2% | 높음 | 채택 후보 |
| `service_zone` | `tlc.taxi_zones` | 그룹 평균차 6분 | null 0% | 중간 | 채택 후보 |
| `passenger_count` | `tlc.yellow_trips` | corr 0.03 | null 2% | 낮음 | 보류 (효과 작고 결측 있음) |

근거 강도는 측정치 크기가 아니라 **그 측정을 믿을 근거**임(표본 크기, 결측, 분포 안정성).

## 누수 후보 (강하지만 쓸 수 없음)

| 컬럼 | 측정 | 채워지는 시점 | 판정 |
|---|---|---|---|
| `trip_distance` | corr 0.8 | 하차 후 확정되는 주행 거리 = 예측 앵커 이후 | 누수. 피처 아님 |

**상관이 강한 것이 유용함의 근거가 아님.** 예측 앵커 이후에 알려지는 값과의 상관은 누수의
증상이며, 이 표가 그것을 분리하는 자리임 (`.claude/rules/model/leakage.md`).

## 기각

| 컬럼 | 사유 |
|---|---|
| `store_and_fwd_flag` | 표본 거의 전체에서 같은 값 |
| `VendorID` | 값이 두 개뿐이고 그룹 평균차가 표본 오차 수준 |

## 확인 필요 사항

- `service_zone` 의 구역 분류가 기간 중 바뀌었는지 확인 못 함. 바뀌었다면 그룹 평균차가
  분류 변경 효과와 섞임
- 1월 한 달만 측정함. 계절성 확인은 다음 탐색 회차

## 재획득

```sql
-- sql/trip_duration_profile.sql 전문 또는 커밋 경로
SELECT ...
```

측정을 다시 얻는 데 필요한 것: 위 쿼리, 표본 정의 표의 조건, 그리고 스냅샷
`tlc.yellow_trips/month=2023-01`.
```

Required sections: 타깃과 예측 시점, 표본 정의, 피처 후보, 누수 후보, 기각, 확인 필요 사항,
재획득. `N/A — reason` for a genuinely empty one (an exploration with no rejected column is
plausible; one with no 확인 필요 사항 usually means the section was skipped, not that nothing
is open).
