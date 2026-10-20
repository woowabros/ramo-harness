# CHANGELOG

ramo-harness 의 릴리스 기록임. 형식은 append-only 이며 과거 항목은 수정하지 않음
(`.claude/rules/common/sot-authoring.md` SOT-3 의 CHANGELOG 면제 조항).

버전 표기는 `harness/VERSION` 이 정본이고, 소비 저장소에는 `.claude/hooks/ramo/.seed-info` 의
`version=` 줄로 기록됨.

## 0.5.0

공개판 첫 릴리스. 한 조직 안에서 여러 회차 실사용으로 다듬은 하네스를 특정 인프라 없이 쓸 수
있게 정리한 판임.

### 구성

- **8단계 파이프라인과 선택 단계 0.** research → interview → eda → plan → run → verify →
  diagnose → doc → mr. 단계 사이는 사람의 확인(배턴)으로 넘어감
- **서브에이전트 19종.** 탐색·설계·구현·검증 좌석이 도메인(data, model)별로 나뉘고, 판정 좌석은
  서로의 출력을 보지 않고 병렬로 검토함
- **강제 기구.** 훅이 서브에이전트 출력 형식(`<ramo>STATUS</ramo>` + result envelope)과 도메인별
  재현성 증거 키를 검사하고, SQL CLI 직접 실행과 workspace 밖 쓰기, verify PASS 없는 PR/MR 생성을 막음
- **행 검사 런타임.** `acceptance.py` 가 계획서의 실행 표·검사 명령·validity 블록을 파싱하고,
  run 과 verify 에서 행 증거를 보편 불변식과 재계산 digest 로 판정함
- **문서·위키 승격.** 카테고리 구조와 템플릿, 위키 발행 트랜잭션(초안 → 검증 → 의미 리뷰 → 커밋)

### 데이터 접근

- **데이터 접근 어댑터 `.claude/scripts/ramo-data.py`.** 모든 데이터 단계가 같은 명령
  (`ping`, `search`, `schema`, `partitions`, `explain`, `query`)으로 데이터를 읽음. 읽기 문장 하나가
  아니면 거부함(문장 검사 + DuckDB 샌드박스 이중 방어, 종료 코드 3)
- **DuckDB 기본 구현.** 프로젝트 루트 `ramo-data.json` 에 로컬 parquet·CSV·JSON 파일을 테이블로
  선언해 씀. 다른 엔진은 같은 명령 계약을 구현하면 됨(`harness/rules/data/engines/`)
- **쓰기는 빌드 스크립트로만.** 데이터셋 빌드는 workspace 스키마(기본 `workspace`, `ramo-data.json`
  으로 변경 가능)에만 씀

### 협업 도구

- **PR/MR 단계는 GitHub 와 GitLab 을 모두 지원함.** `.claude/schema/harness.json` 의 `vcs.provider`
  로 고르고, 티켓 링크는 선택(`tracker.url_template`)
- **리서치는 웹 채널만 기본 제공함.** 팀의 내부 지식 채널은 `source-discovery.md` 에 추가할 수 있음

### 예제

- 규칙과 템플릿의 예시는 NYC TLC 옐로 택시 공개 데이터의 운행시간 예측 시나리오로 통일함.
  `docs/getting-started.md` 가 같은 예제로 첫 사이클을 안내함

### 테스트

- `tests/test_ramo_data.py`: 어댑터의 읽기 명령과 쓰기 거부(다중 문장, CTE 뒤 DML, `COPY`, `ATTACH`,
  `INSTALL`, `PRAGMA`, 데이터 폴더 밖 파일 읽기 등)를 검증함. `python3 -m pytest tests/`
