---
title: Frontmatter Schema (OKF v0.2 aligned)
impact: CRITICAL
tags: foundation, frontmatter, metadata, okf
---

## Frontmatter Schema (OKF v0.2 aligned)

Every document in `docs/` must begin with YAML frontmatter delimited by `---` lines.
Frontmatter is the machine-readable layer that enables agents to filter, sort, and
cross-reference documents without reading full content. The vocabulary follows the
OKF v0.2 spec (Open Knowledge Format,
https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md); the parts used
here are restated in this file, and the runtime never reads the upstream spec.

### Required Fields

| Field | Type | Values |
|-------|------|--------|
| `type` | string | OKF concept type — the only OKF-required key. Use descriptive values: `Dataset`, `Model Card`, `Analysis`, `Feature Spec`, `Runbook`, `ADR`, `Reference`, `Research Topic` |
| `title` | string | Human-readable document title |
| `category` | enum | `architecture` \| `data` \| `analysis` \| `feature` \| `model` \| `pipeline` \| `common-rules` \| `research` |
| `status` | enum | `draft` \| `stable` \| `deprecated` (OKF v0.2 lifecycle; ADRs keep MADR statuses — see exception) |
| `created` | ISO date | Date of first creation — never changes after set |
| `updated` | ISO date | Date of last update — must be updated on every change |
| `tags` | comma-separated | Keywords for Grep discovery — at least 2 |

### Optional Fields (OKF trust / provenance / lifecycle families)

| Field | Shape | Purpose |
|-------|------|---------|
| `generated` | `{ by, at }` | How the current content was produced. `by` is an actor (below); `at` is ISO-8601 datetime. Replaces legacy `timestamp` (accept `timestamp` only as a read fallback; never write it) |
| `verified` | list of `{ by, at }` | Verification events. A bare mapping counts as a one-element list. Trust tier is derived, never stored: no key = unverified; non-`human:` actors only = machine-confirmed; any `human:<id>` = human-reviewed |
| `sources` | list | Provenance entries. `resource` required per entry; `id` needed when the body cites the source; optional `title`, `author`, `usage_count`, `last_modified`; sibling `usage_window: { from, to }` |
| `stale_after` | ISO date | Absolute staleness date (`today >= stale_after` means stale). Replaces the legacy `stale-since` |
| `relates-to` | comma-separated paths | Source code paths this document describes |
| `depends-on` | comma-separated paths | Other docs this document depends on for accuracy |

**Actor convention (OKF §7):** `human:<id>` for people (`human:<your-id>`),
`process:<id>` for scheduled processes (`process:eval-nightly`),
`<producer>/<version>` for agents (`ramo-doc-writer/claude-sonnet-5`).

**Per-claim citation:** attribute a specific claim with a markdown footnote whose label
is a `sources[].id` — keyed, not positional, so agent rewrites cannot silently
misattribute:

```markdown
Yellow trips are partitioned daily by `pickup_date`.[^trips-ddl]

[^trips-ddl]: Yellow trips table schema
```

**ADR exception:** ADRs under `docs/architecture/adr/` keep the MADR status set
(`proposed` | `accepted` | `deprecated` | `superseded`) with `supersedes` /
`superseded-by` fields — decision records need supersession semantics that the 3-value
lifecycle cannot express. This is a deliberate deviation from OKF.

**Incorrect (no type, legacy keys, stored trust score):**

```yaml
---
title: Trip Duration Model
status: active            # Wrong: 'active' is legacy vocabulary, not OKF v0.2
timestamp: 2026-08-20     # Wrong: legacy key; write generated: { by, at }
trust_score: 0.9          # Wrong: trust is derived from verified events, never stored
---
```

**Correct (OKF v0.2 aligned):**

```yaml
---
type: Model Card
title: Trip Duration Model v2
category: model
status: stable
created: 2026-08-20
updated: 2026-08-21
tags: trip-duration, lightgbm, regression
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-21T04:12:00Z }
verified:
  - { by: human:<your-id>, at: 2026-08-21T09:00:00Z }
stale_after: 2026-11-21
relates-to: src/trip_duration/train.py
depends-on: docs/data/trips-snapshot.md
---
```
