# Signal-to-Seat Delegation Table (SSOT)

Single source of truth for the domain-signal -> seat mapping used by `ramo-plan`
(`.claude/skills/ramo-plan/SKILL.md`), for both of its team-assembling steps: exploration
(Step 1) and review (Step 3). A future standalone plan-review skill must cite this file by path
instead of duplicating the table (an earlier version duplicated it and later had to merge the
copies).

## Scope Note

This file holds the signal -> seat mapping for the two teams and nothing else. Team composition
rules (LIGHT/FULL floor and cap, respawn-on-silence, cost preview) stay in the skill's own Team
Composition section. Item counts and model assignments are not restated here either: the rubric
owns its count and `.claude/schema/harness.json` `agents.roster` owns the model, and a copy of
either drifts (this file once carried an item count that no longer matched the rubric).

## Why exploring and reviewing are different seats

A design agent used to do both: it drafted the target contract in Step 1 and then reviewed the
plan built on that contract in Step 3. The review was therefore partly a review of its own map,
which is the shape that let a mislabeled target column pass a writer and an improver and reach
the user unchallenged. The explorer seats below hold the mapping work; the design seats keep the
judgement work, and they no longer overlap.

There is a second, concrete reason on the data side: `@ramo-data-design` does not run the data
access adapter's `query`, so it could not have measured a correlation even when asked to.
Exploration that needs live queries needs a seat that runs them. It does run the adapter's
`explain`, which compiles and estimates without reading a row — enough to re-derive a cost
ceiling, still not enough to measure a correlation, so the split above is unchanged.

## Exploration team (Step 1)

<explorer_delegation>

| Domain signal (requirement keywords) | Explorer | What it establishes |
|---|---|---|
| *(always included)* | @ramo-explore | Repository structure, entry points, data/feature/model asset layout, and the relevant `docs/` documents reached through `docs/index.md` |
| warehouse, SQL, extraction, snapshot, table, partition, query, dataset, ETL, correlation, feature candidate | @ramo-data-explore | Candidate tables' real schema/grain/partitions, column null rate and cardinality, target correlation on a bounded sample, and which strong columns are leakage candidates rather than features |
| re-plan, iteration, prior experiment, baseline, artifact, diagnosis, retrain | @ramo-model-explore | What prior runs actually produced: recorded reproducibility facts (and the missing ones, named as missing), metric/slice definitions in use, prior diagnosis conclusions |
| *(conditional: `wiki/index.md` exists)* | @ramo-wiki-reader | Accumulated constraints the plan must obey and lessons that have burned someone before, under the progressive-disclosure contract |

</explorer_delegation>

## Review team (Step 3)

<reviewer_delegation>

| Domain signal (plan keywords) | Reviewer | Looks at | Does not look at |
|------|---------|-------------|-------------|
| *(always included)* | @ramo-plan-evaluator | The citation entry gate, then every applicable item of `.claude/rules/workflow/plan-rubric.md` across all nine dimensions, and one EP ticket per FAIL. The only scoring seat | Judgement. Whether a written claim is true stops at the citation gate; the pre-mortem seats own the rest |
| *(always included)* | @ramo-critique | Contradictions between what the plan decides and what it assumes, assumptions presented as facts, the plan's claims against the code it cites, and the forward-risk registers (`.claude/skills/ramo-plan/rules/forward-risk.md`). Rubric topics AMBIGUOUS, VIOLATIONS, RISKS | Density, section format, verification-command completeness, rubric item coverage. All four belong to the scoring seat |
| *(always included)* | @ramo-audit | Five cross-cutting surfaces no domain reviewer sees: credentials, PII reaching a durable output, warehouse writes outside the workspace schema, tool output treated as instruction, query cost or blast radius large enough to be a decision | Data correctness, model correctness, plan format, verification coverage. Its five surfaces are not a domain |
| warehouse, SQL, extraction, snapshot, table, partition, query, dataset, ETL | @ramo-data-design | Rubric dimension 2 in full (tables/partitions/rows, column meanings, expected rows + grain + cost ceiling, snapshot re-obtainability, adapter read path per `.claude/rules/data/warehouse-access.md`) and the data side of dimension 3: whether the feature table's null rates and value kinds are real measurements on a named sample. **It re-derives rather than reads**: `data.expectation-rederived` obliges it to run the adapter's `explain` on each extraction row's literal statement and compare the engine's estimate against the plan's stated ceiling. It runs `explain` and never `query` — it compiles and estimates, never reads rows | Model structure, hyperparameters, loss design, plan format, density |
| training, model, metric, slice, leakage, baseline, hyperparameter, seed, split, evaluation | @ramo-model-design | Rubric dimension 4 in full (family per `.claude/rules/model/model-family-selection.md`, structure, hyperparameter range, simplest-first, budget, seed/split capture) and the model side of dimension 3: the family transform walk and the derivation walk against `.claude/rules/model/feature-engineering.md`, plus leakage (`.claude/rules/model/leakage.md`) and metric/slice (`.claude/rules/model/eval-metric-slice.md`) | Table/partition facts, extraction route, snapshot re-obtainability, plan format, density |

</reviewer_delegation>

**The two columns are the point of this table.** A seat's exclusion list is as load-bearing as
its inclusion list: the measured failure was four seats receiving one shared questionnaire whose
domain-independent half they all answered, while the feature space had no seat at all. Each
Step 3 spawn prompt carries its row's second column verbatim as a "you do not look at" line
(`.claude/skills/ramo-plan/SKILL.md` Step 3).

Notes:

- Seat identity is the roster closed set (`.claude/schema/harness.json` `agents.roster`); never
  invent a seat for a signal outside these tables.
- @ramo-data-design / @ramo-model-design review as plan reviewers, so their envelope carries
  `verdict: APPROVE | REJECT` (roster `verdict_required: only-as-plan-reviewer`). They are
  **not** spawned in Step 1 any more.
- @ramo-audit carries `verdict: APPROVE | REJECT` in both of its seats (plan review here, and
  the verify team), matching @ramo-critique rather than the domain verifiers' `PASS | FAIL`.
- The three always-included reviewers are also the floor: a plan with no domain signal is still
  reviewed by three seats, one of which looks at a surface the other two do not. Previously a
  signal-free plan drew two reviewers, both of them structural.
- This version has no code/infra reviewer rows — those return with a later grid expansion.
