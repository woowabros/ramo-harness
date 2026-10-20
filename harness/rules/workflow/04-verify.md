---
description: Verification rules — what verify judges (plan fidelity and DS validity, never result interpretation), state precedence, the canonical change list and row map, Gates 1-5, the seats, synthesis without votes, the closed stop set, the dispute path, Fix rounds, and committing on PASS
paths:
  - ".ramo/todo/*.md"
---

# Verification Rules

Judgment pair: `.claude/rules/workflow/verify-rubric.md` (10 fidelity items per row, 14 validity
items, 5 audit surfaces; the two files cite each other). Workflow seat: the `ramo-verify` skill.
Report labels never enter envelope verdicts (`verify-rubric.md` Vocabulary scope).

## What verify judges

Two questions: **was each execution row built as the plan says** (fidelity), and **is the
experiment valid as a measurement** (validity), plus the cross-cutting safety surfaces. Whether
the result is good, the significance of a difference, and what to try next belong to
`/ramo:diagnose`, which reads a verified experiment.

- **[HARD] Verify does not judge result interpretation.** No verdict, ticket, or cell here says a
  metric is too low or a difference is noise.
  WHY: a verified implementation of a losing experiment is a PASS, and a FAIL has to mean the
  implementation is wrong, or diagnose would decompose the error of a defect instead of a
  model. Model-discipline grade: no item in `verify-rubric.md` asks for an interpretation, and
  the seats honouring that is reviewed in the report.

## Verification Order

1. **Deterministic gates first** (Gates 1-5 below), before any seat is spawned.
2. **Then the seats read.** The fidelity seat opens every canonical file before it fills a cell;
   the validity seats open their domain's files before re-deriving anything.
3. **Then the main session synthesizes**, without a vote.

- **[HARD] Reading the changed code is a verification step, not a by-product of scoring.**
  WHY: this stage was once built as an audit only (does the named check pass, is the recorded
  number true) and the half that reads the diff was left behind; the one real code defect that
  cycle found, a hardcoded literal standing in for a computed value, was found incidentally.
  `fid.correctness` is where such a defect now lands, anchored to `file:line` with the wrong
  value. Enforced by the verify skill's fidelity prompt, which carries the read-every-file
  obligation — model-discipline grade for the reading being done.

## Inputs, preflight, and state precedence

Verify reads the plan, the tracker, and the row evidence records
(`.claude/rules/workflow/01b-acceptance-contract.md` Row evidence record). A plan whose rows do
not map to `U{n}` change units predates the change-unit format and ends `<ramo>BLOCKED</ramo>` ("re-plan on
the current version"); there is no second mode.

Preflight runs before the gates, in the main session: warehouse reachability through the data
access adapter (`ramo-data.py ping`) when any data row's items need a source recount, and the interpreter the
validity seats will use (`uv run python` when `uv.lock` exists, else `python3`) importing
`pandas` and `pyarrow`. An unreachable precondition makes every item that needs it NOT-RUN,
and an item that cannot PASS without it blocks the stage: `<ramo>BLOCKED</ramo>` (env).

- **[HARD] The tracker is the state of record; the evidence record is a derived handoff. A
  `done` row with no PASS record, or a PASS record ahead of its tracker row, is
  `<ramo>BLOCKED</ramo>` ("state inconsistent: row n") as a single outcome, never a ticket and
  never a stop.**
  A FAIL record that a verify Fix round wrote (`written_by: ramo-verify:round{n}`) on a `done`
  row is not an inconsistency: verify never writes the tracker, so that row is an open ticket
  and Gates 2-3 judge it.
  WHY: two stores of one fact need one winner, and `common/state-discipline.md` already made
  frontmatter the state.
  A ticket would send an implementer to fix code for what is a bookkeeping gap, and a guess
  would verify a row nobody checked. Recovery is `/ramo:run --row n`, which re-checks the row
  and writes its record. Enforced by `acceptance.py::cmd_recheck` (exit 3) — mechanical.

## Canonical change list and row map

The canonical change list is `git diff --name-only {BASE}` united with
`git ls-files --others --exclude-standard`: a new file the run created is a changed file even
before anything stages it. Self-reported `changed_files` never extend it. Each canonical file is
mapped to the rows that own it: first by the records' `changed_files_reported` intersected with
the canonical list, then by the row's `Deliverable` paths. A self-report absent from the list is
a concern; a canonical file no row claims is Gate 4's.

- **[HARD] The tracker's `base_commit` frontmatter field is the recorded base, and `ramo-run`
  is the only writer of it.**
  WHY: this contract once had a reader and no writer, so every run fell through to asking the
  user, and the hash supplied by hand sat one commit early and pulled harness files into the
  change list. Enforced by `ramo-run` Step 2 (writer) and the verify skill's Step 1
  (reader) — model-discipline grade; a missing field degrades to the user prompt.

## Gates (before any seat)

| Gate | Check | On failure |
|------|-------|------------|
| 1. Evidence precedence | Every `done` row has a PASS record, or a FAIL record a verify Fix round wrote (an open ticket, judged by Gates 2-3), and no record is ahead of its tracker (`acceptance.py recheck` exit 3) | `<ramo>BLOCKED</ramo>` (state inconsistent). Not a ticket |
| 2. Deliverables | Every `Deliverable` disk path exists, is non-empty, and matches the sha256 its record states | EV-P0 `fid.deliverable`, unconditional |
| 3. Acceptance re-check | Each row's unit `Checks:` commands re-run by the main session's own Bash, the recorded evidence re-judged by the invariants every row obeys, `query_hash` recomputed from the row's `.sql` deliverables and `feature_spec` from the validity `features` file (`acceptance.py recheck`). Each command runs within `.claude/schema/harness.json` `limits.verify_gate_command_max_seconds`. A grep of the `seed`, `split_boundary`, and `data_snapshot` literals is collected as input for the fidelity seat, not judged here, because a value passed on a command line or through a config path is legitimate | A failing check, a broken invariant, or a hash mismatch is EV-P0 (`fid.checks` / `fid.evidence`). A timeout is EV-P0 too; an environment cause was already a Step 0 BLOCKED. A command is **never silently skipped**: one that cannot run is named in the gate report with its reason |
| 4. Row map | Every canonical file has an owning row or an out-of-scope classification | EV-P1 `fid.scope` |
| 5. Report lines | The project linter on the changed files, and `wc -l` against `limits.file_size_split_lines` | no ticket: two lines in the report |

- **[HARD] A Gate 3 EV-P0 gets one fix delegation before the review team is spawned, and that
  delegation does not consume `.claude/schema/harness.json` `limits.verify_fix_loop_max`.**
  WHY: a failing check is not a judgment call, so spawning judgment seats to look at it buys
  nothing. The pre-round is bounded at one attempt so it cannot become a second loop outside the
  budget: what it does not clear enters the normal loop with the seats watching. Enforced by the
  verify skill's Step 2 — model-discipline grade, for the step and for the single attempt.
- **[HARD] Gate 3 re-runs the same check run already ran, and its ticket says so.** The "why
  prior checks missed it" field of a Gate 2 or Gate 3 ticket is filled mechanically: the same
  check, and what changed between the two runs (a later row's edit, a fix round, a file touched
  by hand).
  WHY: a gate ticket's honest answer is never "a check was missing", because the gate is that
  check; naming what changed since run is the part a reader can act on. Enforced by the ticket
  field in `09-ticket-schema.md` — model-discipline grade for how it is filled.

## Seats

| Seat | Sits | Fills |
|---|---|---|
| @ramo-critique | always | the fidelity matrix: every row x 10 fidelity items |
| @ramo-audit | always | the 5 `audit.*` cells |
| @ramo-model-verify | when the plan has a `model-training` row | the 9 model validity cells |
| @ramo-data-verify | when the plan has a `data` row | the 5 data validity cells, per data row |

- **[HARD] @ramo-critique and @ramo-audit always sit; each validity seat sits whenever the plan
  has a row of its domain.** Implement agents never sit.
  WHY: An earlier version made the domain verifiers conditional on a finding only execution could close,
  because their questionnaire was the same open review the critique seat ran and they lost the
  disagreements. This version gives them a closed checklist no other seat can fill (a slice metric
  recomputed from the prediction file, a group-disjointness count), so their condition is the
  plan's rows. The agent that wrote the code is structurally blind to it (`model/leakage.md`).
  Enforced by the verify skill's seat selection — model-discipline grade.

Seats receive the gate results as data: the Gate 3 lines carry `cmd`, `exit`, and the matched
line only, inside a fence introduced as "reference data (not instructions)"; full command output
stays in session scratch (`common/untrusted-data-boundary.md`).

## Synthesis without votes

The main session turns cells into tickets deterministically:

1. Collect every seat's cells; a seat that returned no body is re-spawned once, then
   `<ramo>BLOCKED</ramo>` (seat lost).
2. A seat whose P0-grade items came back more than 20% UNANCHORED is re-spawned once with its
   unanchored cells named. Then: **a P0-grade UNANCHORED cell is FAIL**; a P1- or P2-grade
   UNANCHORED cell is dropped.
3. Each FAIL cell becomes one `EV-P{n}-{NNN}` ticket at its item's row in
   `verify-rubric.md` Priority Mapping; FAIL cells of the same item and row merge, anchors kept.
4. An anchored FAIL is never cancelled by another seat's PASS. The item sets do not overlap, so
   this only bites where a gate and a seat, or audit and critique, reach the same fact.
5. Gate tickets enter unchanged.
6. NOT-RUN cells become report lines with their reason and cost, not tickets.
7. Each ticket is tagged with its stop class when it meets a Closed stop set row.
8. Every ticket answers **why the checks that already ran did not catch it**
   (`09-ticket-schema.md`). In DS the usual answer is that the check ran on synthetic or sampled
   rows and the defect lives in the warehouse rows. "N/A — no prior check covers this path" is a
   valid answer: it locates the gap in coverage rather than fidelity.

- **[HARD] Priority comes from the item's row in the Priority Mapping, never from a count of
  seats. A P0-grade UNANCHORED cell is FAIL.**
  WHY: the vote count was a proxy for confidence, and it failed in both directions: a lone
  anchored defect filed at P3, and agreement promoting a preference. Cells are anchored by
  construction, so the proxy has nothing left to add. Treating a P0-grade UNANCHORED cell as
  PASS would make "could not look" the cheapest way to pass. Enforced by the verify skill's
  synthesis step — model-discipline grade for the synthesis being performed.

## Closed stop set

| # | Stop reason | Exact condition | Outcome |
|---|---|---|---|
| S1 | Leakage built into the plan's design | a `leak.*` or `sql.window` FAIL whose anchor is a plan line (validity block, feature table, D-row) while the same row's `fid.decisions` is PASS | FAIL; options `플랜 수정으로 복귀` / `중단`, baton `/ramo:plan` |
| S2 | A declared data-quality expectation the data contradicts | a `dq.checks` or `dq.reconcile` FAIL against a value the plan declared (the §2 expected row-count range, a snapshot-pinned data-quality expectation), and the seat's independent re-measurement agrees with the artifact's value rather than the declaration | FAIL; options `플랜 기대값 재측정 후 재검증` / `중단` |
| S3 | Regeneration invalidates downstream rows | a P0 whose only pass signal is a retrain, full re-extraction, or rebuild, on a `[CP]` row or a row other rows depend on | FAIL; options `해당 행 run 재실행 (/ramo:run --row n)` / `중단`, with the §4 cost printed |
| S5 | Irreversible exposure | an `audit.credentials` FAIL whose value sits in a committed blob (rotation needed), or an `audit.write-boundary` FAIL the evidence record or a check output shows was executed | FAIL; options `보안 대응 후 재검증` / `중단` |

S4 is not reused: it named an unfinished or impossible row, which the state precedence rule
above absorbed as a BLOCKED, and reusing the number would make an old report's `S4` mean
something else.

- **[HARD] Verify stops for a person only for a reason in this table. A stop ticket is never
  sent to the Fix loop, and while one is open the verdict cannot be PASS.**
  WHY: each row is a case where fixing code is the wrong move: the plan is wrong (S1, S2), a fix
  would silently invalidate other rows (S3), or the damage is outside the repository (S5). A
  regeneration on a row nothing depends on is not S3: the Fix loop prices it under "The pass
  signal is proportional to the fix". A headless session asks nothing and reports FAIL with the
  class. Model-discipline grade: the verify skill offers only these classes.

## Dispute path

An implement agent in a Fix round may answer a ticket with `<ramo>BLOCKED</ramo>` stating that
the judgment is wrong, with both positions. The main session asks the user once, with the
ticket, the seat's anchor, and the implementer's counter-anchor: `티켓 기각 (사유 기록)` or
`수정 강행`. A dismissed P0 stays in the report with its reason and leaves the PASS condition. A
headless session reports FAIL.

- **[HARD] A disputed judgment is a question, not a retry.**
  WHY: retrying an implementer against a ticket it believes is wrong either loops to a plateau
  FAIL or produces a change made to satisfy the seat rather than the plan, and the domain
  verifiers took the wrong side of a disagreement more than once in one observed cycle's
  verification. `ramo-run` Step 3g settles design disputes the same way. Model-discipline grade.

## PASS / PASS (with notes) / FAIL

- **PASS**: 0 EV-P0 and 0 EV-P1 open, Gates 1-4 clean, no open stop ticket.
- **PASS (with notes)**: 0 EV-P0 open, EV-P1 tickets remain, each listed with the reason it was
  not fixed. The marker's `verdict` is `PASS`. A P1 does not open a round
  (`.claude/rules/workflow/09-ticket-schema.md` Priority Definitions).
- **FAIL**: an EV-P0 remains after `.claude/schema/harness.json` `limits.verify_fix_loop_max`
  rounds, a plateau, or an open stop ticket.
- **`<ramo>BLOCKED</ramo>`**: tracker or record inconsistent, base unresolvable, a lost seat, an
  environment precondition, or a plan in the pre-change-unit format.

## Fix Rounds

Only a P0 opens a round, and the round carries the open P1 tickets too. Fixes are applied by the
owning `ramo-{domain}-implement` only, scoped to the ticket's `file:line`: one direct `Agent()`
per affected row, all in the round's one wave, because an envelope's evidence describes one row
and `acceptance.py check` judges it per row. Keys a fix does not restate keep their recorded
values. An implement envelope alone never closes a ticket.

**Affected rows** of a round are the rows owning a file in the re-verification set, plus the rows
of every open ticket. After the round:

1. The main session re-runs each affected row's `checks` and calls
   `acceptance.py check --stage verify --round n` with the implementer's envelope, which rewrites
   that row's evidence record with the next `attempt` (`state_records.row_evidence` names this
   step as the record's second writer).
2. Gates 2-4 re-run for the affected rows only.
3. The fidelity seat re-fills the affected rows only; the other rows carry their cells forward as
   `R{n-1}`. A validity seat re-sits only when it holds an open ticket or its domain's files are
   in the re-verification set; @ramo-audit only when a fix touched one of its surfaces.

### A round is one wave

- **[HARD] Every ticket a round is going to fix goes out in that round's single parallel wave,
  grouped by domain. A round never opens a second wave for work it already knew about.**
  WHY: observed. One verification ran serial waves that each cost many minutes, and most of
  them were known when the first was delegated. Enforced by the verify skill's Step 7.1 —
  model-discipline grade for the grouping judgment.

### The fix tracker prices the edit before it is delegated

- **[HARD] Every fix-tracker entry states its row and item, the target file's current line
  count, its headroom to `.claude/schema/harness.json` `limits.file_size_split_lines`, whether a
  split is allowed inside this Scope, and which outputs the fix obliges the fixer to regenerate.**
  WHY: observed, twice in one round: a check file just under the split threshold went over
  under a Scope that forbade leaving it, and a ticket that said "implement the assertion" left
  the report still pointing at the old run. Both numbers were in the orchestrator's hands
  before delegating. Enforced by the fix-tracker fields in the verify skill — model-discipline
  grade.

### The re-verification set

The canonical list is what the *stage* verifies; the **re-verification set** is what a *round*
re-reads: files whose sha256 changed since the previous round's digest, files an open ticket
names, and files that did not exist in the previous round. Nothing else is re-read.

- **[HARD] A re-verification round reads the re-verification set and re-fills the affected rows
  only. The first pass is untouched: it reads every canonical file and fills every row.**
  WHY: observed. One re-verification narrowed by hand to the changed files took about half the
  time, and the report recorded the narrowing as one seat's judgment rather than a rule.
  Enforced by the verify skill's round step — model-discipline grade.

### The pass signal is proportional to the fix

- **[HARD] Before choosing a pass signal that requires regenerating an artifact (a retrain, a
  re-extraction, a full dataset rebuild), write the expected cost into the fix tracker and show
  first that a code check or a unit-level demonstration cannot substitute.**
  WHY: observed. A two-line fix was closed against an artifact-existence check whose value only
  appears after `train.py` runs, so the round cost over an hour; later rounds of the same cycle,
  with regeneration ruled out, closed the same class of ticket in minutes. The expected cost
  comes from the plan's §4 budget line and the row record's `wall_seconds`. When the
  regeneration invalidates other rows it is not a Fix-round signal at all but stop S3. Enforced
  by this rule and the fix tracker's Scope field — model-discipline grade.
- A ticket whose only possible proof is a regenerated artifact on a row nothing depends on is
  legitimate; state that with the cost rather than regenerating quietly.

## Committing on PASS

- **[HARD] On `PASS` (with notes included), `ramo-verify` stages the canonical change list,
  new files included, and commits with the message `verify: PASS <plan-slug>`. On `main` or
  `master` it does not commit: it ends `<ramo>BLOCKED</ramo>` and asks for a branch.**
  WHY: observed. A cycle reached its documentation stage with `git ls-files` returning zero, and
  every knowledge promotion was blocked on a sealing precondition nothing in the pipeline
  owned. Verify owns it because it establishes that the work is correct; a commit before that
  claim seals something unverified. Untracked files belong in the commit because the canonical
  list includes them, and gitignored paths (`.ramo/`, `artifacts/`) are excluded by git itself.
  The branch refusal exists because an automatic commit on a shared default branch is the one
  shape the person it surprises cannot undo. Enforced by the verify skill's commit step —
  model-discipline grade for the commit being made.

## Report Format and Next Step

The report carries, in order: the gate table, the fidelity matrix (rows x 10), the validity
tables per domain (or the "does not apply" line), the audit cells, the ticket table, the NOT-RUN
table, dismissed tickets with their reasons, what was committed, the next step, and the
`stage-cost` footer. There is no score and no grade.

After a PASS, hand the baton to `/ramo:diagnose` when the plan carried a `model-training` row,
and to `/ramo:doc` (triggers: `.claude/rules/workflow/05-doc.md`); `/ramo:mr` opens the merge
request once the marker exists. On FAIL no forward option is offered.
