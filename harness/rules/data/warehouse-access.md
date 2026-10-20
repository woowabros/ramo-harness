---
description: Warehouse access discipline — every read runs through the data access adapter (refused if not a single read), every dataset build runs through a build script that writes only into the workspace schema; the shell is not a path; no PII; snapshot and query_hash describe the source, never the workspace table
paths:
  - "**/*.sql"
---

# Warehouse Access and Dataset Build

Data-domain agents (`ramo-data-design`, `ramo-data-explore`, `ramo-data-implement`,
`ramo-data-verify`) also cite this file by path in their prompts — the design stage has no
`.sql` file open for `paths:` to match. Engine-specific behavior lives in `data/engines/`.

## Precondition: the Adapter Answers

- **[HARD] Run `python3 .claude/scripts/ramo-data.py ping` before concluding anything about a
  warehouse failure.**
  WHY this is HARD rather than a note: a configuration or connectivity failure rarely says so.
  A missing data file surfaces as a query error, an unreachable remote engine as a timeout, a
  missing client library as a dependency error; each reads as a different problem entirely. An
  earlier version spent a whole run task diagnosing a package gap that was a connectivity
  outage. Model-discipline grade: no hook can tell a configuration failure from a query failure.

Check the adapter first, then interpret the error. The exit code is the first fact.

| Symptom | Read it as |
|---|---|
| Exit 2, `ramo-data.json not found` or `invalid JSON` | configuration, not a query problem; the file is user-owned at the project root (`data/engines/duckdb.md`) |
| Exit 4, `BLOCKED: the data adapter needs DuckDB` | dependency missing; install it, never rewrite the query |
| Exit 3, `BLOCKED:` | the statement was refused as not a single read, or the engine sandbox refused a file outside the declared data directories: a path decision (is this a dataset build?), not a defect to reword around |
| Exit 1 naming a declared table's file | the source file moved or is missing: configuration |
| Exit 1 while `ping` passes | a real query problem |

A configuration or connectivity failure is BLOCKED with the `ping` output as evidence: never a
RETRY loop, and never grounds for changing the sanctioned path. Rewording a refused statement
until the lexical check lets it through is the same violation the check exists to stop.

## Two Sanctioned Paths

Warehouse SQL travels one of two paths with different powers and grades; conflating them made
an earlier version of this rule forbid the dataset step of the workflow it governs.

| Path | Used for | Can it write? | Grade |
|------|----------|---------------|-------|
| data access adapter (`python3 .claude/scripts/ramo-data.py`) | discovery, authoring, validation, every read | no — refused by the adapter (statement check plus engine sandbox) | 2 |
| build script over the engine's own connection (DuckDB: the project database file; another engine: its DB-API cursor) | materializing a dataset | yes, into the workspace schema only | 3 |

### Read path: the data access adapter

**It refuses to write, in two layers.** The statement check admits exactly one
statement that starts with a read keyword and carries no write or session-changing keyword
outside string literals. The engine sandbox runs it on a connection where the project database
is attached read-only, file access is limited to the declared data directories, extension
loading is off, and the configuration is locked before the statement runs. Neither layer alone
covers everything — the check is lexical, and the sandbox alone would still let a statement
copy into a data directory — so both run on every statement (refusal: exit 3, `BLOCKED:`).
Grade 2, not structural: the refusal is the adapter's own code, and a team that implements the
contract for another engine must keep both layers (`data/engines/`).

### Write path: the build script

**The write path is the build script's connection itself**, not any particular client library
that reaches it. A wrapper package may expose the same connection, but it is one optional layer
and its absence is never the reason a write cannot happen. Naming a wrapper here once sent a
consumer looking for a missing package and cost it a task.

**The statement leaves from inside a script**, so no hook sees it. Enforced by
`post_write.py::main`, which flags a schema-qualified non-workspace target in an authored `.py`
or `.sql` at write time — detection, not prevention — and reviewed at verification time by the
`audit.write-boundary` item of `.claude/rules/workflow/verify-rubric.md`.

**The shell is not a path.** Enforced by `pre_bash.py::names_sql_cli`: a SQL CLI in command
position carrying an execute flag, or in command position at the receiving end of a pipe
(`pre_bash.py::sql_cli_receives_a_pipe` — `echo 'select 1' | psql` executes just as surely as
`psql -c`), is denied. A CLI name elsewhere in the string — inside an import path, a filename,
a grep pattern — is not an invocation and does not block. The adapter is a python script, not
a SQL CLI; its own refusal is what keeps it read-only.

**Writing about SQL is not writing SQL.** The gate rewrites the command before judging it
(`pre_bash.py::strip_heredoc_bodies`, `::strip_quoted_literals`): a heredoc body headed for a
file is a document and is dropped, a body headed for a shell or a SQL CLI is command text and is
kept whole, and a body headed for an interpreter keeps its text while losing the line boundaries
that made a body line read as a command. Quoted literals are blanked for the CLI-name and
exec-flag tests only, so `psql -c "DROP TABLE x"` still blocks while a commit message quoting
the same words does not. One class stays undecidable in both directions: a statement written
entirely inside a quoted string is textually identical to prose quoting one. The exits are the
kill switch the block message names, and the Write tool, which this gate never sees.

## Engine Facts

Properties of an engine that hold for every table live in `data/engines/<engine>.md`, not in
`data/table-pitfalls.md` (traps in one table or join). A row there needs the error text and the
date observed: asserted without the error message, it cannot be told apart from a recollection.

## Authoring Sequence (model discipline)

Reads and authoring run on the adapter, one plain Bash command per step, in this order:

1. `python3 .claude/scripts/ramo-data.py search <keyword>` — tables by name, description, or column.
2. `... schema <table>` — real columns and types. Never guess a table or column name from memory.
3. `... partitions <table>` — the partition key and its range, before any query, not after.
4. `... explain --file <path>` — read the plan before a full run against a large table.
5. `... query --file <path> --limit <N>` — validate row shape and counts on a bounded sample
   before the full extraction. Output is capped at `--limit` (default 1000) and says so.

Prefer `--file` over `--sql` for anything longer than one line: the file is the statement text
that gets recorded verbatim and hashed, and it keeps quoting and `$` out of the shell command,
which a Class-B agent cannot send (`.claude/rules/workflow/12-subagent-bash-hygiene.md`). An
agent without `Write` sends `--sql "<stmt>"` with single-quoted SQL literals and no `$`.

**Gate-grade honesty:** the order is model discipline. It is executable because the adapter
ships and every data agent that reads holds `Bash`; an earlier version described it through
tools no agent declared, and it stayed prose no agent could run.

## Building a Dataset Never Runs Through the Read Path, Regardless of Cost

**The read path's scope is checking, not building.** Discovery, schema and partition lookups,
authoring aid, and validating a sample are what "every read" in the table above means. The
moment a task is `dataset-build` — an aggregation whose output is the training data itself, not
a check of it — the SQL runs through a build script instead, **as a default, not an escalation
decided from `explain`'s cost.** A rolling or lookback aggregation like a "28-day zone duration
median" (`zone_duration_median_28d`) is always this shape, however cheap it happens to measure:
the read path cannot write, its output is capped at `--limit`, and treating a fast build as an
exception just means the next `dataset-build` task — slow or not — has to re-derive the same
judgment call from scratch.

**Both the intermediate aggregation and the final join stay in SQL.** The python script's job
is orchestration — open the connection, run each statement in order — not local computation. A
build that combines several source tables runs as: (1) one or more `CREATE OR REPLACE TABLE ...
AS SELECT` statements into the workspace schema for each intermediate aggregate, then (2) a
final `SELECT` or `CREATE OR REPLACE TABLE ... AS SELECT` in the same schema (or a python-driven
download of that final query's result to parquet) that joins those intermediates with whatever
else the training set needs. Nothing gets pulled into a python dataframe to be joined there — a
join the engine can do, the engine does; python's dataframe layer starts after the dataset is
already assembled (training, evaluation, plotting — `data/dataset-materialization.md`).

`data-extraction` and `data-analysis` tasks are unaffected: a one-off check or an analysis
conclusion is not a training dataset, and the read path (aggregates included) stays the default.

**The one further escalation is a person, not python-in-a-different-place.** When even the
script-driven SQL is too heavy for the session to run synchronously (`explain`'s cost signal
plus a pilot-scale wall-clock projection say so), hand the vetted SQL to a person to run on the
team's batch facility. The table the person creates is not a harness write — `Warehouse writes
land only in the workspace schema` (below) governs what *the harness* writes, and this path has
the harness write nothing; it only reads the table back afterward through the read path. Record
which of the two paths ran (script or person) in the report the same way a snapshot or a query
hash gets recorded — an unrecorded choice is unreproducible even when the result is correct.

**Grade:** model discipline for the default-path rule itself — no hook distinguishes a training
set built by a script from one an agent assembled out of `query` output, and the
escalation-to-a-person judgment leans on the same unenforceable `explain` signal. What is
enforceable is downstream of the choice: the script's write still travels the one sanctioned
write path (HARD rule below), and a person-built table still needs a `data_snapshot` that names
the source window covering it, not the workspace table's name.

## HARD Rules

- **[HARD] Warehouse writes land only in the workspace schema** named by
  `.claude/schema/harness.json` (`data.workspace_schema`, default `workspace`). Source tables
  are read-only from every layer.
  WHY: blast radius differs by target. A write into a source table someone else owns is
  unrecoverable; a table in the workspace schema is disposable by construction. A rule that
  bans both bans the work it exists to support. Enforced by
  `_common.py::sql_writes_confined_to_workspace` (the judgment both hooks share),
  `pre_bash.py::names_sql_cli` for the shell shortcut, and `post_write.py::main` for authored
  files. The build script itself stays model-discipline grade.
- **[HARD] Qualify every write target** as `<catalog>.<schema>.<name>` or `<schema>.<name>`.
  WHY: an unqualified name resolves against whatever catalog and schema the session happens to
  carry, so it is evidence of nothing; both hooks therefore treat it as outside the workspace.
  Enforced by `_common.py::sql_write_targets`.
- **[HARD] No PII in query output, reports, or envelopes.**
  WHY: extraction results flow into `.ramo/` files and reports that outlive the session.
  Aggregate or redact; describe sensitive columns by name and shape only. Boundary rules:
  `common/untrusted-data-boundary.md`. Enforced by hook logs being key-names-only by design,
  and the `audit.pii` item of `verify-rubric.md`, which is always EV-P0; content-level
  compliance inside a result set is model-discipline grade.
- **[HARD] Every full extraction records `data_snapshot` and `query_hash`, and `data_snapshot`
  names the source window — never a workspace table.**
  WHY: an extraction that cannot be re-obtained is not evidence, and a workspace table is
  volatile by definition, so naming one as the snapshot makes the key false within weeks. The
  re-obtainable pair is the source partition window plus the query that read it; a workspace
  table name may accompany them as a convenience, never as the reproducibility basis. Formats:
  `.claude/schema/harness.json` (`envelope.evidence.key_formats`). Enforced by
  `subagent_stop.py::check_evidence` and the run skill's envelope gate (missing keys =
  mechanical RETRY); that the recorded value describes the source is model-discipline grade,
  reviewed by the `fid.evidence` rubric item (a pinned partition, never `latest`).

## Practices

- Pin the extraction window explicitly (partition predicates, date bounds); an implicit
  "latest partition" is mtime-thinking applied to tables.
- Run `explain` before full runs on large tables; validate a sample's row shape first.
- Record row counts against expectation in the report (`common/explanation-style.md` rule 5).

## Incorrect / Correct

```sql
-- Incorrect — guessed table name, unbounded scan, implicit window
SELECT * FROM taxi_trips;

-- Incorrect — dataset materialized into a schema that holds source data
CREATE TABLE tlc.trip_features_v2 AS SELECT PULocationID FROM tlc.yellow_trips;

-- Correct — schema-verified table, pinned partitions, bounded validation first (adapter `query`)
SELECT PULocationID, tpep_pickup_datetime, tpep_dropoff_datetime
FROM tlc.yellow_trips
WHERE pickup_date BETWEEN DATE '2023-01-01' AND DATE '2023-01-31'
LIMIT 100;  -- sample validated, then run full with the same predicates

-- Correct — dataset materialized into the workspace schema by a build script, target qualified
-- (catalog `ramo_project` = the project database file, attached by the script: engines/duckdb.md)
CREATE OR REPLACE TABLE ramo_project.workspace.trip_features_v2 AS
SELECT PULocationID, tpep_pickup_datetime,
       date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) AS trip_duration_min
FROM tlc.yellow_trips
WHERE pickup_date BETWEEN DATE '2023-01-01' AND DATE '2023-01-31';
```

Reproducibility for the workspace table above is `data_snapshot` =
`tlc.yellow_trips / pickup_date=2023-01-01..01-31` plus the `query_hash` of the statement that
built it — not the string `workspace.trip_features_v2`, which is how the adapter reads the
table back.

## See Also

- `data/engines/` — `ramo-data.json`, the bundled DuckDB adapter, how a build script writes
  into the project database, and the same contract over a remote engine.
- `data/dataset-materialization.md` — turning a query result into a durable dataset.
- `data/domain-definitions.md` — the domain facts a query encodes (B in the four-way split).
- `data/table-pitfalls.md` — the traps a table or a join hides (C).
