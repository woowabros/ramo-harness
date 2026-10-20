---
title: 처음 쓰는 사람을 위한 첫 사이클 안내
category: architecture
type: Runbook
status: stable
created: 2026-08-22
updated: 2026-10-15
date: 2026-10-15
summary: NYC Taxi 운행시간 예측을 예제로 선택 단계 0 research 와 interview→eda→plan→run→verify→diagnose→doc 7단계를 손으로 따라가는 문서. 8번 mr 은 원격 저장소가 있는 코드 사이클에서만 쓰므로 범위 밖임. data 태스크 1개와 model 태스크 1개로 된 최소 예제를 단계마다 보여줌. 설치는 README.md, 막힌 지점은 각 절의 "막히면" 항목을 볼 것
tags: guide, onboarding, getting-started, ramo-harness
relates-to: README.md
---

# 처음 쓰는 사람을 위한 첫 사이클 안내

`ramo init` 까지 끝냈다는 전제로 시작함(설치 자체는 `README.md`). 여기서는 공개 데이터인
NYC TLC 옐로 택시 운행 기록으로 과제 하나를 0번(선택)부터 7번까지 통과시켜 봄. data 태스크
1개(데이터셋 빌드)와 model 태스크 1개(훈련)를 포함한 최소 예제를 씀. 각 단계 절 끝의
"막히면" 이 그 단계에서 흔히 걸리는 지점과 확인 순서임.

**단계별 출력은 걸어보기용 예시 텍스트임.** 실제 값(지표 수치, 후보 수 등)은 실행할 때마다
달라짐. 형태와 순서를 보여주는 것이 목적임. 데이터 행 수와 상관처럼 "실측" 이라고 적은 값만
공개 파일에서 잰 값임.

## 사이클 지도

```text
(0 research) -> 1 interview -> 2 eda -> 3 plan -> 4 run -> 5 verify -> 6 diagnose -> 7 doc
  자료조사(선택)    질문        데이터탐색  계획서확정  구현     독립검증    에러분석     지식승격
```

0번은 선택 단계임. 처음 맡은 문제처럼 분야에서 이미 알려진 것을 먼저 모아야 할 때만 씀.

2번과 6번이 DS 사이클에만 있는 단계임. 2번은 후보 테이블에서 타깃과 관계있는 컬럼을
찾고, 6번은 틀린 곳을 슬라이스로 분해해 다음 실험 후보를 순위화함. 6번의 산출물이 다음
회차 계획의 반복축이 되므로, 사이클이 실제로 돌게 만드는 자리가 6번임.

각 단계는 사람의 확인(배턴)을 거쳐 다음으로 넘어감. 자동 연쇄가 아님. 한 단계가 끝나면
화면에 다음에 무엇을 치면 되는지가 나옴.

## 예제로 쓸 과제

> 승차 시점에 택시 운행시간(분)을 예측하고 싶다. 운행 기록에서 학습용 데이터셋을 만들고
> (data 태스크) 회귀 모델을 훈련한다(model 태스크).

## 준비. 데이터와 어댑터

데이터 단계는 데이터 접근 어댑터(`.claude/scripts/ramo-data.py`)로만 데이터를 읽음. 예제
데이터는 NYC TLC 공개 데이터 두 파일임. 운행 기록은 Parquet 으로만 배포되고 지역표는 CSV 임.

```bash
mkdir -p data
curl -L -o data/yellow_tripdata_2023-01.parquet \
  https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet   # 약 48MB
curl -L -o data/taxi_zone_lookup.csv \
  https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
pip install duckdb pandas pyarrow scikit-learn
```

데이터 이용 조건은 NYC TLC 의 공개 데이터 안내를 따를 것. `data/` 는 커밋하지 않는 것이
보통이므로 `.gitignore` 에 넣어 둠.

프로젝트 루트에 `ramo-data.json` 을 두고(예시는 `README.md` 의 "데이터 연결" 절과
`.claude/rules/data/engines/duckdb.md`) 연결을 확인함.

```
$ python3 .claude/scripts/ramo-data.py ping
engine: duckdb 1.5.6          # 설치된 DuckDB 버전에 따라 다름
config: /path/to/project/ramo-data.json
tlc.yellow_trips: 3066766 rows
tlc.taxi_zones: 265 rows
```

**막히면.** 종료 코드가 4 면 DuckDB 가 없는 것이고, 2 면 `ramo-data.json` 이 없거나 경로가
틀린 것임. 메시지가 고칠 곳을 알려 줌.

## 0. `/ramo:research` (선택)

받은 코드나 관련 논문·기술 블로그를 웹에서 모아 주제별로 짧게 정리함. 조사 질문을 먼저 정하고,
**본문을 읽기 전에** 후보 목록과 주제 나누기를 보여 주며 어느 것을 읽을지 사람이 고름.

```
> /ramo:research 택시 운행시간 예측 https://arxiv.org/abs/xxxx.xxxxx
[ramo-research] 무엇을 알고 싶나요? > 문제 정의 관행, 평가 지표·베이스라인, 공개 사례
[ramo-research] 후보 12건, 추천 7건 → 주제 2개: trip-duration-baselines(대상 분석) · external-travel-time-cases(사례 비교)
  > 추천대로 진행
[ramo-research] 예상 에이전트 4기 (ramo-research-reader)
  읽은 깊이: full 5 · partial 1 · failed 1 (PDF 만 공개)
[ramo-research] 문서: docs/research/trip-duration-baselines/README.md, docs/research/external-travel-time-cases/README.md
다음 단계: /ramo:interview docs/research/trip-duration-baselines/README.md
```

산출물은 주제마다 `docs/research/{주제}/README.md` 하나이고 커밋 대상임. 대상 분석 주제는
전체 아키텍처·피처와 타깃·학습 방법·주의사항, 사례 비교 주제는 사례 비교 표와 사례 요약을 담음.
모든 주장에는 위치(코드 경로, §·표·소제목)가 붙고, 수치는 지표 정의·데이터·비교 대상과 함께
옮겨짐. 소스별 상세 보고는 `.ramo/research/` 에만 남고 커밋하지 않음. 인터뷰는 이 문서를
배경으로 읽고 찾은 정의를 선택지로 내놓지만, 우리 문제의 정의는 여전히 사람이 정함.

**막히면.** PDF 로만 공개된 논문은 읽지 못해 `failed` 로 남을 수 있음. 보고서의 "직접 받아야
할 자료" 를 내려받아 `/ramo:research {주제} ~/Downloads/paper.pdf` 로 다시 실행하면 남은
소스부터 이어서 읽음. 받은 코드만 정리하고 싶으면 `/ramo:research {주제} {코드 경로}` 처럼
소스를 주면 질문과 탐색 없이 바로 읽고, 외부 사례까지 찾으려면 `--survey` 를 붙임.

## 1. `/ramo:interview`

문제를 명확히 하는 질문 6차원(목표·제약·데이터·평가·일정·이해관계자)을 최대 12개
받음. 아는 것만 답하면 됨. 모르는 항목은 "모름" 이라고 답해도 진행됨.

```
> /ramo:interview
[ramo-interview] 목표: 무엇을 예측/개선하려 하나요?
> 승차 시점에 운행시간(분) 예측 (회귀). 타깃은 하차 시각 - 승차 시각
[ramo-interview] 평가: 성공을 어떻게 판정하나요?
> test MAE 4.5분 이하, 공항 트립과 희소 zone 에서도 크게 나빠지지 않을 것
[ramo-interview] 데이터: 어떤 테이블을 쓰나요?
> tlc.yellow_trips, tlc.taxi_zones
...
```

산출물은 `.ramo/interviews/{날짜}-{슬러그}.md`. 끝나면 다음 단계(`/ramo:eda`)가 뜸. 이게
배턴임.

**막히면.** 질문에 "모름" 만 반복 답해도 인터뷰는 끝남. 다만 `/ramo:plan` 이 그 항목을
플레이스홀더로 만든 뒤 표시하니, 계획 단계에서 채워 넣을 각오를 할 것.

## 2. `/ramo:eda`

인터뷰가 지목한 후보 테이블에서 **타깃과 관계있는 컬럼**을 찾음. 어댑터의 `schema`·`partitions`
로 실물을 확인하고, 표본을 한 번 정한 뒤 그 표본에서 상관·결측·카디널리티를 잼.

```
[ramo-eda] 타깃: trip_duration_min (하차 - 승차, 분) / 예측 앵커: tpep_pickup_datetime
[ramo-eda] 표본: pickup_date 2023-01-01~01-31, 0~180분 운행 3,063,669행 (월 범위 밖 승차와 음수 운행시간 제외)
[ramo-eda] 타깃 분포: p50 11.5분 · p95 36.2분 · p99 56.1분
[ramo-eda] 스윕: ramo-data-explore 1기
  피처 후보: PULocationID·DOLocationID (zone 별 중앙값 차이 큼), 승차 시각의 시간대, passenger_count (corr 0.03, 결측 2.3%)
  누수 후보: fare_amount (corr 0.78) · trip_distance (corr 0.01) · total_amount · tip_amount (모두 하차 후 확정)
  기각: store_and_fwd_flag (타깃과 무관), VendorID (값 2개)
```

위 표본 행 수, 분위수, 상관은 공개 파일에서 잰 실측임.

**예측 앵커를 먼저 정하는 것이 이 단계의 핵심임.** 앵커가 없으면 어떤 컬럼이 누수인지
판정할 수 없음. 위 예에서 `fare_amount` 는 상관이 가장 강해 강도로 정렬하면 맨 위에 오지만
하차 후에 확정되는 값임. 반대로 `trip_distance` 는 이상치 몇 건 때문에 피어슨 상관이 0.01
밖에 안 나오지만(100마일 초과 88건을 빼면 0.8) 역시 하차 후 확정이라 누수임. 누수는 강도가 아니라 값이 알려지는 시점으로
판정하므로, 피처 후보와 누수 후보를 **분리된 표**로 넘김.

`.ramo/eda/{날짜}-{슬러그}.md` 로 저장되고, 다음 단계의 계획이 이 파일을 증거로 읽음.

**막히면.** 타깃이나 앵커가 애매하면 이 단계는 BLOCKED 로 멈춤. 모호한 타깃에 대한 상관은
증거처럼 보이지만 증거가 아니므로 인터뷰로 돌아가는 것이 맞음. 어댑터가 거부(종료 코드 3)하면
읽기 문장 하나가 아닌 것을 보낸 것이므로 쿼리를 확인할 것. 탐색이 필요 없는 과제(피처가 이미
정해졌거나 직전 진단이 다음 변경을 지목한 경우)는 이 단계를 건너뛰고 `/ramo:plan` 으로 바로 감.

## 3. `/ramo:plan`

인터뷰와 탐색 결과를 계획서로 구체화함. 코드 위치, 변경 형태, 실행 표(6열 동결 계약)까지
확정함. 예제라면 실행 표가 대략 이렇게 나옴(형태 예시, 실제 열 이름·값은 계획서가 채움).

```
| # | Task | Domain | Type | Dependencies | Deliverable |
|---|---|---|---|---|---|
| 1 | U1 학습용 운행 데이터셋 빌드 | data | dataset-build | - | workspace.trip_base:experiment |
| 2 | U2 운행시간 회귀 모델 훈련 | model | model-training | 1 | experiments/2026-09-24-trip-duration/artifacts/model_trip_duration_seed42.pkl |
```

각 행의 Task 칸은 변경 단위 하나(`U1`, `U2`)를 가리키고, 그 단위 절의 `Binding decisions:` 줄과
선택 줄 `Checks:`(exit 0 이 통과인 검사 명령)가 행의 결속 결정과 검사가 됨. 계획서는 무엇을
어떻게 잴지만 적고 결과값을 미리 적지 않음.

`[CP]` 로 표시된 행(핵심 판정이 걸린 행)이 있으면 **설계 브리핑**이 먼저 뜸. 예를 들어
"학습 표본에서만 180분 초과 운행을 거르면 평가 표본과 분포가 달라짐" 같은 판정을 사람이
확인하는 지점임. 병렬 리뷰(설계·데이터·모델 관점)를 거쳐 합의되면
`.ramo/plans/{날짜}-{슬러그}.md` 가 `status: active` 로 저장됨. 데이터 좌석은 어댑터의
`explain` 으로 쿼리 비용을 미리 확인함.

**막히면.** 리뷰가 여러 라운드 반복되면(개선 루프) 정상 동작임. 계획서 품질이 낮으면 몇
라운드가 걸림. 계속 막히면 인터뷰로 돌아가 목표/제약을 더 구체화할 것.

## 4. `/ramo:run`

계획서의 실행 표를 그대로 실행함. **태스크당 위임 1회**이고(data 행만 쿼리 게이트로
2회로 쪼개짐), run 은 설계하지 않음. 설계는 계획서 §1 선결 결정 표가 이미 끝낸 것이고,
그 표가 답하지 않는 설계 질문이 있는 행은 조용히 결정하지 않고 **가시적 BLOCKED** 로
계획 단계로 되돌림.

사람이 멈추는 자리는 닫힌 정지 집합으로 정해져 있음(`.claude/skills/ramo-run/rules/human-gates.md`).
대표적인 것은 `[CP]` 행의 **설계 브리핑**임. data 행의 쿼리는 사람 대신 기계 검사 3종(표본
행수가 기대 범위 안, 전부 null 인 컬럼 없음, `explain` 비용 추정이 상한 아래)으로 판정하고,
3/3 이 아니면 그때 멈춤.

```
[ramo-run] 프리플라이트: ramo-data.py ping OK, 인증 확인 -> 트래커 기록
[ramo-run] 태스크 1/2: 학습용 운행 데이터셋 빌드 (data)
  설계 브리핑 [CP] -> 확인 요청
  > 예
  phase 1 (쿼리 작성 + 어댑터 query --limit 로 표본 증명, 쓰기 없음)
  쿼리 게이트: 표본 행수 OK · 전부 null 컬럼 없음 · explain 비용 OK -> 3/3
  phase 2 (빌드 스크립트가 project.duckdb 의 workspace.trip_base 생성) -> 행 검사 -> 재현성 필드 기록
[ramo-run] 태스크 2/2: 운행시간 회귀 모델 훈련 (model)
  위임 1회 -> 행 검사 -> 재현성 필드 기록 (seed, split_boundary, data_snapshot, feature_spec)
```

각 태스크가 끝날 때마다 `evidence:` 에 그 도메인이 요구하는 재현성 키를 기록함. 빠지면
기계적으로 RETRY 됨(도메인별 필수 키는 `.claude/schema/harness.json` `domains.<name>.evidence`).
데이터셋을 쓰는 위치는 workspace 스키마로만 제한되고, 원천 테이블에 쓰려는 SQL 은 훅이 막음.

**막히면.** 쿼리 게이트가 3/3 이 아니면 어느 검사가 실패했는지 보고 계획서의 기대 범위나
쿼리를 고칠 것. envelope(재현성 필드) 누락으로 반복 RETRY 되면 해당 도메인 태스크의 `Type`
열이 맞는지(`data-extraction` vs `dataset-build` 등) 계획서를 확인할 것. "설계가 확정되지
않았다" 는 BLOCKED 가 나오면 계획서에 그 결정의 `D`-row 를 추가해야 함. run 에서 즉석으로
정하지 않는 것이 설계임.

## 5. `/ramo:verify`

verify 가 묻는 것은 두 가지임. 각 행이 계획대로 만들어졌는가(충실도), 실험이 측정으로서
타당한가(타당성). 결과가 좋은지는 `/ramo:diagnose` 가 봄.

먼저 좌석을 부르기 전에 결정적 게이트가 돔. run 이 남긴 행별 증거 기록
(`.ramo/todo/{계획}-evidence/row-{nn}.json`)과 트래커가 맞는지 보고, 산출물의 sha256 과
각 행 단위의 `Checks:` 명령을 다시 돌리며, 기록된 증거를 보편 불변식(예: `quality_checks` 가
전부 통과이고 0건이 아님)으로 다시 판정하고 `query_hash`·`feature_spec` 을 재계산함.
그다음 `ramo-critique` 가 행마다 충실도 항목을, `ramo-model-verify`·`ramo-data-verify` 가
타당성 점검표를, `ramo-audit` 가 안전 표면을 셀로 채움. 투표 없이 항목의 등급으로
티켓이 되고, P0 만 Fix 라운드를 엶. 고치는 것은 원래 구현한 implement 에이전트뿐임.

```
[ramo-verify] 게이트: G1 정합 OK · G2 산출물 3/3 · G3 수용 재검사 2/2 · G4 매핑 OK
[ramo-verify] 팀: ramo-critique, ramo-audit, ramo-data-verify, ramo-model-verify
  ramo-model-verify: eval.cells FAIL (기대 공항 트립 슬라이스, 실측 없음, 출처 reports/slices.csv)
[ramo-verify] EV-P0-001 → Fix 라운드 1/N: ramo-model-implement 가 slice 추가, 행 2 기록 갱신
[ramo-verify] 재검증: PASS
```

계획이 데이터와 모순되거나 누수가 계획 설계 자체에 있으면 Fix 없이 사람에게 물음(닫힌
정지 집합). 끝나면 판정(PASS / PASS (with notes) / FAIL)과 다음 단계가 뜸. PASS 면
`.ramo/context/verify-pass.json` 마커가 남고, 8번 mr 은 이 마커가 있어야 PR/MR 을 엶.

**막히면.** Fix 라운드가 상한에 닿아도 안 고쳐지면 계획 자체의 가정이 틀렸을 가능성이 큼.
`/ramo:plan` 으로 돌아가 그 가정을 다시 검토할 것.

## 6. `/ramo:diagnose`

검증을 통과했다는 것은 구현이 옳다는 뜻이고, 실험이 목표를 달성했는지는 아직 말하지
않음. 이 단계가 그 차이를 다룸. 계획이 **선언한 슬라이스**로 오차를 분해하고, 원인
가설마다 반증 조건을 붙이고, 다음 실험 후보를 순위화함.

```
[ramo-diagnose] 목표 대비: test MAE 4.7분 / 목표 4.5분, 부족분 0.2분
[ramo-diagnose] 슬라이스 분해: 공항 트립 9.8(+5.1), 희소 zone 7.2(+2.5), 맨해튼 평일 낮 3.9(-0.8) ...
  모든 셀의 편향 부호가 동일 → 슬라이스 하나의 문제가 아님
[ramo-diagnose] 가설 H1: 학습 표본에서만 180분 초과 운행을 걸러 긴 운행을 짧게 예측함
  반증 조건: 평가 표본에 같은 필터를 걸어 재계산해도 편향이 남으면 기각
[ramo-diagnose] 다음 실험 후보: ① 필터 기준 통일(권장) ② 공항 트립 전용 피처 보강
```

위 수치는 예시임.

**후보 순위는 기대 효과가 아니라 부족분을 닫을 가능성으로 정함.** 큰 효과를 내지만
부족분에 거의 기여하지 않는 슬라이스를 고치는 후보를 1번에 두면 회차를 낭비함.
근거 없는 후보도 표에 남기되 마지막에 두고 이유를 적음. 지우면 다음 회차가 같은 후보를
다시 제안함.

`.ramo/diagnoses/{날짜}-{슬러그}.md` 로 저장됨. 다음 회차에 `/ramo:plan` 을 이 파일로
호출하면 반복축(`parent`·`change`·`objective`)이 자동으로 채워지고, `change` 는 위 후보
중 사용자가 고른 것이 됨.

**막히면.** 평가 산출물이 없으면 BLOCKED 임. 평가하지 않은 실험의 진단은 창작이므로
`/ramo:run` 의 평가를 먼저 돌릴 것. model 태스크가 없는 계획(추출만 한 회차)은 이 단계를
건너뜀.

## 7. `/ramo:doc`

verify 를 통과한 변경 중 문서화 트리거(데이터셋·피처·모델·실험 결론 등 6종)를
평가하고, 승격 트리거(반복 가능한 실패 유형·해석이 필요했던 도메인 사실·기각된
접근 3종)도 함께 평가함. 예제라면 데이터셋 문서(`docs/data/`)와 모델 카드
(`docs/model/`)가 생기고, 실험이 부정 결과로 끝났다면 그 결론이 `docs/analysis/`
에 남음. 억지로 긍정으로 바꾸지 않는 것이 이 하네스의 강한 신호임.

```
## 문서화 완료
**만든/고친 문서:** docs/data/trips-snapshot.md, docs/model/trip-duration-card.md,
docs/analysis/trip-duration-diagnosis.md
**트리거 평가:** ... (6종 각각 발화/미발화)
**위키 승격:** 발화 1건, "하차 후 확정되는 금액·거리 컬럼은 상관과 무관하게 누수" 교훈
**결정 라우팅:** ...
다음 단계: 계획 status 를 done 으로
```

**막히면.** 카테고리를 못 정하겠으면(어느 `docs/` 폴더인지 애매하면) 그 자리에서
멈추고 물어봄. 임의로 새 폴더를 만들지 않음(`.claude/skills/ramo-doc/rules/foundation-category-structure.md`).

## 여기서부터

한 사이클을 완주했으면 계획서 `status` 가 `done` 이 됨. **같은 과제의 다음 회차**는
`/ramo:plan {진단 파일}` 로 시작함. 진단이 반복축을 채우므로 인터뷰부터 다시 하지 않음.
**새 과제**는 다시 `/ramo:interview` 부터, 낯선 문제라면 `/ramo:research` 부터 시작함. 원격
저장소가 있으면 `/ramo:mr` 로 PR/MR 을 열 수 있음(`.claude/schema/harness.json` 의
`vcs.provider`). 하네스 자체의 규칙이 궁금하면 프로젝트 루트 `CLAUDE.md` 의 ramo 블록과
`.claude/rules/INDEX.md` 부터 볼 것.
