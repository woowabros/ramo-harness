# ramo-harness

데이터 사이언스 작업을 위한 Claude Code 하네스. Claude Code 안에서 8단계 파이프라인(과 그 앞의
선택 단계 0 research)을 도메인 서브에이전트, 강제된 출력 형식, 재현성 게이트로 반복 가능하게
만듦.

프롬프트 모음이 아니라 **강제 기구가 붙은 구성**임. 훅이 서브에이전트의 출력 형식과 재현성
증거(seed, split 경계, 데이터 스냅샷, 피처 명세)를 검사해 누락되면 막고, 데이터는 읽기 전용
어댑터로만 읽게 하고, 설치기가 시드 결손 시 조용히 넘어가지 않고 실패함.

## 8단계 파이프라인

```text
(0 research) → 1 interview → 2 eda → 3 plan → 4 run → 5 verify → 6 diagnose → 7 doc → 8 mr
  자료조사(선택)    문제정의    데이터탐색  계획확정   구현     독립검증    에러분석    지식승격   코드리뷰
```

| # | 명령 | 하는 일 | 산출물 |
|---|---|---|---|
| 0 | `/ramo:research` | (선택) 코드·논문·기술 블로그를 웹에서 모아 사람이 고르고, 주제별로 짧게 정리 | `docs/research/<주제>/README.md` (커밋 대상) |
| 1 | `/ramo:interview` | 문제를 6차원으로 질문해 확정 | `.ramo/interviews/` |
| 2 | `/ramo:eda` | 후보 테이블 해소, 타깃과의 관계 측정, 피처 후보와 누수 후보 분리 | `.ramo/eda/` |
| 3 | `/ramo:plan` | 계획 작성 후 좌석별 병렬 리뷰와 개선 루프 | `.ramo/plans/` |
| 4 | `/ramo:run` | 실행표의 태스크를 도메인 에이전트에 위임해 구현 | 코드, 데이터셋, 모델 |
| 5 | `/ramo:verify` | 바뀐 파일을 독립 팀이 검증하고 결함을 고침 | 검증 보고 |
| 6 | `/ramo:diagnose` | 오차를 슬라이스로 분해하고 다음 실험 후보를 순위화 | `.ramo/diagnoses/` |
| 7 | `/ramo:doc` | 오래 쓸 지식을 문서로 승격 | `docs/`, `wiki/` |
| 8 | `/ramo:mr` | 사이클의 코드로 PR/MR 생성 (verify PASS 필요) | GitHub PR 또는 GitLab MR |

각 단계는 사람의 확인(배턴)을 거쳐 다음으로 넘어감. 자동 연쇄가 아니고, 한 단계가 끝나면
다음에 무엇을 치면 되는지가 화면에 나옴.

### 단계별 설명

**0. research 자료 조사 (선택).** 새 모델을 맡았을 때 "이 코드는 어떻게 생겼고, 남들은 어떻게
하는가" 를 먼저 정리하는 단계임. 조사 질문을 2~4개로 정한 뒤 받은 코드 경로나 링크, 논문,
기술 블로그에서 **본문을 읽지 않고 후보만** 모으고, 사람이 읽을 목록과 주제 나누기를 고름.
깊게 볼 대상(코드베이스, 논문 하나)은 `대상 분석` 주제, 비교할 외부 사례는 `사례 비교` 주제로
폴더가 따로 생김. `@ramo-research-reader` 가 읽고 보고하면 메인 세션이 주제마다 README 하나를
씀. 여기 담긴 수치는 남의 데이터에서 잰 것이므로 interview 와 plan 은 이를 **배경 근거**로만
읽고 우리 데이터의 측정을 대신하지 않음. 기본 채널은 웹뿐이고, 팀의 내부 위키나 코드 검색을
붙이려면 `harness/skills/ramo-research/rules/source-discovery.md` 에 채널을 추가하면 됨.

**1. interview 문제 정의.** 목표·제약·데이터·평가·일정·이해관계자 6차원으로 최대 12개를
물음. 아는 것만 답하면 되고 모르는 항목은 "모름" 으로 넘어감. 이 단계의 산출물이 이후 모든
단계가 참조하는 문제 진술이 됨.

**2. eda 데이터 탐색.** DS 사이클에만 있는 단계임. 후보 테이블을 데이터 접근 어댑터로 실제로
조회해 해소하고, 제한된 표본에서 각 후보 컬럼과 타깃의 관계를 측정함. 핵심은 **피처 후보와
누수 후보를 나누는 것**임. 예측 시점(앵커) 이후에 채워지는 컬럼은 상관이 높게 나오지만 쓰면
안 되므로, 이 자리에서 갈라 놓지 않으면 계획이 누수를 피처로 착각함.

**3. plan 계획 확정.** 탐색 결과와 인터뷰를 근거로 실험 계획을 쓰고, 판단 좌석 여러 기가
**서로의 출력을 보지 않고** 병렬로 검토함. 좌석마다 보는 것과 보지 않는 것이 정해져 있어
(사전 부검, 횡단 감사, 데이터 설계, 모델 설계) 같은 지적이 중복되지 않음. 합의는 메인
세션이 하고, 지적이 P0 면 개선 라운드를 돌림. 계획서는 데이터·피처·모델을 각각 절로
확정하므로 run 은 새로 판단하지 않음.

**4. run 구현.** 계획서의 실행표를 파싱해 태스크 트래커를 만들고, 각 행을 그 도메인의 구현
에이전트에 한 번씩 위임함. 쿼리 행은 사람에게 묻지 않고 기계 검사 3종(표본 행수가 기대 범위
안, 전부 null 인 컬럼 없음, 쿼리 비용 추정이 상한 아래)으로 판정함. 계획이 기대치를 선언하지
않았으면 통과가 아니라 멈춤임. 서브에이전트가 재현성 증거를 빠뜨리면 훅이 막음.

**5. verify 독립 검증.** 구현한 주체가 아닌 팀이 `git diff` 로 확정한 변경 목록을 읽음.
결정적 검사(테스트, 린트, 파일 크기)를 돌리고, 각 행이 계획대로 만들어졌는지와 실험이
타당한지를 판정하고, 재현성 필드를 감사함. 결함은 Fix 라운드로 되돌려 고치며 라운드 예산이 있음.

**6. diagnose 에러 분석.** DS 사이클에만 있는 두 번째 단계임. 총합 지표 하나로는 무엇을
고쳐야 할지 알 수 없으므로, 오차를 선언된 슬라이스별로 분해하고 원인 가설마다 **반증
조건**을 붙임. 그리고 다음 실험 후보를 "격차를 닫을 확률" 로 순위화함. 이 산출물이 다음
회차 계획의 반복축이 되므로, 사이클이 실제로 돌게 만드는 자리가 여기임.

**7. doc 지식 승격.** 실험 폴더에 남으면 사라지는 결론을 문서로 올림. 카테고리 구조와
템플릿(데이터셋, 모델카드, EDA, 진단, 아키텍처, 피처, 실험 원장 등)이 정해져 있음.
교훈과 제약은 위키 발행 트랜잭션(초안 → 검증 → 의미 리뷰 → 커밋)을 통과해야 올라감.

**8. mr 코드 리뷰 요청.** verify PASS 를 사전 조건으로 GitHub PR 또는 GitLab MR 을 생성함.
PR/MR 은 **코드를 리뷰하는 자리이고 실험 결과를 승인하는 자리가 아님.** 실험 판정은 verify 와
diagnose 가 이미 했고, 본문은 그 결과가 어디 있는지를 가리킴. 원격 저장소가 없으면 이 단계는
건너뛰고 7단계까지만 돌려도 됨.

## 설치

### 1. 하네스 설치 (사람당 1회)

```bash
git clone https://github.com/woowabros/ramo-harness.git
cd ramo-harness && ./install.sh
ramo version
```

`install.sh` 가 시드 페이로드를 `~/.local/share/ramo/<version>/` 에, CLI 를
`~/.local/bin/ramo` 로 설치하고, 클론한 원격 주소를 `~/.local/share/ramo/source` 에 기록함.
이후 `ramo update` 가 그 주소에서 새 버전을 받음. `~/.local/bin` 이 `PATH` 에 없다는 경고가
뜨면 셸 설정에 추가한 뒤 새 셸에서 `ramo version` 을 다시 확인할 것.

설치 위치는 환경변수로 바꿀 수 있음. 이미 다른 ramo 설치본이 있는 기기에서 따로 시험해 볼 때
유용함.

| 변수 | 기본값 | 용도 |
|---|---|---|
| `RAMO_INSTALL_ROOT` | `~/.local/share/ramo` | 페이로드 설치 위치 |
| `RAMO_BIN_DIR` | `~/.local/bin` | `ramo` CLI 위치 |
| `RAMO_HOME` | `$RAMO_INSTALL_ROOT/current` | CLI 가 읽을 설치본 |
| `RAMO_DIST_REMOTE` | 클론한 원격 | `ramo update` 가 새 버전을 받을 저장소 |

### 2. 작업할 저장소에 적용

```bash
cd <작업할 저장소>
ramo init          # 별칭 ramo install
```

`ramo init` 은 먼저 배포 저장소에 더 새 버전이 있는지 확인하고, 있으면 설치 여부를 물은 뒤
받아서 설치함. 그다음 preflight 를 통과하면 그 저장소에 `.claude/`(에이전트·스킬·룰·훅·어댑터)와
`.ramo/`(작업 상태)를 심음.

새로 만든 폴더처럼 git 저장소가 아닌 곳이면 `ramo init` 이 `git init` 을 대신 실행함. 홈
디렉터리와 `/` 에서는 초기화하지 않고 멈춤. git 을 요구하는 이유는 세 가지임.

- 심을 위치를 `git rev-parse --show-toplevel` 로 정함. 워크트리를 쓸 때 메인 체크아웃이 아니라
  지금 작업 중인 워크트리에 심기 위함
- `/ramo:verify` 가 검증 대상을 `git diff --name-only` 로 확정함. 자기보고를 믿지 않음
- `/ramo:doc` 의 위키 발행이 커밋된 파일만 근거로 인용함

### 3. 데이터 연결 (data 단계를 쓸 때 필수)

eda·plan·run·verify 는 데이터를 **데이터 접근 어댑터** `.claude/scripts/ramo-data.py` 로만 읽음.
에이전트는 아래 명령만 쓰고, 어댑터는 읽기 문장 하나가 아니면 거부함(종료 코드 3).

```bash
python3 .claude/scripts/ramo-data.py ping                      # 설정 확인과 테이블별 행 수
python3 .claude/scripts/ramo-data.py search trip               # 테이블·컬럼 찾기
python3 .claude/scripts/ramo-data.py schema tlc.yellow_trips   # 컬럼과 타입
python3 .claude/scripts/ramo-data.py partitions tlc.yellow_trips
python3 .claude/scripts/ramo-data.py explain --sql "SELECT count(*) FROM tlc.yellow_trips"
python3 .claude/scripts/ramo-data.py query --sql "SELECT * FROM tlc.taxi_zones" --limit 20
```

동봉된 구현은 DuckDB 로 로컬 parquet·CSV·JSON 파일을 읽음. 준비는 두 가지임.

1. DuckDB 설치: `pip install duckdb` (또는 `uv pip install duckdb`). 에이전트는 PATH 의
   `python3` 로 어댑터를 부르므로, Claude Code 를 띄우는 셸에서 `python3 -c "import duckdb"` 가
   성공해야 함(가상환경을 쓰면 활성화한 셸에서 Claude Code 를 띄울 것)
2. 프로젝트 루트에 `ramo-data.json` 작성 (git 에 커밋해 팀이 공유)

```json
{
  "engine": "duckdb",
  "data_dir": "data",
  "database": "project.duckdb",
  "workspace_schema": "workspace",
  "tables": {
    "tlc.yellow_trips": {
      "path": "data/yellow_tripdata_2023-01.parquet",
      "derive": {"pickup_date": "CAST(tpep_pickup_datetime AS DATE)"},
      "partition_key": "pickup_date",
      "description": "NYC yellow taxi trips, January 2023, one row per trip"
    },
    "tlc.taxi_zones": {
      "path": "data/taxi_zone_lookup.csv",
      "description": "TLC taxi zone lookup (LocationID to Borough and Zone)"
    }
  }
}
```

위 예시는 NYC TLC 공개 데이터(옐로 택시 운행 기록은 Parquet, 지역표는 CSV)를 `data/` 에
받아 둔 경우임. 데이터셋을 만드는 빌드 스크립트는 `database` 파일의 `workspace` 스키마에만
씀. 다른 엔진(Trino 등)을 쓰는 팀은 같은 명령과 종료 코드를 그 엔진 위에 구현하면 됨. 설정과
엔진별 안내는 `harness/rules/data/warehouse-access.md`, `harness/rules/data/engines/` 에 있음.

`ramo init` 은 이 어댑터 명령 하나만 프로젝트 권한 허용 목록에 넣음. 백그라운드 서브에이전트가
권한 확인 창 때문에 멈춘 것처럼 보이는 일을 막기 위함임.

### 4. 첫 사이클

Claude Code 를 그 저장소에서 띄우고 `/ramo:interview` 로 시작할 것. 처음 맡은 문제라 관련
연구부터 모으고 싶으면 `/ramo:research <주제>` 로 시작하고, 끝에 안내되는 대로
`/ramo:interview docs/research/<주제>/README.md` 로 넘어가면 됨. NYC Taxi 운행시간 예측을 예로
단계를 손으로 따라가는 안내는 `docs/getting-started.md` 임.

## 하단 표시줄 (statusline)

`ramo init` 이 `statusLine` 도 심음. 세션 중 4줄이 하단에 뜸.

```
ramo 0.5.0 | 📁 taxi-trip-duration | ▶ 2026-09-24-trip-duration (active)
███░░░░░░░ 37% | $3.42 | 1h30m
5H 42% | 7D 18%
⚡ Opus [HIGH]
```

컨텍스트는 채워질수록 색이 짙어져 빨강으로 감. 1열의 `▶` 는 `.ramo/plans/` 의 `status: active`
계획이므로 지금 어느 실험을 돌리는 중인지가 항상 보임.

**이미 `statusLine` 을 쓰고 있으면 ramo 가 덮지 않음.** 그대로 두고 한 줄 안내만 함. 바꿔 보려면
`~/.claude/settings.json` 또는 저장소의 `.claude/settings.json` 에서
`.claude/statusline-ramo.py` 를 가리키게 하면 됨. `NO_COLOR` 를 설정하면 색 없이 그림.

## 설치 전 확인할 것

**개인 에이전트가 하네스 에이전트를 가릴 수 있음.** `~/.claude/agents/` 아래 같은 이름의
개인 자산이 있으면 Claude Code 의 에이전트 로더가 그쪽을 먼저 찾아 하네스 에이전트가 실행되지
않을 수 있음. `ls ~/.claude/agents/` 로 확인하고 겹치는 이름이 있으면 비활성화할 것(`.disabled`
확장자로 이름 변경 등). 하네스 에이전트는 전량 `ramo-` 프리픽스를 가지므로 겹칠 가능성은
낮음. 같은 이유로 `/ramo:*` 이름을 쓰는 다른 플러그인이 켜져 있으면 꺼 둘 것.

## 요구 사항

- git (작업 트리가 아니면 `ramo init` 이 `git init` 함. bare repo 는 대상 아님)
- python3 3.9 이상 (훅 핸들러는 stdlib 만 씀)
- Claude Code 최신 버전
- (data 단계 사용 시) `duckdb` 파이썬 패키지와 프로젝트 루트의 `ramo-data.json`
- (research 단계 사용 시) 웹 접근(`WebSearch`·`WebFetch`)
- (mr 단계 사용 시) `gh` 또는 `glab` 인증, 그리고 `.claude/schema/harness.json` 의 `vcs.provider`
  (`github` 기본, `gitlab` 가능). 티켓 링크를 쓰려면 `tracker.url_template`

`ramo init` 의 preflight 가 이 항목을 검사하고 미충족 항목을 구체적인 사유와 함께 나열함.

## 갱신과 제거

```bash
cd <작업 저장소>
ramo update --dry-run          # 새 버전이 있는지, 무엇이 바뀔지 먼저 보기 (아무것도 쓰지 않음)
ramo update                    # 새 버전 받기 + 이 저장소 .claude/ 갱신
ramo verify                    # 시드 자산이 온전한지 확인
```

`ramo update` 는 배포 저장소의 최신 `vX.Y.Z` 태그를 확인하고, 설치본과 다르면 그 사이
`CHANGELOG.md` 절 제목을 보여 주며 설치 여부를 `[y/N]` 으로 물음. 확인하면 새 버전을 설치하고
새 CLI 로 이 저장소를 갱신함. 옵션은 아래와 같음.

| 옵션 | 용도 |
|---|---|
| `--version X.Y.Z` | 최신 대신 그 버전을 설치함. 되돌리기나 단계적 업그레이드에 씀 |
| `--yes` | 묻지 않고 설치함. 비대화형 실행에서는 이 옵션이 없으면 버전을 바꾸지 않고 멈춤 |
| `--no-fetch` | 배포 저장소에 접속하지 않고 설치본으로만 갱신함 |

네트워크 문제로 배포 저장소에 닿지 못하면 경고를 출력하고 설치본으로 계속함. 다른 저장소는
각각 그 저장소에서 `ramo update` 를 실행해야 갱신됨.

`ramo update` 는 파일별로 소유권을 판정해 **사람이 고친 파일은 덮지 않고 보고만 함.**
업그레이드 전에 `CHANGELOG.md` 의 파괴적 변경 절을 읽을 것. `ramo update` 는 삭제된 자산을
지우지 않으므로 손으로 지워야 하는 항목이 그 절에 적혀 있음.

제거는 `ramo uninstall` 이며 하네스가 심은 파일만 지움. 사람이 고친 사본과 `.ramo/` 작업
상태는 남김.

## 알려진 제약

- 위키 스키마의 필수 섹션 이름과 리서치 문서 라벨은 한국어로 고정돼 있음.
  `RAMO_DOCUMENTATION_LANGUAGE=en` 으로 바꾸면 위키 발행 검증에서 섹션 이름이 맞지 않을 수 있음
- 동봉된 어댑터는 DuckDB 하나뿐임. 다른 엔진은 `harness/rules/data/engines/` 의 계약대로 직접 구현해야 함

## 더 읽을 것

| 무엇 | 어디 |
|---|---|
| 첫 사이클 걸어보기 (NYC Taxi) | `docs/getting-started.md` |
| 파이프라인과 HARD 규칙 | `harness/CLAUDE.md` |
| 규칙 전문 (진입점) | `harness/rules/INDEX.md` |
| 데이터 접근 계약 | `harness/rules/data/warehouse-access.md` |
| 버전별 변경과 파괴적 변경 | `CHANGELOG.md` |

## 지원 범위

코드 공유 목적의 저장소임. 이슈와 PR 은 받지만 응대는 best-effort 이며 응답 의무는 없음.
문의는 GitHub 이슈로만 받음.

## 라이선스

MIT. `LICENSE` 참고.
