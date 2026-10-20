---
title: Category Structure
impact: CRITICAL
tags: foundation, categories, structure
---

## Category Structure

All service documentation lives in `docs/` under exactly 8 DS category folders, aligned
with the harness domain axis (data / analysis / feature / model / pipeline + architecture,
common-rules, and research). Every document belongs to exactly one category. Choosing the right
folder determines whether a document can be found by agents and humans alike — a
misplaced document is effectively invisible.

The 8 categories and their ownership boundaries:

| Folder | Purpose |
|--------|---------|
| `docs/architecture/` | System-level structure, experiment infrastructure, ADRs (subdirectory: `adr/`) |
| `docs/data/` | Dataset docs: source tables, extraction queries, snapshot policies, quality checks |
| `docs/analysis/` | Durable conclusions of EDA and ad-hoc analyses — decisions, not scratch work |
| `docs/feature/` | Feature definitions, computation windows, leakage boundaries |
| `docs/model/` | Model cards, evaluation protocols (metric/slice), champion history |
| `docs/pipeline/` | Batch schedules, deployment, serving interfaces, runbooks |
| `docs/common-rules/` | Cross-cutting conventions, error patterns, logging standards |
| `docs/research/` | Research topics written by `ramo-research` before an interview: one folder per topic, its `README.md` the whole document |

Special files that live outside category folders:

- `docs/index.md` — the document catalog. Machine-generated where the repository ships a
  generator (an `AUTO-GENERATED` first line); hand-written otherwise
- `docs/GLOSSARY.md` — domain terms and abbreviations
- `docs/experiments.md` — the experiment ledger, one row per plan
  (`.claude/skills/ramo-doc/rules/template-experiment-ledger.md`). It sits outside the
  categories because it is the one document about the *sequence* of experiments rather than
  about any one of them; a category folder would file it under whichever experiment came first
- `docs/getting-started.md` — the first-cycle onboarding walkthrough, a single
  entry point rather than a per-category concern
- Each category must contain `_overview.md` — the entry point for that category

Two subdirectory kinds are permitted, and no others: `docs/architecture/adr/`, and one
folder per research topic, `docs/research/<topic>/`, holding that topic's `README.md` and its
optional HTML companion (`visual.html` or `README.html`) and nothing deeper. Every other
category is flat — no nested subdirectories. Research uses folders because topics are added by
several people in parallel: each person writes only inside their own topic folder, and the
category's `_overview.md` table is generated from the READMEs rather than edited by hand.

`docs/research/` is **created** by `ramo-research` from its own templates
(`.claude/skills/ramo-research/templates/`) and norms (`.claude/rules/workflow/00-research.md`),
not by this skill's category templates. This skill registers, cross-references, and
maintains those documents like any other — including rewriting a stale topic in place.

**`wiki/` is not a 9th category.** It is a sibling tree at the repository root
(`wiki/lessons/`, `wiki/constraints/`, `wiki/notes/`), published only through the
`ramo-wiki` transaction gate (`.claude/rules/workflow/05-doc.md` Promotion Triggers) —
never created here as a new `docs/` folder. A recurrence-prevention contract or a
constraint to obey belongs there, not in any of the 8 folders above.

**Incorrect (dataset doc placed in the model folder):**

```
docs/
  model/
    trips-snapshot.md     # Wrong: snapshot policy belongs in docs/data/
    trip-duration-card.md
```

**Correct (each document in its owning category):**

```
docs/
  data/
    trips-snapshot.md     # Correct: dataset doc lives in docs/data/
  model/
    trip-duration-card.md # Correct: model card lives in docs/model/
```

**Incorrect (inventing a new top-level folder):**

```
docs/
  experiments/            # Wrong: not one of the 8 categories
    trip-duration-v2-results.md
```

**Correct (route to the closest matching category):**

```
docs/
  analysis/
    trip-duration-v2-conclusion.md  # Correct: durable experiment conclusion lives in docs/analysis/
```
