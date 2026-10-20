---
title: Completeness Check
impact: MEDIUM
tags: quality, completeness, template
---

## Completeness Check

Every document must fill all required template sections. Placeholder text, empty
sections, and TODO markers indicate an incomplete document.

### Rules

- All required sections from the category template must be present.
- No placeholder text: `[TODO]`, `TBD`, `...`, `Lorem ipsum`.
- No empty tables (headers with no rows) and no empty code blocks.
- Frontmatter must have all required fields filled (not `title: ""`).
- If a section genuinely does not apply, replace it with: `N/A — [brief reason]`.

### Completeness by Status (OKF v0.2 lifecycle)

| Status | Completeness Requirement |
|--------|------------------------|
| `draft` | Frontmatter complete, at least the Overview section filled; other sections may carry `[DRAFT]` markers |
| `stable` | All template sections filled, no placeholders, all examples verified |
| `deprecated` | Deprecation note present with a link to the replacement document |

**Incorrect (incomplete document claiming stable):**

```yaml
---
type: Model Card
title: Trip Duration Model v2
status: stable
---
# Trip Duration Model v2

## Intended Use
TODO: describe

## Evaluation
| Metric | Overall | Slice |
|--------|---------|-------|

## Reproducibility
TBD
```

**Correct (complete stable document):**

```yaml
---
type: Model Card
title: Trip Duration Model v2
category: model
status: stable
created: 2026-08-20
updated: 2026-08-21
tags: trip-duration, lightgbm
---
# Trip Duration Model v2

## Intended Use
Trip duration estimate at pickup for NYC yellow taxi trips, scored per trip.

## Evaluation
| Metric    | Overall | sparse-zone slice | airport slice |
|-----------|---------|-------------------|---------------|
| MAE (min) | 4.6     | 4.4               | 7.2           |

## Reproducibility
seed 42, split_boundary 2023-01-22, data_snapshot tlc.yellow_trips/month=2023-01.
```
