---
description: File and function size limits — split threshold is the verify deterministic gate, single-sourced in .claude/schema/harness.json
paths:
  - "**/*.py"
  - "**/*.sql"
  - "**/*.ipynb"
---

# File and Function Size Rules

These are project-wide defaults. Language-specific rules may be stricter.

- Functions should usually be under 50 lines.
- Files should usually be 200-400 lines.
- **Files above the split threshold require strong justification or splitting.** The threshold
  number is single-sourced in `.claude/schema/harness.json` (`limits.file_size_split_lines`) and is the
  same number the verify skill uses as its deterministic `wc -l` gate — do not restate the
  number here or anywhere else (a restated copy drifts from its source).
- Split by responsibility, not by arbitrary line count.

Rules:

- MUST NOT create god files such as `utils.py` or `helpers.py` containing unrelated code.
- MUST NOT create pipeline scripts that mix extraction SQL, feature computation, training,
  and evaluation in one file — each stage is a separate, individually runnable module.
- MUST NOT hide complexity in one-line nested expressions (chained `.pipe()` /
  nested list comprehensions that need re-reading count).

## Dependency Rules

- Follow the existing lockfile and package manager (this project: `uv`).
- Add dependencies only when they solve a clear problem; prefer maintained, typed libraries.
- Keep runtime dependencies separate from dev dependencies. Hook handlers take **zero**
  dependencies (stdlib-only — `.claude/schema/harness.json` `python.handler_min_version`).
- MUST NOT add a new package for trivial utilities.
- MUST NOT bypass lockfile updates.

## Incorrect / Correct

```python
# Incorrect — one god script: extract + features + train + eval, 1200 lines
# pipeline.py

# Correct — stage-per-module, each runnable and testable alone
# extract.py / features.py / train.py / evaluate.py
```
