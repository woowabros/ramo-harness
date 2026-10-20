---
title: Dataset Document Template
impact: HIGH
tags: template, dataset, data, snapshot
---

## Dataset Document Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

Dataset documents live in `docs/data/` and are the single source of truth for how a
dataset is obtained, snapshotted, and trusted. Every model card and analysis that
consumes the dataset links here instead of restating extraction details. A dataset
without this document cannot satisfy the harness reproducibility gate honestly — the
`data_snapshot` key in envelopes should point at a policy this document defines.

Structural lineage: this template adapts a database-documentation shape (overview →
schema tables → constraints → migration log) to DS datasets (overview → source → schema
→ snapshot policy → quality → changelog).

**Incorrect (extraction details scattered, no snapshot policy, no PII note):**

```markdown
---
title: Trips Data
---

We pull trips from the warehouse with a big SQL query. Ask the team for details.
```

**Correct (full template):**

```markdown
---
type: Dataset
title: Yellow Trips Snapshot
category: data
status: stable
created: 2026-08-20
updated: 2026-08-20
tags: trips, snapshot, duckdb
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-20T05:00:00Z }
relates-to: sql/trips_snapshot.sql
sources:
  - id: trips-ddl
    resource: tlc.yellow_trips (ramo-data.py schema)
    last_modified: 2026-08-01
---

# Yellow Trips Snapshot

## Overview

One paragraph: what this dataset is, what it is for, and who consumes it.

## Source

| Item | Value |
|---|---|
| Origin tables | `tlc.yellow_trips`, `tlc.taxi_zones` (verified via the data access adapter)[^trips-ddl] |
| Extraction query | `sql/trips_snapshot.sql` (committed; `query_hash` derives from this file) |
| Access path | the data access adapter (`.claude/scripts/ramo-data.py`) only — see `.claude/rules/data/warehouse-access.md` |

## Schema

| Column | Type | Description | PII |
|--------|------|-------------|-----|
| PULocationID | integer | Pickup zone; joins `tlc.taxi_zones.LocationID` | no |
| VendorID | integer | Taxi technology provider; no person identifier | no |
| tpep_pickup_datetime | timestamp | Meter engaged (the prediction anchor) | no |
| pickup_date | date | Partition key, `CAST(tpep_pickup_datetime AS DATE)` | no |

## Snapshot Policy

| Item | Value | 근거 |
|---|---|---|
| Snapshot id format | `tlc.yellow_trips/month=YYYY-MM` | Matches the recorded `data_snapshot` key verbatim so a card's value resolves without translation |
| Cutoff | 04:00 local | The fleet's operating day turns over at 04:00, so a midnight cut splits one operating day's late-night trips across two partitions |
| Cadence / retention | monthly / 12 months | Monthly matches the source's release grain; 12 months covers the longest feature window in use (28d) with room to re-run a full season |
| Re-obtain procedure | run the committed extraction query against the named month | The query is the only artifact that survives; a described procedure decays |

## Quality Checks

| Check | Expectation | Where enforced | 근거 |
|-------|-------------|----------------|------|
| Row count vs previous day | within ±20% | extraction script assertion | Day-over-day spread sat well inside ±20% across a month (illustrative); ±20% catches a truncated load without firing on a holiday |
| Null rate on PULocationID | 0 | extraction script assertion | It is the join key to `tlc.taxi_zones`: one null silently drops a row from every zone-level aggregate |
| Row reconciliation | artifact rows == source rows | extraction script assertion | A silently truncated download is invisible in any single number, which is why the equality is written out |

## PII Handling

Which columns are PII/pseudonymous, what redaction applies, and the rule that governs it
(`.claude/rules/common/untrusted-data-boundary.md`). Raw PII never appears in docs,
logs, or envelopes.

## Changelog

| Date | Change | Breaking |
|------|--------|----------|
| 2026-08-20 | Initial documentation | No |

[^trips-ddl]: Yellow trips table schema via `ramo-data.py schema tlc.yellow_trips`
```

Required sections: Overview, Source, Schema, Snapshot Policy, Quality Checks,
PII Handling, Changelog. A section that does not apply becomes `N/A — reason`, never an
omission (quality-completeness).

**Every table carries a 근거 column where the value was a choice.** A cutoff, a threshold, a
retention window and a check expectation are all decisions, and a template that shows only the
value teaches the next author to invent one. The contrast observed during testing: a template
that used `| Property | Value | Rationale |` with real values in every row raised document
quality more than adding further templates did.
