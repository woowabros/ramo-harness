---
description: Documentation workflow gate — DS triggers, required evidence, and the mandatory skip-decision record after verify and before wrap-up.
paths:
  - "docs/**/*.md"
  - ".ramo/plans/**"
---

# Documentation Workflow Rules

`ramo:doc` runs after `ramo:verify` passes and before the work is wrapped up
(the wrap-up boundary is marking the plan `done`).

Canonical flow:

```text
03-run -> 04-verify -> (diagnose) -> 05-doc -> plan status: done
```

The diagnose stage sits between them and is **conditional on a `model-training` row**: it
decomposes the experiment's error and ranks the next experiment's candidates
(`.claude/skills/ramo-diagnose/SKILL.md`). When it ran, its output is the source for the model
card's `다음 시도 후보` section and for a `docs/analysis/` diagnosis document
(`.claude/skills/ramo-doc/rules/template-diagnosis.md`) — restated in the body, never cited by
its `.ramo/` path (SOT-1).

Do not mark a plan `done` before required documentation is complete or the skip
decision is recorded (see below).

## When To Run `ramo:doc` (DS triggers)

Run `ramo:doc` after verify passes when any of these changed:

1. **Dataset extraction or snapshot** — a new extraction query, snapshot policy, or
   partition scheme worth re-obtaining later (`docs/data/`).
2. **Feature definitions** — new or changed feature logic, leakage-relevant boundaries, or
   computation windows (`docs/feature/`). **A feature verdict fires this trigger even when the
   verdict was to exclude**: which columns were rejected and why is the part a later experiment
   most needs and least able to re-derive. This trigger did not fire in an early cycle while the
   feature decisions were being made, and `docs/feature/` was written later on request.
3. **Model training or evaluation** — a trained model, changed evaluation
   (metric/slice), or champion change → model card (`docs/model/`).
4. **Experiment conclusion** — an experiment produced a durable decision or lesson that
   future sessions must not re-derive (`docs/analysis/`; route the decision itself per
   **Decision Routing** below). **A completed diagnosis fires this trigger**: its slice
   decomposition and ranked candidates are exactly what the next cycle must not re-derive, and
   `.ramo/diagnoses/` is volatile.
   - **[HARD] This trigger owes two outputs, not one: the analysis document AND one row in
     `docs/experiments.md`** (`.claude/skills/ramo-doc/rules/template-experiment-ledger.md`).
     One plan is one row, carrying date, `parent`, `change`, `objective`, the result, the first
     ranked next candidate, and the document the conclusion lives in.
     WHY: nothing else in the harness holds the sequence of experiments. `.ramo/diagnoses/` is
     volatile, a model card covers one model, an analysis document covers one question — so the
     fact a reader wants most often, what has been tried and what happened, had no home. The
     externally-measured version of this is probabl's numbered `JOURNAL.md` History plus its
     backlog, and TDSP's Model Report Next Steps section; both exist because the per-experiment
     document does not answer the across-experiment question. A negative result gets a row too,
     and it is the most valuable row in the table because it is the one a later session is most
     likely to re-run. Enforced by `.claude/skills/ramo-doc/SKILL.md` Step 6's six-row trigger
     walk (which cannot be completed without naming this row) — model-discipline grade, no
     mechanical check.
5. **Pipeline or serving interface** — batch schedule, deployment, or serving contract
   change (`docs/pipeline/`).
6. **Architecture decision or cross-cutting convention** — anything a future maintainer
   needs to understand (`docs/architecture/` for the current shape, `docs/common-rules/`
   for a convention, `docs/architecture/adr/` for the decision itself — **Decision
   Routing** below is the test, not the reader's judgement).

Skip `ramo:doc` only when the change is purely internal AND no existing document
becomes stale.

## Decision Routing (ADR vs category doc)

Every trigger above can fire on the same piece of work, so the question is not *whether* to
document but *where the decision goes*. The test comes from `common/sot-authoring.md` SOT-3:
a category document is **hard-deleted and rewritten** when the fact it states changes, and
soft deprecation is allowed for exactly three document classes — ADRs, versioned external API
contracts, and CHANGELOG. So:

**If the decision's history must survive the next update, it is an ADR. If only the current
state matters, it is a category document.**

Four signals, any one of which makes it an ADR:

| Signal | Why the category doc cannot hold it |
|--------|-------------------------------------|
| The decision **reverses** an earlier one | A category doc states the current state only; "what changed and why" has no place to live and is deleted with the old text |
| An **alternative was rejected** | The rejected option is not a current fact, so SOT-3 deletes it — and the next person re-proposes it |
| The next person **must not re-derive it** | Re-deriving is exactly what happens once the reasoning is gone and only the conclusion remains |
| Removing it would leave a **rule with no reason** | A constraint whose WHY was deleted reads as arbitrary and gets dropped at the first inconvenience |

Everything else — how the thing currently works, what a column means, which partition to read
— is a category document, and staying out of `adr/` keeps that directory readable.

- **[HARD] A decision matching any signal above is written as an ADR in the same doc step,
  and a decision judged not to need one is recorded as a judgement with its reason.**
  WHY: the failure this prevents is not a missing document but a missing *judgement*. In
  an early cycle, several experiment decisions were spread across category documents — a defensible
  choice — while nothing recorded that the choice had been made, so the next update would have
  deleted the reasoning under SOT-3 with no trace that anything was lost. Some of them met a
  signal above (a reversal, a rejected alternative). Enforced by the Required Evidence
  item below and this rule — **model-discipline grade, no mechanical check**: no gate can read
  a decision's history requirement off a diff.

### Where the judgement is recorded

Two places, because neither alone is enough.

1. **The doc step's report** (Required Evidence item 6 below). This is the seat that matters:
   the original failure was noticed by a person reading a report that never mentioned ADRs.
2. **One line per decision in `.ramo/context/doc-decisions.md`**, same shape as the skip record:

```markdown
- 2026-08-21 | plan: 2026-08-19-trip-duration-prediction | decision: airport trips
  excluded then reinstated | -> adr/002 | signal: reverses an earlier decision
- 2026-08-21 | plan: 2026-08-19-trip-duration-prediction | decision: workspace schema
  for intermediates | -> docs/architecture/warehouse-access.md | signal: none (current state only)
```

`.ramo/context/` is volatile and banned as SoT evidence (SOT-1), so this line is a run-time
audit trail, not documentation. **The no-ADR branch has no durable home yet** — writing
"this needed no ADR" into the category document puts it in the text SOT-3 deletes. Stating the
gap is the honest position; the wiki layer is where a recurrence-prevention record gets one.

Write an ADR at decision time. When writing one **retroactively** — the decision was already
made and shipped — date `created` to the decision's own date, not today's, state in Context
that the record was written after the fact, and cite the artifacts the decision actually left
behind. A retroactive ADR with today's date claims a history it does not have.

**Two properties belong in the wiki, not a category document or an ADR**: a
*recurrence-prevention contract* and a *constraint to be obeyed* are neither current-state
facts nor decision records — a category document would lose the contract to SOT-3's next
hard-delete, and an ADR records that a decision was made, not that a future session must
obey something. They land in `wiki/lessons/` and `wiki/constraints/` via the `ramo-wiki`
skill (`.claude/skills/ramo-wiki/SKILL.md`) — see **Promotion Triggers** below for when
that skill fires. The wiki's own run-feedback injection (surfacing a lesson automatically
during a later `run`) is deferred to a later version; landing in the wiki now only guarantees the fact can be
found later, not that it will be surfaced unprompted.

## Promotion Triggers (wiki)

Fire `ramo-wiki` (do not draft the candidate yourself) when any of these happen during
this plan's run/verify cycle, in addition to the category-document/ADR triggers above:

1. **A `verify` FAIL traces to a repeatable failure class** — the same defect shape would
   recur on the next plan, not just this one. → lesson (`failed_approach` feature if the
   FAIL was a rejected implementation approach, not just a bug).
2. **A domain fact took symptom-to-interpretation work to establish** — `run` needed more
   than one round to go from "what broke" to "why", and that interpretation is not yet
   written anywhere durable. → lesson (`module_gotcha` or `cross_cutting` feature,
   whichever the fact's scope matches).
3. **An approach was tried and rejected** before the plan settled on its actual design —
   the rejection reasoning itself, not just the final choice. → lesson with the
   `failed_approach` feature, distinct from the Decision Routing "alternative was
   rejected" signal above (that one is about a *decision already recorded elsewhere*
   needing an ADR; this one is about the *rejected attempt itself* being worth recording
   so nobody retries it).

A trigger firing produces a promotion candidate, not an automatic publish — `ramo-wiki`'s
own transaction gate (deterministic validation + semantic review) decides whether it
actually reaches `wiki/`. A candidate that fails validation twice and aborts is not a
documentation failure; report it as such in Required Evidence item 7.

### The candidate is recorded when the trigger fires, not when doc runs

- **[HARD] `ramo-run` and `ramo-verify` append one line to
  `.ramo/context/promotion-candidates.md` at the moment a trigger fires. The doc stage consumes
  that file rather than reconstructing the cycle from memory.**

```markdown
- 2026-08-26 | stage: run | trigger: 2 (symptom-to-interpretation) | fact: tlc.yellow_trips 가 CTE
  참조마다 재인라인돼 여러 번 스캔됨 | evidence: sql/trip_base_1.sql, sql/trip_base_2.sql
```

  WHY: all three triggers describe things that happen during run or verify — a repeatable FAIL
  class, a domain fact that took more than one round to interpret, an approach tried and
  rejected. Recording them at the doc stage puts the whole cycle between the event and its
  record, and the observed result was that a CTE re-inlining trap discovered by hand in the
  query plan (`explain`) — a warehouse fact worth more than the experiment that found it — was
  marked as a promotion candidate in one round's notes and never reached the doc stage's
  four-item registry. Nothing carried it. Enforced by `ramo-run` Step 5 and `ramo-verify`
  Step 8 (each writes its own lines) and by `ramo-doc` Step 3.0b (which reads the file) —
  model-discipline grade, no mechanical check.
- The `evidence:` field is load-bearing twice: it is what makes the fact checkable later, and it
  is the source set `ramo-wiki` seals at `stage`. A line with no committed path means the
  evidence never became durable, which the doc stage reports rather than papering over.
- **[HARD] `evidence:` is only a sealable set when its paths are git-tracked, and the doc stage
  checks that with `git ls-files` before calling `ramo-wiki`.** An untracked path is a question
  for the caller (commit it, or drop this candidate with a reason), never a transaction to open
  and lose.
  WHY: observed. Every promotion candidate of one cycle failed at the same place. The
  sealing function rejects anything outside `git ls-files`, and no stage owns the commit:
  `run` and `verify` do not commit their outputs, and `ramo-doc-writer`'s write scope is
  `docs/` with no commit authority. A person committed by hand, which is the proof the
  precondition was real and unowned. **Commit ownership is now assigned:** `ramo-verify`
  commits the canonical change list on `PASS`
  (`.claude/rules/workflow/04-verify.md` Committing on PASS), so by the time the doc stage runs
  the cycle's outputs are tracked. This rule's own job did not change — it makes an unmet
  precondition visible one command earlier, which turns a run of identical failures into
  one question — but the ordinary case is no longer a failure at all. Enforced by
  `.claude/skills/ramo-doc/SKILL.md` Step 3.0b and `.claude/skills/ramo-wiki/SKILL.md` Step 0,
  with `wiki_runtime.py::seal_sources` as the mechanical backstop — model-discipline grade for
  the check happening early.
- **Mark an ignored evidence path at the moment the candidate is recorded**, by running
  `git check-ignore` over the paths before writing the line. A verify commit fixes the *timing*
  problem (nothing was committed yet) and does nothing about the *scope* one: candidates in that
  cycle cited `experiments/*/data/*.parquet` and `experiments/*/artifacts/*`, both
  gitignored, so no commit at any time would ever seal them. That class needs a different repair
  — promote the recomputation code instead, or state the fact inline as a dated first-party
  assertion (`common/sot-authoring.md` SOT-1a) — and the choice is cheapest to make while the
  evidence is still in front of the person recording it, not one stage later where the only
  remaining move is to drop the candidate.
- `.ramo/context/` is volatile working state and is never cited as evidence in `docs/`
  (SOT-1) — the line is a hand-off, not a citation.

## Skip-Decision Record (mandatory)

A skip is a decision, not an omission. When documentation is skipped, append one line to
`.ramo/context/doc-skips.md`:

```markdown
- 2026-08-20 | plan: 2026-08-20-churn-experiment | skipped: internal refactor of
  feature pipeline tests; no doc becomes stale
```

Enforcement is model-discipline grade with one check: the verify→doc baton in `ramo-verify`
asks for the record when doc is skipped. Nothing mechanically verifies that the line was
written. `.ramo/context/` is volatile working state — never cite it as
evidence in `docs/` (SOT-1); the record exists for run-time audit, not documentation.

## Required Evidence

The documentation step must report all seven:

1. Documentation files created, updated, or intentionally left unchanged.
2. Source files or plan items that drove each documentation update.
3. Any stale documentation found and how it was resolved (or flagged).
4. The skip record location, when documentation was skipped.
5. Any documentation blockers that should stop the plan from being marked `done`.
6. **The decision-routing judgement**: every decision this work produced, the destination
   chosen (`adr/` or a named category document), and which signal decided it — including the
   decisions judged not to need an ADR. An empty list is a valid report only when the work
   produced no decision at all; say that explicitly rather than omitting the item.
7. **Every Promotion Trigger outcome**: which trigger fired, whether `ramo-wiki` committed
   the candidate or aborted it, and the resulting path or abort reason. An empty list is
   valid only when no trigger fired at all; say that explicitly.

## Scope

`ramo:doc` owns living documentation under `docs/` (categories:
`.claude/skills/ramo-doc/rules/foundation-category-structure.md`). Use it to create or
update dataset docs, model cards, analysis conclusions, feature specs, pipeline
runbooks, ADRs, `docs/index.md`, `docs/GLOSSARY.md`, and cross-references; and to
verify examples, commands, paths, and frontmatter are current.

The wiki layer (`wiki/lessons/`, `wiki/constraints/`, `wiki/notes/`) is a separate tree
`ramo:doc` does not own or index — Promotion Triggers above hand a candidate to `ramo-wiki`
instead of drafting it here. Its run feedback loop (surfacing a wiki document automatically
during a later `run`) is deferred to a later version.
