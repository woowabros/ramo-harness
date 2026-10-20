---
description: Trino as the warehouse engine — public engine behaviors that break plausible SQL, and how a team implements the data access adapter's command contract and exit codes over a Trino DB-API cursor
paths:
  - "ramo-data.json"
---

# Engine: Trino

The bundled adapter (`.claude/scripts/ramo-data.py`) runs on DuckDB and exits 2 for any other
`engine`. A team whose warehouse is Trino keeps every rule in `data/warehouse-access.md` and
supplies an adapter that honors the same commands and exit codes. This file holds what is
specific to Trino: engine behaviors that hold for every table, and what that adapter must do.

## Engine Facts

Properties of the engine, true of every table. They belong here rather than in
`data/table-pitfalls.md`, which holds traps in a particular table or join. Each row is a
statement that compiled, or looked like it would, and then cost a re-plan, a BLOCKED task, or a
broken check.

| Fact | What it breaks | What to write instead |
|---|---|---|
| `xxhash64(to_utf8(x))` returns `varbinary`, not `bigint` | `mod(hash, n)` fails with `FUNCTION_NOT_FOUND: Unexpected parameters (varbinary, integer)`. `ORDER BY` on the same expression compiles fine, so "deterministic ranking by hash" works while "deterministic remainder by hash" does not — mix the two idioms in one plan and only one of them fails | Wrap it: `from_big_endian_64(xxhash64(to_utf8(x)))`. The result is a **signed** bigint and `mod` follows the dividend's sign, so `= 0` keeps the intended 1-in-n selectivity (about 10% for `n = 10`) while `= k` for any other `k` halves it |
| A correlated partition predicate is not statically pruned | Writing one table's partition column as a range against another's (`a.pickup_date BETWEEN b.pickup_date - INTERVAL '1' DAY AND b.pickup_date + INTERVAL '1' DAY`) leaves the planner unable to prune, and on a partitioned connector the statement fails on the partition ceiling (`HIVE_EXCEEDED_PARTITION_LIMIT`) | Fold the bound to literals, or split the run by date. A join window that must stay correlated is a per-date loop, not one statement |
| Replace-in-place is connector-dependent | `CREATE OR REPLACE TABLE` works on some connectors (Iceberg, for one) and is rejected on others, so an idempotent build written for one catalog fails on another | Probe the form at smoke scale against the target catalog; where it is rejected, `DROP TABLE IF EXISTS` then `CREATE TABLE ... AS` (`data/dataset-materialization.md` Writing) |

Adding a row here needs the error text and the date it was observed
(`data/warehouse-access.md` Engine Facts).

## Implementing the adapter over a DB-API cursor

The contract is the command line, not the code: agents, skills, and rules call
`python3 .claude/scripts/ramo-data.py <command>` and read its exit code, so an adapter that
keeps both can replace the bundled one without touching any other harness asset. Keep the
replacement in the harness source the team installs from, at the same path. The client is the
PyPI `trino` package (`trino.dbapi.connect`).

**Configuration.** `ramo-data.json` keeps its role and gains `"engine": "trino"`. Declare the
catalogs and schemas the read path may see, and the logical tables when the team wants
`search` limited to them; `partition_key` and `description` keep their meaning. Host, port,
user, and any credential come from environment variables, never from the file — it is
committed (`dataset-materialization.md` Connecting).

| Command | What it does on Trino |
|---|---|
| `ping` | Connect and run one cheap statement (`SELECT 1`, or the server version), then list the declared tables from metadata. Never count rows per table: on a warehouse that is a full scan per table |
| `search <kw>` | Match the keyword against `information_schema.tables` and `information_schema.columns` (names, plus table comments where the connector exposes them), limited to the declared catalogs and schemas |
| `schema <table>` | `DESCRIBE <table>`, or `information_schema.columns` with the column comment |
| `partitions <table>` | Read the connector's partition metadata table (`"<table>$partitions"` on the Hive and Iceberg connectors) instead of grouping the table itself; print the count, the first and last value, and a capped list |
| `explain` | `EXPLAIN <stmt>`; `EXPLAIN (TYPE IO)` adds the tables and partition ranges the statement would read, which is the cost signal the authoring sequence asks for |
| `query` | Wrap the checked statement as `SELECT * FROM (<stmt>) LIMIT <N+1>`, fetch, print at most `N` rows, and say when it truncated. Same `--limit` default (1000), cap, and `md`/`csv` formats |

**Read-only stays two layers.** Keep the statement check exactly as the bundled adapter applies
it (one statement, a read keyword first, no write or session keyword outside literals). The
engine layer is the credential: connect the read path as a principal the cluster's access
control grants `SELECT` only, so a statement the lexical check misses still cannot write. A
read path that connects as a principal able to write has one layer, and the rules that cite
this adapter as grade 2 would then overclaim.

**Exit codes are the same.** 0 ok; 1 query error (including a connection that times out or is
refused, with the error class in the message, so `ping` is what tells connectivity apart);
2 usage or configuration error (missing or invalid `ramo-data.json`, missing environment
variable, unknown table); 3 refused as not read-only, stderr starting `BLOCKED:` (the
statement check, or the engine's access-denied error); 4 the `trino` package is not installed.

**Authorization prompts are a person's job.** When the cluster's authentication needs an
interactive step (a browser login, a token refresh), the adapter exits non-zero with what the
person must do; an agent cannot complete it and reports BLOCKED rather than retrying.

## The write path on Trino

A `dataset-build` script opens its own DB-API connection, as a principal allowed to write only
into the workspace schema where the access control can express that, and runs each statement in
order (`data/warehouse-access.md` Building a Dataset). Two client behaviors matter:

- Fetch each statement's result before running the next. `execute()` can return while the
  statement is still running; a script that moves on reads an incomplete table, and one that
  closes the connection early can leave the statement cancelled.
- Qualify every target as `<catalog>.<workspace_schema>.<name>`. The connection's default
  catalog and schema are whatever the session was opened with, and the write-boundary hooks
  match the schema segment, not the catalog.

A build too heavy to run from the session is handed to a person to run on the team's batch
facility; record which path ran (`data/warehouse-access.md`).

## See Also

- `data/warehouse-access.md` — the two sanctioned paths, the authoring sequence, HARD rules.
- `data/engines/duckdb.md` — the bundled implementation this contract is read from.
- `data/dataset-materialization.md` — dataset shapes, idempotent writes, retention.
