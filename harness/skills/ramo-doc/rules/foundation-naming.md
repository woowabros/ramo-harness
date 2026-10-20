---
title: Naming Convention
impact: CRITICAL
tags: foundation, naming, files
---

## Naming Convention

All filenames in `docs/` are lowercase kebab-case, topic-first, singular nouns, with no
dates. Consistent filenames make documents findable by glob patterns, prevent
duplicates, and group related files alphabetically in directory listings.

Rules at a glance:

| Rule | Rationale |
|------|-----------|
| Lowercase kebab-case only | Prevents case-sensitivity bugs across OS and tools |
| No category prefix in the filename | The folder is the category — `docs/data/trips.md` not `docs/data/data-trips.md` |
| Topic-first for subtopics | Groups related files: `trip-duration-card.md`, `trip-duration-eval-protocol.md`, `trip-duration-snapshot.md` |
| No dates in filenames | Dates belong in YAML frontmatter `created:` / `updated:` |
| Singular nouns | `feature-spec.md` not `feature-specs.md` |
| `_overview.md` per category | Underscore prefix sorts first in every directory listing |
| ADR exception: `NNN-title.md` | Sequential numbering enables ordering: `001-temporal-split-policy.md` |
| Research exception: `<topic>/README.md` | One folder per topic so parallel researchers never touch the same file; `README.md` renders when the folder is opened on GitHub or GitLab: `trip-duration-baselines/README.md` |

Glob patterns that must resolve correctly under these rules:

```
docs/data/*.md                   # All dataset documents
docs/model/trip-duration-*.md    # All trip-duration-model documents
docs/**/_overview.md             # Every category overview
docs/architecture/adr/???-*.md   # All ADRs
docs/research/*/README.md        # All research topics (one folder per topic)
```

**Incorrect (date in filename, plural noun, category prefix repeated):**

```
docs/model/2026-08-20-model-cards-trip-duration.md
```

Why this fails:
- `2026-08-20` — date belongs in frontmatter, not the filename
- `model-cards` — plural; and the `docs/model/` folder already provides this context

**Correct (topic-first, singular, no date, no redundant prefix):**

```
docs/model/trip-duration-card.md
```

**Incorrect (no topic grouping):**

```
docs/data/
  snapshot.md
  trips-table-snapshot-policy.md
  zones.md
```

**Correct (topic-first grouping):**

```
docs/data/
  _overview.md
  trips-snapshot.md
  zones-snapshot.md
```
