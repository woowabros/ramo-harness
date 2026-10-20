---
description: DS artifact naming conventions — feature columns, snapshots, experiment directories, model artifacts, and the identifiers reproducibility keys refer to
paths:
  - "**/*.py"
  - "**/*.sql"
  - "**/*.ipynb"
---

# Naming Conventions (DS Artifacts)

General naming conventions reduced to what DS work actually produces. Naming is not cosmetic
here: reproducibility keys (`data_snapshot`,
`query_hash`, `split_boundary`) are *references to named things*, so an unstable name makes a
recorded key unresolvable later.

## Code Identifiers (Python)

| Kind | Convention | Example |
|------|-----------|---------|
| module, package | `lower_snake` | `feature_store.py` |
| function, variable | `lower_snake` | `build_trip_features` |
| class | `CapWords` | `SnapshotSpec` |
| constant | `UPPER_SNAKE` | `DEFAULT_SPLIT_BOUNDARY` |
| private helper | leading underscore | `_normalize_window` |

Booleans read as predicates (`is_active`, `has_label`, `should_retrain`), never as nouns
(`active`, `label_flag`). Functions that return a value are named for the value, not the act
(`zone_daily_trips`, not `get_data`).

## Feature Columns

`{entity}_{aggregation}_{window}` in `lower_snake`, window last.

```text
zone_trip_count_7d       zone_duration_median_28d       zone_pickup_rate_1h
```

- Window suffixes use a unit letter: `h` hour, `d` day, `w` week. No bare numbers.
- A column whose value depends on the label period carries `_leak_risk` in its name until a
  leakage check clears it (`.claude/rules/model/leakage.md`).
- Never encode the source table in the column name; lineage lives in the dataset doc.

## Snapshots and Extractions

```text
{dataset}_{YYYYMMDD}[_{HH}]        yellow_trips_20230201
```

- The date is the **snapshot boundary**, not the run date. Re-running an extraction on a later
  day with the same boundary MUST produce the same name.
- The recorded `data_snapshot` reproducibility key is exactly this string.
- Query files: `sql/{dataset}_{purpose}.sql` (`sql/yellow_trips_extract.sql`).

## Experiments and Model Artifacts

```text
experiments/{YYYY-MM-DD}-{english-kebab-slug}/
  ├── config.yaml
  ├── artifacts/model_{slug}_{seed}.{ext}
  └── reports/
```

- The experiment slug matches its plan slug (`.ramo/plans/YYYY-MM-DD-{slug}.md`) so plan and
  output are joinable by name alone.
- Model artifact names carry the seed, because the same config at a different seed is a
  different artifact.
- Nothing is written outside its experiment directory or the workspace schema; source
  data stays read-only (`.claude/rules/common/architectural-boundaries.md`).

## Rules

- **[HARD] A name recorded in a reproducibility key MUST be stable and re-derivable.**
  WHY: `data_snapshot: yellow_trips_20230201` is only useful if that string still resolves
  months later. Enforced at review time by `plan-rubric.md` `repro.reobtain` and
  `verify-rubric.md` `fid.evidence` (a pinned partition, never `latest`).
- Rename in one commit, with every consumer updated in the same change. A half-renamed column
  is worse than a badly named one.
- Do not abbreviate beyond a well-known domain term. `cnt`, `amt`, `dt` are forbidden; `sla`,
  `roi`, `utc` are fine.

## Incorrect / Correct

```text
# Incorrect — window buried, unit implicit, run date instead of boundary
zoneTrips7              snapshot_20260819_rerun         model_final_v2.pkl

# Correct
zone_trip_count_7d      yellow_trips_20230201           model_trip_duration_seed42.pkl
```

## See Also

- `common/architectural-boundaries.md` — where each artifact is allowed to live.
- `model/eval-metric-slice.md` — slice names appear in evaluation output and follow the same
  column convention.
