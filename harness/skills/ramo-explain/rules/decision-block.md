---
description: When a report may attach an AskUserQuestion, as a three-condition AND, and the prohibition on fabricating an option to fill the shape.
---

# Decision Block

A report sometimes ends in a question and usually does not. This file decides which, so the
choice is not made by how uncertain the writer happens to feel.

## The three conditions (AND)

Attach an `AskUserQuestion` only when **all three** hold:

1. **The decision is the user's.** It turns on preference, risk appetite, business priority, or
   knowledge the repository does not contain. A question the artifact could answer by reading
   one more file is not the user's decision; it is unfinished work.
2. **It changes what happens next.** Different answers produce materially different
   deliverables. If every answer leads to the same next action, the question is decoration.
3. **Real options exist.** At least two are genuinely viable, and each one's cost can be stated
   in a line. A single viable path is a constraint to report, not a choice to offer.

Fail any one and the report ends without a question. State the open item in prose instead:
`결정과 그 다음` is where it goes.

## HARD Rules

- **[HARD] Never fabricate an option to satisfy the shape.** Two real options or none.
  WHY: a manufactured second option makes the recommended one look considered when it was not,
  and the user then spends a decision on a false choice. Padding the form is worse than omitting
  it. Model-discipline grade, no mechanical check.
- **[HARD] Every option carries its cost, and the recommended one is named with its reason.**
  A menu with no recommendation moves the work to the user instead of the decision
  (`.claude/rules/common/explanation-style.md` rule 8).
  WHY: the point of asking is to get a decision the artifact cannot make; an unranked menu asks
  the user to redo the analysis first. Model-discipline grade.
- **[HARD] One question per report.** When two decisions are genuinely open, ask the one that
  gates the other and report the second in prose.
  WHY: a report that ends in three questions is a report that did not converge, and the
  user answers the first and loses the rest. Model-discipline grade.
- **[HARD] A question is never a substitute for verification.** If the answer is discoverable by
  running a command or opening a file, run it or open it.
  WHY: this is the failure mode the harness has measured repeatedly under a different name —
  carrying an unverified claim forward instead of checking it. Asking the user to adjudicate a
  fact the session could have measured is the same defect wearing a politer form.

## Where the option set comes from

Options are the alternatives the work actually surfaced, in the words of the decision rather
than the mechanism:

- Good: `① 슬라이스 A 를 먼저 개선 (효과 큼, 데이터 재추출 필요) ② 피처 2개 추가 (효과 작음,
  재추출 불필요)`
- Bad: `① 진행 ② 중단` when stopping was never on the table.

## Incorrect / Correct

```text
# Incorrect — condition 3 fails; the second option exists only to fill the form
① LightGBM 으로 진행 (권장)  ② 다른 것 (미정)

# Correct — condition 3 fails, so no question is attached
결정과 그 다음: 모델 계열은 정형 지도학습 기본값(LightGBM)이 그대로 맞아 질문 없이 확정함.
열린 것은 슬라이스 A 의 재추출 여부 하나이며 다음 진단에서 결론 냄.
```

## See Also

- `.claude/skills/ramo-explain/SKILL.md` — the report step that applies this
- `.claude/rules/common/explanation-style.md` — rule 8, the option/recommendation contract
- `.claude/rules/model/model-family-selection.md` — one concrete caller: the deviation question
