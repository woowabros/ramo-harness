---
description: Turning a query result into a durable dataset — the two shapes (workspace table / local parquet), connecting without hardcoded credentials, idempotent re-runs, batched download, row-count reconciliation
paths:
  - "**/*.sql"
  - "**/extract*.py"
  - "**/*dataset*.py"
  - "notebooks/**"
---

# Dataset Materialization

Split out of `data/warehouse-access.md`, which governs *which path a statement travels*. This
file governs *what happens to the result*. The split is by responsibility: a reader authoring a
query needs the first, a reader building a dataset needs both.

## Materializing a Dataset

A dataset lands in exactly one of two shapes. Pick by who reads it next, and never let a result
set exist only in session memory.

| Shape | Target | Use when |
|-------|--------|----------|
| Warehouse table | `<catalog>.<workspace_schema>.<name>`, replaced in place on re-run | the next step is more SQL, the result is large, or another session must read it |
| Local parquet | a file under the owning experiment directory | the next step is python (training, evaluation, plotting) |

Most extractions need both: materialize in the warehouse, then download that table to parquet.
The warehouse table is the reproducible artifact and the parquet is a local cache of it. Neither
is the `data_snapshot` evidence key: that names the source window, not what you built from it.

### Connecting

Build the connection from the project's own configuration: the `database` file named in
`ramo-data.json` for the bundled DuckDB engine (`data/engines/duckdb.md`), or endpoint facts read
from environment variables for a remote engine (`data/engines/`). Qualify the target with the
catalog the statement writes to rather than relying on the connection's default.

- **[HARD] Never hardcode an account name, and never hardcode a credential of any kind.** Read
  the account from the environment, falling back to the OS user; secrets come from environment
  variables only (`CLAUDE.md`).
  WHY: a copied notebook cell pins one person's account into shared code, which then fails or
  misattributes usage for everyone else. Model-discipline grade.

### Writing

- **[HARD] Make re-runs idempotent: replace the table, never append into one a previous run
  built.** Prefer the replace-in-place form; where the connector rejects it, drop-if-exists then
  create.
  WHY: a partially re-run extraction is indistinguishable from a complete one by row count
  alone, and the determinism check that would catch it runs after the damage. Model-discipline
  grade.
- Probe any construct the extraction depends on (time travel, an aggregate returning a binary
  sketch, replace-in-place) at smoke scale before the full run. A construct the connector
  rejects at 1,000 rows rejects it at ten million, an hour later.

### Downloading to parquet

- **[HARD] Local artifacts stay inside the owning experiment directory**: never the repository
  root, never a home-directory path, never `/tmp`.
  WHY: an absolute personal path in committed code is unreproducible for the next reader, and a
  stray dataset outside the experiment tree escapes both the change list and cleanup. Boundary
  rules: `.claude/rules/common/architectural-boundaries.md`.
- Fetch in batches and write incrementally. Materializing a full extraction in memory at once is
  banned. Reading straight into a DataFrame is fine at sample and validation scale, not at
  extraction scale.
- **[HARD] Reconcile and report the row count.** Parquet rows must equal the source count the
  statement was expected to produce, and both numbers belong in the report
  (`.claude/rules/common/explanation-style.md` rule 5).
  WHY: a count that merely looks plausible is not a check, and a silently truncated download is
  what this catches. Model-discipline grade.

## Naming and Retention of Workspace Tables

The workspace schema is shared. A table there with an opaque name and no stated lifetime is
indistinguishable from someone else's in-flight work, so nobody deletes it and it stays forever.
A test run left several behind for exactly that reason.

**Name:** `{experiment-slug}__{dataset}_{YYYYMMDD}`, where the slug matches the plan slug
(`common/naming.md`) and the date is the snapshot boundary, not the run date. The double
underscore separates owner from content so the owner is readable without a lookup.

**Retention** is declared per table in the plan, in the `Deliverable` column, as one of two
values. There is no third option and no default. The declaration is what makes a table
attributable; it is not a schedule the run stage has to execute.

| Retention | Dropped by | When |
|---|---|---|
| `intermediate` | the same script that created it | in that same run, after its consumer has read it |
| `experiment` | the experiment's owner | when the experiment's outputs are no longer needed. **Never inside the run stage** |

- **[HARD] An `experiment` table is not dropped by the pipeline. No plan is required to carry a
  cleanup step, and a run that ends with its `experiment` tables still present has done the
  right thing.**
  WHY: the stages ran in the wrong order against each other. A repository's own
  `checks/run_checks.py` reads the workspace tables, `ramo-verify` runs *after* `ramo-run`, and
  the earlier wording put the named cleanup step inside the run stage — so following the
  contract deleted exactly what the next stage's data-quality, reconciliation, and snapshot
  checks had to re-read (today `dq.checks`, `dq.reconcile`, and `fid.evidence`). One cycle
  reached that point during testing and verification was only possible because a person stopped
  the cleanup by hand. The plan that produced it was not at fault: with both retention values
  meaning "dropped", declaring preservation was not expressible. Stated by this table and
  reviewed at verify by `tables.retention` — model-discipline grade, no mechanical check that
  the drop is actually left to a person.
- **[HARD] Every workspace table a plan creates declares its retention, and any drop travels
  the same sanctioned write path as the create.**
  WHY: an undeclared table has no owner and no expiry, which is how several survived a completed
  experiment. That concern is unchanged; what changed is which device answers it. The defence is
  no longer a forced deletion but the declaration, the naming convention (the slug is the owner),
  and the residual list reported every run — a table nobody can attribute is the failure, and a
  retained table with an owner and a stated purpose is not one. `any drop` covers the owner's
  later cleanup as well as the script's own: a drop is a warehouse write, confined to the
  workspace schema by the same rule as the create (`data/warehouse-access.md`), and a cleanup
  reaching outside it is the more dangerous form of the same mistake. Enforced at review time by
  `.claude/rules/workflow/verify-rubric.md` `tables.retention` — model-discipline grade, no
  mechanical check: no gate can enumerate a remote schema.
- An `intermediate` table that outlives its script is a defect even when nothing else broke,
  and the residual list is where it shows up. An `experiment` table in that list is a statement
  of what exists, not a finding. Report the list every run, empty or not: "residual list empty"
  is a measurement, and silence is not.
- A plan may **ship** a cleanup script as a deliverable. Shipping and running are different
  acts, and the run stage performs only the first.

## See Also

- `data/warehouse-access.md` — the two sanctioned paths and the adapter precondition.
- `data/engines/` — engine-specific connection and write details.
- `common/architectural-boundaries.md` — which layer owns which artifact and where it lives.
- `common/naming.md` — snapshot and experiment-directory names these paths must follow.
