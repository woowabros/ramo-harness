---
description: The wiki publish transaction state machine, repair budget, writer/publisher separation, and escalation contract. Cites wiki_runtime.py as the enforcing mechanism, does not restate its logic.
---

# Wiki Transaction Lifecycle

Enforcing mechanism: `.claude/skills/ramo-wiki/scripts/wiki_runtime.py` (python3 stdlib
CLI, carrying an earlier multi-script runtime's state-machine contract as a single
consolidated script).

## States

```text
STAGING -> VALIDATING -> READY -> COMMITTING -> COMMITTED
              |
              +-> NEEDS_REPAIR -> VALIDATING   (attempt 1)
              +-> NEEDS_REPAIR -> VALIDATING   (attempt 2)
              +-> NEEDS_REPAIR -> NEEDS_HUMAN  (attempt 3 would exceed the budget)
```

`begin` opens STAGING and records the transaction's single target path
(`wiki/<subtype>s|constraints|notes/<slug>.md` — spelled out per subtype in
`foundation-schema-contract.md`). That target is the transaction's whole manifest scope
and it cannot change after `begin` — a simplification of an earlier version's multi-target
manifest, but the invariant it guards ("scope frozen after begin, no partial publish") holds
trivially with exactly one target.

## Source attestation: the third gate

`stage` seals the evidence set: the draft's own cited sources, unioned with any set `begin
--sources` declared (optional). The seal is a sha256 per file the sources resolve to (a glob
seals its whole current match set) plus one aggregate `sources_attestation_sha256`.

- **[HARD] `commit` recomputes the attestation and aborts with `ATTESTATION_MISMATCH`
  when any sealed source changed after `stage`.**
  WHY: the two-report gate above proves the candidate was well-formed and that a reviewer
  read it — neither says the sources still hold the bytes that reviewer read. In an earlier
  version a transaction passed both reports and still had to be redone for exactly this
  reason, and that abort was known only because a later reviewer described it in prose.
  The operational consequence is a rule for callers: open the transaction after the code has
  stopped moving. Enforced by `wiki_runtime.py::seal_sources` and `::cmd_commit` (mechanical).
- **[HARD] A declared set is also the closed evidence set: `validate` fails with
  `sources-closed-set` when the candidate cites a path outside what `begin --sources`
  declared.**
  WHY: an author who may open anything and cite it leaves no way to establish afterwards
  what was *not* consulted, which is the audit question that matters when a durable claim
  turns out to be wrong. Enforced by `wiki_runtime.py::validate_candidate` (mechanical).

## Every death records its cause

- **[HARD] Every path into `ABORTED` writes `abort_reason`, `failed_checks`, and
  `aborted_at` into the transaction's `state.json`, and the directory is kept.**
  `abort` therefore requires `--reason`.
  WHY: an earlier version recorded `{"attempt": 0, "status": "ABORTED"}` and an empty journal,
  so "why did this die" was unanswerable from the record — several aborted transactions in one
  cycle left no cause between them. A gate that can kill work owes an explanation to whoever
  finds the corpse. Enforced by `wiki_runtime.py::_abort_state` (mechanical), and
  `::cmd_abort` refuses a reasonless abort.
- `begin --dry-run` judges a target and source set without creating state, so probing what
  the runtime accepts never needs a real transaction (an earlier version's exploration opened
  and aborted several just to probe).

## The two-report commit gate

- **[HARD] `commit` refuses without both a PASS validation-report (deterministic,
  `wiki_runtime.py validate`) and an APPROVE review-record (semantic,
  `ramo-wiki-reviewer`).**
  WHY: a single gate conflates "well-formed" with "sound", and testing an earlier version
  caught the exact defect this pair is built to prevent — a candidate whose sections were
  all present and whose sources all existed, but whose central claim had no citation
  actually backing it. Enforced by `wiki_runtime.py::cmd_commit` (mechanical; refuses and
  names which of the two is missing).
- **[HARD] A REJECT verdict from `record-review` never writes a review-record.** It goes
  straight to `NEEDS_REPAIR`, consuming the same repair budget a validation failure does.
  WHY: a rejected review-record sitting in the transaction directory reads as "reviewed"
  to anyone who lists the directory contents even though the verdict was negative;
  omitting the file entirely makes "no review-record exists" the one, unambiguous signal
  for "not yet approved". Enforced by `wiki_runtime.py::cmd_record_review`.

## The reviewer's three outcomes, mapped onto two vocabularies

The semantic review has three possible outcomes, and this harness expresses them with the
vocabularies it already has rather than a new envelope field:

| Outcome | Reviewer emits | Orchestrator does | Budget |
|---|---|---|---|
| sound and sourced | `verdict: APPROVE` + `<ramo>DONE</ramo>` | `record-review --verdict APPROVE --report-file …` | untouched |
| unsupported claim, fixable by redrafting | `verdict: REJECT` + `<ramo>DONE</ramo>` | `record-review --verdict REJECT` | one attempt |
| evidence cannot settle a competing claim | `<ramo>BLOCKED</ramo>`, **no** `verdict:` | ask the user, never `record-review` | untouched |

- **[HARD] The third outcome never reaches `record-review`.**
  WHY: an earlier version carried this outcome as a third value in a `review_outcome` envelope field; this
  harness already owns the same exit in the `<ramo>` tag, where `BLOCKED` is defined as
  "cannot proceed, needs human, never auto-retried" (`common/output-contract.md`). Reusing it
  avoids a fifth vocabulary layer and, more importantly, keeps the repair budget honest: a
  question about which of two sources is authoritative is not a drafting defect, so a redraft
  cannot answer it and the two attempts it would consume both land on the same ambiguity.
  Enforced by `subagent_stop.py::main` for the tag's closed set (mechanical) and by
  `.claude/skills/ramo-wiki/SKILL.md` Step 4 for the skipped call (model-discipline grade).

## Repair budget and escalation

At most two `NEEDS_REPAIR` round-trips (`REPAIR_BUDGET = 2` in `wiki_runtime.py`); a third
failure hands the transaction to a person (`NEEDS_HUMAN`, draft kept) rather than looping
forever.

- **[HARD] When the same check fails on two consecutive `validate` calls, the runtime
  prints `ESCALATE: USER_DECISION_REQUIRED` and the orchestrating skill MUST stop and ask
  the user rather than spending the remaining repair attempt on the same fix.**
  WHY: a repair loop redrafts the candidate, but an unchanged failure on the same check
  means the redraft did not address the actual defect — spending the last attempt
  automatically wastes it and still lands on `NEEDS_HUMAN` with the draft unfixed. This
  turns the design principle "ambiguity stops at USER_DECISION_REQUIRED; never edit by
  inference" into a concrete signal rather than leaving it as prose the orchestrator must
  remember unprompted. Enforced by `wiki_runtime.py::cmd_validate` (mechanical: compares
  this round's failed-check set against the last one) for the *detection*; the *stop* is
  model-discipline grade — no gate can force the orchestrating skill to actually pause.

## Writer / publisher separation

`ramo-wiki-writer` returns candidate bytes as its final message body; it never calls
`wiki_runtime.py`. Only the orchestrating skill (main session) invokes `stage`, `validate`,
`record-review`, and `commit`. This is a **tools-frontmatter** guarantee, not a prompt
instruction: `ramo-wiki-writer` and `ramo-wiki-reviewer` are both `bash_class A` (full Bash
deny, `.claude/rules/workflow/12-subagent-bash-hygiene.md`), so neither agent is capable of
running the CLI even if its own prompt were somehow subverted.

## Argument contract

Every subcommand's flags and an example invocation are declared once, in the script's own
`argparse` help (`python3 wiki_runtime.py <subcommand> --help`) — not restated in this
rule or in `harness/schema/harness.json`. A `--help` string cannot drift from the code
that parses it the way a hand-copied markdown table can; an earlier version shipped exactly
such a docs/behavior mismatch for one of its flags, and a second static copy here would
reproduce the same class of bug.

## Error and validation discipline

- Every CLI error names which argument, why it is wrong, and how to fix it (`CliError` in
  `wiki_runtime.py`) — never a bare code or an unqualified message.
- All arguments are validated before any transaction-mutating operation runs (subtype and
  slug shape checked in `begin`; file existence checked in `stage`/`record-review`) — a
  malformed input returns a named validation error, never an uncaught traceback.

## See Also

- `foundation-schema-contract.md` — what `validate` checks the candidate against
- `foundation-dead-document-prevention.md` — the `sources` resolution check inside `validate`
- `.claude/rules/common/output-contract.md` — the fourth vocabulary layer this state
  machine occupies, kept separate from `<ramo>`/`verdict:`/report-body labels
