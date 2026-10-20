---
description: DS experiment plan structure written for the person — fixed §0-§5 top half (purpose, decisions, data, features, model, evaluation) and adaptive §6-§8 bottom half (change units, execution and verification, risks). The machine handoff is 01a-execution-structure.md; this is the spec side of the spec-rubric pair
paths:
  - ".ramo/plans/*.md"
---

# Plan Writing Rules

An implementation plan is an executable change map: what behavior changes, where it changes,
the target shape, and how to prove it works — for DS work this includes what data is read,
how it is snapshotted, and how the result is reproduced. It is not a requirements report.

**A plan has two readers and they need different things.** A person decides whether the approach
is right, which needs the relationships visible: what depends on what, what this fixes for later
rows, what was rejected. `ramo-run` executes it in a new session with empty context, which needs
the Execution Structure table parseable. That table and its contract are the machine-readable
handoff and live in `.claude/rules/workflow/01a-execution-structure.md`; this file holds the rest,
which is written for the person.

Getting this backwards produces a plan that parses and cannot be read. Density means removing what
does not change an execution decision, never removing what makes the structure visible.

This file is one half of a pair. The scoring half is
`.claude/rules/workflow/plan-rubric.md`; every mandatory requirement below names its rubric
item IDs in the Spec-Rubric Map, and the two files cite each other (model discipline; a change
to one is reviewed against the other).

## File Naming and Frontmatter

```text
.ramo/plans/YYYY-MM-DD-kebab-case-slug.md
```

- Creation date + short English kebab-case slug. Plan prose follows
  `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`); paths, symbols, commands, agent names, and
  `Skill()` calls stay in English.
- Frontmatter contract (`.claude/schema/harness.json` `doc_frontmatter.ramo_plan`, OKF v0.2):
  `type: plan`, `status: draft|active|done|superseded`, `created`, `updated`, `ticket`,
  `generated: {by, at}` (e.g. `by: ramo-plan-writer/claude` , ISO-8601 `at`).
- Iteration axis (optional fields, same schema key `optional`): `parent` is the previous plan's
  file name or the literal `null`, `change` is the one atomic difference from the parent, and
  `objective` is the metric name plus the parent's value on it. Write `parent: null` explicitly
  for a first experiment -- an omitted field and a declared root are different facts, and only
  the second one says the question was asked. Scored by `plan-rubric.md` `intent.parent`.

## Core Quality Contract

Every non-trivial plan MUST satisfy all four qualities:

1. **Location** — name the exact existing `file:line` or `file::symbol` anchoring each change.
   For data work, name the exact source tables/partitions verified through the data access
   adapter (`.claude/rules/data/warehouse-access.md`). For a new file, name its target path and symbol.
2. **Change shape** — show what will be added, removed, or rewritten. Use a short excerpt,
   target pseudocode, signature, or schema when prose alone permits materially different
   implementations.
3. **Proof** — name exact test/check files, cases, commands, and observable pass conditions.
4. **Density** — keep only information that changes implementation or review decisions. A §6
   change unit cites §0-§5 rather than restating them.

Never invent a line number, symbol, table, row count, or current behavior. Use
`TBD (blocked: reason)` only when evidence cannot be discovered; high-impact TBDs block approval.

## Required Plan Shape

**§0-§5 are fixed and appear in that order with those numbers. §6-§8 are adaptive** — the
information is mandatory, the headings and grouping are yours.

WHY the top half is fixed: a plan has to be read before it is executed, and a reader who does not
know where the target distribution or the feature verdict lives has to search the whole document
for it. An earlier cycle put the business purpose in prose under the title, the target's p50/p95/p99
inside a change unit, and the two-stage model decision in a `D`-row hundreds of lines down; the reviewer's objection was never length, it was that the same fact sat in a different
place in every plan. The bottom half stays adaptive because change units differ in shape and a
fixed skeleton there produces empty sections. Skeleton and per-section table headers:
`.claude/skills/ramo-plan/templates/plan.md`.

### 0. Purpose and Problem

`# Plan: {specific outcome}`, then five things, in this order:

1. **Business purpose** — one paragraph: who consumes the result, which decision it changes, and
   what happens today without it. Not the method, not the metric.
2. **Prediction target and anchor** — what is predicted, and the moment past which a value is no
   longer available to the model (`.claude/rules/data/eda.md`).
3. **Target distribution** — a measured table: quantiles, tail, null rate, and the sample the
   numbers were taken on. Carry it over from the eda stage rather than restating a guess.
4. **Baseline** — the number this experiment must beat, and where it came from.
5. **Goal metric and decision condition** — one metric name, and what value on which slices
   decides the experiment succeeded. The full slice list belongs to §5.

- **[HARD] The target distribution is measured, never described.** A plan that says the target
  is skewed without quantiles has not looked at it.
  WHY: a large share of an observed cycle's label was null and the nulls were not random, which changed the
  loss, the split, and the population — and it was discovered during execution because no
  section had asked for the distribution up front. Scored by `plan-rubric.md`
  `problem.target-shape`; no mechanical check can tell a measured quantile from an invented one,
  so this is model-discipline grade with the sample citation as its trace.

### 1. Governing Decisions

The settled-decisions table, then a compact metadata table only for decision-relevant facts
(ticket, data window, rollout boundary).

```markdown
## 선결 결정 (구현 전 확정, 재논의 대상 아님)

| ID | 결정 | 근거 | 확정 범위 |
|----|------|------|-----------|
| D1 | {the decision, stated as a fact} | {evidence or the user's answer} | {which change units it binds} |
```

- **[HARD] Every design question this plan has answered gets a `D`-row, and the table is
  labelled closed to renegotiation.**
  WHY: this table is what makes execution cheap. A plan that fixed its decisions here had its
  run stage cross every task with almost no back-and-forth; one that left them open had every
  task re-open them, and the redesign budget was spent in full on two tasks. Enforced by `.claude/skills/ramo-run/SKILL.md` (reads it for the `[CP]`
  briefing; BLOCKs a task no `D`-row answers) and scored by `plan-rubric.md`
  `intent.decisions`.
- A decision belongs here when a later row would otherwise have to make it: prediction anchor,
  label definition, split boundary, exclusion predicate, model family, snapshot boundary,
  write target.
- State a decision, never a goal. `D3 | 라벨은 tpep_pickup_datetime 기준` is a decision;
  "라벨 정의를 명확히 한다" is not. A question still open goes to §8's user-verification list
  instead — written as settled, it is worse than either.
- Non-goals, the iteration axis (`parent` / `change` / `objective`), and high-impact assumptions
  marked VERIFIED or UNVERIFIED also live here.

### 2. Data

- **Tables** — exact table names, partition range, and verified row counts, obtained through the
  data access adapter (`.claude/rules/data/warehouse-access.md`).
- **Columns used** — every column the work reads, with what it means and which table it comes
  from. An exclusion list is not a substitute: it says what was rejected, not what is being read.
- **Snapshot** — the boundary each snapshot pins and how it is re-obtained later.
- **Expectations per extraction row** — expected row-count range, output grain, and cost ceiling.

- **[HARD] Every extraction row states its expected row-count range, its output grain, and its
  cost ceiling.**
  WHY: `ramo-run` runs extraction in two phases and compares the phase-1 sample against these
  three numbers instead of asking a person to eyeball the SQL. With them absent there is nothing
  to compare against, and a join that silently multiplied rows or a query that scans far more
  than intended reaches the dataset. Enforced by `.claude/skills/ramo-run/rules/human-gates.md`
  Gate 2 (the machine check reads these three values) and scored by `plan-rubric.md`
  `data.expectation`.

- **[HARD] A statement the plan settles as a decision is written out in a fenced `sql` block,
  verbatim. A statement described in prose is a statement nobody compiled.**
  WHY: `.claude/skills/ramo-plan/SKILL.md` Step 2a compiles every fenced `sql` block before a
  reviewer is spawned, and `plan-rubric.md` `data.expectation-rederived` has the data seat run
  the analyzer on the same text. Both read literal blocks, so a decision paraphrased as "hash the
  row key and keep one bucket in ten" is invisible to both and reaches the run stage untested —
  which is exactly how a type error in `mod(xxhash64(to_utf8(x)), 10)` survived several improve
  rounds, replicated into config keys and an EDA section on the way. A block carrying a
  placeholder is a template and is skipped by the gate; write it as a template deliberately or
  write it literally, and do not leave the reader to guess which was meant.

### 3. Features

The feature table with the model family stated above it, per
`.claude/rules/model/feature-engineering.md`. Four things belong here:

1. **The feature table**, whose columns are feature / hypothesis / transform / needed by this
   family, plus the three state columns (null rate / handling / value kinds).
2. **The family transform walk** — the declared family's transform list walked one row at a
   time, each marked needed or not needed with its reason.
3. **The derivation walk** — the derivation types walked, each producing a candidate or a stated
   reason the data cannot support one.
4. **Exclusions with reasons**, and the leakage checks planned (`.claude/rules/model/leakage.md`).

### 4. Model

- **Family** — the `D`-row from §1, restated in one line
  (`.claude/rules/model/model-family-selection.md`).
- **Structure** — `단일` on one line, or every stage with its own objective and how the stages
  connect.
- **Loss and selection procedure** — the objective, and how the winning configuration is chosen.
- **Hyperparameters** — the search range per parameter, the selection method, and the file that
  will hold the final values.
- **Simplest-first** — a `parent: null` plan states that this is the family's simplest
  configuration, or why the first experiment is not the simplest one.
- **Budget** — the expected wall-clock for each `model-training` row, shown as expected
  iterations times a measured per-iteration cost rather than as a bare total, plus the
  `min_delta` beside any declared early stopping. A stopping rule with no tolerance leaves the
  ceiling as the effective value, which is a budget decision made by accident
  (`.claude/rules/model/training-budget.md`). The one copy a machine reads is §5 validity's
  `wall_minutes`.
- **Split and seed** — the split boundary and the seed the row will consume.

- **[HARD] A plan with a `model-training` row carries a model-family `D`-row**, naming either
  the matched default case or the user's answer to the deviation question.
  WHY: in the observed cycle the family reached the plan as a value in a constants table, so the
  choice was never anyone's decision — one line is what makes a wrong match visible. Scored by
  `plan-rubric.md` `model.family`.
- **[HARD] The structure decision is written here, not left to the training row.** Single-stage
  is one word; multi-stage names each stage's objective and the connection between them.
  WHY: the observed cycle's two-stage design surfaced as a user decision in a `D`-row while the
  plan's model section named only the family, so the structure was never reviewed as a design —
  it arrived as a fact. Scored by `plan-rubric.md` `model.architecture` — model-discipline grade,
  no mechanical check.

### 5. Evaluation

The metric, the required slices, the decision condition, and how uncertainty is reported.

- Metric and slices per `.claude/rules/model/eval-metric-slice.md`; a single aggregate number is
  never the only pass criterion.
- **Uncertainty** — the method (bootstrap interval, fold spread, or seed repetition), or an
  explicit N/A with its reason. A point estimate cannot tell a real difference from noise.
- **[HARD] A plan with a `model-training` row carries one fenced `validity` block here**
  (`.claude/rules/workflow/01b-acceptance-contract.md` Validity): metric and direction, slice
  column names, baseline, split boundary, seed, the training row's `wall_minutes` budget,
  anchor, label window, and the prediction and feature-list files the evaluation row delivers. A plan without such a row carries none.
  WHY: the prose above is what a person reads, and verify's validity seat cannot recompute a
  slice metric from prose, so without named columns and files every slice cell it fills is a
  reading of the report rather than a measurement. Enforced by `acceptance.py parse` (BLOCKs a
  missing or extra `validity` block) run as the plan skill's parse gate — mechanical for the
  parser, model-discipline grade for the gate being run.

### 6. Change Units (adaptive)

One unit per independently verifiable behavior, bug, or design change. Each unit MUST contain:

- **Outcome** — one or two sentences defining the observable behavior or result to change.
- **Current evidence** — exact `file:line-range` / `file::symbol`; small excerpt when it
  clarifies the seam. A line range is the right form here: a plan's citations are consumed in the
  session that wrote them, and the range is the more precise of the two over that lifespan. The
  symbol-only rule applies to durable documents, whose citations must outlive the next refactor
  (`.claude/rules/common/sot-authoring.md` SOT-1) — so a fact promoted from this plan into
  `docs/` or `wiki/` is re-anchored to a symbol on the way, not copied across as a line number.
- **Implementation shape** — exact files/symbols/queries to create, modify, or delete; control
  and data flow; boundary and error behavior; a short target sketch when useful.
- **Verification** — exact test/check files, named cases, commands, and the current RED gap for
  a behavior change.
- **Reproducibility intent** — which execution rows carry `task_type: model-training`
  (seed, split_boundary, data_snapshot, feature_spec), which of the three data types, or
  `code-change`.
- **Binding decisions** — the §1 `D`-row IDs answering this unit's design questions, written
  `- **Binding decisions:** D1, D3`, or `none`. Required on every unit an implementation row
  names; `acceptance.py` reads it as the row's binding. A unit carrying it goes straight to
  implementation, and a unit whose design question no `D`-row answers is a visible BLOCKED
  instead of a decision made quietly mid-execution.
- **Checks** (optional line) — `- **Checks:** `cmd`, `cmd``: the plain commands that exercise
  this unit, each passing on exit 0 (`01b-acceptance-contract.md` Unit checks). A check states
  *how* the unit is exercised, never *what value* it will produce: no expected counts, no regex
  over output. It is the unit's work definition, so the implementer sees it.

**A change unit cites §0-§5, it does not restate them.** The target, the columns, the feature
verdict, and the model structure were decided above; repeating them here is the duplication
`plan-rubric.md` `density.unique` scores.

Rules: prefer the smallest excerpt proving the seam — **do not paste whole functions**;
distinguish verified facts from decisions and unresolved assumptions; name all consumers
affected by a schema/signature/output change.
File-size limits: `.claude/rules/common/file-size-rules.md` — no speculative line-budget tables.

**Unit size is calibrated, not capped.** Plans that read well ran roughly 20-80 lines per unit;
past ~80 it is usually two units, under ~20 usually a row in someone else's. This is a reference
point and **not a budget** — a genuinely intricate seam may need 70 lines, and padding to reach
40 is worse than 25. An earlier cycle's units ran about twice that long, and the reader's
objection was not length but that the intent had stopped being visible.

### 7. Execution Structure and Verification (adaptive)

The machine-readable handoff. Its frozen column contract, the `[CP]` marking criteria, and the
domain delegation map live in `.claude/rules/workflow/01a-execution-structure.md` — that file is
the half `ramo-run` parses, and it is where a change to the table's shape belongs. A plan carries
the table itself here, after the change units, with phases ordered by dependency.

- **[HARD] Every implementation row's `Task` cell names exactly one change unit `U{n}`**, and
  that unit carries its `Binding decisions:` line (`.claude/rules/workflow/01b-acceptance-contract.md`
  Row mapping). Docs and `other` rows are exempt. The plan predicts no evidence value for any
  row: how a row is judged is the invariants' and the verify seats' business, not the author's.
  WHY: an earlier version first asked each row for an expectation block, and the expectations became the
  implementer's target once relayed, carried formal patterns where nothing could be predicted,
  and left the data's own answer subordinate to a guess made before the data was seen. The
  mapping the parser needs was already in the plan. Enforced by `acceptance.py parse` (BLOCKs a
  `Task` cell without exactly one `U{n}` and a unit without `Binding decisions:`) — mechanical.

Then the verification commands: exact, repository-valid commands and phase gates. Name the
observable output that means each command passed, separating automated criteria (exit code,
metric threshold, assertion) from manual ones. Add a live/manual matrix only when a runtime
boundary (deployed batch, external system) cannot be proven by local checks.

**Acceptance Criteria (release-scoped plans only).** A plan that ends in a release or a hand-off
carries a numbered acceptance list: the conditions that decide *whether it ships*, each with how
it is measured and its grade (mechanical / observed / model-discipline). This is a different
question from the verification commands, which say what each step runs, and from a change unit's
`Outcome`, which is behaviour-level. Neither answers "is it done enough to give to someone".
Say which single criterion is decisive when several pass and one fails. Omit the whole item for
plans that ship nothing. These criteria are not the row check: that check decides whether each
row was built as planned and is run by a machine, while this list decides whether the whole plan
ships and is read by a person.

WHY this slot exists: an acceptance list was written for an early test round with no place in
the format to hold it, so it lived in prose, went unreferenced, and the one unmet item
was found only by re-reading the round's notes afterwards.

### 8. Risks, Docs, and Open Items (adaptive)

- Compact risk table with concrete mitigations; unresolved high-impact assumptions go in a
  short user-verification list. No generic risk padding.
- Name exact stale `docs/` paths only when the change makes them stale; otherwise one line:
  `Documentation: N/A — {reason}`.
- **Rollout and rollback** — when the plan promotes a model (champion swap), changes a batch
  schedule, or alters a serving contract, state how the change is rolled out and how it is
  reverted, including which consumer version interoperates with which model/data version.
  When the work stays inside `experiments/` with nothing promoted, one line: `Rollback: N/A —
  no deployment boundary`.
- Apply `.claude/skills/ramo-plan/rules/forward-risk.md`; untriggered registers are omitted
  entirely, never written as "N/A".

## Optional Content

Include only when it materially improves execution, never by default:

- **A diagram, when three or more parts interact.** Write a `mermaid` code fence directly in the
  plan — there is no diagram skill to call. This is the item whose absence was observed: an
  early release plan laid out table after table with no picture of how the phases depended on
  each other, and the relationships were invisible until one was added.
- A rollout/rollback plan, when a deployment boundary exists.
- A compatibility matrix, when an interface others consume changes.
- A prior-art note, when an approach was tried before and abandoned.

## Content to Omit

- **Restatement/tutorial** — request restatement, generic stack inventory, framework tutorials.
- **Duplication** — separate TODO lists duplicating the Execution Structure; content already
  governed by CLAUDE.md.
- **Empty sections** — sections kept only to satisfy a template; orphaned acceptance criteria.

## Spec-Rubric Map

Which rubric item scores each mandatory requirement above lives with the rubric that owns those
items: `.claude/rules/workflow/plan-rubric.md`. Each file cites the other. This file states what a plan must contain; that file states how each of those is scored,
and keeping the coverage table on the scoring side means adding an item cannot leave the map
behind.

## Final Author Check

- Every change unit has current evidence and an implementation shape.
- Every existing-code/data claim resolves to a real file/symbol or verified table fact.
- Every behavior change maps to a verification case and exactly one execution row per domain slice.
- Execution rows use the frozen 6 columns with valid closed-set values.
- `python3 .claude/skills/ramo-run/scripts/acceptance.py parse --plan <file>` prints nothing.
- Every implement row's `Type` is deliberate — `other` on a training/extraction row is a defect.
- Repeated request prose, generic background, and empty sections are removed.
