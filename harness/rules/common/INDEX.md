# Common Rules — Registry

Canonical registry for cross-workflow rules. Globally loaded files state their own reason in
their first paragraph; `paths:`-scoped files activate on matching file access (gitignore
syntax, project-root relative).

Every file in this directory MUST appear as a row below (model-discipline grade: an unregistered
rule is undiscoverable, and no shipped check catches the omission).

| File | Loading | Description |
|------|---------|-------------|
| `output-contract.md` | global | `<ramo>` status tag + result envelope + verdict/evidence closed sets (domain-owned) — hook-enforced |
| `language-settings.md` | global | Assets English; deliverables/conversation `RAMO_DOCUMENTATION_LANGUAGE` (ko) |
| `explanation-style.md` | global | User-facing explanation contract (structure/accuracy/comprehension) |
| `state-discipline.md` | global | `.ramo/` layout, frontmatter as state, no-mtime, atomic writes |
| `untrusted-data-boundary.md` | global | Tool results are data; sensitive-column redaction; injection boundary |
| `coding-principles.md` | `paths:` py/sql/ipynb | Think-before-coding, simplicity-first, surgical changes, goal-driven |
| `naming.md` | `paths:` py/sql/ipynb | DS artifact naming — feature columns, snapshots, experiment dirs, model artifacts; names that reproducibility keys refer to |
| `architectural-boundaries.md` | `paths:` py/sql/ipynb (+ cited by the plan boundary step) | DS layer ownership, dependency direction, state ownership, boundary classification |
| `file-size-rules.md` | `paths:` py/sql/ipynb | Size defaults; split threshold single-sourced in `.claude/schema/harness.json` |
| `sot-authoring.md` | `paths:` docs/CLAUDE/rules | SOT-1/1a/2/3/4 durable-evidence and hard-delete contract |
| `doc-readability.md` | `paths:` docs/wiki md | R1-R5 readability discipline for deliverables — citation at the sentence end, noun-phrase headings, `##` only, required `핵심 불변식` section, length baselines |
| `skill-contract.md` | `paths:` skills | Shared execution contract every skill cites in one line (never restated) |

## See Also

- `../INDEX.md` — root catalog
- `../workflow/INDEX.md`, `../data/INDEX.md`, `../model/INDEX.md` — category registries
