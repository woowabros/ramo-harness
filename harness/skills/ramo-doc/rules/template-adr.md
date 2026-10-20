---
title: Architecture Decision Record (ADR) Template
impact: HIGH
tags: template, adr, architecture, decision
---

## Architecture Decision Record (ADR) Template

## Readability, in five lines

Full discipline: `.claude/rules/common/doc-readability.md`. The five habits it enforces:

1. A citation sits at the end of its sentence, once. Never mid-clause, never two per sentence.
2. A heading names its subject. The conclusion goes in the first sentence under it.
3. `##` only. A section that wants a `###` is a table or its own document.
4. A SoT, architecture, or overview document carries `## 핵심 불변식` — numbered, each line
   naming what verifies it.
5. Baselines, not caps: about 15 lines a section, about 150 a document. Crossing them prompts
   one question (is this two documents?) and nothing more.

ADRs capture significant technical decisions: why a choice was made, what alternatives
were rejected, and what consequences the team accepted. Store ADRs in
`docs/architecture/adr/` as `NNN-kebab-case-title.md` (e.g.,
`001-temporal-split-policy.md`).

**Whether a decision belongs here is not this file's judgement.** The four signals that route
a decision to `adr/` instead of a category document live in
`.claude/rules/workflow/05-doc.md` (Decision Routing) — read them there and do not restate
them, because a second copy drifts from the one the doc step actually applies. This file
governs the shape of the record once that test has already said "ADR".

ADRs are permanent records. Once accepted, they are never deleted — they are superseded
by newer ADRs (`status: superseded` + `superseded-by:`; the successor fills
`supersedes:`). This is why the routing test exists at all: `adr/` is the only place a
superseded decision survives, because every other document is hard-deleted on change
(`.claude/rules/common/sot-authoring.md` SOT-3).

Write ADRs at decision time, not after implementation; a retrospective decision loses the
context that made the alternatives feel real. Writing one **retroactively** is still better
than losing it, under three conditions: `created` carries the decision's own date rather than
today's, Context says the record was written after the fact, and every claim cites an artifact
the decision actually left behind. A retroactive ADR dated today claims a history it does not
have, and its alternatives read as invented because they are being reconstructed.

**Incorrect (no alternatives, no consequences, status missing):**

```markdown
---
title: We Use Temporal Splits
---

We decided to split train/test by time because random splits leak.
```

Problems: no ADR number, missing `type`/`status`/`created`/`updated`/`category`/`tags`,
no context, no alternatives (the decision looks unexamined), no consequences.

**Correct (full MADR template):**

```markdown
---
type: ADR
title: "ADR-001: Temporal Split as the Default Evaluation Split"
category: architecture
status: accepted
created: 2026-08-20
updated: 2026-08-20
tags: adr, evaluation, split, leakage
relates-to: src/trip_duration/split.py
depends-on: docs/architecture/_overview.md
supersedes:        # path to the ADR this one replaces, if any
superseded-by:     # filled in when this one is superseded
---

# ADR-001: Temporal Split as the Default Evaluation Split

## Status

`accepted` — Adopted on 2026-08-20. Implemented in `src/trip_duration/split.py`.

Valid statuses: `proposed` | `accepted` | `deprecated` | `superseded`.
When superseding, set `status: superseded` and fill `superseded-by`. Do not delete.

---

## Context

Describe the situation that forced a decision. Include: what was being modeled and what
data it used; which constraints applied (label delay, seasonality, compliance); the cost
of delaying the decision; what was uncertain at the time.

Example: trip durations follow the hour of day and the day of week, and traffic shifts
across the month. A random split let the model see trips from the same days and hours as the
test set, so the same traffic conditions sat on both sides, inflating offline MAE by about
0.5 minutes versus a later held-out week (illustrative). The team must fix the split policy
before any model comparison is meaningful.

---

## Decision

State the decision in one sentence, then the rationale referencing the Context.

**All model evaluations use a temporal split at a declared `split_boundary`; random
splits require an ADR-level exception.**

Rationale: same-day traffic conditions and the pickup zone's recent history both cross a
random split, so only a time-based boundary prevents leakage; a declared boundary also becomes the
reproducibility key (`split_boundary`) the harness envelope requires.

---

## Consequences

State every consequence knowingly accepted, in the three action-shaped kinds below. One
table, three groups of rows: the kinds are what a reader scans for, and a table keeps them at
one heading depth (`.claude/rules/common/doc-readability.md` R3). Omitting the costs is a red
flag that the decision was not examined honestly.

| 종류 | 내용 |
|---|---|
| 따라오는 작업 | Every experiment plan declares `split_boundary`; the run gate rejects model-training envelopes without it |
| 따라오는 작업 | The evaluation report gains a near-boundary slice so the shrinkage below is visible |
| 버려지는 것 | Maximal training data: the effective training set shrinks near the boundary, and recent-period behaviour is under-represented |
| 버려지는 것 | Cross-experiment comparability with any earlier random-split result |
| 남는 위험 | Seasonality inside the holdout window can still make one period look better than the model is; unmeasured, and the near-boundary slice is what would surface it |

---

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| **Random split** | Maximal training data; simple | Leaks same-day traffic conditions across the split | Inflated offline metrics, about 0.5 min MAE optimistic (illustrative) |
| **Group split (by pickup zone)** | Prevents zone-history leakage | Still leaks time (seasonality, drift) | Does not address the same-day traffic leak |
| **Rolling-origin CV** | Most faithful to deployment | Compute cost; complicates comparison across experiments | Adopt later for final candidates; overkill as the default |

---

## 확정을 막는 열린 질문

What is still unresolved, and what would settle it. `없음` is a valid answer only when the
decision is genuinely closed — write it explicitly rather than omitting the section.

- Rolling-origin CV for final candidates: adopt or not? Settled by measuring its compute cost
  on one real candidate, not by argument.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-20 | Initial draft, accepted after team review |
```

Required sections: Status, Context, Decision, Rationale, Consequences (one table, three
action-shaped kinds), Alternatives Considered, **확정을 막는 열린 질문**, Changelog.

**Why the consequences are action-shaped rather than Positive/Negative/Neutral.** An evaluative
label leaves the reader with nothing to do: "negative — training data shrinks" is a judgement,
while "버려지는 것 — maximal training data, and comparability with earlier random-split results"
names what was traded. The three kinds each answer a different question a reader arrives with:
what do I now have to do, what did I lose, what could still bite me.

**Why 열린 질문 is in the template at all.** In an earlier version of this harness the best ADR
produced in a real cycle carried exactly this section, although the ADR template did not ask for
it. The model absorbed the pattern from uncertainty outlets it had seen elsewhere in the cycle
and invented this one on its own, which means the quality was a habit rather than an asset and
the next session would not reproduce it. Putting it in the template is the cheapest fix: what
was obtained by accident is now obtained every time.

Reference: [MADR](https://adr.github.io/madr/) | [Michael Nygard — Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
