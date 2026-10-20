---
description: The two gates execution passes through — the [CP] design briefing and the unconditional query gate — with their print formats, the three machine checks that replaced the query gate's question, and the closed set of reasons a person is stopped at all. Cited by ramo-run Step 3.
---

# Execution Gates

Two gates, and only two. Both were added at the user's request after a cycle that built
correctly and explained nothing, and both keep their **print**. Neither asks a question any
more: the briefing prints and continues, and the query gate's question was replaced by three
machine checks. That reversal is a settled design decision, and this file states it in full.

`ramo-run` Step 3 cites this file. The step owns when each gate fires; this file owns what is
printed, what is checked, and the closed set of reasons a person is stopped at all.

## What still stops a person (closed set)

- **[HARD] Execution stops for a person only for a reason in this table. Nothing else.**

| Stop reason | Where it is detected | Outcome |
|---|---|---|
| A warehouse write aimed outside the workspace schema (`.claude/schema/harness.json` `data.workspace_schema`, default `workspace`) | phase 1 report, or `pre_bash.py` | `<ramo>BLOCKED</ramo>` |
| Estimated query cost above the plan's declared ceiling | machine check 3 below | RETRY once, then `<ramo>BLOCKED</ramo>` |
| A design question no `D`-row in the plan answers | Gate 1's briefing assembly | `<ramo>BLOCKED</ramo>` — the plan needs the decision |
| Machine-value retry budget exhausted (`.claude/schema/harness.json` `limits.run_implement_retry_max`) | the retry loop | `<ramo>BLOCKED</ramo>` |
| An unresolved precondition (missing state file, missing seeded asset, network absent) | Step 0 preflight | `<ramo>BLOCKED</ramo>` |

  WHY: the previous contract stopped a person on every data row regardless of what the row did,
  so a plan with five data rows spent five waits, and the thing being waited on was mostly
  values a machine can compare. Making the stop list closed is what lets the default path be
  unattended without making it unattended-and-unbounded: everything outside the table either
  proceeds or blocks, and neither of those needs a person present. Enforced by `ramo-run`
  Step 3 citing this table — model-discipline for the run honouring it.

## Gate 1 — Design briefing (`[CP]` rows only)

The `[CP]` marker exists to buy this stop (`.claude/rules/workflow/01a-execution-structure.md`
Marking `[CP]`). Non-`[CP]` rows run silently; that is what the marker is for.

**Source of the content is the plan, not a design stage.** With the per-task design stage gone,
the briefing draws on the plan's §1 선결 결정 table and the row's change unit — which is where
those decisions were supposed to be settled anyway
(`.claude/rules/workflow/01-plan.md` §1). If the row's design questions are not answered there,
the briefing is not the remedy: the row is a visible BLOCKED and the plan needs the decision.

Print in `RAMO_DOCUMENTATION_LANGUAGE`:

```text
## 설계 브리핑 — 태스크 {n} [CP]

**만들 것:** {산출물 경로와 형태}
**묶여 있는 결정:** {이 행이 인용하는 D-row 들. 각각 결정과 근거 한 줄}
**이 행이 확정하는 것:** {예측 시점 앵커, 라벨 정의, 제외 술어, 분할 경계, 피처 의미 중 해당분}
**기각한 대안:** {플랜이 기록한 것. 없으면 "없음" 이라고 적음}
**아래 행들이 이것에 묶이는 방식:** {이 판정이 확정하는 downstream 계약}
**증거:** {file:line 또는 실측 수치. 추정은 추정이라고 표시}
```

**No question follows.** The briefing prints and the row proceeds. Its purpose was never
approval: it is the record of which settled decisions this row is about to freeze, and that
record is worth the same whether or not someone is watching when it prints. The one case that
still stops is the one the briefing cannot be assembled for — a design question no `D`-row
answers — and that is a `<ramo>BLOCKED</ramo>` back to planning, not a question.

`--interactive` restores the question for a single invocation (`ramo-run` Step 0). It is a
per-run choice, not a norm.

## Gate 2 — Query gate (every data row, unconditional)

- **[HARD] Every `data-extraction`, `dataset-build`, and `data-analysis` row splits its
  implementation into two delegations with the three machine checks in between: phase 1 authors
  the statement and proves it at sample scale, the gate prints it and runs the checks, phase 2
  executes.**
  WHY: fixing a query after the dataset exists costs more than every other correction in the
  cycle, because the tables, the local artifact, the quality thresholds, and anything trained on
  them are all downstream of it. The split is what makes a sample result exist at all, and
  without a sample result there is nothing to check — which is why the split survived when the
  question did not. Unlike the briefing it is **not** limited to `[CP]`: a wrong query on an
  unmarked row is just as expensive. Enforced by `ramo-run` Step 3 — model-discipline grade for
  the split being kept and for the checks actually running.

### Phase 1 relay block

Relay verbatim into the phase-1 implement prompt:

```text
<query_probe>
**"Write" in this block always means a warehouse write (DDL/DML/CTAS), never authoring text.**
Phase 1's whole job is to author the statement; what it must not do is change anything in the
warehouse or run at full scale.

- Author the statement, then run it through the read path (the data access adapter,
  `python3 .claude/scripts/ramo-data.py query --file <path> --limit <n>`) restricted to a small
  sample: a narrow partition, a row limit, or both. Report the limit you used.
- Return in the body: the full statement text, the sample result's shape (row count, column
  names and types), the per-column null rate of the sample, anything surprising in the values
  (unexpected cardinality, a join that multiplied rows), and the cost signal the adapter's
  `explain` gives for the full-scale form (the engine's plan and its row estimates).
- **These three numbers are compared against the plan, so report them as numbers, not prose:**
  the sample row count, the list of columns whose sample null rate is 100%, and the estimated
  full-scale cost. The plan's §2 declares the expectation each is compared against
  (`.claude/rules/workflow/01-plan.md` §2); if the plan declares none, say so — that is a plan
  defect, not something to fill in here.
- For `dataset-build`: the full-scale run in phase 2 is SQL executed by the build script
  through the engine's own connection (the project DuckDB file, or another engine's DB-API
  cursor) by default -- never through the read adapter -- regardless of what this sample's cost
  looks like (`.claude/rules/data/warehouse-access.md`, write path). Project a full-scale
  wall-clock from this pilot run and name whether even the build-script path is heavy enough to
  hand the vetted SQL to a person to run in the team's own batch or notebook tool instead.
- For `dataset-build`: also return the exact table names you will create and each one's
  retention (`intermediate` | `experiment`), per
  `.claude/rules/data/dataset-materialization.md`.
- Issue no warehouse write (no DDL, DML, or CTAS) and run nothing at full scale. Authoring the
  statement text is exactly what you are here for; executing it beyond the sample is not. End
  with `<ramo>DONE</ramo>` and no evidence mapping -- phase 1 produces no artifact, so the keys
  are not due yet.
- Relay this block verbatim to the implement agent prompt.
</query_probe>
```

### The three machine checks

Run all three against the phase-1 report. Each one names the plan value it compares against.

| # | Check | Plan value it reads | Fails when |
|---|---|---|---|
| 1 | Sample row count | §2 expected row-count range for this row | The sample count falls outside the declared range, scaled to the sample's limit |
| 2 | All-null columns | §2 used-column list | Any column the plan says the work reads is 100% null in the sample |
| 3 | Estimated cost | §2 cost ceiling for this row | The adapter's `explain` estimate for the full-scale form exceeds the ceiling |

- **All three pass → phase 2 spawns automatically.** No question, no wait.
- **Any one fails → RETRY that row once** with the failing check and its two numbers relayed
  into the re-spawn of phase 1. This is a machine-value retry and counts against
  `.claude/schema/harness.json` `limits.run_implement_retry_max`.
- **Fails again → `<ramo>BLOCKED</ramo>`** naming the check, the expected value, and the
  observed value.
- **The plan declares no expectation → `<ramo>BLOCKED</ramo>`, not a pass.** A missing
  declaration means the check cannot run, and a check that cannot run is not a check that
  passed. The remedy is in the plan (`plan-rubric.md` `data.expectation`), not here.

What these three do **not** cover, stated plainly because the coverage gap is the cost of this
design: a statement whose predicate is wrong passes all three. A misplaced anchor, a label
window off by one day, an exclusion predicate that changes the population — each produces a
plausible row count, no all-null column, and an ordinary cost. Those are caught downstream by
the SQL reading of `.claude/rules/workflow/verify-rubric.md` `sql.window`, after the dataset
exists. That is a real regression against the removed question, and it is the reason the verify
stage's changed-file reading is not optional.

### Gate print format

```text
## 쿼리 확인 — 태스크 {n} ({Type})

**쿼리:**
```sql
{전문. 요약하지 않음}
```
**샘플 실행:** {제한 조건} → {행수}행, 컬럼 {n}개
**눈에 걸리는 것:** {전부 null 인 컬럼, 예상 밖 카디널리티, 행이 불어난 조인 — 없으면 "없음"}
**전체 규모 예상:** {explain 비용 신호와 예상 행수}
**실행 경로:** {dataset-build 만: 빌드 스크립트가 엔진 연결(DuckDB 파일 또는 DB-API 커서)로 실행(기본값) — 파일럿 기준 전체 소요 예상 및, 그마저 무거우면 "검증된 SQL 을 사람이 팀의 배치·노트북 도구에서 실행"으로 대체 권고. data-extraction/data-analysis 는 해당 없어 생략}
**만들 테이블:** {dataset-build 만 — 이름과 보존(intermediate|experiment). 그 밖에는 "없음"}

**기계 검사 3종**
| 검사 | 계획 선언값 | 실측 | 판정 |
|---|---|---|---|
| 표본 행수 | {§2 기대 범위} | {행수} | 통과 / 실패 |
| 전부 null 컬럼 | 없어야 함 | {컬럼 목록 또는 "없음"} | 통과 / 실패 |
| 추정 비용 | {§2 상한} | {explain 추정} | 통과 / 실패 |

**판정:** {3/3 통과 → phase 2 자동 진행 | {검사명} 실패 → RETRY 1회 | 재실패 → BLOCKED}
```

**No question follows.** The verdict line is the outcome. `--interactive` restores the question
for a single invocation; with it on, the three checks still run and print first, and the
question is asked after them rather than instead of them.

### Phase 2 relay block

```text
<evidence_requirements>
- Self-declare `evidence.task_type`; it must equal the execution row's `Type`.
- Fill that type's required keys (`.claude/schema/harness.json` `domains.<name>.evidence`);
  required on DONE envelopes only. `dataset-build` owes the table list with retentions, the
  quality-check tally, and the row reconciliation; `data-analysis` owes the path its conclusion
  lives at.
- Missing keys without a `concerns:` justification are a mechanical RETRY.
- **Run the approved statement as approved.** A change between the gate and execution
  invalidates the approval: return RETRY and go back through the gate.
- Relay this block verbatim to the implement agent prompt.
</evidence_requirements>
```

## Unattended execution is the default path

There is no longer a separate non-interactive branch, because there is no question to skip. The
table that used to describe the exception is now the norm:

| Type | Behaviour |
|---|---|
| `data-extraction`, `data-analysis` | print the block, run the three checks, proceed on 3/3 |
| `dataset-build` | print the block, run the three checks, and proceed on 3/3 **when the write target is inside the workspace schema** (`.claude/schema/harness.json` `data.workspace_schema`, default `workspace`). A target outside it is a stop-set row and blocks |

- **[HARD] `dataset-build` proceeding unattended rests entirely on the write being reversible.**
  A workspace-schema table can be dropped; the same statement aimed at a source table cannot be
  undone by dropping anything. That is why the write-target check is in the closed stop set
  rather than among the three machine checks: it is not a threshold comparison, it is a
  precondition.
  WHY: the previous contract blocked `dataset-build` outright when nobody was there to ask, on
  the reasoning that "nobody was there" is not authorization. That reasoning holds for an
  irreversible write and does not hold for a droppable one, and treating the two the same is
  what made the unattended path unusable for the common case. Enforced by
  `pre_bash.py::_common.sql_writes_confined_to_workspace` (mechanical, for shell-issued
  statements) and by the phase-1 report's declared table list — model-discipline for statements
  a build script issues through its own connection, which the hook cannot see.

Model-discipline grade for the checks running at all: nothing mechanical can tell a printed
gate from a skipped one.

## See Also

- `.claude/skills/ramo-run/SKILL.md` Step 3 — when each gate fires
- `.claude/rules/workflow/01-plan.md` §1 — the settled-decisions table gate 1 reads
- `.claude/rules/data/warehouse-access.md` — the read/write path split gate 2 enforces
