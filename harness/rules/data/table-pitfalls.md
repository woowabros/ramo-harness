---
description: Traps a table or a join hides — duplicate rows, 1:N explosion, columns filled after the prediction anchor, flags that disagree. Accumulated one line at a time; starts empty on purpose
paths:
  - "**/*.sql"
  - "**/*.py"
  - "notebooks/**"
---

# Table Pitfalls (C)

**This file starts empty and grows one entry at a time.** It holds what you can only learn by
being burned: the shape of a table or a join that produces a plausible wrong answer.

## What belongs here

A trap that produces a result which looks right. A failure that raises an error does not need an
entry; the error is the documentation.

| Belongs | Does not belong |
|---|---|
| "This table carries duplicate rows per key, so a naive count overstates by the duplicate rate" | "This column is nullable" (the schema says so) |
| "This join is 1:N and explodes the row count; deduplicate on the left before joining" | A query that fails with a type error |
| "This column is filled after the prediction anchor, so using it as a feature is leakage" | A column whose name already says what it is |
| "These two flags describe the same thing and disagree on a small fraction of rows; the population definition depends on which you pick" | Anything the adapter's `schema` or `search` answers |
| A trap in one table, one join, or one window | A property of the engine that holds for **every table** — those live in `data/engines/<engine>.md` Engine Facts, because an entry per table would be the same fact copied once per table and stale in most of them |

## Entry format

One `###` heading per trap, in `RAMO_DOCUMENTATION_LANGUAGE`. Each entry carries:

- **Symptom**: what you see that looks fine.
- **Cause**: the property of the table or join that produces it.
- **What to do instead**, concretely enough to write.
- **Measured evidence**: the numbers observed, with the date. A trap asserted without numbers
  cannot be told apart from a rumour.
- **Scope**: which table, which join, which window.

Add an entry the moment a trap costs someone time. That is the only moment when the numbers are
still in front of you.

## See Also

- `data/domain-definitions.md` — facts about the domain, rather than traps in its tables.
- `model/leakage.md` — the leakage checklist a post-anchor column trips.
