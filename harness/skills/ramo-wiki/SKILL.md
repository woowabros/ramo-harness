---
name: ramo-wiki
description: "Author and publish a wiki lesson, constraint, note, or pipeline overview through the transaction gate — draft, deterministic validation, semantic review, commit. Invoked by ramo-doc's promotion triggers or directly when a caller already has a candidate fact to record."
argument-hint: "[subtype] [slug] [evidence: what happened, why it matters, where the evidence lives]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Wiki Publish

Execution contract: `.claude/rules/common/skill-contract.md` (cited, not restated).
Language: conversation follows `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`); prompts,
paths, and commands stay English.

Rules to read before Step 1: `.claude/skills/ramo-wiki/rules/foundation-schema-contract.md`,
`.claude/skills/ramo-wiki/rules/foundation-transaction-lifecycle.md`,
`.claude/skills/ramo-wiki/rules/foundation-dead-document-prevention.md`.

This skill is a workflow step invoked by another skill's instructions (`ramo-doc`'s
promotion triggers, `.claude/rules/workflow/05-doc.md`) or directly when the caller already
has a specific fact and evidence in hand — it is not a top-level `/ramo:*` command, the
same pattern `ramo-explain` uses for `ramo-plan` and `ramo-verify`.

You (the main session) run the transaction; `ramo-wiki-writer` and `ramo-wiki-reviewer`
never touch `wiki_runtime.py` (`bash_class A`, structurally incapable of it).

## Step 0 — Resolve subtype, slug, evidence, and the source set

From the caller's context, determine:
- `subtype`: `lesson` (a recurring failure and its guard), `constraint` (a rule to obey, with
  allowed exceptions), `note` (a fact worth recording without a repair contract), or `overview`
  (what the pipeline currently looks like — one per pipeline or experiment family, rewritten
  rather than appended to when the shape changes).
- `slug`: kebab-case, matching `.claude/rules/common/naming.md`.
- The evidence itself: the verify report, the run finding, or the rejected-approach
  record — pass this in full to the writer, never a summary of it.
- **The source set, optionally.** `--sources` is optional at `begin` and the seal is taken at
  `stage` from the draft's own citations. Declare a set only when you already know it: a
  declared set stays a closed set the draft may not leave, which is the tighter gate. Guessing
  one is what the optionality exists to stop — an orchestrator that guesses before the draft
  exists guesses wrong, and the old order killed two legitimate drafts for citing a committed
  file the caller had not listed.
- **Confirm the evidence is committed, before `begin`.** Run `git ls-files <path>` on every
  path the evidence lives in. An untracked path cannot be sealed at any point in this
  transaction, so the check belongs here rather than as a stage failure — see
  **Precondition: the evidence must be committed** below.

Abort condition: no concrete evidence exists yet (only an intent to write something) —
BLOCKED, ask the caller for the evidence first.

### Precondition: the evidence must be committed

- **[HARD] Before `begin`, run `git ls-files` over the evidence paths. Any untracked path is a
  stop: ask the caller (or the calling stage) to commit it, and only then open the
  transaction.**
  WHY: observed. Every promotion candidate of one cycle failed at the same place, because
  `seal_sources` rejects anything outside `git ls-files` and neither `run` nor `verify` commits
  its own outputs while `ramo-doc-writer`'s write scope is `docs/` with no commit authority.
  The actual resolution was a person committing by hand, which means the precondition was real
  and unowned. Moving the check before `begin` costs one command and turns a batch of identical
  transaction failures into one question. Enforced by this step and
  `wiki_runtime.py::seal_sources` as the backstop (mechanical) — model-discipline grade for the
  check happening early.
- Ask with a single `AskUserQuestion`: ① commit the evidence now and continue ② skip this
  candidate and record why ③ stop. Never commit on the caller's behalf: this skill's write
  scope is `wiki/` and the transaction directory.

Use `begin --dry-run` to check a target and source set without opening a transaction:

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py begin --subtype <subtype> --slug <slug> --sources <paths> --dry-run
```

## Step 1 — Begin the transaction

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py begin --subtype <subtype> --slug <slug> [--sources <path-or-glob>[,...]]
```

A non-zero exit here (target already exists, bad slug, an unresolved declared source) is a hard
stop — report the error to the caller and do not proceed. Keep the printed `tx-id` for every
following call.

- **[HARD] Do not edit any source between `stage` and `commit`.** The seal is taken at `stage`,
  so an edit before staging is inside the sealed bytes and an edit after it is a mismatch.
  WHY: `stage` records a sha256 for every file the sealed set resolves to plus one aggregate
  attestation; `commit` recomputes them and aborts with `ATTESTATION_MISMATCH` if anything
  moved, because the reviewer then approved a document describing bytes that no longer exist.
  Both prior gates can pass and this one still fires — that case was observed in an earlier
  version, not a hypothetical. Enforced by `wiki_runtime.py::cmd_stage` +
  `::cmd_commit` (mechanical).
- **A declared set is a closed evidence set.** When `--sources` was given, `validate` fails
  with `sources-closed-set` if the candidate cites a path outside it, so the writer cannot
  widen a set the caller asserted (`wiki_runtime.py::validate_candidate`). With no declared
  set there is nothing to widen: the draft's citations *are* the set, and every one of them
  still has to resolve to a committed file.

## Step 2 — Draft

Spawn `ramo-wiki-writer` with the subtype, slug, and full evidence. Expect
`<ramo>DONE</ramo>` with the candidate document in the body.

**n candidates from one cycle are one writer spawn, not n.** This is the normal path, not an
optimization: pass all n (subtype, slug, evidence) triples in one prompt and expect n candidate
documents in one body, each opening with its own `## Candidate: <subtype> / <slug>` heading.
The reviewer is likewise spawned once for all n. **Transactions stay per document** — one
`begin`/`stage`/`validate`/`record-review`/`commit` chain each — because the one-target
guarantee is what makes a partial publish impossible.

- **[HARD] Do not spawn the writer or the reviewer once per candidate when the candidates come
  from the same cycle.**
  WHY: observed. One cycle's candidates consumed far more agent spawns than necessary, and the
  per-document spawning was the second-largest contributor after the writer not knowing the
  reviewer's criteria. Nothing about drafting document 2 depends on document 1's transaction,
  so the spawn boundary was never load-bearing; the transaction boundary is, and it stays.
  Enforced by this step — model-discipline grade, no mechanical check (no gate can count what
  a caller chose not to batch).
- A candidate whose evidence is untracked is dropped from the batch at Step 0, not carried into
  it. One untracked path must not stall the other n-1.

- **[HARD] No body received = re-spawn once, then `BLOCKED` if the second spawn also
  loses the body.** Never re-spawn a third time and never proceed on a missing body.
  WHY: observed during testing: most sub-agents lost their body on first resumption, so body
  loss must never sit on a critical path unguarded. `ramo-wiki-writer`'s candidate is
  exactly that — the only copy of the drafted document.

Write the candidate to a scratch file for the next step (do not paraphrase it).

## Step 3 — Stage and validate

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py stage --tx <tx-id> --body-file <scratch-file>
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py validate --tx <tx-id>
```

**Several candidates at once: one line per candidate, the pair written out.**

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py stage --tx tx-a1 --body-file /tmp/ramo/trip-duration-window.md
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py stage --tx tx-b2 --body-file /tmp/ramo/zone-partition-grain.md
```

- **[HARD] Never pair tx-ids with body files through array indexing, positional zips, or any
  other construct that keeps the two lists apart. The id and its file appear on the same line.**
  WHY: observed. One batch was staged by indexing two shell arrays, the shell's arrays are
  1-indexed where the loop assumed 0, and **most of the batch's documents were staged into the
  wrong transaction**. `validate` caught only one. It compares the candidate's frontmatter
  `category` against the transaction's `subtype`, so a swap between two transactions of the
  same subtype satisfies it exactly — the more candidates of one kind a batch holds, the lower
  the detection rate. Sealing is no help either: the sealed source set is derived from the
  document's own citations, so a misplaced document seals its own sources successfully. The
  batch was aborted and restarted, so nothing wrong was published; the next one might not be
  noticed. Enforced by this step — model-discipline grade for the shell that is actually
  written; the `stage` echo below makes a swap visible.
- After each `stage`, read back the line it prints: it names the transaction, the subtype, and
  the candidate's own title. A title that does not belong to the transaction you meant is the
  swap, visible at the moment it happens rather than at review.

- `PASS` → go to Step 4.
- `FAIL` with `ESCALATE: USER_DECISION_REQUIRED` in stderr → **stop, surface the two
  unchanged failures to the user, do not spend the remaining repair attempt automatically**
  (`foundation-transaction-lifecycle.md`).
- `FAIL` without escalation, transaction still `NEEDS_REPAIR` → re-spawn
  `ramo-wiki-writer` with the validation errors appended to the evidence, return to Step 2.
  The runtime's own budget (2 attempts) bounds this loop; do not add a second counter.
- `FAIL`, transaction now `NEEDS_HUMAN` → the repair budget is spent and the loop could not
  close the gap. Report the draft's path and every rejection reason to the user; the
  transaction directory is kept with `needs_human_reason` and `failed_checks` in its
  `state.json`, the draft survives at `candidate.md`, and nothing was published. A person
  repairs the draft and re-runs `stage`, or aborts deliberately. **Budget exhaustion never
  reaches `ABORTED`** — that state is reserved for a contract violation (attestation mismatch,
  a failed publish swap, an explicit `abort`).
- `FAIL` with `sources-closed-set` → the candidate cited evidence outside the sealed set.
  This is not a redraft loop: either the writer must cite only the declared sources, or the
  source set itself was wrong, in which case `abort --reason` and begin again with the
  correct set.

## Step 4 — Review

Spawn `ramo-wiki-reviewer` with the candidate and its cited sources. Expect
`<ramo>DONE</ramo>` with `verdict: APPROVE | REJECT` in the envelope, or
`<ramo>BLOCKED</ramo>` with no `verdict:` field.

- Same body-receipt HARD rule as Step 2: no body = one re-spawn, then BLOCKED.
- **[HARD] `<ramo>BLOCKED</ramo>` from the reviewer means the evidence cannot settle a
  competing claim. Do NOT call `record-review`, do NOT re-spawn the writer: surface the
  reviewer's `사용자 결정 필요` section to the user, ask its question, and wait.** With the
  user's answer, return to Step 2 with that answer appended to the evidence; if the user
  declines to decide, `abort --reason` the transaction.
  WHY: a question about which of two sources is authoritative is not a drafting defect, so
  a redraft cannot resolve it — calling `record-review --verdict REJECT` here would spend a
  repair attempt on a redraft that lands on the same ambiguity, and two of those aborts the
  transaction. Skipping `record-review` is what keeps the budget intact, and it is the same
  reason the reviewer's BLOCKED envelope omits `verdict:` entirely. Enforced by this step —
  model-discipline grade; the runtime cannot tell a skipped call from a call not yet made.

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py record-review --tx <tx-id> --verdict <verdict> [--report-file <reviewer-report-file>]
```

`--report-file` is required only for `APPROVE` (the runtime rejects `APPROVE` without
one). A `REJECT` needs no report file — the mapping rule
(`foundation-transaction-lifecycle.md`) writes no review-record for it.

- `APPROVE` → go to Step 5.
- `REJECT` → re-spawn `ramo-wiki-writer` with the reviewer's blocking issues appended to
  the evidence, return to Step 2 (Step 3's `stage`/`validate` runs again on the redraft).
  The same repair budget covers review rejections and validation failures together.

## Step 5 — Commit

```
python3 .claude/skills/ramo-wiki/scripts/wiki_runtime.py commit --tx <tx-id>
```

Prints the committed path (`wiki/<subtype>s|constraints|notes/<slug>.md`) and regenerates
`wiki/index.md`. The transaction directory is removed on success.

## Report and Next Step

End with a report in `RAMO_DOCUMENTATION_LANGUAGE`, not an envelope (this is a
main-session skill, per the execution contract cited above):

- What was published (path) or why it was not (aborted / blocked, with the reason)
- The evidence it cites
- Any concern the writer or reviewer raised even after approval

Next step: nothing further for a lesson/note; a constraint's caller may want to add a
cross-reference from the nearest category document. When invoked from `05-doc.md`'s
promotion triggers, hand control back to that step's own next step.

## See Also

- `.claude/rules/workflow/05-doc.md` Promotion Triggers — what invokes this skill and when
- `.claude/rules/common/output-contract.md` — the fourth vocabulary layer (transaction
  state) this skill's Bash output carries, kept separate from `<ramo>`/`verdict:`
