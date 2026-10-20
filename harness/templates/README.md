# ramo-harness authoring templates

Master copies to duplicate when authoring new harness assets. This directory is not a
path Claude Code interprets — nothing here activates anything. Pure reference.

## Where field values are canonical

**The machine-readable SSOT for field names, allowed values, and required-ness is
`.claude/schema/harness.json`.** Its `_why` keys carry the rationale.
Template comments repeat some values (model assignments, permission combos) because a
template must be self-contained to be useful. **On any mismatch, the schema wins.**
No authoring linter ships with the payload: check a new asset against the schema by hand
(or with your own pre-commit check) before committing it.

## Why templates instead of a spec document

An earlier harness shipped a release containing an agent file missing several required
fields despite having a long authoring spec and a separate gate document. Reading a spec
and filling fields can skip fields; copying a template cannot.

## Files

| Template | Target path |
|---|---|
| `agent.md` | `.claude/agents/ramo/<roster-name>.md` (closed roster, `agents.roster`) |
| `rule.md` | `.claude/rules/{common,workflow,data,model}/*.md` |
| `skill.md` | `.claude/skills/ramo-*/SKILL.md` (save as uppercase `SKILL.md`) |
| `hook-shim.sh` | `.claude/hooks/ramo/ramo-hook.sh` |

## Judgments each template locks in

| Judgment | Shape in the template | Why |
|---|---|---|
| Agent XML fixed at 6 blocks, no tags outside the list | `agent.md` has exactly 6 blocks, no extension slots | one-off tags invented per agent cannot be reused or checked by anyone else |
| `success_criteria` absorbed into `execution_order` completion condition | last `execution_order` item is completion + abort condition | almost every agent needs one, so it belongs in the shared shape rather than an optional tag |
| `[HARD]` + `WHY:` pair required | `constraints` examples are pair-only; WHY names the enforcing mechanism | without the pair, about half of the hard rules end up carrying no reason at all |
| `rules:` frontmatter key rejected | absent from frontmatter; rules-to-read are paths in `scope` | the runtime never interprets it, so it reads as wiring while doing nothing |
| Read-only double lock | `tools` + `disallowedTools` declared together | a single declaration site widens by accident |
| Bash hygiene as tool composition | Class A omits Bash from `tools`; B/C carry body constraints | classes are enforced by `pre_bash.py::main`, not invented frontmatter keys |
| `paths:` single notation | `rule.md` shows block sequence + double quotes only | the runtime accepts several notations; a checker that reads only one of them silently misjudges the rest |
| `activation_env` rejected | absent from `rule.md` frontmatter | runtime-unread field |
| Global load requires a reason | `rule.md` comment demands a first-paragraph reason | missing `paths:` and intentional global look identical otherwise |
| Skill contract is one citation line | `SKILL.md` second line cites the contract rule | a contract copied into each skill gets re-authored each time and drifts |
| No logic in the hook shim | `hook-shim.sh` has no branching; event mapping lives in settings.json | hooks run on every tool call |
| Envelope + hand-off guarantee | `output_format` ends with a hand-off instruction + `<ramo>` tag + result block | the envelope format can hold while report bodies are lost; format and hand-off are separate layers |

## Enforcement status

Format compliance is enforced in layers, and only the runtime layer ships as code:

| Layer | Status |
|---|---|
| Frontmatter fields, closed sets, roster, forbidden keys, `paths:` notation | **review** — checked by hand against `.claude/schema/harness.json`; no linter ships |
| XML 6-block structure, `[HARD]`/`WHY:` pairs, inline-domain-knowledge ban, grid diff budget | **review** — same; model discipline at authoring time |
| Envelope at runtime (tag, fields, verdict, evidence) | **live** — `subagent_stop.py::main` + orchestrator parsing |
| Bash hygiene class per agent | **live** — `pre_bash.py::main` (roster mirrored in `_common.py`) |

## How to use

1. Copy the template to its target path.
2. Delete the top `<!-- ... -->` comment block (or the comment header in `hook-shim.sh`).
   It is authoring guidance, not part of the artifact.
3. Fill every `<...>` placeholder. A remaining `<...>` means the file is unfinished.
4. For `agent.md`, pick the model/permission/bash-class combination for the roster name
   from `.claude/schema/harness.json`, and add the same entry to `ROSTER` in
   `.claude/hooks/ramo/handlers/_common.py` — the hooks read the mirror, not the schema.
