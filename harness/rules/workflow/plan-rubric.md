---
description: Quantitative plan-scoring rubric (65 evidence-anchored items, 9 DS dimensions, plus a citation entry gate that is not scored) — the scoring half of the spec-rubric pair with workflow/01-plan.md, loaded by ramo-plan-evaluator
paths:
  - ".ramo/plans/*.md"
---

# Plan Evaluation Rubric

Read-only rubric loaded by @ramo-plan-evaluator. Score the plan against the contract in
`.claude/rules/workflow/01-plan.md` — its scoring pair; item IDs match that spec's Spec-Rubric Map
and each file cites the other. Never
invent a repository fact or pass an item from impression: quote plan evidence before every
PASS/FAIL, and check data claims against actual files.

**The dimensions are the DS questions in the order a reader asks them**: what are we predicting
and why, off which data, with which features, in what model, on what code evidence, in what shape,
handed off how, proven how, in what order. Dimensions 1-4 hold 52% because that is where a wrong
plan produces a wrong result; dimension 7 holds 6% because the run parser already rejects the
column contract mechanically.

## Evaluation Workflow

1. Read the plan and `.claude/rules/workflow/01-plan.md`.
2. **Citation entry gate — pass/fail, before any scoring.** Resolve every citation the plan
   makes: `file:line`/`file::symbol` anchors, table and partition facts, roster agent names,
   `Skill()` references. All resolve → report `Citations: {n}/{n} verified` and continue. Any
   fails → return them as an `EP-CITE-{NNN}` list and stop, scoring nothing and grading nothing.
   The caller may hand back a **carried** citation list (the repair cap in
   `.claude/rules/workflow/02-review-plan.md` was reached). Those are excluded from this gate —
   they do not stop scoring. Score every item that rested on a carried citation with the
   evidence `"not found"`, and raise one `EP-P2` ticket per carried citation so the unresolved
   anchor is still on the record.
3. Identify each change unit and every Execution Structure row, then build the outcome
   traceability matrix: outcome -> evidence -> shape -> task row -> proof.
4. Apply N/A rules, then score all applicable items with quoted evidence.
5. Compute weighted scores; create one `EP-P{0-3}-{NNN}` ticket per FAIL
   (`.claude/rules/workflow/09-ticket-schema.md`).
6. Return matrix, score sheet, tickets, summary, and the standard envelope.

- **[HARD] Citation integrity is an entry condition, never a scored item.** A stale or invented
  citation returns as `EP-CITE-{NNN}`: a mechanical repair list with no findings budget, no
  P-level, no consensus vote, no improve round. Roster agent names and `Skill()` references
  resolve here too, which is why no scored item re-checks their existence.
  WHY: observed. In one cycle most blocking findings changed no output value, and every one of
  those was a citation or consistency defect — because the rubric scored citations, so the
  findings budget flowed there. A design that scores them nowhere and reports "citations
  verified: n/n" as a precondition had its reviewers raise almost no citation findings while
  being harsher on contract and logic: where citations are counted was the difference, not
  temperament. Enforced by this step and `.claude/skills/ramo-plan/SKILL.md` Step 5, which routes
  a citation-only failure to a mechanical repair instead of an improve round — model-discipline
  grade, no mechanical check.

## Dimensions

Weights sum to 100%.

| # | Dimension | Items | Weight |
|---|-----------|-------|--------|
| 1 | Problem and Objective | 8 | 14% |
| 2 | Data and Tables | 7 | 12% |
| 3 | Feature Design | 5 | 14% |
| 4 | Model Design | 6 | 12% |
| 5 | Code Evidence | 4 | 8% |
| 6 | Implementation Shape | 6 | 10% |
| 7 | Execution Handoff | 6 | 6% |
| 8 | Verification and Reproducibility | 11 | 14% |
| 9 | Sequencing, Risk, Density, and Readability | 12 | 10% |

## Checklist (65 items)

### 1. Problem and Objective

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| problem.purpose | One paragraph naming who consumes the result, which decision it changes, and the baseline the experiment must beat | Title and metric only, so why the experiment is worth running is nowhere |
| problem.target-shape | The target's measured distribution (quantiles, tail, null rate) and its prediction anchor, each taken on a named sample | Target named with no measured shape, or a distribution quoted with no sample behind it |
| intent.outcome | Specific observable outcome/problem stated | Generic "run experiment" or solution-only title |
| intent.parent | `parent` names the plan this iterates on, or is the explicit literal `null`; when a parent exists, `change` and `objective` are filled | Field omitted, so it cannot be told apart from a root, or a parent named with no stated change |
| intent.decisions | §1 carries the 선결 결정 table: every design question the plan has answered has a `D`-row with a decision, its basis, and the units it binds, labelled not open for renegotiation; units whose design is covered carry a `Binding decisions:` line | No settled-decisions table, or a row stating a goal rather than a decision, or a design question left open that an execution row will therefore have to answer |
| intent.non-goals | Scope boundary stated when drift is plausible | Material adjacent work has no boundary |
| intent.assumptions | High-impact assumptions marked VERIFIED/UNVERIFIED with evidence | Assumptions presented as facts |
| intent.trace | Every outcome maps to evidence, shape, task, and proof | Any outcome unmapped in the matrix |

### 2. Data and Tables

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| evidence.data-source | Data claims name exact tables/partitions with verified shape facts (rows, window) | Unverified table names or invented row counts |
| data.columns | Every column the work reads is listed with its meaning and its source table | Table names only, or an exclusion list standing in for the used-column list |
| data.expectation | Each extraction row states its expected row-count range, its output grain, and its cost ceiling | Any of the three absent, so `ramo-run`'s phase-1 machine check has nothing to compare the sample against (`.claude/skills/ramo-run/rules/human-gates.md`) |
| data.expectation-rederived | The data seat re-derived each extraction row's cost ceiling by running the adapter's `explain` on the plan's literal statement, and the estimate sits inside the stated ceiling | Scored by @ramo-data-design only; @ramo-plan-evaluator marks it N/A with the reason `no query tool`. FAIL: the plan has no literal statement to compile, the compile fails, or the estimate exceeds the ceiling |
| snapshot.lineage | Source data read-only; derived artifacts land in declared experiment paths or the workspace schema | Plan mutates source tables, writes outside the workspace schema, or scatters outputs |
| snapshot.read-route | Reads authored through the data access adapter, and any warehouse write declared with a workspace-schema target (`data.workspace_schema`), per `.claude/rules/data/warehouse-access.md` | Raw SQL CLI path, or a write target outside the workspace schema |
| repro.reobtain | Each snapshot states how it is re-obtained later | Snapshot named but unrecoverable |

### 3. Feature Design

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| feat.table | Model-domain plans carry the feature table (feature / hypothesis / transform / needed by this family), model family stated above it | Features listed without a hypothesis, or a transform list that does not follow from the declared family |
| feat.state | Every feature row carries its measured null rate, the handling that rate implies, and its value kinds (cardinality for categorical, range for continuous) | A feature table of hypothesis and transform only, so nobody established the column is usable |
| feat.transform-walk | The declared family's transform list in `.claude/rules/model/feature-engineering.md` is walked one row at a time, each marked needed or not needed with its reason | Transforms listed with no family-derived walk, or a walk that skips rows the family's table names |
| feat.derivation | The derivation types in `.claude/rules/model/feature-engineering.md` were walked, each producing a candidate or a stated reason none is possible | A verdict made only of exclusions, or no evidence the list was considered |
| snapshot.leakage | Leakage checks planned per `.claude/rules/model/leakage.md` (time/target/group) | Training plan silent on leakage |

### 4. Model Design

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| model.family | A plan with a `model-training` row has a model-family `D`-row naming the matched default case or the user's deviation answer (`.claude/rules/model/model-family-selection.md`) | The family appears only as a constant or a config value, so no one decided it |
| model.architecture | The structure after the family: `단일` on one line, or every stage with its own objective and how the stages connect (`.claude/rules/model/model-family-selection.md`) | Family named and the structure left for the training row to invent |
| model.hyperparameters | Search range per hyperparameter, the selection method, and the file that will hold the final values | A constants table of final values with no range or method, or search deferred with no statement that it was |
| model.simplest-first | A `parent: null` plan runs the family's simplest configuration (minimal derived features, single stage), or states why the first experiment is not the simplest one | A first experiment stacking stages or engineered targets with no reason given |
| model.budget | Every `model-training` row states its expected wall-clock, derived as expected iterations times a measured per-iteration cost, and any declared early stopping states its `min_delta` (`.claude/rules/model/training-budget.md`) | No expected duration, so a slow row cannot be told from a hung one and fix rounds cannot price a retrain; a row total with no factors behind it; or early stopping declared with no improvement tolerance, which makes the ceiling the effective value |
| repro.model-keys | model-training rows plan capture of seed, split_boundary, data_snapshot, feature_spec | Training planned without seed/split/snapshot capture |

### 5. Code Evidence

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| evidence.location | Every existing-code change has exact `file:line-range`/`file::symbol` (a plan is a session-consumed document, so a line range scores as full credit here — `common/sot-authoring.md` SOT-1 requires symbols only of durable documents) | Vague path/module reference |
| evidence.current | Current behavior/root cause supported by code or run evidence | Unsupported diagnosis |
| evidence.excerpt | Small excerpt included when it clarifies the seam | Complex change rests on prose alone |
| evidence.callers | Schema/signature/output changes name affected consumers | Downstream consumers omitted |

### 6. Implementation Shape

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| shape.operations | Exact files/symbols/queries to create/modify/delete named | "Update the pipeline" |
| shape.logic | Target control/data flow concrete | Multiple materially different implementations fit |
| shape.contract | Changed schemas, signatures, feature definitions, output formats explicit | Boundary contract implied |
| shape.validation | Input/error/edge behavior defined at changed boundaries | Happy path only |
| shape.pattern | Placement follows verified neighboring patterns with rationale | New abstraction ignores local seam |
| shape.cleanup | Deletions name proof of zero consumers and ordering | Speculative cleanup |

### 7. Execution Handoff

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| task.concrete | Every row names a change unit and concrete file/symbol slice | Bare verbs such as "implement" |
| task.type | Every `Type` deliberate: training/extraction rows never `other` | Training row typed `other` without justification |
| task.deliverable | Every row lists exact output paths | Generic "implementation" deliverable |
| task.coverage | Every change unit appears in rows exactly once per domain slice | Missing or duplicated work |
| exec.cp-marking | Every row meeting a `[CP]` criterion in `.claude/rules/workflow/01a-execution-structure.md` carries the marker | A row that fixes a downstream contract or embeds an unrevisited judgement is unmarked, so its decision never reaches a design briefing |
| agent.separation | Cross-domain work split across domain owners | One row owns unrelated domain edits |

The frozen column contract itself is not scored. `ramo-run` Step 3 BLOCKs on a missing or renamed
6-column header, on a `Domain` outside its closed set, and on a dependency that names no existing
earlier task. Scoring what the parser rejects spends findings budget on defects that can never
reach execution, which is the trade this dimension's 6% weight records: the weight it gave up
went to the feature and model dimensions, where no seat was looking.

### 8. Verification and Reproducibility

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| verify.files | Exact test/check files named per behavior change | Generic "add tests" |
| verify.cases | Named cases specify inputs and observable outputs | Scenario list without assertions |
| verify.commands | Repository-valid commands listed | "Run tests" only |
| verify.gates | Each phase has one observable `Gate:` pass condition | Completion defined by file creation alone |
| verify.red | Behavior changes state the current RED gap | No proof a check would catch old behavior |
| verify.boundary | A live/manual matrix exists only where a runtime boundary (deployed batch, serving, external system) cannot be proven locally | Required cross-boundary proof missing, or gratuitous manual steps for work local checks cover |
| repro.task-type | Every implement row's `Type` matches its change unit's reproducibility intent | Declared type contradicts the work |
| repro.data-keys | data-extraction rows plan capture of data_snapshot, query_hash | Extraction planned without snapshot/hash capture |
| repro.metric-slice | Metric AND required slices declared per `.claude/rules/model/eval-metric-slice.md` | Single aggregate number as the only pass criterion |
| eval.validity-declared | A model plan's §5 carries the `validity` block: slices are prediction-file column names, `predictions` and `features` appear in a `Deliverable`, and `forbidden_columns` lists the eda artifact's leakage candidates when it has any | A model plan with no block, slices written as prose, or `forbidden_columns` empty while the eda artifact lists leakage candidates |
| eval.variance | The uncertainty-reporting method is named (bootstrap interval, fold spread, or seed repetition), or carries an N/A with its reason | A single point metric offered as the decision criterion, so a difference cannot be told from noise |

### 9. Sequencing, Risk, Density, and Readability

| ID | PASS evidence | FAIL signal |
|----|---------------|-------------|
| seq.order | Producers precede dependent consumers and verification | Impossible/circular order |
| seq.parallel | Independent work grouped; dependent work separated | Needless serialization or unsafe parallelism |
| seq.critical | Critical path marked when multiple phases exist | Key dependency chain hidden |
| release.safety | Champion swap, batch schedule, or serving-contract change states rollout/rollback (or an explicit N/A reason) | Irreversible deployment step planned with no way back |
| docs.sot | Exact stale docs paths named, or one concise N/A reason | Generic "update docs" |
| risk.concrete | Risks specific with actionable mitigations | Generic risk padding |
| risk.verify | High-impact unresolved assumptions listed for user verification | Hidden blocker |
| density.signal | Content changes an implementation/review decision | Request restatement, tutorials |
| density.unique | Tasks and decisions appear once | Duplicate TODO/phase tables |
| read.relations | When three or more parts interact, their relationship is visible in one place — a diagram, or one table whose rows are the dependencies rather than the items | Only per-item tables, so what depends on what has to be reassembled by the reader |
| read.done-signal | Each phase and the plan as a whole state what "finished" looks like, in a form someone other than the author can check | Completion implied by the task list running out |
| complete.ready | No unresolved high-impact placeholder; executor can start without rediscovery | `TBD`/`TODO` in the executable core |

## Evidence-Anchored Scoring

Per applicable item output `Evidence: "..." -> PASS|FAIL (reason)`, using `"not found"` when
absent. Verify at least one citation per change unit and every citation implicated in a P0/P1
decision. Dimension score = PASS / applicable items (N/A excluded); overall = weighted sum.

## N/A Rules

- Greenfield: `evidence.current`/`evidence.excerpt` may be N/A with exact new paths + reason.
- No `model-training` rows: dimension 3 and 4 items plus `repro.metric-slice`, `eval.variance`,
  `eval.validity-declared` may be N/A. No `data-extraction` rows: `data.expectation`, `data.expectation-rederived`,
  `repro.data-keys`, `snapshot.read-route` may be N/A. `data.expectation-rederived` is also N/A
  for any seat without a query tool, which is every seat except @ramo-data-design — the item
  measures rather than reads, so a seat that cannot measure records `no query tool` and moves
  on rather than guessing. Never dimensions 2 and 4 both entirely N/A for a DS plan — if
  nothing is reproducible, question whether the plan belongs in this pipeline.
- `parent` names a plan: `model.simplest-first` is N/A; on `parent: null` it never is.
- Single-phase work: `seq.parallel`, `seq.critical` may be N/A.
- No deployment boundary (experiment stays inside `experiments/`, nothing promoted or
  scheduled): `release.safety` and `verify.boundary` may be N/A with the boundary stated.
- Deletion not proposed: `shape.cleanup` N/A. No stale docs: `docs.sot` passes with one reason.
- Never N/A: dimension 1 items, density items, `complete.ready`, `task.*` items.

## Priority Mapping

| Priority | Criteria |
|----------|----------|
| P0 | Missing executable core, or a defect likely to produce a wrong/unreproducible result |
| P1 | Major location/shape/proof/ordering gap forcing rediscovery or divergence |
| P2 | Local gap recoverable without redesign |
| P3 | Cosmetic or minor density issue |

Default P0: `problem.purpose`, `problem.target-shape`, `feat.state`, `feat.transform-walk`,
`model.architecture`, `intent.outcome`, `shape.contract`, `task.type`, `task.coverage`,
`repro.task-type`, `snapshot.leakage`, `complete.ready`, `data.expectation`,
`repro.metric-slice`, `verify.commands`, `eval.validity-declared`.
The middle three of those moved up from P1 because each one's absence disables a downstream machine, not
just a reader: without `data.expectation` `ramo-run`'s phase-1 query check has nothing to
compare a sample against and BLOCKs, without `repro.metric-slice` the `eval.cells` item of
`.claude/rules/workflow/verify-rubric.md` has no slice to recompute, and without `verify.commands` the
deterministic gate `ramo-verify` runs before spawning any seat has no command list to run.
The last one starts at P0 for the same reason: without the validity block the verify validity
seat has no column or file to recompute from.
Default P1: `data.columns`, `data.expectation-rederived`, `model.family`, `model.hyperparameters`,
`model.simplest-first`, `model.budget`, `eval.variance`, `agent.separation`, `seq.order`,
`release.safety`, **every remaining dimension 1, 3, and 4 item** (`intent.parent`,
`intent.decisions`, `intent.non-goals`, `intent.assumptions`, `intent.trace`, `feat.table`,
`feat.derivation`), and the remaining evidence/shape/task/verify/repro/snapshot items.
Default P2: other functional items including `verify.boundary`.
Default P3: density items (promote to P1 when boilerplate hides executable work).

- **[HARD] A dimension 1, 3, or 4 FAIL is never scored below P1.**
  WHY: this rubric was rebuilt because a plan scored near the top while no seat had looked at which
  features it chose or how the model was built. At P2 a weighted total carries such a gap: format
  items pass, the average stays high, and the item that decides the result reaches no ticket
  anyone acts on. Enforced by the Default P0/P1 lists above, which name every dimension 1, 3,
  and 4 item explicitly rather than through a prefix catch-all, and by @ramo-plan-evaluator's
  ticket step — model-discipline grade, no mechanical check. The catch-all is why this had to be
  spelled out: `and the remaining evidence/shape/task/... items` enumerates ID prefixes, and
  `intent.*` and `feat.*` are not among them, so seven items this rule covers were landing in
  `Default P2` while the rule above claimed to prevent exactly that.
  **What P1 means here is coverage, not force.** A P1 ticket is listed in full in the final
  report and is fixed inside any round a P0 opens; it does not open a round by itself
  (`.claude/rules/workflow/09-ticket-schema.md` Priority Definitions). The floor this rule sets
  is what keeps such an item from sliding to advisory, which was the failure it was written
  against — a round trigger was never what made the guarantee hold.

## Output Format

1. **Outcome Traceability Matrix** — `| Change Unit | Evidence | Shape | Task row(s) | Proof | Status |`
2. **Score Sheet** — 9 dimensions with PASS/FAIL/N/A counts, score, weight, weighted score.
3. **Tickets** — one `EP-P{0-3}-{NNN}` per FAIL.
4. **Summary** — score/grade (A>=90, B>=80, C>=65, D>=50, F<50), P0-P3 counts, and the report-local
   label `PASS | CONDITIONAL PASS | FAIL` (`.claude/rules/workflow/02-review-plan.md`). Report labels
   never enter the envelope, whose `verdict` is `APPROVE` (0 P0 + 0 P1 + score >= 80) or `REJECT`
   otherwise (`.claude/schema/harness.json` roster vocabulary).

## Spec-Rubric Map

Which item scores each mandatory requirement of the plan format
(`.claude/rules/workflow/01-plan.md`). It is kept on the scoring side so that adding an item above
cannot leave the coverage claim behind. Every item in the checklist appears in exactly one row.

| Spec requirement | Rubric items |
|---|---|
| §0 business purpose, prediction target and anchor, target distribution, baseline, goal metric | `problem.purpose`, `problem.target-shape`, `intent.outcome` |
| §1 선결 결정 table + per-unit `Binding decisions:`, non-goals, iteration axis, assumptions | `intent.decisions`, `intent.non-goals`, `intent.parent`, `intent.assumptions`, `intent.trace` |
| §2 tables/partitions/rows, used columns and meaning, snapshot, expected rows + grain + cost ceiling | `evidence.data-source`, `data.columns`, `data.expectation`, `data.expectation-rederived`, `repro.reobtain`, `snapshot.lineage`, `snapshot.read-route` |
| §3 feature table + state columns, family transform walk, derivation walk, exclusions, leakage | `feat.table`, `feat.state`, `feat.transform-walk`, `feat.derivation`, `snapshot.leakage` |
| §4 family, structure, loss and selection, hyperparameter range, simplest-first, budget, split and seed | `model.family`, `model.architecture`, `model.hyperparameters`, `model.simplest-first`, `model.budget`, `repro.model-keys` |
| §5 metrics, slices, decision condition, uncertainty reporting, `validity` block | `repro.metric-slice`, `eval.variance`, `eval.validity-declared` |
| §6 change units: current evidence, excerpts, consumers, implementation shape | `evidence.location`, `evidence.current`, `evidence.excerpt`, `evidence.callers`, `shape.operations`, `shape.logic`, `shape.contract`, `shape.validation`, `shape.pattern`, `shape.cleanup` |
| §7 Execution Structure rows (the column contract itself is the run parser's, not an item) | `task.concrete`, `task.type`, `task.deliverable`, `task.coverage`, `exec.cp-marking`, `agent.separation`, `repro.task-type`, `repro.data-keys` |
| §7 verification: files, cases, commands, gates, RED, runtime boundary | `verify.files`, `verify.cases`, `verify.commands`, `verify.gates`, `verify.red`, `verify.boundary` |
| §8 phase order, parallel grouping, critical path, rollout and rollback | `seq.order`, `seq.parallel`, `seq.critical`, `release.safety` |
| §8 docs, risks, density, readability, no unresolved placeholders | `docs.sot`, `risk.concrete`, `risk.verify`, `density.signal`, `density.unique`, `read.relations`, `read.done-signal`, `complete.ready` |
