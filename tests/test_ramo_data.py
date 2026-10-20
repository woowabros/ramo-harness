# 데이터 접근 어댑터(ramo-data.py)의 읽기 명령과 읽기 전용 차단을 검증하는 테스트
"""Run with: python3 -m pytest tests/ (needs `duckdb` and `pytest`)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

SCRIPT = Path(__file__).resolve().parents[1] / "harness" / "scripts" / "ramo-data.py"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
          SELECT * FROM (VALUES
            (1, TIMESTAMP '2023-01-01 08:00:00', TIMESTAMP '2023-01-01 08:12:00', 132, 2.5),
            (2, TIMESTAMP '2023-01-01 09:00:00', TIMESTAMP '2023-01-01 09:30:00', 138, 9.1),
            (1, TIMESTAMP '2023-01-02 10:00:00', TIMESTAMP '2023-01-02 10:05:00', 132, 0.8)
          ) AS t(VendorID, tpep_pickup_datetime, tpep_dropoff_datetime, PULocationID, trip_distance)
        ) TO '{data / "trips.parquet"}' (FORMAT parquet)
        """
    )
    (data / "zones.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n132,Queens,JFK Airport,Airports\n138,Queens,LaGuardia Airport,Airports\n"
    )
    ws = duckdb.connect(str(tmp_path / "project.duckdb"))
    ws.execute("CREATE SCHEMA workspace; CREATE TABLE workspace.trip_base AS SELECT 1 AS a")
    ws.close()
    config = {
        "engine": "duckdb",
        "data_dir": "data",
        "database": "project.duckdb",
        "workspace_schema": "workspace",
        "tables": {
            "tlc.yellow_trips": {
                "path": "data/trips.parquet",
                "derive": {"pickup_date": "CAST(tpep_pickup_datetime AS DATE)"},
                "partition_key": "pickup_date",
                "description": "Yellow taxi trips, one row per trip",
            },
            "tlc.taxi_zones": {"path": "data/zones.csv", "description": "Zone lookup"},
        },
    }
    (tmp_path / "ramo-data.json").write_text(json.dumps(config))
    return tmp_path


def run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=project, capture_output=True, text=True
    )


def test_ping(project):
    r = run(project, "ping")
    assert r.returncode == 0, r.stderr
    assert "tlc.yellow_trips" in r.stdout and "tlc.taxi_zones" in r.stdout


def test_schema_includes_derived_column(project):
    r = run(project, "schema", "tlc.yellow_trips")
    assert r.returncode == 0, r.stderr
    assert "tpep_pickup_datetime" in r.stdout and "pickup_date" in r.stdout


def test_partitions(project):
    r = run(project, "partitions", "tlc.yellow_trips")
    assert r.returncode == 0, r.stderr
    assert "2023-01-01" in r.stdout and "2023-01-02" in r.stdout


def test_partitions_without_key(project):
    r = run(project, "partitions", "tlc.taxi_zones")
    assert r.returncode == 0, r.stderr
    assert "no partition key" in r.stdout


def test_search_matches_table_and_column(project):
    assert "tlc.taxi_zones" in run(project, "search", "borough").stdout
    assert "tlc.yellow_trips" in run(project, "search", "trip").stdout


def test_query_join_and_limit(project):
    sql = (
        "SELECT z.Borough, count(*) AS n FROM tlc.yellow_trips t "
        "JOIN tlc.taxi_zones z ON t.PULocationID = z.LocationID GROUP BY 1"
    )
    r = run(project, "query", "--sql", sql, "--limit", "10")
    assert r.returncode == 0, r.stderr
    assert "Queens" in r.stdout and "| 3 |" in r.stdout


def test_query_outer_limit_applies(project):
    r = run(project, "query", "--sql", "SELECT * FROM tlc.yellow_trips", "--limit", "1")
    assert r.returncode == 0, r.stderr
    assert "1 row" in r.stdout and "truncated" in r.stdout


def test_query_from_file_and_workspace_table(project):
    (project / "q.sql").write_text("-- comment\nSELECT a FROM workspace.trip_base;\n")
    r = run(project, "query", "--file", "q.sql")
    assert r.returncode == 0, r.stderr
    assert "| 1 |" in r.stdout


def test_query_csv_format(project):
    r = run(project, "query", "--sql", "SELECT Zone FROM tlc.taxi_zones ORDER BY 1", "--format", "csv")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0] == "Zone"


def test_explain(project):
    r = run(project, "explain", "--sql", "SELECT count(*) FROM tlc.yellow_trips")
    assert r.returncode == 0, r.stderr
    assert "PLAN" in r.stdout.upper() or "SCAN" in r.stdout.upper()


def test_summarize_is_allowed(project):
    r = run(project, "query", "--sql", "SUMMARIZE tlc.yellow_trips")
    assert r.returncode == 0, r.stderr


def test_string_literal_with_keyword_is_allowed(project):
    r = run(project, "query", "--sql", "SELECT 'drop table; insert' AS note")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE x",
        "WITH x AS (SELECT 1) INSERT INTO workspace.trip_base SELECT * FROM x",
        "CREATE TABLE workspace.y AS SELECT 1",
        "DELETE FROM workspace.trip_base",
        "COPY (SELECT 1) TO 'data/leak.csv'",
        "ATTACH 'other.duckdb' AS o",
        "INSTALL httpfs",
        "LOAD httpfs",
        "PRAGMA enable_progress_bar",
        "SET threads = 1",
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_text('/etc/hosts')",
    ],
)
def test_refuses_non_read(project, sql):
    r = run(project, "query", "--sql", sql)
    assert r.returncode != 0
    assert not (project / "data" / "leak.csv").exists()


def test_refusal_exit_code_and_message(project):
    r = run(project, "query", "--sql", "DROP TABLE workspace.trip_base")
    assert r.returncode == 3
    assert "BLOCKED" in r.stderr


def test_missing_config(tmp_path):
    r = run(tmp_path, "ping")
    assert r.returncode == 2
    assert "ramo-data.json" in r.stderr


def test_unknown_table(project):
    r = run(project, "schema", "tlc.nope")
    assert r.returncode == 2
