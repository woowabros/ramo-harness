---
description: Sub-agent status tag (DONE / RETRY / BLOCKED) + result envelope format — enforced by the subagent_stop hook and orchestrator parsing
---

# Output Contract

Loaded globally (no `paths:`): this contract governs every sub-agent response regardless of
which files are touched, so conditional loading would leave gaps exactly where enforcement
matters most.

Every sub-agent MUST end its response with a `<ramo>` status tag followed by a result envelope.
The vocabulary SSOT is `.claude/schema/harness.json` (`envelope` section); the enforcing mechanisms are
`.claude/hooks/ramo/handlers/subagent_stop.py` (exit 2 on violation) and the orchestrator's own
envelope parsing (second path — background spawns bypass hooks).

## Scope: sub-agents only (HARD)

- **[HARD] A main-session skill is not a sub-agent and owes no envelope.** It ends with the
  report its own step prescribes, in `RAMO_DOCUMENTATION_LANGUAGE`. The one exception is the
  escalation token `<ramo>BLOCKED</ramo>`, which stays because a blocked stage must be
  recognizable without reading Korean prose.
  WHY: an envelope emitted into the main session has no enforcement, no consumer, and the wrong
  reader. `subagent_stop.py` fires on the `SubagentStop` event only, stage handoff is a manual
  baton read by a person, and `common/language-settings.md` puts envelope values in English
  while the reader is a Korean-speaking user. Worse, it *displaced* the report: the envelope sat
  in the skill's last section framed as a contract, so the model treated it as the ending and
  the prescribed Korean report was never printed — observed in testing, taking the plan score
  and the P0 ticket count with it. Model-discipline grade: the five pipeline skills carry no
  `result` fence and no success tag, and no shipped check asserts it, so a skill edit that
  adds one is caught only in review.

## Spawn Shape (HARD)

- **[HARD] An `Agent()` spawn passes `subagent_type` and `prompt`, never `name`.**
  WHY: Claude Code delivers the `name` argument in the SubagentStop payload's `agent_type`
  field and keeps no other key naming the agent (observed in testing: a payload carries one
  identifying key, and two spawns of the same `subagent_type` differing only in `name` split
  into roster-matched and unmatched). `agent_type` is the field this gate reads, so a named
  spawn left the roster and skipped every check below — in one observed run stage every spawn
  passed through unjudged, and that is where the reproducibility keys are required.
  Model-discipline grade for the spawn call itself (no shipped check reads skill bodies), with
  `hooks/ramo/handlers/subagent_stop.py::resolve_roster` recovering the seat from a name that
  still carries the roster key (mechanical backstop). A name carrying no roster key is unrecoverable:
  the common contract below still applies, but the seat-specific rules (verdict vocabulary,
  read-only write access, implement-agent evidence) cannot.

- **[HARD] If a `name` is attached anyway, it is `<roster-key>:<label>` — the seat's roster key
  first, then a colon, then whatever the label needs to say.**
  WHY: the ban above governs what a skill body writes, and a name the orchestrator composes
  while a stage is running is not in any skill body. Observed: one run stage produced
  SubagentStop payloads named in the shape `t3-phase1`, none of which contains a roster key, so
  `resolve_roster` returned `None` and the implement-agent evidence backstop — guarded by
  `roster_key is not None` — did not fire on the one stage where the reproducibility keys are
  required; several of them carried no `<ramo>` tag either. The prescription is a shape rather
  than a stronger prohibition because a prohibition already exists and was not what failed. The
  colon form needs no code: `resolve_roster` recovers a seat by substring today, so a conforming
  name keeps every seat-specific rule alive while still labelling the spawn. Enforced by
  `hooks/ramo/handlers/subagent_stop.py::resolve_roster` (mechanical for recovery) —
  model-discipline grade for the name actually being composed that way, since no gate sees the
  spawn call itself.

## Canonical Status Set (HARD)

There are exactly **3** canonical `<ramo>` values:

```
<ramo>DONE</ramo>   <ramo>RETRY</ramo>   <ramo>BLOCKED</ramo>
```

- **[HARD] Only `DONE | RETRY | BLOCKED` are valid `<ramo>` values.**
  WHY: derivatives (`DONE-WITH-CONCERNS`, `PARTIAL`, `SUCCESS`, `APPROVED`, ...) force the
  orchestrator to interpret natural language, which is how failures get read as successes.
  Enforced by `subagent_stop.py::main` (exit 2) against the closed set in
  `_common.py::STATUS_VALUES`.
- **[HARD] Comparison is case-sensitive.** Lowercase or mixed-case variants also block.
  WHY: a single canonical spelling keeps the hook parser and orchestrator parser trivial and
  identical. Enforced by `subagent_stop.py::main` (plain membership test, no normalization).

| Status | Meaning | Gate action |
|--------|---------|-------------|
| `<ramo>DONE</ramo>` | Task completed, proceed | pass |
| `<ramo>RETRY</ramo>` | Task failed, retry possible | pass + orchestrator may re-spawn |
| `<ramo>BLOCKED</ramo>` | Cannot proceed, needs human | escalate to user; never auto-retried |
| Any other / missing | — | **exit 2 (block) + stderr reason** |

## Envelope Format

```
<ramo>DONE</ramo>

```result
verdict: <closed-set value per agent — see Verdict Field>
summary: <1-3 sentence summary of what was done>
artifacts:
  - <key output paths or identifiers>
changed_files:
  - <files modified; MUST be [] for read-only agents>
concerns:
  - <concerns if any, empty list if none>
blockers:
  - <blocking issues, empty list if none>
retryable: true | false
evidence:
  <task-type keys — see Evidence Field>
next_step_hint: <suggested next action>
```

## Verdict Field

`verdict:` is a **closed set per agent**. It is advisory — the `<ramo>` tag carries the
orchestration signal. Value assignments live in `.claude/schema/harness.json` (`agents.roster`).

| Agent | Allowed `verdict:` values |
|-------|---------------------------|
| ramo-plan-evaluator, ramo-critique | `APPROVE` \| `REJECT` |
| ramo-audit | `APPROVE` \| `REJECT` in both of its seats (plan review and verify) — it is a judgment seat like ramo-critique, not a check-runner, and the verify team already carries both vocabularies |
| ramo-data-verify, ramo-model-verify | `PASS` \| `FAIL` |
| ramo-data-design, ramo-model-design | `APPROVE` \| `REJECT` (the plan-review seat, which is the only seat they occupy) |
| ramo-wiki-reviewer | `APPROVE` \| `REJECT`, **and no `verdict:` field at all** when it ends `<ramo>BLOCKED</ramo>` because the evidence cannot settle a competing claim — the absent field is what stops the orchestrator calling `record-review` and spending a repair attempt |
| ramo-plan-writer, ramo-plan-improver, ramo-explore, ramo-data-explore, ramo-model-explore, ramo-doc-writer, ramo-wiki-writer, ramo-wiki-reader, ramo-data-implement, ramo-model-implement | **field MUST be omitted** |

Forbidden: `CONDITIONAL_PASS`, past-tense forms (`APPROVED`, `REJECTED`), free-form labels,
and `BLOCKED` as a verdict (the ramo tag already carries the block signal).

## Evidence Field

DS replacement for a coverage gate. **Each domain owns its own contract**: task types and their
required keys are declared by the domain, not by a global table
(SSOT: `.claude/schema/harness.json` `domains.<name>.evidence`).

| Domain | Task type | Required keys |
|--------|-----------|---------------|
| data | `data-extraction` | `data_snapshot`, `query_hash` |
| model | `model-training` | `seed`, `split_boundary`, `data_snapshot`, `feature_spec` |
| code | `code-change` | `test_command`, `red_evidence`, `coverage_line` |
| — | `other` | none — the domain-independent fallback |

- **[HARD] Missing required evidence keys = mechanical RETRY.**
  WHY: an unrecorded snapshot, seed, or feature set makes the result unverifiable and
  unrepeatable; prompt-level persuasion does not survive context pressure, so the gate is
  structural. Enforced by `subagent_stop.py::check_evidence` and the run skill's envelope gate.
  A justified exception must be stated in `concerns:` to pass.
- **[HARD] `other` is for work belonging to no registered domain.** Declaring it for work that
  does belong to one is a gate bypass, because its required-key list is empty.
  WHY: a global task-type table let any unregistered domain inherit an empty gate; ownership by
  domain removes the inheritance. Enforced by the orchestrator's cross-check of the declared
  task type against the plan's `Domain` column — model-discipline grade, no mechanical check
  (the hook is given only the self-declared task type, never the domain).

## Report-local Vocabulary Warning

Review-report labels (`BLOCKING | WARNING | NOTE`, score grades, `NEEDS-REVISION`, ...) are
**report-local** and MUST NOT appear inside `<ramo>` tags or `verdict:` fields. Four vocabulary
layers stay separate: status tag (orchestration), verdict (advisory judgment), report body
labels, and the wiki publish transaction's own state (`STAGING | VALIDATING | READY |
COMMITTING | COMMITTED | NEEDS_REPAIR | NEEDS_HUMAN | ABORTED`, plus its `validate` result
`PASS | FAIL` --
`.claude/skills/ramo-wiki/scripts/wiki_runtime.py`). The fourth layer belongs to a different
machine entirely (the transaction runtime, not the envelope), so a runtime state or a
`validate` result never appears inside `<ramo>`/`verdict:`/report-body labels, and the
reverse never happens either — `ramo-wiki-reviewer`'s `verdict: APPROVE | REJECT` stays a
`verdict:` field even though it feeds `record-review`, it does not become a transaction
state.

## Rules

- The `<ramo>` tag + envelope MUST be the final block in your response.
- `changed_files` MUST be `[]` for read-only agents; the deterministic change list is
  `git diff --name-only` — self-reports are cross-checked, not trusted.
- `concerns:` non-empty = completed with caveats (orchestrator proceeds but logs them).
- `retryable: true` means the orchestrator may re-run this agent with adjustments.
- Receipt is part of the contract: format compliance without a received body is a failure. The
  orchestrator treats "completion signal received but no body" as RETRY, never as success.
