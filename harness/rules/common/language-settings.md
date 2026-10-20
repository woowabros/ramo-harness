---
description: Language policy — all harness assets in English; deliverables and conversation follow RAMO_DOCUMENTATION_LANGUAGE (default ko)
---

# Language Settings

Loaded globally (no `paths:`): language policy governs every response and artifact, not any
particular file path.

All harness assets MUST be written in English:

- Agent prompts and descriptions
- Skill content (SKILL.md) and skill-local rules
- Rule files (.claude/rules/**/*.md)
- Hook shim and handlers (.claude/hooks/ramo/**)
- Templates (.claude/templates/**)
- Code comments and docstrings, **except** the one-line role comment on a source file's
  first line (see below)
- CLAUDE.md (the ramo marker block)
- Result envelopes (field values such as `summary:` included)

## First-line role comment (exception)

The one-line comment on the first line of a source file states what the file is for, and it
follows `RAMO_DOCUMENTATION_LANGUAGE` rather than the English rule above. Every other comment
in the same file stays English.

WHY the exception exists: the two rules it reconciles both hold. English bodies are what make
structural comparison between assets work, and that comparison reads the body, never the
one-line header. A reader-language header is what lets the next session (human or agent) tell in one
line what a file does without reading it, which is the whole point of that habit. Scoping the
exception to line 1 keeps both properties.

This is model-discipline grade — no mechanical check distinguishes a role comment from any
other comment.

Deliverables and user-facing text follow `RAMO_DOCUMENTATION_LANGUAGE` (default: `ko`):

- `.ramo/plans/`, `.ramo/interviews/` outputs
- `docs/` documents produced by the doc skill
- `wiki/lessons/`, `wiki/constraints/`, `wiki/notes/` documents published by `ramo-wiki`,
  including the runtime-generated `wiki/index.md` — a generated index inherits the
  language of what it catalogs (Korean deliverable summaries), not the language of the
  `.py` script that generates it (`.claude/skills/ramo-wiki/scripts/wiki_runtime.py`
  stays an English asset; its output does not)
- Conversational explanation prose in the main session

Exception: quoted example text that demonstrates user-facing output may be written in
`RAMO_DOCUMENTATION_LANGUAGE`. This covers illustrative samples only — instructional and
normative text stays English.

Code, identifiers, file paths, and commands stay in their original form in both directions.

WHY assets are English: structural comparison between assets, and a cross-domain diff of the
same contract, must work without a language barrier.
