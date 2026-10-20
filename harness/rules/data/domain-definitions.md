---
description: Domain facts a query has to encode — business-day boundaries, status sets, entity grain, exclusion predicates. Accumulated one line at a time; starts empty on purpose
paths:
  - "**/*.sql"
  - "**/*.py"
  - "notebooks/**"
---

# Domain Definitions (B)

**This file starts empty and grows one entry at a time.** It holds the class of knowledge that
exists only in people's heads: what a business term means when it becomes a predicate.

## What belongs here

A domain fact that a query must encode and that no tool will tell you.

| Belongs | Does not belong |
|---|---|
| "The fleet's operating day turns over at 04:00, so a daily aggregate cut at midnight splits one day's work in two" | Which table holds trip records, and its partition key |
| The closed set of `payment_type` codes that mark a trip as voided or disputed, and which of them still carry a fare | A verified query shape for daily aggregation |
| The grain a fact table is actually keyed at, when it differs from what its name suggests | A column's data type |

The two exclusions are deliberate. A table map goes stale and then beats the live catalog, which
the adapter's `search` and `schema` already answer; a query pattern belongs in the team's shared
query store, or next to the code that uses it, where other people's queries can find it. Both
were considered and rejected for this file.

## Entry format

One `###` heading per fact, in `RAMO_DOCUMENTATION_LANGUAGE`. Each entry carries:

- **The fact**, stated as the predicate or boundary a query would write.
- **Why it is not obvious** — what a reasonable person would have assumed instead.
- **Where it was learned**: a committed `file:line`, a document path, or a dated first-party
  statement when the source was a conversation (`common/sot-authoring.md` SOT-1a).
- **Scope**: which tables or which pipeline the fact holds for. A fact stated without scope gets
  applied where it is false.

Add an entry when an experiment discovers one. Do not seed this file speculatively: an invented
domain fact is worse than an absent one, because it reads as verified.

## Entries

*(none yet)*

## See Also

- `data/table-pitfalls.md` — traps in a table or a join, rather than facts about the domain.
- `data/warehouse-access.md` — the paths a query travels.
