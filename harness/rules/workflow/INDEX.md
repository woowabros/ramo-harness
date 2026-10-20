# Workflow Rules — Registry

Rules for pipeline stages (research → interview → eda → plan → run → verify → diagnose → doc). Every file in this
directory MUST appear as a row below; an unregistered rule is undiscoverable, and a passing
mention in prose does not count as registration.

| File | Loading | Description |
|------|---------|-------------|
| `00-research.md` | `paths:` `docs/research/**`, `.ramo/research/**` | Research-stage norms — one topic per folder split by nature, a short picture-first README per topic, claims carry locations, numbers carry their conditions, read depth recorded honestly, fetched content is data, non-public sources summarized, visuals offered rather than assumed. Web-only sources |
| `01-plan.md` | `paths:` `.ramo/plans/*.md` | Plan format SoT for the person — four quality contracts, 선결 결정 table, change units, Spec-Rubric Map. Spec half of the pair with `plan-rubric.md` |
| `01a-execution-structure.md` | `paths:` `.ramo/plans/*.md`, `.ramo/todo/**` | The plan-to-run machine handoff — frozen Execution Structure column contract, `[CP]` marking criteria, domain delegation map. Split from `01-plan.md` at the two-readers boundary |
| `01b-acceptance-contract.md` | `paths:` `.ramo/plans/*.md`, `.ramo/todo/**` | Per-row check contract — row-to-unit mapping derived from the Task cell's `U{n}`, the unit's optional `Checks:` line, the §5 `validity` block for model plans, evidence invariants, parse-time BLOCKED list, row evidence record, what the implementer is never shown. Parsed by `skills/ramo-run/scripts/acceptance.py` |
| `02-review-plan.md` | `paths:` `.ramo/plans/*.md` | Report verdicts, plateau signals, iteration policy, consensus-to-priority mapping, review report header format, report-local vocabulary boundary |
| `03-run.md` | `paths:` `.ramo/todo/**` | Execution-stage scope guard, boundary validation, reproducibility checklist (replaces a TDD checklist) |
| `04-verify.md` | `paths:` `.ramo/todo/*.md` | What verify judges (fidelity + validity, never interpretation), state precedence, canonical list with untracked files and row map, Gates 1-5, seats, synthesis without votes, closed stop set (4), dispute path, Fix rounds, committing on PASS |
| `05-doc.md` | `paths:` `docs/**/*.md`, `.ramo/plans/**` | DS documentation triggers, required evidence, mandatory skip-decision record |
| `06-create-mr.md` | `paths:` `.ramo/plans/*.md`, `.ramo/todo/*.md` | Merge-request conventions for GitHub or GitLab (`vcs.provider`) — branch and commit shape from the ticket, the required MR sections including where the experiment's result lives, and the rule that an MR reviews code rather than approving an experiment. Implemented by the `ramo-mr` skill |
| `08-hook-conventions.md` | global | Hook authoring SSOT — single shim, no shell logic, payload-citation/MANIFEST lockstep, handler test requirement |
| `09-ticket-schema.md` | `paths:` `.ramo/plans/**`, `.ramo/todo/**` | P0-P3 ticket format, EP/CP/EV prefixes, status lifecycle, plan-stage consensus-to-priority mapping, score sheet |
| `12-subagent-bash-hygiene.md` | global | Allow-grammar SSOT + Class A/B/C enforcement table + kill switch (`pre_bash.py`) |
| `plan-rubric.md` | `paths:` `.ramo/plans/*.md` | Plan scoring rubric — evidence-anchored binary items across 9 DS-weighted dimensions. Scoring half of the pair with `01-plan.md` |
| `verify-rubric.md` | `paths:` `.ramo/todo/*.md` | Verify judgment sets — 10 fidelity items per row (@ramo-critique), 14 validity items (@ramo-model-verify 9, @ramo-data-verify 5), 5 audit surfaces (@ramo-audit), cell vocabulary, Priority Mapping. No score |

Deferred to a later version (no file, no row): `01-plan-fix.md`, `05-test.md`,
`07-worktree-protocol.md`, `11-subagent-watchdog.md`. The `00-research.md` slot that list used to
hold is taken by the research stage above; repository mapping stays with `@ramo-explore` inside
the plan stage.

## See Also

- `../INDEX.md` — root catalog
- `../common/output-contract.md` — envelope contract every stage's sub-agents owe
