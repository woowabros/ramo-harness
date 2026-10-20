---
description: Merge-request conventions for DS work (GitHub pull requests or GitLab merge requests) — branch and commit shape from the ticket, the required MR sections, what an MR does NOT approve, and the size and draft rules. Implemented by the `ramo-mr` skill.
paths:
  - ".ramo/plans/*.md"
  - ".ramo/todo/*.md"
---

# Merge Request Conventions

The team ships through either GitHub pull requests or GitLab merge requests, chosen by
`.claude/schema/harness.json` `vcs.provider` (`github` | `gitlab`). This file says **MR** for
both: the conventions below are the same on either host, and only the mechanics (the creation
command, the template directory, how a draft is marked) differ. Those mechanics live in one
provider table in `.claude/skills/ramo-mr/SKILL.md`, so a rule here never sends a reader
looking for a button their host does not have.

`ramo-mr` implements this file; a person opening an MR by hand follows the same conventions.

## An MR reviews the code, not the experiment

- **[HARD] An MR is the review unit for the code that produced an experiment. It is not the
  approval gate for the experiment's result.**
  WHY: a DS experiment's output is a trained model, a warehouse table, and an evaluation
  report. None of those are in the diff — the model is an artifact, the table lives in the
  warehouse, and the report is a document. A conventional PR template has no section with a
  place for a result; its changes table is keyed by file. So an MR that tried to approve an experiment would be approving it on evidence
  it cannot see. The experiment's approval already has a seat with real evidence: `ramo:verify`
  plus the envelope's `evidence` keys, which the SubagentStop hook enforces
  (`.claude/rules/common/output-contract.md`). Enforced by the MR body shape below, which
  **points at** the verification and documentation outputs instead of restating them —
  model-discipline grade, no mechanical check.
- The practical test: if a reviewer would need to re-run training to judge the MR, the MR is
  scoped wrong. Split the code change from the result claim.

## Do not add a test-plan checklist

- **[HARD] The MR body carries no `Test Plan` table of commands and pass/fail checkboxes.**
  WHY: this harness already records what ran and what it proved, in a place a hook checks — the
  run tracker's per-row checks and the envelope's evidence keys. A second, hand-filled
  checklist creates two evidence systems for one fact, and the measured behaviour is that
  people fill the loose one. A test-plan table makes sense in a harness with no envelope; this
  one has the envelope. Link the verification report instead.

## Branch naming

```text
{type}/{TICKET}      # e.g. feature/PROJ-123
{type}/{slug}        # when the team uses no ticket tracker, e.g. feature/trip-duration-baseline
```

Types: `feature`, `fix`, `refactor`, `docs`, `test`, `chore`.

- The ticket is the branch's identity, not a decoration. One ticket, one branch, one MR.
- In a team that tracks work in tickets, a branch with no ticket is a signal that the work has
  no agreed scope yet, which is a planning problem rather than a naming problem. A team with no
  tracker uses the plan's slug in the ticket's place, and every `{TICKET}` below reads as that
  slug.

## Commit messages

```text
[{TICKET}][{type}] {한 줄 설명}
```

- The same `{type}` vocabulary as the branch.
- **Every commit on the branch carries the prefix, including commits that address review
  comments.** A fixed string such as "Fix review comments" drops the ticket and the type, and
  the branch's history stops being readable from `git log --oneline` alone.
- One logical change per commit. The test is whether a single sentence describes it.

## Required MR sections

The MR body is in `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`); paths, symbols, commands, and
the ticket key stay English. Five sections, and the fifth is the DS-specific one.

```markdown
## 배경

{왜 이 변경이 필요한가. 어떤 문제를 어떻게 풀었고 기존 작업과 어떻게 이어지는가}

## 참고 자료

- 티켓: [{TICKET}]({티켓 링크})
- 계획: {plan 문서 경로 또는 티켓}

## 수정 사항

| 파일 | 동작 | 무엇을 | 왜 이 방식으로 |
|---|---|---|---|
| `{경로}` | 추가/수정/삭제 | {바뀐 것} | {선택 근거} |

## 실험 결과가 사는 곳

| 항목 | 위치 |
|---|---|
| 검증 판정 | {verify 리포트 경로 또는 PASS/FAIL 과 그 근거 문서} |
| 모델 카드 | `docs/model/{...}.md` 또는 `해당 없음` |
| 실험 원장 행 | `docs/experiments.md` 의 {행 식별자} 또는 `해당 없음` |
| 재현성 키 | seed / split_boundary / data_snapshot / feature_spec 이 기록된 산출물 경로 |

## To Reviewers

- @{리뷰어} {무엇을 봐 주었으면 하는지}
```

- **`실험 결과가 사는 곳` 은 비울 수 없습니다.** 해당 없음이면 그렇게 적습니다. 빈 칸은 결과가
  없다는 뜻이 아니라 어디 있는지 아무도 안 적었다는 뜻이며, 그 상태가 리뷰어에게 diff 만 남깁니다.
- The ticket link is `.claude/schema/harness.json` `tracker.url_template` with `{TICKET}`
  substituted. With no template set the key stands alone without a link, and with no tracker
  the 티켓 line is omitted.
- Reviewer 요청은 사람 이름과 볼 지점을 함께 적습니다. "봐 주세요" 만으로는 리뷰어가 무엇을
  판단해야 하는지 알 수 없습니다.

## Repository-specific checklists

Some repositories require their own checklist in the MR body, and that checklist is the
repository's contract rather than this file's.

- **[HARD] When the target repository ships an MR template, that template wins over the section
  list above for anything the two disagree on.** Add this file's `실험 결과가 사는 곳` table to
  it rather than replacing the repository's own blocks.
  WHY: those checklists exist because something went wrong in that repository, and a harness
  that overwrites them re-opens whatever they closed. Detection is the presence of the
  provider's template path (`.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/`
  on GitHub, `.gitlab/merge_request_templates/` on GitLab) — model-discipline grade, no
  mechanical check.

## Draft, size, and when to open

- **Draft uses the provider's own mechanism**: on GitLab the title prefix
  `Draft: [{TICKET}][{type}] ...` (removing it marks the MR ready); on GitHub the `--draft` flag
  of `gh pr create` (marked ready with `gh pr ready`).
- **Size**: `.claude/schema/harness.json` `limits.mr_size_working_lines` is the range a reviewer
  reads in one sitting, and past `limits.mr_size_justify_lines` the MR body states why it was not
  split. Both count changed lines of code, not generated artifacts or data files.
- **When to open**: after `ramo:verify` reaches PASS and `ramo:doc` has run or been explicitly
  skipped with its reason recorded. Opening earlier means the reviewer reads code whose result
  is not yet established, and the MR then accumulates review rounds that the verification
  stage was going to answer anyway.
- A draft MR opened early for visibility is fine and is not the case above; what the rule
  forbids is asking for review before verification.

## Review readiness

Before requesting review, all of these hold:

1. Branch name carries the ticket; every commit carries the `[TICKET][type]` prefix.
2. The checks the target repository runs (its CI, tests, linters) pass on the branch.
3. No secrets, credentials, or PII in the diff, the MR body, or the linked artifacts
   (`.claude/rules/common/untrusted-data-boundary.md`).
4. The MR has one logical responsibility; unrelated changes are a separate MR.
5. `실험 결과가 사는 곳` is filled, including its `해당 없음` rows.

## See Also

- `.claude/rules/workflow/05-doc.md` — the stage that must complete before an MR opens
- `.claude/rules/workflow/04-verify.md` — where the experiment itself is approved
- `.claude/rules/common/untrusted-data-boundary.md` — the PII boundary item 3 cites
