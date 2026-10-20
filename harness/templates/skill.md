---
name: ramo-<name>
description: "<Trigger conditions only — summarizing the workflow here makes callers skip the body>"
argument-hint: "[<argument>]"
allowed-tools: <Read, Write, Edit, Bash, Grep, Glob, Agent, AskUserQuestion>
---

<!-- Authoring template for workflow skills. Copy as SKILL.md (uppercase), then delete
     this whole comment block.

     Field values SSOT: .claude/schema/harness.json (skills section). If comments here disagree
     with the schema, THE SCHEMA WINS.

     Judgments this template locks in:
       - Contract body is never copied into the skill; one citation line replaces it.
         A contract copied into every skill gets re-authored in most of them and drifts;
         the cost driver is authoring, so citation reduces authoring surface to zero
       - Size caps: single-purpose 80 lines / interactive 700 lines
         (.claude/schema/harness.json limits)
       - Routing is explicit subcommand + ask, two tiers only. Keyword-inference
         tables are rejected
       - When ambiguous, AskUserQuestion — never guess
       - Frontmatter uses only name / description / argument-hint / allowed-tools.
         Other runtime-valid keys must be registered in the schema before use

     Dependency: the citation line below requires .claude/rules/common/skill-contract.md
     to exist. Create that rule first if it is missing.

     Language: skill body is English (asset); outputs and user-facing dialogue follow
     RAMO_DOCUMENTATION_LANGUAGE (default ko).
-->

# <Skill title>

Contract: follow `.claude/rules/common/skill-contract.md`.

<One paragraph: what this skill does. Name inputs and outputs.>

## Arguments

```
ramo:<name> [<argument>]
```

| Argument | Required | Meaning |
|---|---|---|
| `<argument>` | yes / no | <description> |

If the argument is missing, ask with `AskUserQuestion`. Never guess.

## Steps

1. <step>. On failure: <RETRY or BLOCKED>.
2. <step>.
3. <step>.

<!-- If a step spawns agents, spell out the Agent() call and its baton.
     Subagents never spawn subagents; only the main session spawns. -->

## State updates

Name the files and fields this skill updates. Write "none" if it updates nothing.

| File | Field | When |
|---|---|---|
| `.ramo/plans/<date>-<topic>.md` | `status`, `updated` | end of step <n> |

## Output

<ramo>DONE</ramo>

```result
summary: "<one line>"
artifacts:
  - "<path>"
changed_files:
  - "<path>"
concerns: []
blockers: []
retryable: false
next_step_hint: "<next step>"
```
