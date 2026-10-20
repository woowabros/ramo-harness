---
title: Experiment Ledger Template
impact: HIGH
tags: template, experiment, ledger, iteration
---

## Experiment Ledger Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

`docs/experiments.md` is one table for the whole project: **one plan is one row.** Nothing else
in the harness holds the sequence of experiments. `.ramo/diagnoses/` is volatile, a model card
covers one model, and an analysis document covers one question — so the fact a reader most often
wants ("what has been tried and what happened") had nowhere to live.

The ledger is a **record, not a plan**. It states what a row's experiment did and what came of
it; the next experiment's design lives in the next plan. The numbers in the example are
illustrative.

**Correct:**

```markdown
---
type: reference
title: 실험 원장
category: analysis
status: active
created: 2026-09-01
updated: 2026-09-14
tags: experiment, ledger, iteration
---

# 실험 원장

## 원장

| # | 날짜 | parent | change | objective | 결과 | 다음 후보 | 문서 |
|---|---|---|---|---|---|---|---|
| E3 | 2026-09-14 | E2 | 시간대·요일 혼잡 피처 3개 추가 | test MAE 4.6 → | **4.6** (목표 4.5 미달) | E4: 라벨 필터 재검토 | [진단](analysis/e3-diagnosis.md) |
| E2 | 2026-09-08 | E1 | 손실을 l2 → l1 | test MAE 4.7 → | **4.6** | E3: 혼잡 피처 | [카드](model/trip-duration-card.md) |
| E1 | 2026-09-01 | null | (첫 실험) | 베이스라인 MAE 5.0 | **4.7** | E2: 손실 교체 | [카드](model/trip-duration-card.md) |

## 열의 뜻

- **parent / change / objective** — the plan's own frontmatter fields, copied verbatim. A row
  whose `change` names two things is a row that should have been two experiments.
- **결과**: the objective's metric on the declared test set, bold, with the goal in parentheses
  when it was missed. One number, not a paragraph.
- **다음 후보**: the ranked first candidate from that cycle's diagnosis, and nothing more. The
  full ranking stays in the diagnosis document.
- **문서**: the durable document this row's conclusion lives in.

## 백로그

Candidates raised and not yet run, newest first. A candidate leaves this list only by becoming
a row above or by being struck with a reason.

| # | 후보 | 근거 | 상태 |
|---|---|---|---|
| B2 | zone 별 계층 모델 | E3 진단의 슬라이스 분해에서 승차 zone 이 최대 잔차 축 | 대기 |
| B1 | 라벨 필터 재검토 | E1~E3 전 회차에서 20셀 전량 음의 편향 | E4 로 승격 |
```

**Incorrect:**

```markdown
## 실험 이력
- 여러 실험을 진행했고 MAE 가 개선되었음. 자세한 내용은 각 모델 카드 참조.
```

Problems: no per-experiment row, so the sequence is unreadable; no `change`, so nobody can tell
what each experiment isolated; no result number, so improvement is a claim; and it points the
reader at n documents instead of answering the question.

Required sections: **원장**, **열의 뜻**, **백로그**. Newest row first in both tables.

- **[HARD] The ledger is updated in the same doc step that concludes an experiment.** A row
  added later is a row reconstructed from memory.
  WHY: this is the one artifact that outlives every individual experiment, and the failure mode
  is not a wrong row but a missing one — an experiment that ran, produced a conclusion, and left
  no trace in the sequence. Enforced by `.claude/rules/workflow/05-doc.md` trigger 4 (which
  names the ledger as its second required output) and by `ramo-doc` Step 4's trigger walk —
  model-discipline grade, no mechanical check.
- **A negative result gets a row.** An experiment that missed its goal is the most valuable row
  in the table, because it is the one a later session is most likely to re-run.

External precedent: probabl's `JOURNAL.md` keeps a numbered History plus a `B<N>` backlog and
warns against picking a single winning finding; TDSP's Model Report requires a Next Steps
section. This template is those two joined into one table.
