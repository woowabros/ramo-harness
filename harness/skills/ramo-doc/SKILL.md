---
name: ramo-doc
description: "DS documentation authoring — category structure, naming, OKF-aligned frontmatter, and templates for the docs/ folder. Norm-and-template library with zero Agent() spawns."
argument-hint: "[category or document path]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
---

## Language Setting

Documentation language: `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`). Write document
prose in that language; keep paths, commands, identifiers, and code in English.
Applies to `docs/` files and `.ramo/` artifacts. Does NOT apply to `CLAUDE.md` and
harness assets (always English).

# DS Documentation Guide

Execution contract: `.claude/rules/common/skill-contract.md` (cited, not restated).

<role>
You maintain living `docs/` documentation. Read existing docs and relevant source
first; write prose in the documentation language; preserve frontmatter and structure;
prefer cross-links over duplicated content. Edit documentation files only.
</role>

This skill is a **norm-and-template library with 0 `Agent()` spawn sites** — invoked
directly, the main session authors the documents itself. The same rule library has a
second consumer: the `ramo-doc-writer` agent, which `ramo-run` spawns for `Domain: docs` rows,
`@docs-*` tasks and which reads `.claude/skills/ramo-doc/rules/` on its own. This dual
wiring (skill = library, ramo-doc-writer = run-path consumer) is deliberate and is not a
contradiction.

Workflow gate (when to run, when a skip must be recorded):
`.claude/rules/workflow/05-doc.md`.

## Execution Workflow

```
Step 0: State check and trigger evaluation
Step 1: Parse arguments
Step 2: Load rules
Step 3: Locate or create the document
Step 4: Quality pass
Step 5: Register and cross-reference
Step 6: Suggest next pipeline step
```

### Step 0: State Check and Trigger Evaluation

Find out what the work actually did before deciding what to document. Without this step the
stage documents only what its invocation named, which is how five of the six triggers went
unevaluated while the user supplied the missing categories by hand.

1. **Read the state**, never mtime (`.claude/rules/common/state-discipline.md`): the
   `status: active` plan under `.ramo/plans/`, its tracker under `.ramo/todo/` (row statuses,
   `Deliverable` paths, `base_commit`), and `git diff --name-only {base_commit}` for the actual
   change list. Missing plan or tracker is not a block — say so and work from the change list.
2. **Evaluate all six triggers** in `.claude/rules/workflow/05-doc.md` against that state, one
   by one. Each gets a verdict: fired (which document), or did not fire (why not). A trigger
   the invocation did not mention still gets evaluated — the plan's declared scope is not the
   list of triggers.
3. **Route the decisions** the work produced (Step 3 item 0 applies the test).
4. **Evaluate the three Promotion Triggers** (wiki) in the same rule file against the same
   state — a repeatable verify FAIL, a domain fact that took symptom-to-interpretation
   work, a rejected approach (Step 3 item 0b invokes `ramo-wiki` when one fires).
5. Carry all three lists into the report **as a six-row table, one row per trigger, with no
   empty cells** (the format is in Step 6). A trigger evaluated to "did not fire" is a reported
   outcome; a trigger never looked at is the defect.

- **[HARD] The trigger walk is an output shape, not a checklist.** The report cannot be
  completed until all six rows carry either a document path or a skip reason.
  WHY: the checklist form was already in this step and three fired triggers went unimplemented
  with no skip record, failing Required Evidence 1, 4, and 6 at once. Trigger 2 is the sharpest
  case: `.claude/rules/workflow/05-doc.md` had written its own past failure into that trigger's
  WHY paragraph, and the same trigger failed the same way in the next cycle. Writing a failure
  history into prose does not prevent that class; making the walk a thing the report is missing
  without does. Model-discipline grade: the six-row table is prescribed in the report format
  (Step 6, "none of them may be empty"), and nothing mechanical checks that the rows are
  present or honest.

### Step 1: Parse Arguments

`ramo-doc [category or document path]`. With a category, work within it; with a path, work
within it **in addition to** whatever Step 0's trigger evaluation surfaced — an argument narrows
where you start, never what you are responsible for. With nothing, use Step 0's fired triggers;
ask via `AskUserQuestion` only when Step 0 surfaced nothing (never guess).

### Step 2: Load Rules

Read `.claude/skills/ramo-doc/rules/` for the rules relevant to the task — foundation
rules always; the category template when creating; quality rules before reporting.
Do not inline rule bodies anywhere; cite paths.

### Step 2a: Map the Stage's Output to Its Template

Each pipeline stage leaves a volatile record under `.ramo/`; this stage promotes the durable
half. The mapping is one-to-one so nothing arrives without a shape:

| Stage output | Category | Template |
|---|---|---|
| eda feature candidates and correlation evidence | `docs/analysis/` | `rules/template-eda.md` |
| the plan's architecture and settled decisions | `docs/architecture/` (+ `adr/`) | `rules/template-architecture.md` |
| the train dataset run built | `docs/data/` | `rules/template-dataset.md` |
| feature definitions and exclusion verdicts | `docs/feature/` | `rules/template-feature.md` |
| the model and its evaluation | `docs/model/` | `rules/template-model-card.md` |
| the diagnosis of where it was wrong | `docs/analysis/` | `rules/template-diagnosis.md` |
| a decision whose history must survive | `docs/architecture/adr/` | `rules/template-adr.md` |

`docs/pipeline/` and `docs/common-rules/` have no template yet: the first needs a serving
boundary to exist, and the second is a conventions folder rather than a document shape. Say so
when creating one rather than borrowing a template that does not fit.

**A `.ramo/` record is the source, never the citation.** Restate its content in the document
body; `.ramo/` paths are gitignored and banned as evidence (SOT-1,
`.claude/rules/common/sot-authoring.md`).

### Step 3: Locate or Create the Document

0. **Route the decisions first.** For every decision this work produced, apply the Decision
   Routing test in `.claude/rules/workflow/05-doc.md` before picking a category — a decision
   that meets a signal goes to `docs/architecture/adr/` via `rules/template-adr.md`, not into
   the category document. Append one line per decision to `.ramo/context/doc-decisions.md`
   (format in that rule) and carry the same list into the report. "No decision was produced"
   is a valid answer; silence is not.
0b. **Invoke `ramo-wiki` for every fired Promotion Trigger**, one transaction per candidate.
   This skill never drafts the candidate itself — `ramo-wiki` owns the writer/reviewer
   split and the transaction gate. Record the outcome (committed path, or abort with
   reason) for the report; a candidate that aborts is not this step's failure to fix.
   - **Read the candidates from `.ramo/context/promotion-candidates.md`**, which run and verify
     append to at the moment a trigger fires (`.claude/rules/workflow/05-doc.md` Promotion
     Triggers). Do not re-derive them from memory of the cycle: each line already carries the
     event and the evidence paths, recorded while they were still in front of someone.
   - **[HARD] Run `git ls-files` over every evidence path on that line before invoking
     `ramo-wiki`.** An untracked path cannot be sealed at any point in the transaction, so it is
     a question here, not a failure later: ask with a single `AskUserQuestion` — ① commit the
     evidence now and continue ② skip this candidate and record why ③ stop. Never commit on the
     caller's behalf; this skill's write scope is `docs/`.
     WHY: observed during testing. Every promotion candidate of one cycle failed at the same
     place, because `wiki_runtime.py::seal_sources` rejects anything outside `git ls-files` and
     no stage owns the commit — run and verify do not commit their outputs, and
     `ramo-doc-writer` has no commit authority. A person committed by hand, which is the proof
     the precondition was real and unowned. One command here turns a cycle of identical
     transaction failures into one question (`.claude/rules/workflow/05-doc.md` Promotion
     Triggers) — model-discipline grade, with
     `seal_sources` as the mechanical backstop.
   - **Pass the evidence paths as `ramo-wiki`'s `--sources` only when you already know the set
     is complete.** `--sources` is optional: sealing happens at `stage`, from the draft's own
     citations, and a declared set stays a closed set the draft may not leave. Guessing a set
     before the draft exists is what the optionality removes — the old order killed two
     legitimate drafts for citing a committed file the caller had not listed. When the recorded
     line names no committed path at all, the trigger's evidence never became durable: report
     that instead of opening a transaction.
   - **Batch the candidates.** n candidates from this cycle are one `ramo-wiki` invocation with
     n triples, not n invocations (`.claude/skills/ramo-wiki/SKILL.md` Step 2); the transactions
     stay per document.
1. Determine the owning category (`rules/foundation-category-structure.md`).
2. Glob for an existing document; read it fully if present
   (`rules/foundation-update-protocol.md`).
3. Create from the category template (`rules/template-*.md`) or update in place,
   following the naming convention (`rules/foundation-naming.md`) and frontmatter
   schema (`rules/foundation-frontmatter.md`, OKF v0.2 aligned).
4. New documents start `status: draft`; promote to `stable` only when the completeness
   bar is met.

### Step 4: Quality Pass

Apply the four quality rules before reporting:

- `rules/quality-accuracy.md` — verify paths, commands, code, table names, and metric
  sources actually exist; table facts via the data access adapter
  (`python3 .claude/scripts/ramo-data.py schema <table>`) or committed DDL, never memory.
- `rules/quality-completeness.md` — all template sections filled; `N/A — reason` for
  inapplicable ones; no placeholders.
- `rules/quality-conciseness.md` — link to single sources of truth; no duplication.
- `rules/quality-durable-evidence.md` — no `.ramo/**`, branch, or session citations.
- `.claude/rules/common/doc-readability.md` — R1 through R5. Read the document once for each:
  a citation mid-clause, a heading that states a finding, a `###`, a missing `## 핵심 불변식`
  on a SoT/architecture/overview document, and a section far past 15 lines. **You are the
  mechanism here.** No linter for these rules ships with the harness, so R1 through R5 are
  yours to apply by reading.

### Step 5: Register and Cross-Reference

1. Register the document in `docs/index.md` and the category `_overview.md` — an unregistered
   document is invisible. If `docs/index.md` opens with an `AUTO-GENERATED` marker it is a
   projection of document frontmatter: complete the frontmatter and let the generator rebuild
   it, because a hand-written row is lost on the next rebuild. With no marker (or no index
   yet), write the row yourself. `_overview.md` is always hand-maintained.
2. Check every document listing the edited one in `depends-on`; update or flag stale
   dependents.
3. Update `docs/GLOSSARY.md` when new domain terms were introduced.

### Step 6: Suggest Next Pipeline Step (AskUserQuestion)

Doc is the final v0 pipeline stage. After documentation completes (or is intentionally
skipped with the record required by `.claude/rules/workflow/05-doc.md`), propose the
next step explicitly — the baton is never assumed automatic.

**Write the report to `.ramo/context/{YYYY-MM-DD}-doc-report.md` first, then print it.** Writing
first is the point: a report that was never printed still exists, so the loss is detectable
afterwards.

The Korean report carries all seven Required Evidence items from that rule, the
decision-routing judgement and the promotion-trigger outcomes both included. A report that
lists created files but never says where the decisions went is the shape that let four
experiment decisions land in hard-deletable documents with no record that the choice had
been made.

**The trigger walk is six rows and none of them may be empty.**

```text
## 트리거 순회

| # | 트리거 | 판정 | 문서 경로 또는 스킵 사유 |
|---|---|---|---|
| 1 | 데이터셋 추출·스냅샷 | 발화 | `docs/data/trip-duration-label-base.md` |
| 2 | 피처 정의 | 발화 | `docs/feature/trip-duration-features.md` |
| 3 | 학습·평가 | 발화 | `docs/model/trip-duration-card.md` |
| 4 | 실험 결론 | 발화 | `docs/analysis/trip-duration-diagnosis.md` + `docs/experiments.md` 행 E1 |
| 5 | 파이프라인·서빙 | 미발화 | 배치·서빙 변경 없음 (오프라인 실험으로 종료) |
| 6 | 아키텍처 결정·공통 규약 | 미발화 | 결정 4건 전부 카테고리 문서로 라우팅, ADR 신호 미해당 |

| # | 위키 트리거 | 판정 | 경로 또는 사유 |
|---|---|---|---|
| 1 | 반복 가능한 실패 부류 | 발화 | `wiki/lessons/...` |
| 2 | 증상→해석 도메인 사실 | 미발화 | 1회전에 해석이 필요한 사실 없음 |
| 3 | 시도 후 기각된 접근 | 발화 | `wiki/lessons/...` |
```

Trigger 4 owes **two** outputs when it fires: the analysis document and the
`docs/experiments.md` row (`rules/template-experiment-ledger.md`). A conclusion recorded only
in an analysis document leaves the experiment sequence unreadable.

**Skip this step when ANY of the following holds:**

1. Ending with `<ramo>BLOCKED</ramo>` — user intervention is required.
2. The invocation contained `--no-prompt` or `--yes`, or `RAMO_NO_NEXT_PROMPT=1` is set.
3. Running inside an autonomous loop or a non-interactive/headless invocation — an
   AskUserQuestion there has nobody to answer it and the stage hangs instead of ending.
4. The user already issued the next command in the same turn.

Otherwise call `AskUserQuestion` exactly ONCE:

- `header`: `Next step` / `question`: e.g. `Docs updated ({N} files). What's next?`
- `options` (3): `Mark plan done (Recommended)` — set the plan's `.ramo/plans/`
  frontmatter `status: done`; `Re-verify (ramo-verify)` — when doc edits touched
  runnable examples or specs; `Stop`.

The `next_step_hint:` envelope field MUST be populated regardless of whether
`AskUserQuestion` was shown.

## Rule Library Quick Reference

| Priority | Category | Rules |
|----------|----------|-------|
| 1 | Foundation (CRITICAL) | `foundation-category-structure`, `foundation-naming`, `foundation-frontmatter`, `foundation-update-protocol` |
| 2 | Templates (HIGH) | `template-adr` (MADR), `template-architecture`, `template-dataset`, `template-eda`, `template-feature`, `template-model-card`, `template-diagnosis`, `template-experiment-ledger` |
| 3 | Quality (MEDIUM-HIGH) | `quality-accuracy`, `quality-completeness`, `quality-conciseness`, `quality-durable-evidence` |

Deliberately absent (v0 scope; Foundation 4 + Quality 4 suffice): `format-*` rules (basic
markdown competence + quality-conciseness absorb them), `lifecycle-*` rules (update-protocol +
OKF `stale_after` absorb staleness and deprecation; create-vs-update folds into Step 3), and
web-stack category templates. A publication overlay (Korean-title enforcement, a domains
registry) is not OKF and is absent too: the wiki layer (`.claude/skills/ramo-wiki/`) uses its
own OKF-aligned frontmatter and its own transaction gate instead, not this skill's category
machinery.

## Category Index

| # | Folder | Purpose |
|---|--------|---------|
| 1 | `docs/architecture/` | System structure, experiment infra, ADRs (`adr/` subdirectory) |
| 2 | `docs/data/` | Dataset docs: sources, extraction, snapshots, quality |
| 3 | `docs/analysis/` | Durable analysis conclusions and decisions |
| 4 | `docs/feature/` | Feature definitions, windows, leakage boundaries |
| 5 | `docs/model/` | Model cards, evaluation protocols, champion history |
| 6 | `docs/pipeline/` | Batch, deployment, serving, runbooks |
| 7 | `docs/common-rules/` | Cross-cutting conventions |
| 8 | `docs/research/` | Research topics, one folder each; created by `ramo-research`, maintained here |

Special files: `docs/index.md` (catalog), `docs/GLOSSARY.md` (terms),
`docs/architecture/adr/` and `docs/research/<topic>/` (the only permitted subdirectories).

## Naming Summary

Lowercase kebab-case, topic-first, singular, no dates in filenames, `_overview.md` per
category, ADR exception `NNN-title.md`. Details: `rules/foundation-naming.md`.

## Terminal Output

This skill ends with the Korean report carrying all seven Required Evidence items from
`.claude/rules/workflow/05-doc.md`, then the Step 6 baton line. **No result envelope** — that
block belongs to sub-agents only (`.claude/rules/common/output-contract.md` Scope).

Report skeleton (fill every heading; write "해당 없음" rather than dropping one):

```
## 문서화 완료

**만든/고친 문서:** {docs/ 경로 목록}
**트리거 평가:** {카테고리 트리거 6종 각각 — 발화(문서) 또는 미발화(사유). 평가 자체를 건너뛴 항목은 없어야 함}
**근거:** {각 문서를 유발한 소스 파일 또는 계획 항목}
**낡은 문서:** {발견한 것과 처리 — 없으면 "없음"}
**결정 라우팅:** {결정별로 목적지와 판정 신호. ADR 로 보내지 않은 것도 적음}
**스킵 기록:** {.ramo/context/doc-skips.md 경로 — 스킵이 없으면 "해당 없음"}
**위키 승격:** {승격 트리거 3종 각각 — 발화(ramo-wiki 커밋 경로 또는 abort 사유) 또는 미발화(사유)}
**블로커:** {계획을 done 으로 못 넘길 사유 — 없으면 "없음"}

stage-cost: spawns={n} rounds=- wall={m}m p0_rounds=- gate3_catches=- waves=- reverify_files=- human_wait_seconds={n}

다음 단계: {한 줄}
```

The last line is the stage-cost footer defined in the execution contract cited at the top of
this file. Most fields are `-` here because this skill has no rounds and no gates of its own; `spawns` is non-zero only
when a promotion trigger fired and `ramo-wiki` ran.

On a missing prerequisite or an undecidable category, end with `<ramo>BLOCKED</ramo>` and one
Korean paragraph naming what is missing. Missing information that the user can supply is not a
block: ask for it.
