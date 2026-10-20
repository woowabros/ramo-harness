---
title: Durable Evidence Only
impact: HIGH
tags: quality, evidence, sot
---

## Durable Evidence Only

Every citation in `docs/` must survive a fresh clone. This restates SOT-1 and SOT-1a
from `.claude/rules/common/sot-authoring.md` (the cross-skill SSOT) in ramo-doc's
worked-example style — do not fork the contract itself, only its illustration.

### What Counts as Durable

Cite only artifacts that survive a fresh clone: committed `file::symbol`, committed test
names, merged commit SHAs, issue/MR URLs, ADR paths. Forbidden as evidence: any path under
`.ramo/` (`plans/`, `todo/`, `interviews/`, `context/`, `logs/`), branch names, and
session/transcript IDs. This applies to body prose and `sources:` / `relates-to`
frontmatter alike.

`docs/` is a durable tree, so its code anchors are **symbols, not line ranges** — a line
number is a fact about today's formatting and dies on the first edit above it while still
looking precise. Use a line range only where no enclosing symbol exists (a config block, a
data file) and say so. A fact arriving here from a plan is re-anchored to a symbol on the
way in; copying the plan's line range across is how the citation rots
(`.claude/rules/common/sot-authoring.md` SOT-1 owns the contract).

### The Bare-Directory-vs-Filename Discriminator

A bare directory named as a workflow concept is not a citation; a concrete filename
cited as substantiating evidence is. Ask: *would a reader open this path to verify the
claim?*

**Permitted (bare directory, workflow concept, nothing to verify):**

```markdown
`ramo uninstall` preserves `.ramo/plans/` so prior planning artifacts remain on disk
after the harness is removed.
```

**Banned (specific plan file cited as substantiating evidence):**

```markdown
The temporal-split decision was made in `.ramo/plans/2026-09-24-trip-duration.md`, which
explains why split_boundary is 2023-01-22.
```

The second sentence asks the reader to open a `.ramo/` path to verify a design decision
— but `.ramo/` is gitignored working state, gone in another contributor's clone. The
fix is to cite the merged commit, the ADR, or the committed eval report that recorded
the decision, or restate it inline as a dated first-party assertion (SOT-1a).

A command example naming a plan path in passing is not a citation either —
`/ramo:run .ramo/plans/2026-09-24-trip-duration.md` illustrates command usage, it does not
substantiate a claim.

### Never Substitute Derived Provenance for Primary Evidence

When primary evidence is irrecoverable, the commit that merely added the document
recording it is not a valid replacement — that is circular (SOT-1a).

**Incorrect (circular substitution):**

```markdown
The 04:00 operating-day cutoff was chosen for the reasons described in commit a1b2c3d,
which added this document.
```

**Correct (dated first-party assertion, primary artifact not retained):**

```markdown
As of 2026-08-20, the 04:00 operating-day cutoff was chosen because a midnight cutoff
split one operating day's late-night trips across two partitions (observation; the original
EDA notebook that measured this was not retained).
```

### Rules

- Never cite `.ramo/**`, a branch name, or a session/transcript ID as evidence in
  `docs/**`, `CLAUDE.md`, or `README.md` — apply the discriminator above first.
- Never point a normative claim (`[HARD]`, MUST) at a plan file — see SOT-4 in
  `.claude/rules/common/sot-authoring.md` for valid enforcing-mechanism classes.
- When durable evidence cannot be found, say so explicitly rather than inventing a
  citation or laundering it through the commit that recorded it.

See `.claude/rules/common/sot-authoring.md` for the full SOT-1/SOT-1a/SOT-4 contract
this rule restates; do not duplicate the contract text itself, only illustrate it here.
