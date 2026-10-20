---
description: Readability discipline for durable documents — citation placement, heading form, single heading depth, the required invariants section, and length baselines. Applies to docs/ and wiki/ deliverables, not to harness assets.
paths:
  - "docs/**/*.md"
  - "wiki/**/*.md"
---

# Document Readability

A document nobody can read is not documentation. This file holds the five habits that decided
whether a real document was readable, found by comparing a long SoT nobody could scan against
a much shorter reference document, dense with citations, that read cleanly.

Scope: deliverables under `docs/**` and `wiki/**`, and the example blocks inside the templates
that produce them (`.claude/skills/ramo-doc/rules/template-*.md`,
`.claude/skills/ramo-wiki/templates/*.md`, `.claude/skills/ramo-research/templates/*.md`). Harness assets are English contracts with a
different reader and are governed by `common/sot-authoring.md` instead.

These are five rules, not a style guide. What makes them rules is that each one has an observed
failure behind it and a stated repair.

## R1 — A citation sits at the end of its sentence

Parenthetical evidence goes at the sentence's end, once. Never two parentheses in one sentence,
never a parenthesis inside a clause the sentence still has to finish.

Observed: the reference document's parentheses were all sentence-final and its citations read
as evidence. The observed SoT's parentheses sat mid-sentence carrying predicates, sample sizes,
and source titles, so a sentence had to be re-entered after each one, and its longest lines ran
to several hundred characters.

```markdown
# Incorrect — three parentheses, two of them mid-clause
라벨 이상률은 1.5% (46,000 / 3,066,766, `trip_duration_min <= 0` 기준) 이며 이상군의 평균
`trip_distance` 는 (측정 A, 단일 파티션) 0.4마일 짧음 (비무작위 이상).

# Correct — one sentence, one citation, at the end
라벨 이상률은 1.5% 이며 이상군의 평균 `trip_distance` 가 0.4마일 짧아 이상이 무작위가
아님 (46,000 / 3,066,766, `trip_duration_min <= 0`, 측정 A, 예시 수치).
```

## R2 — A heading names its subject, it does not state a conclusion

Headings are noun phrases. The conclusion goes in the first sentence under the heading, where a
reader can see what supports it.

Observed: the SoT carried headings like `4.25는 모델의 하한이 아니라 세션 내 변동폭`, which
is a claim. A table of contents made of claims cannot be scanned, and a claim in
a heading is a claim with no visible evidence.

```markdown
# Incorrect — the heading is the finding
## 4.25는 모델의 하한이 아니라 세션 내 변동폭

# Correct — the heading is the subject
## 재현 편차
세션 간 재현에서 4.25 는 하한이 아니라 변동폭임 (seed 42, 3회 반복, 예시 수치).
```

## R3 — `##` only

One heading depth. A section that needs a `###` is a section that wants to be its own document
or its own table.

Observed: the SoT nested `###` under most of its `##` sections, and the model card put
`### 설계` three levels deep, past the middle of the file — the one section a reader opens a
model card for. Depth hid it.

The repair is not always a split. Most `###` groups are a table whose rows are the sub-headings.

## R4 — A SoT, architecture, or overview document carries `## 핵심 불변식`

A numbered list of the properties that must stay true, each with what verifies it.

Observed: the reference document opened with numbered invariants, each naming its test. None of
the other documents reviewed had such a section; the nearest thing was `확인 필요 사항`,
which is the opposite — a list of what is *not* settled. A document that states only open
questions gives the next reader nothing to rely on.

```markdown
## 핵심 불변식

1. 타깃은 `[1, 90)` 분 안에만 존재함: `checks_artifact.py --stage label-base` label-bounds
2. fit / valid / test 의 `pickup_date` 집합은 서로 겹치지 않음: 같은 검사 split-separation
```

Each line: the property, then the mechanism, separated by a colon. A line with no mechanism is
a wish, not an invariant (`common/sot-authoring.md` SOT-4).

## R5 — Length baselines, not caps

About 15 lines per section, about 150 lines per document.

**These are baselines and explicitly not ceilings.** A document with a real reason to be longer
should be longer, and padding a section to reach 15 lines is worse than 6. The numbers exist so
that crossing them prompts one question — is this two documents? — and nothing more. The
contrast that produced them is the long SoT against the short reference, where the difference
was not subject matter but that the long one had never been split.

## Enforcement

| Rule | Mechanism | Grade |
|---|---|---|
| R2, R3 on `wiki/**` | `ramo-wiki-reviewer`, at the review step of the publish transaction | model-discipline grade, no mechanical check |
| R2, R3 on `docs/**` | `ramo-doc-writer`'s quality pass. The rule applies there — see Scope above — and only a reviewer enforces it | model-discipline grade, no mechanical check |
| R1 | none — no parser distinguishes a mid-clause parenthesis from a legitimate aside | model-discipline grade, no mechanical check |
| R4 | `ramo-doc-writer`'s quality pass and `ramo-wiki-reviewer`'s semantic review | model-discipline grade, no mechanical check |
| R5 | none, by design — a baseline that blocks is a cap | model-discipline grade, no mechanical check |

An earlier version named a linter here and recorded mechanical grade for `wiki/**`. It was
false in the only way that matters: the linter never reached the repository the rule governed,
so a rule that recorded its own grade as mechanical had no mechanism there at all. Shipping a
checker was considered and rejected — hook handlers are stdlib-only by contract
(`.claude/rules/workflow/08-hook-conventions.md`), and a warning is not worth a runtime
dependency in every consumer repository. Naming the seat that does the work is the honest
repair.

R2 and R3 are review findings rather than blocks because both have legitimate exceptions: a
heading may carry a version number, and a generated index may nest. A finding puts the case in
front of a person; a block would produce workarounds.

The R2 signal is deliberately narrow. A reviewer flags a measured decimal (`4.25`) or a Korean
predicate ending (`임`, `함`, `이다`, `아니라`, ...) — the two shapes the observed failure had —
and not any digit in a heading, because `## v2 릴리스` and `## 3단계 분할` are subjects, not
conclusions.

## See Also

- `common/sot-authoring.md` — SOT-1 to SOT-4, the durable-evidence contract this sits beside
- `.claude/skills/ramo-doc/rules/quality-conciseness.md` — the density pass that reads this
- `.claude/skills/ramo-doc/rules/template-model-card.md` — the template R3 was observed against
