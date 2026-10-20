---
description: Plan review rules — verdict thresholds, iteration policy, consensus priority mapping, and the report-local vocabulary boundary (labels never enter envelope verdicts)
paths:
  - ".ramo/plans/*.md"
---

# Plan Review

Plans are reviewed through two complementary mechanisms: automated rubric evaluation and manual
pre-mortem analysis.

> **Vocabulary scope (HARD):** The verdict labels on this page (`PASS | CONDITIONAL PASS | FAIL |
> PLATEAU`, `BLOCKING | NON-BLOCKING`) are **report-local** and MUST NOT appear inside `<ramo>`
> tags or envelope `verdict:` fields. The canonical orchestration vocabulary is
> `.claude/rules/common/output-contract.md` (tags `DONE | RETRY | BLOCKED`; plan-reviewer
> envelope verdicts `APPROVE | REJECT` per `.claude/schema/harness.json`).
> WHY: an earlier version had three separate label layers colliding in one field, which made
> verdicts unparseable. Enforced by subagent_stop.py (verdict closed set).

## Automated Evaluation (Primary)

@ramo-plan-evaluator scores plans using `.claude/rules/workflow/plan-rubric.md` (65 evidence-anchored
items, 9 DS dimensions: Problem and Objective 14%, Data and Tables 12%, Feature Design 14%, Model
Design 12%, Code Evidence 8%, Implementation Shape 10%, Execution Handoff 6%, Verification and
Reproducibility 14%, Sequencing/Risk/Density/Readability 10%). Every FAIL item becomes an
`EP-P{0-3}-{NNN}` ticket (`.claude/rules/workflow/09-ticket-schema.md`).

### Citation Entry Gate (before scoring)

Citation integrity is checked before the rubric runs and is **not** one of the 65 items
(`plan-rubric.md` Evaluation Workflow step 2). Its failures come back as `EP-CITE-{NNN}`, and
they are a different kind of object from a finding:

| | `EP-CITE-{NNN}` | `EP-P{0-3}-{NNN}` / `CP-P{0-3}-{NNN}` |
|---|---|---|
| What it is | a stale, invented, or misdirected citation | a defect in the plan's contract, logic, or coverage |
| Priority | none | P0-P3 |
| Consensus | not voted on | counted per the mapping below |
| Cost to fix | mechanical repair of the citation | a decision by the author |
| Improve round | **does not consume one** | consumes one |
| Repair passes | `.claude/schema/harness.json` `limits.plan_cite_repair_max` per round; leftovers are carried | not applicable — a finding is fixed or it stays open |

- **[HARD] A review round whose only failures are `EP-CITE-*` is not a FAIL. It is a repair
  pass: fix the citations, re-run the gate, and continue the same round.**
  WHY: most blocking findings in one observed cycle changed no output value, and every one of
  those was a citation or consistency fix. Counting them as findings spends the improve budget on
  edits that cannot change a result, and the budget is what the plan needs for the defects that
  can. Enforced by `.claude/skills/ramo-plan/SKILL.md` Step 5 — model-discipline grade.
- **A repair pass is bounded even though it costs no round.** One round allows
  `.claude/schema/harness.json` `limits.plan_cite_repair_max` repair passes. Citations still
  unresolved at the cap are **carried**: they leave the gate, the round proceeds to scoring,
  each carried citation becomes one `EP-P2` ticket, and every rubric item that rested on it
  scores with the evidence `"not found"`.
  WHY: the exemption that makes the repair pass cheap is exactly what removes its stopping
  condition — a loop with no round cost can re-send the same unresolvable citation forever.
  Carrying is what keeps the defect visible without paying a round for it: the anchor is gone,
  so the item it supported fails on its own terms rather than being waved through. Enforced by
  `.claude/rules/workflow/plan-rubric.md` Evaluation Workflow step 2 — model-discipline grade
  for the per-round count.

### Report Verdicts

| Report label | Condition | Action |
|---------|-----------|--------|
| **PASS** | 0 P0 + 0 P1 + score >= 80% | Deliver plan to user |
| **CONDITIONAL PASS** | 0 P0 + score >= 65%, and either P1 tickets remain or the score is under 80% | Deliver, list every open P1 with its ticket, and ask the user once via AskUserQuestion — `fix now` (spend one improve round on the P1 set) or `proceed`. Headless sessions take `proceed` |
| **FAIL** | P0 remain, OR score < 65% | Improve loop (max rounds: `.claude/schema/harness.json` `limits.plan_improve_max_rounds`) |
| **PLATEAU** | See plateau signals below | Stop early, explain, deliver best version |

The severity definition behind these three rows is `.claude/rules/workflow/09-ticket-schema.md`
Priority Definitions: P0 opens a round, P1 is listed in full and rides a round that is already
running. CONDITIONAL PASS is where a P1 set lands, which is why that row asks the person rather
than deciding for them — the seat that can weigh a quality gap against the cost of another round
is the one that has to live with the plan.

### Plateau Signals

| Signal | Criterion |
|--------|-----------|
| Score plateau | Overall score improves <3% AND no P0 resolved this round |
| Issue plateau | Same P0 issues remain open after a fix attempt |
| Oscillation | Issue resolved in round N reappears in round N+1 |
| Length regression | Plan grew this round AND the P0 count did not decrease — revert the round |

### Iteration Policy

- Max improve rounds: `.claude/schema/harness.json` `limits.plan_improve_max_rounds`.
- Each round: parallel multi-review -> main-session consensus -> ramo-plan-improver fixes P0/P1 ->
  regression check (fixes must not break previously passing items; improver returns a
  regression diff table).
- **[HARD] The last improve round is scored before the plan reaches the user.** Each round is validated by the
  next round's review, so the final round has no validator and its edits would otherwise ship
  unreviewed. One @ramo-plan-evaluator spawn on the final file closes it
  (`.claude/skills/ramo-plan/SKILL.md` Step 5b) — not a full round, and not the improver's own
  regression table, which is a self-report.
  WHY: observed, both halves. Earlier rounds in one cycle introduced new defects while fixing
  others, and defects from that cycle's unreviewed final round reached the user.
  **The step is conditioned on an improve round having run.** When no improve round ran, the
  file Step 3's review scored is the file being delivered, so a second evaluator spawn scores
  the same bytes twice and the hole this rule closes does not exist. The condition is the WHY
  read literally: what goes unvalidated is an improver's edits, and with no improver there are
  none.

## Consensus Priority Mapping (multi-reviewer)

When `ramo-plan` runs its review loop, combined P0/P1 counts from consensus-derived
(`CP-P{N}-{NNN}`) and evaluation-derived (`EP-P{N}-{NNN}`) tickets determine the verdict.

| Consensus level | Criterion | Priority |
|----------------|-----------|----------|
| Majority | >50% of reviewers agree, and the finding is BLOCKING | P0 |
| Majority, NON-BLOCKING | >50% agree on a finding no reviewer called BLOCKING | P1 |
| Strong minority | 33-50% agree | P1 |
| Minority | <33% agree | P2 |
| Single voice | 1 reviewer | P3 |

Veto, two seats wide: a **@ramo-critique** BLOCKING finding is minimum P1 regardless of vote
count, and a **@ramo-data-design or @ramo-model-design** BLOCKING finding inside its own
dimensions is minimum P1 on the same terms. 50/50 splits escalate to the user via
AskUserQuestion — never auto-resolve.

- **[HARD] A domain seat's BLOCKING finding within its assigned rubric dimensions carries the
  same veto as @ramo-critique's.**
  WHY: the consensus table maps agreement count to priority, and a finding only one seat is
  equipped to make can never reach majority. The feature and model dimensions have exactly one
  reviewer each (`.claude/skills/ramo-plan/rules/reviewer-delegation.md`), so without this the
  only seat that measured a null rate or walked a transform list lands at P3 as a single voice
  and the improve loop never reaches it. The veto is scoped to the seat's own dimensions
  precisely so it does not become a general one: a data seat's opinion about the model section
  is a single voice like anyone else's. Enforced by `.claude/skills/ramo-plan/SKILL.md` Step 4
  (the consensus step applies it) — model-discipline grade, no mechanical check.

The table above is the plan stage's mapping. The verify stage does not vote: its seats return
anchored cells for disjoint item sets, and each FAIL cell takes its item's priority
(`.claude/rules/workflow/04-verify.md` Synthesis without votes).

## Review Report Header (report-local)

Every reviewer opens its findings body with this header so the consensus step counts flags
mechanically instead of parsing prose. The header is report-local: these labels never enter a
`<ramo>` tag or an envelope `verdict:` field.

Domain reviewers and `@ramo-critique`:

```text
BLOCKING: {n}
NON-BLOCKING: {n}
Summary: {1-2 sentences}
```

`@ramo-plan-evaluator`:

```text
Citations: {n}/{n} verified
Score: {XX}% (Grade {A|B|C|D|F})
P0: {n} | P1: {n} | P2: {n} | P3: {n}
Report label: PASS | CONDITIONAL PASS | FAIL
```

The citation line comes first and is reported as a passed precondition, not as a score
component. When the gate fails, that line reads `Citations: {k}/{n} verified — EP-CITE list
below` and the remaining three lines are absent, because nothing was scored.

A findings body without this header is a malformed review: the orchestrator re-spawns once,
then reports the reviewer as lost (`.claude/skills/ramo-plan/SKILL.md` Step 3).

## Manual Pre-mortem (Complementary)

1. Assume the plan has already failed — what went wrong?
2. Identify the top 3 most likely failure modes (for @ramo-critique, apply the register structure in
   `.claude/skills/ramo-plan/rules/forward-risk.md`).
3. Add mitigations to the relevant change unit or the compact risk summary.

## Assumption Verification

- Every assumption listed explicitly, marked VERIFIED (with evidence) or UNVERIFIED.
- High-impact UNVERIFIED assumptions go to a concise user-verification list.

## Severity Levels (manual findings)

- **BLOCKING** — missing dependencies, undefined deliverables, no verification criteria,
  circular task graph, invalid roster agent or `Skill()` reference, missing reproducibility
  intent on a training/extraction row.
- **NON-BLOCKING** — missing rollback note, unexploited parallelism, naming or density issues.
  Report with severity and evidence; the consensus step maps them to P-levels.
