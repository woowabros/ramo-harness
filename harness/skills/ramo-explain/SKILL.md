---
name: ramo-explain
description: "Report-time explanation layer — turns a finished artifact (plan, verification report, diagnosis) into a four-part account a reader can act on, before any score or statistic is printed. Called by a pipeline skill at its report step; spawns nothing."
argument-hint: "[artifact path] [what the reader is deciding]"
allowed-tools: Read, Grep, Glob
---

## Language Setting

Explanation prose follows `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`). Paths, symbols,
commands, agent names, metric names, and identifiers stay in English
(`.claude/rules/common/language-settings.md`).

# Report-Time Explanation

Execution contract: `.claude/rules/common/skill-contract.md` (cited, not restated).
Explanation contract: `.claude/rules/common/explanation-style.md` — this skill is the seat
where rule 4 of that file ("do not lead a completion report with verification statistics")
is actually carried out.

A caller invokes this at its report step, after the artifact is written and before the
report is printed. It spawns nothing: the artifact is on disk and reading it is the work.

## Why this seat exists

The user's objection to a finished plan was not that it was wrong but that "직관적으로 뭘
하겠다는 건지 모르겠다" — over a thousand lines, with the machine-parseable table near the end. The
harness already forbade leading with statistics, and the report led with the score anyway:
third line, above the reviewer list and the iteration count. A rule that is not carried out
by a step does not get carried out.

## Step 0 — Resolve the artifact and the decision

1. Read the artifact at the path the caller gives. Never explain from the caller's summary of
   it: the summary is what needs checking.
2. Identify what the reader is deciding right now. A plan's reader decides whether to run it;
   a verification report's reader decides whether to fix or accept; a diagnosis's reader
   decides which experiment comes next.
3. Abort condition: the artifact does not exist or is empty — return that fact in one line so
   the caller can report a hand-off failure rather than printing an explanation of nothing.

## Step 1 — Write the four parts

In order. The order is the contract; the headings may be adapted to the artifact.

| Part | Answers | Length |
|---|---|---|
| 배경 | What was being solved, and which constraint shaped the answer | 2-4 sentences |
| 감 잡기 | The whole thing in one concrete image or a worked line — what a reader would see happen | 3-6 sentences |
| 동작 | How it actually proceeds, in the order it proceeds, naming the parts that matter | the bulk |
| 결정과 그 다음 | What is settled, what is still open, and what the reader does now | 3-6 sentences |

Rules for the body:

- Lead with what the thing does for a person. An identifier is trailing evidence, never the
  subject, unless the caller's question names it (`explanation-style.md` rule 9).
- Interpret every number against its baseline. `MAE 4.7` alone says nothing; "4.7 against a
  4.5 target, so 6% better than the baseline where 10% was needed" is the same number doing work.
- Distinguish fact, inference, and open question. Say how far verification actually reached.
- Name the trade-off that was taken, not only the choice. A decision with no cost stated reads
  as having had no alternative.
- No statistics, scores, or counts in 배경 or 감 잡기. They belong in 동작 at the earliest, and
  the caller's own score block comes after this explanation ends.

## Step 2 — Decide whether a question is attached

Apply `.claude/skills/ramo-explain/rules/decision-block.md` (cited, not restated). It is a
three-condition AND: attach an `AskUserQuestion` only when all three hold, and never invent a
second option to fill the shape.

## Step 3 — Return

Return the explanation text to the caller. The caller prints it, then prints its own report
block (score, ticket counts, team, iterations) beneath it, then runs its own next-step baton.

This skill writes no file and updates no state: the artifact it explains is already durable,
and a second copy of the explanation would be one more thing to keep current.

## Suggest Next Step

None of its own. Control returns to the calling skill, which owns the baton
(`ramo-plan` Step 7, `ramo-verify` Step 9). Saying so explicitly matters: a helper skill that
proposes its own next step competes with its caller's, and the user gets two questions for one
decision.

## Anti-Patterns

- Leading with the score. That is the exact defect this seat was added to remove.
- Explaining the artifact's structure instead of its content ("the plan has five sections").
  The reader can see the sections; they cannot see what the plan will do.
- Restating the artifact section by section. This is an account, not a table of contents.
- Padding 감 잡기 with an analogy that carries no information ("it works like a pipeline").
  A concrete worked line beats a metaphor.
- Attaching a question because the artifact felt uncertain. The three conditions decide it.

## Terminal Output

The four-part explanation in `RAMO_DOCUMENTATION_LANGUAGE`, and nothing else. **No result
envelope** — that block belongs to sub-agents (`.claude/rules/common/output-contract.md`
Scope), and this skill runs in the caller's session.

On abort, one line naming the artifact that could not be read.
