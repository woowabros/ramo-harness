---
description: Canonical ticket schema for P0-P3 issue tickets across plan evaluation, consensus, and verification
paths:
  - ".ramo/plans/**"
  - ".ramo/todo/**"
---

# Ticket Schema

Canonical format for P0-P3 issue tickets used by plan evaluation, consensus synthesis, and
verification. The plan and verify skills also cite this file by path (design/review stages may
have no file open for `paths:` to match).

## Ticket ID Format

```
{PREFIX}-P{0-3}-{NNN}
```

- `PREFIX`: two-letter source identifier (see Prefix Table)
- `P{0-3}`: priority level
- `NNN`: sequential number per priority within the report (001, 002, ...)

### Prefix Table (v0)

| Context | Evaluation Prefix | Consensus Prefix | Example |
|---------|------------------|------------------|---------|
| Plan | `EP` | `CP` | `EP-P0-001`, `CP-P1-003` |
| Verify | `EV` | — | `EV-P0-001` |

Plan-stage evaluation prefixes are set by the evaluating agent and consensus prefixes by the
main session during consensus synthesis. The verify stage has no consensus prefix: seats return
cells, and the main session numbers every ticket `EV` at its item's priority
(`.claude/rules/workflow/04-verify.md` Synthesis without votes). No other prefix exists in the
v0 pipeline; a skill outside it that needs one adds a row here rather than inventing it.

> **`CP-` is not `[CP]`.** The `CP` above is a ticket prefix meaning *consensus-derived, plan
> stage*. The `[CP]` in an execution row's `#` cell is a *critical path* marker that triggers a
> human design briefing (`.claude/rules/workflow/01a-execution-structure.md` Marking `[CP]`).
> Same two letters, unrelated machines: a ticket is numbered, a row is marked. A real user read
> one as the other; renaming either is deferred because the marker sits inside a frozen
> column contract.

## Priority Definitions

| Priority | Criteria | Action |
|----------|----------|--------|
| P0 | Blocks correctness or safety. Must fix before proceeding. | Round required |
| P1 | Significant quality gap. Should fix before the stage completes. | Listed in full in the stage's final report and fixed inside any round P0 is already running; never opens one |
| P2 | Minor quality issue. Fix if time permits. | Advisory |
| P3 | Cosmetic or stylistic. No functional impact. | Advisory |

- **[HARD] Only P0 opens a round. P1 is listed, never dropped, and rides any round that runs.**
  A stage that finds P1 tickets and no P0 delivers, with every open P1 named in its report; a
  stage already running a P0 round fixes the P1 tickets in that same round.
  WHY: observed during testing. A plan stage that reached Grade A over several improve rounds
  still stopped the run stage repeatedly on defects no seat was equipped to measure, so the
  rounds were not buying correctness. The verify stage of the same cycle spent one of its
  serial fix waves on a single P1 (a file-size split) whose finding changed no output value.
  Round cost is the scarce resource and P0 is
  what it is for. The guarantee that survives is coverage, not force: P1 is still raised, still
  written down, still delivered to the person deciding. Enforced by the two verdict tables that
  read this definition (`.claude/rules/workflow/02-review-plan.md` Report Verdicts and
  `.claude/rules/workflow/verify-rubric.md` Report Verdicts), neither of whose FAIL conditions
  names P1 — model-discipline grade, both for keeping those tables aligned and for the
  ticket-by-ticket judgment itself.

## Individual Ticket Format

```markdown
### {PREFIX}-P{0-3}-{NNN}: {Title}

| Field | Value |
|-------|-------|
| **Dimension** | {rubric dimension name} |
| **Item** | `{checklist_id}` — {human-readable name} |
| **Evidence** | plan: quoted text or "not found" / code: `file:line` — "description" |
| **Impact** | {what goes wrong if unfixed — one sentence} |
| **Why prior checks missed it** | {which existing check should have caught this and why it did not — required on `EV` tickets; `N/A` allowed on `EP`/`CP` tickets, where no check has run yet} |
| **Remediation** | {specific fix with concrete example} |
| **Status** | OPEN |
```

- **[HARD] A verify-stage ticket states why the checks that already ran did not catch it.**
  WHY: this is the field that turns a fixed defect into a fixed *class* of defect. A familiar
  expensive defect is a P0 that survives a large passing test suite and high coverage, and its
  record answers exactly this question in one line: every fake in the test suite returned a
  string where the real provider returns a list, so the suite was verifying the fakes rather
  than the system. Without that line the fix is one bug; with it, the gap in the checks is
  visible. The DS form of the same shape is a pipeline that passes on synthetic rows and breaks
  on warehouse rows — different substrate, identical failure. Enforced by
  `.claude/rules/workflow/04-verify.md` Synthesis without votes, which requires the field on
  every `EV` ticket — model-discipline grade, for the field's presence and the answer's
  quality alike.

### Status Lifecycle

```text
OPEN -> RESOLVED (R{n}) | DEFERRED
```

| Value | Meaning | Who sets it |
|-------|---------|-------------|
| `OPEN` | Created by an evaluating agent, or by the verify main session from a FAIL cell. Default state. | ramo-plan-evaluator (`EP`), the plan and verify main sessions (`CP`, `EV`) |
| `RESOLVED (R{n})` | Fixed in improve/Fix round `n`. The round number is required, not optional. | the orchestrating skill (plan, verify) |
| `DEFERRED` | Deliberately not fixed. Requires a one-line justification in the ticket. | the orchestrating skill, after user confirmation for P0 |

- **[HARD] Evaluating agents never set status.** They emit `OPEN` tickets only; the
  orchestrator owns every transition.
  WHY: an agent that marks its own finding resolved removes the independent re-check that
  makes the Fix loop worth running. Enforced by the read-only tool set of every evaluating
  agent (`schema/harness.json` `agents.roster`) and by the orchestrator re-deriving the
  ticket list each round.
- **Fix-round carry-over.** `ramo-verify` re-derives the change list and re-fills the
  affected rows' cells each round. A ticket that was `RESOLVED (R1)` and reappears is a **new** ticket with a fresh
  `{NNN}`, cross-referenced to the old id — never a silent re-open. Oscillation across
  rounds is a plateau signal (`workflow/02-review-plan.md`).

## Consensus Finding Table

Used by the plan stage's main-session consensus step. Consensus is synthesized in the **main
session only** — never delegated to a sub-agent. The verify stage does not vote; it maps cells
to priority by item (`.claude/rules/workflow/verify-rubric.md` Priority Mapping).

```markdown
| Ticket | Finding | Flagged By | Consensus | Priority | Evidence | Status |
|--------|---------|-----------|-----------|----------|----------|--------|
| CP-P0-001 | {finding} | @agent1, @agent2 | Majority (2/3) | P0 | "quoted text" | OPEN |
```

### Consensus-to-Priority Mapping

| Consensus Level | Threshold | Priority |
|----------------|-----------|----------|
| Majority | >50% of reviewers | P0 |
| Strong minority | 33-50% | P1 |
| Minority | <33% | P2 |
| Single voice | 1 reviewer | P3 |

**The Majority row reads P0 only for a finding its reviewers flagged BLOCKING.** A
NON-BLOCKING finding caps at P1 no matter how many seats raised it, so a shared stylistic
preference cannot promote itself into a round trigger by vote count alone. Severity is a
statement about what breaks, and agreement measures confidence in the observation, not its
consequence.

**Veto power:** a `@ramo-critique` BLOCKING finding maps to minimum P1 regardless of vote count.

## Score Sheet

```markdown
| # | Dimension | Pass | Fail | N/A | Score | Weight | Weighted |
|---|-----------|------|------|-----|-------|--------|----------|
| 1 | {dimension} | 4 | 2 | 0 | 67% | 15% | 10.0% |
```

- Score = `pass / (pass + fail)` — N/A excluded from the denominator.
- Weighted = Score × Weight. Overall = sum of the Weighted column.

## Grade Thresholds

| Grade | Score Range |
|-------|------------|
| A | ≥ 90% |
| B | ≥ 80% |
| C | ≥ 65% |
| D | ≥ 50% |
| F | < 50% |

Report-local labels here (`BLOCKING`, grades, priorities) MUST NOT leak into `<ramo>` tags or
`verdict:` fields — see `common/output-contract.md`.
