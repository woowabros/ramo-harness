---
description: The plan delivery contract — the four acts, the frontmatter fields each delivery updates, the report block format, and the plan-mode exit discipline. Cited by ramo-plan Step 6.
---

# Plan Delivery Contract

Every delivery performs four acts in this order, including a second or third delivery of the
same plan. `ramo-plan` Step 6 cites this file; the step keeps the sequence, this file keeps the
mechanics.

Each act below exists because its absence was observed, not because deliveries need ceremony.

## Act 1 — Update the plan's frontmatter

Field by field (`.claude/schema/harness.json` `doc_frontmatter.ramo_plan`):

| Field | Value |
|---|---|
| `status` | `draft` -> `active` |
| `updated` | today |
| `generated.by` | the writing seat (e.g. `ramo-plan-writer/claude`) |
| `generated.at` | the timestamp of **this** delivery |

- **[HARD] `generated.at` is re-stamped on every delivery, never carried over.**
  WHY: a redelivery that leaves it at the first run's value claims the plan has not been touched
  since. Observed once, and it cost the record of a substantial rewrite: `updated` moved,
  `generated.at` stayed. Model-discipline grade, no mechanical check.

## Act 2 — Write the report file before printing it

Write the report to `.ramo/context/{YYYY-MM-DD}-plan-report.md`, then print the same content in
acts 3 and 4.

- **[HARD] The file is written first.**
  WHY: if the print is skipped the report still exists, so the loss is detectable afterwards.
  This was the only path by which the score and the ticket counts reached the user, and it
  silently produced nothing twice.

## Act 3 — Explain, before any number

Call `Skill("ramo-explain", ...)` and print what it returns. The four-part account comes before
the score block, never after.

- **[HARD] No score, grade, or count is printed above the explanation.**
  WHY: `.claude/rules/common/explanation-style.md` rule 4 already forbade leading a completion
  report with verification statistics, and this report led with the score anyway — third line,
  above the reviewer list. The rule was not missing; the step performing it was.

## Act 4 — Print the report block

```text
## 계획 작성 완료{PLAN_MODE ? " (plan mode)" : ""}

{리뷰 미수행 줄 — 해당 시에만, 점수보다 위}

**파일:** {TARGET_PLAN_FILE}
**게이트:** {FULL|LIGHT} — {사유}
**채점 판정:** {XX}% (Grade {X}) / P0 {n} · P1 {n} · P2 {n} · P3 {n}
**부검 판정:** BLOCKING {n}건 (@ramo-critique {n} · @ramo-audit {n} · 설계 좌석 {n})
**리뷰 팀:** {N}기 ({@agent 목록})
**반복:** {n}회 {중단 사유 있으면 명기}

### 미해결 P1 (라운드 없이 전달)
- {CP|EP}-P1-{NNN}: {한 줄} — {왜 이번에 안 고쳤는지 한 줄}

### 미해결 P0 (한도 도달 시)
- {CP|EP}-P0-{NNN}: {한 줄} — {권고}

### 소수 의견 (있는 경우)
- {@agent}: {합의와 다른 판단과 근거}

SQL 컴파일 게이트: {컴파일 n건} / {템플릿 건너뜀 n건} / {보수 n회}
stage-cost: spawns={n} rounds={r} wall={m}m p0_rounds={n} gate3_catches=- waves=- reverify_files=- human_wait_seconds={n}
```

The last line is the stage-cost footer (`.claude/rules/common/skill-contract.md`); the three
dashes are the fields the plan stage has no concept of. The compile-gate line above it comes
from `.claude/skills/ramo-plan/SKILL.md` Step 2a.

The score is the Step 5b final-version score when an improve round ran; when none ran, Step 5b
is skipped and the score is Step 3's, which scored the same bytes being delivered. The report
says which of the two it is.

- **[HARD] Every open P1 is listed here by ticket id, with no exception for a long list.**
  WHY: P1 stopped forcing a round in an earlier version, and the guarantee that replaced the round is this
  section. A P1 that is neither fixed nor listed has simply been dropped, which is the failure
  mode the severity change is judged against
  (`.claude/rules/workflow/09-ticket-schema.md` Priority Definitions). The two headings are
  separate because the reader's next action differs: a P1 list is information for the next
  iteration, and a P0 list means the round cap was reached with a correctness defect open.
  Model-discipline grade, no mechanical check.

## The two verdicts sit side by side

- **[HARD] The report carries the scorer's number and the pre-mortem count as two adjacent
  lines, never the number alone.**
  WHY: observed, and the pair is not a contradiction. In one cycle @ramo-plan-evaluator returned
  a near-perfect score while the judgement seats returned several BLOCKING findings, because the
  two lenses answer different questions: the scorer asks whether the plan has a place for each
  thing, and the pre-mortem asks whether what is written there is true. A report that prints
  only the first tells the user the plan is finished. Enforced by this block's format — model-discipline grade
  for the slot being filled and the counts being right.

## When a review seat is missing

A domain seat lost after its respawn is dropped and the stage continues
(`.claude/skills/ramo-plan/SKILL.md` Step 3.4). A mandatory seat is never dropped; that path
ends `<ramo>BLOCKED</ramo>` and never reaches this report.

- **[HARD] A dropped seat is announced above the score, and the score is marked 유보.**

```text
> **리뷰 미수행:** @ramo-model-design (스폰 2회 실패). 아래 점수는 이 좌석의 차원을
> 보지 않은 상태이므로 **유보** 임.
```

  WHY: the number is what the user acts on, and a number produced by four seats reads exactly
  like one produced by five. Putting the gap below the score means the reader has already
  decided before reaching it, which is the same ordering defect
  `.claude/rules/common/explanation-style.md` rule 4 names. 유보 is the word because a partial
  team's score is not wrong, it is uncalibrated. Model-discipline grade, no mechanical check.

## Plan-mode exit

- **[HARD] Never call `ExitPlanMode`. Print the instruction and let the user exit.**
  WHY: observed — the tool was called automatically and the user saw the "start coding?" prompt
  in place of the instruction, so a saved plan looked unsaved. The exit is the user's.
  Model-discipline grade, no mechanical check.

## See Also

- `.claude/skills/ramo-plan/SKILL.md` Step 6 — the step that cites this
- `.claude/skills/ramo-explain/SKILL.md` — act 3's seat
- `.claude/rules/common/explanation-style.md` — rule 4, the ordering this contract enforces
