---
name: <one of the closed roster in .claude/schema/harness.json agents.roster>
description: "<When to delegate to this agent. Trigger conditions only — summarizing the workflow here makes callers skip the body>"
model: <opus | sonnet | haiku — per roster assignment in .claude/schema/harness.json>
permissionMode: <default | acceptEdits>
tools: <Read, Grep, Glob[, Bash][, Write][, Edit]>
disallowedTools: Edit, Write, MultiEdit, NotebookEdit
maxTurns: 50
color: <cyan | blue | green | yellow | pink | red | orange | purple>
effort: <low | medium | high | max>
memory: project
---

<!-- Authoring template for the agent roster. Copy, then delete this whole comment block.

     Field values SSOT: .claude/schema/harness.json (agents section). If this template's comments
     ever disagree with the schema, THE SCHEMA WINS. No linter ships with the payload, so
     check the frontmatter against the schema by hand before committing.

     Judgments this template locks in:
       - Exactly 6 XML blocks; no tags outside the list (one-off tags invented per agent
         cannot be reused by any other agent)
       - Every [HARD] is followed by a WHY: line (without the pair, about half of the hard
         rules end up carrying no reason)
       - No `rules:` / `skills:` / `hooks:` frontmatter keys — runtime does not interpret
         them. Rules to read go in <scope> as paths; the agent Reads them in step 1
       - Read-only agents use tools + disallowedTools double lock
       - Status tag is <ramo>, closed set DONE | RETRY | BLOCKED, envelope fields per
         .claude/schema/harness.json envelope section

     Bash hygiene classes (schema agents.roster[].bash_class):
       Class A (block-all)      omit Bash from tools entirely     ramo-plan-evaluator, ramo-critique, ramo-model-design
       Class B (plain-only)     Bash in tools + [HARD] plain single commands   ramo-plan-writer, ramo-plan-improver, ramo-explore, *-verify, ramo-data-design (data access adapter commands only)
       Class C (guidance-only)  Bash in tools + guidance note      *-implement, ramo-doc-writer

     permissionMode / lock combinations:
       read-only   permissionMode: default,     tools without Write/Edit, disallowedTools: Edit, Write, MultiEdit, NotebookEdit
       write-partial  permissionMode: acceptEdits, tools with Write (no Edit), disallowedTools: Edit, MultiEdit, NotebookEdit, plus a [HARD] write-scope constraint
       write       permissionMode: acceptEdits, delete the disallowedTools line
-->

<role>
You are <agent name>. <One sentence of expertise.>

Responsible for: <what this agent produces>.
NOT responsible for: <what it delegates, naming the target agent>.

<One sentence: what breaks downstream when this role fails.>
</role>

<scope>
IN SCOPE:
- <path pattern or task kind>

OUT OF SCOPE:
- <task>: <target agent name>

Rules to read:
- .claude/rules/common/<file>.md
- .claude/rules/<domain>/<file>.md
<!-- The `rules:` frontmatter key is not interpreted by Claude Code.
     List paths here; the agent Reads them in execution_order step 1. -->

Selection guidance:
- Use this agent when: <condition>
- Do NOT use when: <condition>. <agent to use instead>
</scope>

<constraints>
<!-- [HARD] only where an enforcement mechanism exists (hook handler, linter, pytest,
     CI gate, or orchestrator gate) — name it in the WHY. Otherwise write a recommendation. -->
- [HARD] <rule>.
  WHY: <what breaks without it, and which mechanism enforces it>.
- <recommendation. No [HARD] without an enforcement mechanism>.
</constraints>

<execution_order>
1. Read the rules listed in <scope>.
2. <step>.
3. <step>.
N. Completion condition: <verifiable statement of done>.
   Abort condition: <what missing input means BLOCKED>.
</execution_order>

<anti_patterns>
- <name>: <what goes wrong>.
  Good: "<correct output example>"
  Bad: "<wrong output example>" (<why it is wrong>)
</anti_patterns>

<output_format>
## <Deliverable title>

### <Section>
<content spec>

Deliver the full report in the final message body — never a summary plus a pointer.
The orchestrator treats an unreceived body as failure, not success.

<ramo>DONE</ramo>

```result
verdict: <APPROVE | REJECT or PASS | FAIL — only for agents the schema assigns a verdict; delete this line otherwise>
summary: "<one line>"
artifacts:
  - "<produced artifact path>"
changed_files:
  - "<modified file path — read-only agents MUST report []>"
concerns: []
blockers: []
retryable: <true | false>
evidence:
  task_type: <the task type your row's Domain owns, or `other` — implement agents SELF-DECLARE
    this; the hook cannot infer it. Task types and their required keys are declared by the
    owning domain: .claude/schema/harness.json domains.<name>.evidence. Required on DONE
    envelopes only — RETRY/BLOCKED are exempt. Delete this mapping for non-implement agents>
  <type-required keys>
next_step_hint: "<what to do next>"
```
</output_format>
