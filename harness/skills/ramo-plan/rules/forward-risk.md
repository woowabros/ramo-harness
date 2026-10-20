# Forward Risk (Topic 6 — @ramo-critique)

Defines the structure of Topic 6 (RISKS) in the @ramo-critique reviewer prompt. @ramo-critique is
already a mandatory reviewer (`.claude/rules/workflow/02-review-plan.md`); this structures its
risk analysis without adding a new agent or rubric item.

## Pre-mortem Framing

Open the analysis with a pre-mortem instruction: assume this plan has already failed. Name the
three most likely causes and a mitigation for each. Independence across reviewers is already
guaranteed by parallel spawn; no separate independence step is needed.

## Registers

Two registers always apply, plus two conditional registers. **When a trigger is absent, the
block does not exist at all — omit it entirely rather than writing "N/A".**

### Register 1 — Blast Radius (always applies)

Enumerate everything affected by the change:

- Direct call sites and consumers, each with `file:line`.
- Downstream datasets, features, and models that read the changed outputs.
- Batch jobs and schedules that consume or produce the touched tables.

Classify total reach as `local | internal | external-contract`. An `external-contract`
classification (outputs consumed outside the experiment, e.g. serving or another team's batch)
raises review intensity — findings against it take a higher default priority.

### Register 2 — Assumption Register (always applies)

Mark every assumption the plan depends on as:

- `VERIFIED` — with an evidence pointer (`file:line`, table fact, or command output).
- `UNVERIFIED` — no evidence found.

Only high-impact `UNVERIFIED` items escalate to the user-verification list; low-impact ones
are noted but do not block.

### Register 3 — Rollback Safety (TRIGGER: model or batch deployment, schema change, or persisted-data change)

When the plan deploys a model or batch job, changes a schema, or rewrites persisted data,
walk through three stages and state each assertion explicitly:

1. **expand** — is rollback safe here?
2. **migrate/retrain** — is rollback safe here?
3. **contract** — is rollback safe here?

State which consumer version must interoperate with which data/model version (N-1
compatibility) across the sequence.

### Register 4 — Evaluation Design Register (TRIGGER: metric, slice, baseline, or evaluation-protocol change)

When the plan changes what is measured or how, require:

- Declared metric AND required slices (`.claude/rules/model/eval-metric-slice.md`).
- A named baseline and the baseline-vs-candidate comparison gate.
- Deterministic assertions where possible (fixed seed, fixed snapshot) so the comparison is
  attributable to the change, not to data drift.

## Rubric and Veto Interaction

A @ramo-critique BLOCKING finding already promotes to minimum P1 through the veto rule
(`.claude/rules/workflow/02-review-plan.md`). These registers structure Topic 6 output; they do
not add a new scored dimension.
