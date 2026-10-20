---
description: Data-exploration norms — read-only path, bounded sampling, the required target-distribution table, the leakage boundary correlation measurement must respect, the candidate state columns the plan reuses, and what makes a finding re-obtainable.
paths:
  - ".ramo/eda/*.md"
---

# Data Exploration (EDA)

The stage between problem definition and planning: find out what the warehouse actually holds
before designing against it. Its output is a set of feature candidates with measurements, and
the plan treats that as evidence rather than as a suggestion.

Web development work has no equivalent stage — there is no "explore the tables and see which
columns relate to the target" step when the schema is the team's own. The consequence is that
everything here is reasoned from this harness's own failure modes.

## The path is read-only

- **[HARD] Exploration reads. Every statement is a `SELECT`, and nothing in this stage creates,
  replaces, or drops anything in the warehouse.**
  WHY: an exploratory query is by definition one nobody reviewed — that is what makes the stage
  cheap. A write on that path has no gate in front of it. Dataset building is a different stage
  with a different contract (`.claude/rules/data/dataset-materialization.md`) and a human gate
  in front of it (`.claude/skills/ramo-run/rules/human-gates.md`). Enforced by the read path
  itself: the data access adapter refuses anything but a single read (statement check plus
  engine sandbox, grade 2, `.claude/rules/data/warehouse-access.md`); a statement sent any
  other way is model discipline.

## Bound every query

- Filter to a narrow partition range before anything else; the partition key is the first thing
  to look up, not the last (`python3 .claude/scripts/ramo-data.py partitions <table>`).
- Use the adapter's `explain` before running anything whose scan looks broad. A cost signal
  beforehand is cheaper than a cancelled query afterwards.
- Sample deliberately: state the limit, and prefer a full narrow partition over a `LIMIT` across
  everything, because a `LIMIT` without an `ORDER BY` samples whatever the engine reaches first.

## Correlation is measured against the prediction anchor, not against the target alone

This is the section the stage exists for.

- **[HARD] Establish the prediction anchor before measuring anything. A column whose value is
  only knowable after the anchor is a leakage candidate, not a feature candidate, regardless of
  how strong the relationship is.**
  WHY: strength and usefulness are different axes, and the strongest column in an exploration is
  frequently the one written closest to the outcome. Sorting candidates by correlation puts the
  leaks at the top of the list. Recording them in a separate list — not deleting them — is what
  keeps the next person from rediscovering the same 0.93 and believing it. The verdict itself
  belongs to design and review (`.claude/rules/model/leakage.md`); this stage's job is to hand
  over the two lists already separated. Model-discipline grade, no mechanical check.
- Report the method with the number: correlation for two continuous columns, group-mean or rate
  contrast for a categorical one. An unnamed method is an uninterpretable number.
- **Correlation is not causation and this stage never claims it is.** A candidate is a column
  worth trying, with a stated relationship. Anything stronger is the experiment's job.

## The target's own shape is a required output

The stage measures columns against the target, and the target itself is the one column it is
easiest to skip. It goes in its own table, ahead of the candidates.

| 지표 | 값 |
|---|---|
| p50 / p95 / p99 | |
| 결측률 | |
| 꼬리 (상위 1% 대 평균) | |
| 표본 | {윈도우·파티션·행수} |

- **[HARD] The eda output carries the target's measured distribution, and the plan's §0 carries
  it forward rather than restating a guess (`.claude/rules/workflow/01-plan.md`).**
  WHY: in one observed cycle a third of the labels were null and the nulls were not random.
  That single fact changes the loss, the split, and the population, and it surfaced during
  execution because no stage's required output had asked for it. A null rate on the target is not a data-quality
  footnote; it is the population definition. Model-discipline grade, no mechanical check.

## Candidate state uses the plan's column names

The feature-candidate table's coverage columns feed the plan's §3 feature table directly, so they
carry the same three names: **결측률**, **처리**, **값 종류** (cardinality for a categorical
column, range for a continuous one). A candidate handed over with a coverage grade but no null
rate makes the plan re-measure what this stage already ran
(`.claude/rules/model/feature-engineering.md`).

## Evidence strength is about the measurement, not its size

Every candidate carries a strength grade, and it grades **the reason to trust the
measurement** — sample size, null rate, distribution stability across the window — never the
magnitude. A correlation of 0.6 on 400 rows is weaker evidence than 0.2 on 900,000.

## A finding must be re-obtainable

- Record the sample definition once (window, partition filter, exclusions, row count) and state
  every measurement against it. A measurement taken on a different sample says so in place.
- Record the statement text, not a description of it.
- Name the snapshot condition the measurements hold for. Without it, a number that changes later
  cannot be told apart from a number that was always wrong.

The same discipline `data-quality.md` puts on a pinned expectation applies here: an exploratory
number is also a number someone is about to act on.

## Where the output goes

`.ramo/eda/YYYY-MM-DD-<slug>.md`, in `RAMO_DOCUMENTATION_LANGUAGE`
(`.claude/rules/common/state-discipline.md`). The durable promotion is
`docs/analysis/` through the doc stage's `template-eda.md` — the plan reads the `.ramo/` version,
and only facts worth outliving the experiment travel further.

## See Also

- `data/warehouse-access.md` — the two sanctioned paths and which one may write
- `data/data-quality.md` — the pinned-expectation discipline this file borrows
- `model/leakage.md` — the checklist the leakage candidates get handed to
- `.claude/skills/ramo-eda/SKILL.md` — the stage that applies this
