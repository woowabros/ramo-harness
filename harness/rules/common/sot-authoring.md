---
description: SoT authoring contract — durable evidence only, hard delete on change, normative statements name an enforcing mechanism
paths:
  - "docs/**/*.md"
  - "**/CLAUDE.md"
  - "README.md"
  - ".claude/rules/**/*.md"
---

# SoT Authoring

Rules for any durable canonical document: a Source-of-Truth (SoT) statement must survive a
fresh clone, carry its own technical explanation, and stay current through hard delete rather
than accumulated deprecation banners.

`.claude/agents/ramo/ramo-doc-writer.md` carries SOT-1 and SOT-4 as agent-level HARD constraints
in condensed form, citing the IDs rather than repeating the text; SOT-2 and SOT-3 live only
here. This file is the SoT for all four. No mechanical check compares the two — keep the IDs
aligned by hand whenever either side changes.

## SOT-1 — Durable evidence only

Cite only artifacts that survive a fresh clone: committed `file::symbol`, committed test names,
merged commit SHAs, issue/MR URLs, ADR paths. Forbidden as evidence: any path under `.ramo/`
(`plans/`, `todo/`, `interviews/`, `context/`, `logs/`), branch names, and session/transcript
IDs. Applies to body prose **and** `sources:` frontmatter.

**A durable document cites `file::symbol`, not a line range.** A line number is a fact about a
file's current formatting, not about the code, so it decays on the first edit above it while
still reading as precise.

- **[HARD] In a durable document (`docs/**`, `wiki/**`), anchor a code claim to a symbol.
  Use a line range only when there is no enclosing symbol to name (a config block, a data
  file), and say which it is.**
  WHY: observed in practice — one refactor moved code and invalidated dozens of line-range
  citations in a single wiki document at once; after converting to symbols, the same
  document's citations survived. The distinction is lifespan, not accuracy: a plan's
  citations are consumed in the session that wrote them, where a line range is the more precise
  of the two, so `.claude/rules/workflow/01-plan.md` deliberately keeps line ranges. Enforced at
  review time by `ramo-wiki-reviewer` for `wiki/**` and by `ramo-doc-writer`'s SOT-1 constraint
  for `docs/**` — model-discipline grade, no mechanical check (no gate can tell a stale line
  number from a fresh one).

**Discriminator:** a bare directory named as a workflow concept is not a citation; a concrete
filename is. `.ramo/plans/` describing what `ramo uninstall` preserves is legitimate; a specific
`.ramo/plans/2026-08-20-example.md` cited as substantiating evidence is a banned citation.
Likewise `/ramo:run .ramo/plans/2026-08-20-churn.md` in a command example is not evidence.
Test: *would a reader open this path to verify the claim?*

## SOT-1a — Never substitute derived provenance for primary evidence

When primary evidence is irrecoverable, the commit that merely added the document recording it
is **not** a valid replacement — that is circular. The correct repair is to restate the observed
facts inline as dated first-party assertions with an explicit note that the primary artifact was
not retained, or to re-derive the fact from committed code. Never fabricate a citation, and never
delete a substantiated finding merely because its pointer died.

## SOT-2 — The document carries the mechanism

A SoT statement must be verifiable without opening any other tracker. State the enforcing code
and its behavior, why an alternative fails, and the observable consequence. A pointer to where
work is tracked never substitutes for the technical explanation.

**Incorrect** — defers to a plan file's change unit:

> `[HARD]` This validator will reject aspirational claims. See
> `.ramo/plans/2026-08-20-example-replan.md` for the mechanism.

**Correct** — names the validator, its closed field set, and why a rename cannot work:

> `[HARD]` `hooks/ramo/handlers/subagent_stop.py::main` rejects a `<ramo>` status outside the
> closed set (`_common.py::STATUS_VALUES`). Renaming the status alone does not satisfy this,
> because the handler checks membership in the closed value list, not surface wording.

## SOT-3 — Hard delete on change

When a fact changes, delete the stale text in the same commit. Git history is the archive.
Forbidden by default: `DEPRECATED`/`STALE` banners, strikethrough, "previously..." narration,
retained superseded sections.

**Exemptions (closed, normative):** soft deprecation is required for exactly these three
document classes, and only these: ADRs (immutable decision records, superseded via
`status: superseded` + `superseded-by:` / `supersedes:`); externally-consumed versioned API
contracts; and CHANGELOG/release notes (append-only by nature).

**ADR immutability scope:** immutability governs the **decision content** — Context, Decision,
Consequences. Evidence pointers (`sources:`, reference lists) are **metadata**, not decision
content, and MUST be corrected in place when they rot. Correcting a dead pointer does not alter
the decision and does not require supersession.

## SOT-4 — Normative statements assert current enforced behavior

A `[HARD]`, MUST, or contract statement describes what is enforced **now**, and names its
enforcing mechanism. Valid mechanism classes are: a hook handler, a validator/linter, a test,
a CI gate, a named review-time gate (a specific agent's REJECT condition), or **model
discipline** — a rule the agent is expected to follow with no mechanical backstop. A target
state is never written as a normative rule; a known gap goes in a clearly non-normative, dated
section tracked by a durable identifier (issue/MR/ADR) — never a plan-file path.

**Model discipline counts only when the statement says so.** Write the grade next to the
mechanism (`model-discipline grade, no mechanical check`). Most of this harness is prompt text,
where some contracts cannot be checked mechanically even in principle; saying so is the point
of SOT-4, and an unlabelled mechanism reads as a mechanical one.
`workflow/12-subagent-bash-hygiene.md` already grades its three enforcement layers this way.
An unlabelled claim is how a rule ends up naming a check that was never written.

## See Also

- `.claude/rules/common/INDEX.md` — common rules registry.
- `.claude/schema/harness.json` — machine-readable authoring SSOT the hooks and skills read.
- The consuming repository's own SoT entry point and citation conventions, when it keeps one.
