---
description: The four wiki document subtypes (lesson, constraint, note, overview) — required sections, conditional features, and OKF-aligned frontmatter. Machine-readable SSOT is the schemas/*.json files this rule cites, not restated here.
---

# Wiki Schema Contract

Three governance subtypes plus one current-state subtype. The governance three come from an
earlier version's five (`adr`/`feature` stay out — ADRs already have a home in
`docs/architecture/adr/`, and `feature` has no DS counterpart); `overview` is the single
SoT-domain subtype this harness keeps, for the reason below.

## Subtypes

| subtype | path | schema |
|---|---|---|
| lesson | `wiki/lessons/<slug>.md` | `.claude/skills/ramo-wiki/schemas/lesson.json` |
| constraint | `wiki/constraints/<slug>.md` | `.claude/skills/ramo-wiki/schemas/constraint.json` |
| note | `wiki/notes/<slug>.md` | `.claude/skills/ramo-wiki/schemas/note.json` |
| overview | `wiki/architecture/<slug>.md` | `.claude/skills/ramo-wiki/schemas/overview.json` |

## Why `overview` is here and the other SoT-domain subtypes are not

An earlier version carried many SoT-domain subtypes beside its governance ones, and this
harness keeps exactly one of them.

- **`overview` earns its place on observed evidence.** In that version's real use it was the
  only wiki document that kept growing across rounds, while every governance category stayed
  empty for the whole project. A single current-state entry point is needed
  before accumulated knowledge is: "what does this pipeline look like right now" is the question
  a newcomer asks first, and nothing else in `wiki/` answers it.
- **The rest are not ported.** `api`, `db`, `redis`, `access-control`, `infrastructure`,
  `operations`, `scenarios`, `security` are web-service vocabulary, and their DS counterparts
  already have homes under `docs/data/`, `docs/feature/`, `docs/model/`, `docs/pipeline/`.
  Adding them to `wiki/` would make two trees answer the same question, which is the exact
  duplication the earlier version ended up with for ADRs — it defined a governance `adr`
  subtype, and its real ADRs were written to a different folder by a different skill with a different
  template, bypassing the wiki's gate entirely.
- **`overview` is current-state, so it is hard-deleted and rewritten when the shape changes**
  (`.claude/rules/common/sot-authoring.md` SOT-3), unlike a lesson, which records a moment.

**Do not restate `required_sections` or `conditional_features` here.** The schema JSON
files are the single source `wiki_runtime.py validate` reads; a second copy in this rule
would drift from what the gate actually enforces (the exact failure class
`workflow/12-subagent-bash-hygiene.md` names for the Bash allow-grammar). Read the schema
file for the subtype you are drafting or reviewing.

## The uncertainty outlet is a required section, not an authoring habit

Every subtype requires a `확인 필요 사항` section: somewhere legal to put what the evidence
does not settle.

- **[HARD] An author who cannot support a required section's content writes the gap into
  `확인 필요 사항` — never an inference presented as fact, and never a padded restatement of
  the heading.**
  WHY: a required section with no supporting evidence is precisely where a model fabricates,
  and the sections under the most pressure are `lesson`'s `근본 원인` and `constraint`'s
  `근거`. An earlier version carried this outlet in one subtype's schema and pushed it onto the
  others through a global authoring rule, which no gate can read; promoting it into every
  subtype's `required_sections` makes `wiki_runtime.py validate`'s `required-sections` check
  enforce the outlet's *presence* mechanically. Whether the author then uses it honestly
  instead of writing "해당 없음" stays model-discipline grade, backed at review time by
  `ramo-wiki-reviewer`'s `USER_DECISION_REQUIRED` outcome for evidence that cannot be
  resolved either way.

## Frontmatter (OKF v0.2-aligned)

Required: `type`, `title`, `description`, `category` (must equal the subtype — `lesson`
document has `category: lesson`), `status` (`draft | stable | deprecated`, the OKF
vocabulary — **not** the `.ramo/` `active | done | superseded` set), `created`, `updated`,
`tags`.

`description` is one line, and it is what the generated `wiki/index.md` prints as each
document's summary — without it an index can only list titles, which is what the earlier
shape did.

Wiki-specific extensions on top of the OKF baseline:

- `document_features: []` — zero or more of the subtype's declared conditional features.
  An undeclared feature name is a validation failure, not a warning.
- `sources: [{resource: <path or glob>}]` — at least one entry, required. Every
  `resource` must resolve to a `git`-tracked file (dead-document prevention;
  `foundation-dead-document-prevention.md`). This is the field OKF also uses for `docs/`
  documents (`foundation-frontmatter.md`), reused here rather than invented.

## Why `category` carries the subtype instead of a new field

`docs/` frontmatter's `category` is a 7-value enum for the DS document categories
(`foundation-category-structure.md`). Wiki's `category` is a **different, 4-value enum**
scoped to `wiki/` documents only — the two never mix because the two trees are never
scanned by the same tool (`ramo-doc`'s indexing and staleness sweep is `docs/`-only).
Reusing the field name rather than inventing `document_subtype` keeps wiki
frontmatter one field closer to plain OKF instead of carrying an earlier-version field
(`document_schema`/`document_subtype`) that OKF v0.2 has no equivalent for.

## See Also

- `foundation-transaction-lifecycle.md` — the publish gate that reads this schema
- `foundation-dead-document-prevention.md` — the `sources` resolution check
- `.claude/rules/common/naming.md` — `<slug>` follows the same kebab convention as any
  other DS artifact name
