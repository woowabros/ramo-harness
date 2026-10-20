---
description: Coding principles — directional guidance for every implementation task, DS idiom
paths:
  - "**/*.py"
  - "**/*.sql"
  - "**/*.ipynb"
---

# Coding Principles

HARD Rules = verifiable constraints; Principles = directional guidance. On conflict, HARD wins.

## 1. Think Before Coding

**"State the problem and success criterion before writing a single line."**

- Write down what you are trying to do in one sentence before opening a file.
- Define done: what exact output, metric, or test result proves success?
- List assumptions explicitly — unverified assumptions are deferred risks.

```python
# Incorrect — no criterion, assumption-driven
df = pd.read_parquet(path)
df = df.dropna()          # why? which columns? what does success look like?

# Correct — criterion-first: null policy is explicit and testable
# done = feature table with 0 nulls in required cols, row count within 1% of source
required = ["VendorID", "tpep_dropoff_datetime", "PULocationID"]
assert df[required].notna().all().all(), df[required].isna().sum()
```

## 2. Simplicity First

**"The simplest solution that works — not the most general one."**

- Prefer a concrete function over a configurable framework until the second real caller arrives.
- Three similar lines beat a premature abstraction that obscures intent.

```python
# Incorrect — premature FeatureFactory registry for two features
# Correct — two plain functions; refactor when the fifth feature arrives
def zone_trip_count_7d(df): ...
def zone_duration_median_28d(df): ...
```

## 3. Surgical Changes

**"Every line in the diff must trace back to a plan requirement."**

- Implement only what the plan specifies — no drive-by refactors, no gold-plating.
- If a side issue is spotted, record it in `concerns:`; do not fix it inline.

## 4. Goal-Driven Execution

**"Every step has a verifiable success signal — run it before claiming done."**

- After each step, run the proof: the test, the query row count, the metric on the
  declared slices.
- Never claim DONE until fresh verification evidence has been read, not assumed.
- Record evidence keys as you go (`common/output-contract.md` Evidence Field) —
  a result you cannot re-obtain is not a result.

## See Also

- `.claude/rules/workflow/03-run.md` — scope guard and reproducibility checklist
- `.claude/rules/model/leakage.md` — leakage checks that "done" must include for model work
