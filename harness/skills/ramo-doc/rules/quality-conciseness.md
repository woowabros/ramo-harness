---
title: Conciseness and No-Duplication
impact: MEDIUM
tags: quality, conciseness, duplication
---

## Conciseness and No-Duplication

Documentation should be concise and authoritative. Each piece of information lives in
exactly one place. Link to the source of truth instead of duplicating content.

### Rules

- One source of truth per topic. If the snapshot policy is documented in
  `docs/data/trips-snapshot.md`, other documents link to it rather than re-explaining.
- Keep documents focused. A document over 400 lines likely covers too much — consider
  splitting.
- Use tables over prose for structured data (schema columns, metrics, config vars).
- Avoid repeating what is obvious from the code itself. Document the WHY, not the WHAT.
- Prefer linking: `See [Yellow Trips Snapshot](../data/trips-snapshot.md)` over copying the
  snapshot section.

### Link vs Duplicate Decision

| Scenario | Action |
|----------|--------|
| Exact same information needed in two places | Link to the authoritative source |
| Brief context needed before linking | 1-2 sentence summary + link |
| Information is foundational to understanding the current doc | Inline it, but note the source |

**Incorrect (duplicated content across documents):**

```markdown
# docs/model/trip-duration-card.md
## Training Data
Trips are snapshotted monthly into tlc.yellow_trips partitioned by pickup_date. The
snapshot drops out-of-month pickups, applies the 04:00 operating-day cutoff, retains 12 months...
(40 lines of snapshot explanation)

# docs/model/fare-card.md
## Training Data
Trips are snapshotted monthly into tlc.yellow_trips partitioned by pickup_date. The
snapshot drops out-of-month pickups, applies the 04:00 operating-day cutoff, retains 12 months...
(same 40 lines copied)
```

**Correct (single source with links):**

```markdown
# docs/model/trip-duration-card.md
## Training Data
`tlc.yellow_trips` snapshots — see [Yellow Trips Snapshot](../data/trips-snapshot.md) for
policy, cutoff, and retention. This model trains on `pickup_date < split_boundary`.

# docs/model/fare-card.md
## Training Data
`tlc.yellow_trips` snapshots — see [Yellow Trips Snapshot](../data/trips-snapshot.md).
```
