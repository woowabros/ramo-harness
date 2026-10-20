---
title: Accuracy Verification
impact: MEDIUM
tags: quality, accuracy, verification
---

## Accuracy Verification

Every claim in documentation must be verifiable. Code examples must run, commands must
exist, file paths must resolve, and table references must match the real schema.

### What to Verify

| Claim Type | Verification Method |
|-----------|-------------------|
| File path in `relates-to` / body | Glob for the path |
| Code example | Read the source file to confirm it matches |
| Shell command | Run the command (or dry-run with `--help`) |
| Table / column name | Check against committed DDL, or the data access adapter (`python3 .claude/scripts/ramo-data.py schema <table>`) — never from memory |
| SQL example | Confirm it is the committed extraction query (or clearly marked illustrative) |
| Environment variable | Grep for usage in codebase |
| Metric / number | Cite the artifact it came from (eval report path, committed output) |
| **Computed aggregate** (a sum, a share, a difference, a percentage of a whole) | **Recompute it** from the producing artifact or the code that produced it, and cite the recomputation beside the value. Reading it off an upstream document is not verification — that document is where the error came from |

### Rules

- Never document a file path without confirming it exists.
- Code and SQL examples must match the actual implementation, or be clearly marked as
  pseudocode/illustrative.
- Table and column names follow `.claude/rules/data/warehouse-access.md` — schema facts
  come from the adapter's `schema` command or committed DDL, not recall.
- Reported metrics must name their source artifact; a number with no source is a claim,
  not a fact.
- When unsure about accuracy, add a `> **UNVERIFIED:** ...` banner rather than shipping
  a guess.

- **[HARD] A computed aggregate is recomputed from its source artifact before it is written,
  and the recomputation is cited beside the value.**
  WHY: observed during testing. A feature specification stated the combined gain of five
  zone-lookback features as about 65%; recomputing it from the model artifact gave about 67%
  (illustrative values), because one of the five (`zone_trip_count_28d`) had been left out of the
  sum. The wrong figure was computed at the diagnose stage and had already travelled into the
  diagnosis, the feature spec, and a downstream summary before a wiki reviewer caught it. That catch was luck, not a gate: `ramo-doc` spawns no
  `Agent()`, so its quality pass is performed by the author, and a number only meets an
  adversarial reader if it happens to be promoted to the wiki. Gate strength was following the
  tree position rather than the claim. Recomputation is the one check the author can perform on
  their own work, because it does not require doubting the number first. Model-discipline
  grade: this rule states it, and nothing mechanical checks that the recomputation happened.

**Incorrect (unverified claims):**

```markdown
Run `python train.py --config prod` to retrain.
The trips table is `tlc.yellow_trips_daily`.
```

```
# But the project trains via `uv run python -m trip_duration.train`
# And the trips table is actually `tlc.yellow_trips` (checked via `ramo-data.py schema`)
```

**Correct (verified claims):**

```markdown
Run `uv run python -m trip_duration.train --config configs/prod.yaml` to retrain
(verified against `src/trip_duration/train.py::main`).
The trips table is `tlc.yellow_trips` (verified via `ramo-data.py schema tlc.yellow_trips`).
```
