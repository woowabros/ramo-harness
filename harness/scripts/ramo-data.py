#!/usr/bin/env python3
# 데이터 단계가 웨어하우스를 읽는 유일한 경로: 프로젝트 ramo-data.json 의 테이블을 DuckDB 로 읽기 전용 조회하는 어댑터
"""Data access adapter (rules/data/warehouse-access.md).

Every data-stage agent reads data through this one command contract:

    python3 .claude/scripts/ramo-data.py ping
    python3 .claude/scripts/ramo-data.py search <keyword>
    python3 .claude/scripts/ramo-data.py schema <table>
    python3 .claude/scripts/ramo-data.py partitions <table>
    python3 .claude/scripts/ramo-data.py explain (--sql "<stmt>" | --file <path>)
    python3 .claude/scripts/ramo-data.py query (--sql "<stmt>" | --file <path>) [--limit N] [--format md|csv]

Tables are declared in `ramo-data.json` at the project root (searched upward from the working
directory). This implementation targets DuckDB over local parquet/CSV/JSON files; another engine
keeps the same commands and exit codes (rules/data/engines/).

The read path refuses to write, in two layers:
1. Statement check: exactly one statement, starting with a read keyword, with no write or
   session-changing keyword outside string literals.
2. Engine sandbox: an in-memory connection, the project database attached READ_ONLY, file
   access limited to the declared data directories, extension install/load disabled, and the
   configuration locked before any user statement runs.
Neither layer alone covers everything (the sandbox still allows COPY into a data directory; the
statement check is lexical), so both run on every statement.

Exit codes: 0 ok, 1 query error, 2 usage or configuration error, 3 refused (not read-only),
4 dependency missing.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

CONFIG_NAME = "ramo-data.json"
DEFAULT_LIMIT = 1000
MAX_LIMIT = 100_000
PARTITION_LIST_MAX = 60

READ_START = {"SELECT", "WITH", "FROM", "VALUES", "TABLE", "DESCRIBE", "SHOW", "SUMMARIZE", "EXPLAIN"}
WRITE_WORDS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "CREATE", "DROP", "ALTER", "TRUNCATE",
    "COPY", "EXPORT", "IMPORT", "ATTACH", "DETACH", "INSTALL", "LOAD", "FORCE", "PRAGMA", "SET",
    "RESET", "CALL", "USE", "VACUUM", "CHECKPOINT", "ANALYZE", "GRANT", "REVOKE", "BEGIN",
    "COMMIT", "ROLLBACK", "TRANSACTION",
}
# Table functions that read outside the declared tables; the sandbox limits their paths, and the
# statement check refuses the ones that read raw text a table declaration never needs.
REFUSED_FUNCTIONS = {"read_text", "read_blob", "glob", "sniff_csv"}
READERS = {".parquet": "read_parquet", ".csv": "read_csv_auto", ".tsv": "read_csv_auto",
           ".json": "read_json_auto", ".jsonl": "read_json_auto", ".ndjson": "read_json_auto"}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class UsageError(Exception):
    """Bad arguments or configuration (exit 2)."""


class Refused(Exception):
    """A statement that is not a single read (exit 3)."""


# --- statement check ---------------------------------------------------------------------------

def _mask(sql: str) -> str:
    """Blank comments and the contents of quoted strings/identifiers, keeping statement shape."""
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(" " * (j - i))
            i = j
        elif c in ("'", '"'):
            j = i + 1
            while j < n:
                if sql[j] == c and j + 1 < n and sql[j + 1] == c:
                    j += 2
                    continue
                if sql[j] == c:
                    break
                j += 1
            out.append(c + " " * (min(j, n) - i - 1) + (c if j < n else ""))
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def check_read_only(sql: str) -> str:
    """Return the single statement without its trailing semicolon, or raise Refused."""
    masked = _mask(sql)
    parts = [p for p in masked.split(";") if p.strip()]
    if not parts:
        raise Refused("empty statement")
    if len(parts) > 1:
        raise Refused("one statement per call")
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", masked)
    first = words[0].upper() if words else ""
    if first not in READ_START:
        raise Refused(f"statement starts with {first or '?'}; only reads are allowed")
    upper = {w.upper() for w in words}
    hit = sorted(upper & WRITE_WORDS)
    if hit:
        raise Refused(f"write or session keyword outside a string literal: {', '.join(hit)}")
    lowered = {w.lower() for w in words}
    bad = sorted(lowered & REFUSED_FUNCTIONS)
    if bad:
        raise Refused(f"function not available on the read path: {', '.join(bad)}")
    # Strip the trailing semicolon from the original text so the statement can be wrapped.
    end = len(masked.rstrip().rstrip(";").rstrip())
    return sql[:end]


# --- configuration -----------------------------------------------------------------------------

def find_config(start: Path) -> Path:
    for d in (start, *start.parents):
        p = d / CONFIG_NAME
        if p.is_file():
            return p
    raise UsageError(
        f"{CONFIG_NAME} not found from {start} upward. Create it at the project root "
        "(rules/data/engines/duckdb.md has an example)."
    )


def load_config(path: Path) -> dict:
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise UsageError(f"{path}: invalid JSON ({e})") from e
    if cfg.get("engine", "duckdb") != "duckdb":
        raise UsageError(f"{path}: engine '{cfg.get('engine')}' is not handled by this adapter")
    tables = cfg.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise UsageError(f"{path}: 'tables' must map logical names to sources")
    for name, spec in tables.items():
        parts = name.split(".")
        if len(parts) != 2 or not all(IDENT.match(p) for p in parts):
            raise UsageError(f"table name '{name}' must be <schema>.<table>")
        if not isinstance(spec, dict) or "path" not in spec:
            raise UsageError(f"table '{name}' needs a 'path'")
    return cfg


def _reader(path: str) -> str:
    suffix = Path(path.replace("*", "x")).suffix.lower()
    if suffix not in READERS:
        raise UsageError(f"unsupported file type for '{path}' (parquet, csv, tsv, json, jsonl)")
    return READERS[suffix]


def _quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


# --- engine ------------------------------------------------------------------------------------

def connect(cfg: dict, root: Path):
    try:
        import duckdb
    except ImportError:
        print("BLOCKED: the data adapter needs DuckDB. Install it with `pip install duckdb` "
              "(or `uv pip install duckdb`).", file=sys.stderr)
        sys.exit(4)

    con = duckdb.connect(":memory:")
    allowed = {(root / cfg.get("data_dir", ".")).resolve()}
    workspace = cfg.get("workspace_schema", "workspace")
    created_schemas: set[str] = set()

    def ensure_schema(schema: str) -> None:
        if schema not in created_schemas:
            con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            created_schemas.add(schema)

    for name, spec in cfg["tables"].items():
        schema, table = name.split(".")
        src = (root / spec["path"]).resolve() if not Path(spec["path"]).is_absolute() else Path(spec["path"])
        allowed.add(src.parent if "*" not in str(src) else Path(str(src).split("*")[0]).parent)
        reader = _reader(str(src))
        opts = ", hive_partitioning = true" if reader == "read_parquet" and "*" in str(src) else ""
        derive = spec.get("derive") or {}
        extra = "".join(f', {expr} AS "{col}"' for col, expr in derive.items())
        ensure_schema(schema)
        con.execute(f'CREATE VIEW "{schema}"."{table}" AS SELECT *{extra} FROM {reader}({_quote(str(src))}{opts})')

    db = cfg.get("database")
    if db:
        db_path = (root / db).resolve()
        if db_path.exists():
            con.execute(f"ATTACH {_quote(str(db_path))} AS ramo_project (READ_ONLY)")
            rows = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_catalog = 'ramo_project' AND table_schema = ?", [workspace]
            ).fetchall()
            for (t,) in rows:
                ensure_schema(workspace)
                con.execute(f'CREATE VIEW "{workspace}"."{t}" AS SELECT * FROM ramo_project."{workspace}"."{t}"')

    dirs = ", ".join(_quote(str(d) + "/") for d in sorted(allowed))
    for stmt in (
        f"SET allowed_directories = [{dirs}]",
        "SET enable_external_access = false",
        "SET autoinstall_known_extensions = false",
        "SET autoload_known_extensions = false",
        "SET lock_configuration = true",
    ):
        con.execute(stmt)
    return con


def _user_tables(con) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_catalog = current_database() ORDER BY 1, 2"
    ).fetchall()


def _require_table(con, name: str) -> None:
    if tuple(name.split(".", 1)) not in set(_user_tables(con)):
        raise UsageError(f"unknown table '{name}'; run `search` to list declared tables")


# --- output ------------------------------------------------------------------------------------

def _cell(v) -> str:
    return "" if v is None else str(v).replace("|", "\\|").replace("\n", " ")


def render(columns: list[str], rows: list[tuple], fmt: str) -> str:
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(columns)
        w.writerows(rows)
        return buf.getvalue().rstrip("\n")
    head = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(_cell(v) for v in r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


# --- commands ----------------------------------------------------------------------------------

def cmd_ping(con, cfg: dict, cfg_path: Path, _args) -> None:
    import duckdb
    print(f"engine: duckdb {duckdb.__version__}")
    print(f"config: {cfg_path}")
    for name in cfg["tables"]:
        n = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        print(f"{name}: {n} rows")


def cmd_search(con, cfg: dict, _p, args) -> None:
    kw = args.keyword.lower()
    out = []
    for schema, table in _user_tables(con):
        name = f"{schema}.{table}"
        desc = (cfg["tables"].get(name) or {}).get("description", "")
        cols = [r[0] for r in con.execute(f'DESCRIBE "{schema}"."{table}"').fetchall()]
        matched = [c for c in cols if kw in c.lower()]
        if kw in name.lower() or kw in desc.lower() or matched:
            out.append((name, desc, ", ".join(matched)))
    print(render(["table", "description", "matching columns"], out, "md") if out else f"no table matches '{args.keyword}'")


def cmd_schema(con, cfg: dict, _p, args) -> None:
    _require_table(con, args.table)
    spec = cfg["tables"].get(args.table, {})
    if spec.get("description"):
        print(f"{args.table}: {spec['description']}")
    derived = set((spec.get("derive") or {}).keys())
    rows = con.execute(f"DESCRIBE {args.table}").fetchall()
    out = [(r[0], r[1], r[2], "derived" if r[0] in derived else "") for r in rows]
    print(render(["column", "type", "nullable", "note"], out, "md"))


def cmd_partitions(con, cfg: dict, _p, args) -> None:
    _require_table(con, args.table)
    key = (cfg["tables"].get(args.table) or {}).get("partition_key")
    if not key:
        print(f"{args.table}: no partition key declared")
        return
    rows = con.execute(f'SELECT "{key}", count(*) FROM {args.table} GROUP BY 1 ORDER BY 1').fetchall()
    print(f"{args.table}: partition key {key}, {len(rows)} values, {rows[0][0]} .. {rows[-1][0]}" if rows else f"{args.table}: empty")
    shown = rows if len(rows) <= PARTITION_LIST_MAX else rows[:PARTITION_LIST_MAX // 2] + [("...", "")] + rows[-PARTITION_LIST_MAX // 2:]
    print(render([key, "rows"], shown, "md"))


def _statement(args) -> str:
    if bool(args.sql) == bool(args.file):
        raise UsageError("give exactly one of --sql or --file")
    return args.sql if args.sql else Path(args.file).read_text()


def cmd_explain(con, _cfg, _p, args) -> None:
    stmt = check_read_only(_statement(args))
    for _kind, plan in con.execute(f"EXPLAIN {stmt}").fetchall():
        print(plan)


def cmd_query(con, _cfg, _p, args) -> None:
    stmt = check_read_only(_statement(args))
    limit = max(1, min(args.limit, MAX_LIMIT))
    first = re.findall(r"[A-Za-z_]+", _mask(stmt))[0].upper()
    wrap = first in {"SELECT", "WITH", "FROM", "VALUES", "TABLE"}
    sql = f"SELECT * FROM ({stmt}) AS ramo_q LIMIT {limit + 1}" if wrap else stmt
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    truncated = len(rows) > limit
    rows = rows[:limit]
    print(render(columns, rows, args.format))
    if args.format == "md":
        print(f"\n{len(rows)} row{'s' if len(rows) != 1 else ''}" + (f" (truncated at --limit {limit})" if truncated else ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ramo-data.py", description="Read-only data access adapter.")
    ap.add_argument("--config", help=f"path to {CONFIG_NAME} (default: search upward from cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="check the configuration and count rows per table")
    p = sub.add_parser("search", help="find tables by name, description, or column")
    p.add_argument("keyword")
    for name in ("schema", "partitions"):
        p = sub.add_parser(name)
        p.add_argument("table")
    for name in ("explain", "query"):
        p = sub.add_parser(name)
        p.add_argument("--sql")
        p.add_argument("--file")
        if name == "query":
            p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
            p.add_argument("--format", choices=("md", "csv"), default="md")
    args = ap.parse_args(argv)

    try:
        cfg_path = Path(args.config).resolve() if args.config else find_config(Path.cwd())
        cfg = load_config(cfg_path)
        con = connect(cfg, cfg_path.parent)
        handler = {"ping": cmd_ping, "search": cmd_search, "schema": cmd_schema,
                   "partitions": cmd_partitions, "explain": cmd_explain, "query": cmd_query}[args.cmd]
        handler(con, cfg, cfg_path, args)
        return 0
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Refused as e:
        print(f"BLOCKED: {e}. The read path runs single read statements only "
              "(rules/data/warehouse-access.md).", file=sys.stderr)
        return 3
    except Exception as e:  # engine errors, including sandbox permission errors
        name = type(e).__name__
        if "Permission" in name:
            print(f"BLOCKED: {e}", file=sys.stderr)
            return 3
        print(f"error: {name}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
