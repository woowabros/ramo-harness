---
description: User-facing explanation contract — structure, accuracy, and comprehension rules for main-session prose
---

# Explanation Style

Loaded globally (no `paths:`): this governs how the main session *explains*, which is not tied
to which files are edited.

## Scope

- **Applies to**: conversational explanation prose the main session emits to the user
  (in `RAMO_DOCUMENTATION_LANGUAGE`).
- **Does not apply to**: sub-agent report prose, `result` envelopes, code, identifiers,
  file paths, commands — all stay English per `common/language-settings.md`.

## Rules

### Scope layer

0. Structure rules (1-4) apply only to multi-topic explanations, substantive decision requests,
   and completion reports with two or more outcomes — not to single-fact queries, yes/no
   confirmations, code-only responses, or one-line command-result reports.
   **Never add a heading or a skeleton step to fill length.** Accuracy rules (5-8) apply
   whenever the corresponding claim appears, regardless of response length.

### Structure layer

1. Section headings are noun phrases (Problem, Root Cause, Changes, Impact, Decision, ...).
   Not a closed set; a user-specified or skill-prescribed format takes precedence.
2. References and ordinals must be self-identifying at first mention. Do not use a document
   number, ticket, or ordinal whose referent is ambiguous.
3. Classify the response type and apply exactly one skeleton:
   - Unresolved problem: current state → background → scope of impact → open items
   - Completed work: change and rationale → impact → trade-offs → verification → next steps
   - Explanatory answer: subject and scope → current mechanism → evidence → boundaries
   Omit any step with no content.
4. **Do not lead a completion report with verification statistics.** What was done and why
   comes first.

### Accuracy layer

5. Interpret every number used as evidence against its baseline and expected value.
   `398 passed (-2)` alone is bad; state why -2 is expected. Identifiers are exempt.
6. Distinguish fact, inference, proposal, and unknown. Never invent history for a reversed
   decision — state how far verification reached.
7. Support code claims as `file:line-range` or `file::symbol` for investigated repository
   behavior; for proposals or anything unverifiable, state that status and do not invent a
   location. Conversation is consumed immediately, so a line range is fine here — the
   symbol-only form is required of durable documents, where line numbers rot
   (`common/sot-authoring.md` SOT-1).
8. Attach to every substantive unresolved choice: (a) feasible options and what each means,
   (b) the recommended option and why, (c) how deliverables change under that choice. When a
   constraint leaves one viable path, state the constraint instead of inventing alternatives.

### Comprehension layer

9. Explain for a reader who did not write the code. Lead with what the system does for a
   user; an identifier is trailing evidence, not the subject, unless the request names it.
   Plain spoken register in the body; a toy example precedes the real control flow when the
   answer is explanatory.
