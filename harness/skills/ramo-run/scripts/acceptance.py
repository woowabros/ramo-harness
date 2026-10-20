#!/usr/bin/env python3
# 플랜의 행 매핑·단위 Checks·validity 를 파싱하고, 행 증거를 보편 불변식과 재계산 digest 로 판정하는 스크립트
"""Row check runtime (workflow/01b-acceptance-contract.md).
stdlib-only (python >= 3.9, workflow/08-hook-conventions.md HARD 3).

One parser gates plan Step 2b (`parse`), run Step 3f (`check`), and verify Gate 3 (`recheck`).
Every number and vocabulary is read from `.claude/schema/harness.json`; the allow-grammar and the
SQL CLI name set are imported from pre_bash, never copied. The plan declares what is built and
how it is measured, never what the values will be: a row is judged by its deliverables, its
unit's Checks commands (exit 0), and invariants that hold for every plan. A failure line says
what is wrong, never the value that would pass. The script never executes a check command; the
main session runs each with its own Bash tool and hands the outcome in. Kill switch:
`scripts.acceptance.kill_switch` set to `false` makes parse, check, and recheck exit 0 unjudged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PAYLOAD_ROOT = SCRIPT_DIR.parents[2]  # .claude/ in a consumer repo, harness/ in this one
SCHEMA_PATH = PAYLOAD_ROOT / "schema" / "harness.json"
HANDLERS_DIR = PAYLOAD_ROOT / "hooks" / "ramo" / "handlers"

sys.path.insert(0, str(HANDLERS_DIR))
from pre_bash import NOT_PLAIN, names_sql_cli  # noqa: E402
from subagent_stop import TAG_RE, parse_result_block  # noqa: E402  (the hook's own parser)

TABLE_HEADER = "| # | Task | Domain | Type | Dependencies | Deliverable |"
ROW_ID = re.compile(r"^(\d+)( \[CP\])?$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MODULE_FUNCTION = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
TABLE_DELIVERABLE = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*){1,2}:(?:intermediate|experiment)$")
QUALITY = re.compile(r"^(\d+)/(\d+)\b")
RECONCILIATION = re.compile(r"^([0-9][0-9,]*)\s*==\s*([0-9][0-9,]*)$")


class CliError(Exception):
    """A usage error: which argument, why it is wrong, how to fix it."""

    def __init__(self, arg: str, why: str, fix: str):
        super().__init__(f"{arg}: {why} (fix: {fix})")


class Blocked:
    """Collects BLOCKED lines in the `row {n} | {key} | {reason}` shape."""

    def __init__(self):
        self.lines: list[str] = []

    def add(self, row, key: str, reason: str):
        self.lines.append(f"row {row if row is not None else '-'} | {key} | {reason}")


# --------------------------------------------------------------------- schema

def load_schema() -> dict:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError("schema", f"cannot read {SCHEMA_PATH.name}: {exc}",
                       "re-seed the harness payload (ramo init)")
    return {
        "limits": schema["limits"],
        "key_formats": schema["envelope"]["evidence"]["key_formats"],
        "domains": {name: entry["evidence"] for name, entry in schema["domains"].items()
                    if not name.startswith("_")},
        "plan_blocks": schema["plan_blocks"],
        "state_records": schema["state_records"],
        "scripts": schema["scripts"]["acceptance"],
    }


def gate_disabled(schema: dict) -> bool:
    return os.environ.get(schema["scripts"]["kill_switch"], "").strip().lower() == "false"


def type_required_keys(schema: dict, task_type: str) -> list[str]:
    for evidence in schema["domains"].values():
        entry = evidence.get(task_type)
        if isinstance(entry, dict):
            return list(entry.get("required_keys", []))
    return []


# ------------------------------------------------------------ YAML-lite block

def parse_block(text: str, blocked: Blocked, where: str) -> dict:
    """YAML-lite: `key: value`, `- item`, two-space nesting, no flow syntax; values stay raw strings."""
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]
    last_key: dict[int, tuple[dict, str]] = {}

    def fail(key, reason):
        blocked.add(None, f"{where}.{key}" if key else where, reason)

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if line.startswith("- "):
            owner = last_key.get(indent - 2)
            if owner is None:
                fail(None, f"list item with no key above it: {line}")
                continue
            container, key = owner
            if not isinstance(container.get(key), list):
                container[key] = []
            container[key].append(line[2:].strip())
            continue
        key, sep, value = line.partition(":")
        if not sep:
            fail(None, f"line is neither `key: value` nor `- item`: {line}")
            continue
        key, value = key.strip(), value.strip()
        if value[:1] in ("[", "{"):
            fail(key, "flow syntax is not accepted; write one `- item` per line")
            continue
        if not isinstance(parent, dict):
            fail(None, f"key under a list item: {line}")
            continue
        if value:
            parent[key] = value
        else:
            parent[key] = {}
            stack.append((indent, parent[key]))
        last_key[indent] = (parent, key)
    return root


def _mixed_to_list(value) -> list[str]:
    """A key that took `- item` children was first opened as an empty mapping."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and not value:
        return []
    return [value] if isinstance(value, str) else []


# ------------------------------------------------------------------ plan text

def _fenced_blocks(text: str, name: str) -> list[str]:
    """Body of every fence whose info string is exactly `name`."""
    return [m.group(2) for m in re.finditer(rf"^(`{{3,}}){re.escape(name)}[ \t]*\n(.*?)^\1[ \t]*$", text, re.M | re.S)]


def _mixed_deliverables(cell: str) -> bool:
    """A backticked path next to a bare one: the bare part would be silently dropped."""
    rest = re.sub(r"`[^`]+`", "", cell)
    return "`" in cell and bool(re.sub(r"[\s,—]", "", rest))


def _deliverables(cell: str) -> list[str]:
    ticked = re.findall(r"`([^`]+)`", cell)
    if ticked:
        return [t.strip() for t in ticked]
    return [part.strip() for part in cell.split(",") if part.strip() and part.strip() != "—"]


def _fence_step(line: str, fence: str | None, wrapper: str | None) -> tuple[str | None, str | None, bool]:
    """(fence, wrapper, is this a fence line). A fence closes on the same character, at least as
    long, with no info string. A `markdown` fence wraps plan text (the template) and stays open."""
    m = re.match(r"^\s*(`{3,}|~{3,})\s*([\w-]*)", line)
    if not m:
        return fence, wrapper, False
    ticks, info = m.groups()
    closes = lambda opener: bool(opener) and not info and ticks[0] == opener[0] and len(ticks) >= len(opener)  # noqa: E731
    if fence:
        return (None if closes(fence) else fence), wrapper, True
    if info in ("markdown", "md"):
        return None, ticks, True
    return (None, None, True) if closes(wrapper) else (ticks, wrapper, True)


def _units(lines: list[str], mapping: dict) -> tuple[dict, list[tuple[str, str]]]:
    """Each unit's Binding decisions and Checks lines, plus every such line left unattributed."""
    units: dict = {}
    strays, current, fence, wrapper = [], None, None, None
    for line in lines:
        fence, wrapper, is_fence_line = _fence_step(line, fence, wrapper)
        if is_fence_line:
            continue
        m = None if fence else re.match(mapping["unit_heading_regex"], line)
        if m or (not fence and re.match(r"^#{1,3} ", line)):
            current = units.setdefault(m.group(1), {"binding": None, "checks": None}) if m else None
            continue
        for key, word in (("binding", "**Binding decisions"), ("checks", "**Checks")):
            hit = None if fence else re.match(mapping[f"{key}_line_regex"], line.strip())
            if hit and current is not None and current[key] is None:
                current[key] = hit.group(1).strip()
            elif not fence and word in line:
                strays.append((key, line.strip()))
    return units, strays


def parse_plan(text: str, schema: dict) -> dict:
    """Read the plan's machine parts: D-ids, units, execution rows, and the validity fences."""
    blocks = schema["plan_blocks"]
    mapping = blocks["row_mapping"]
    lines = text.splitlines()
    decisions = {m.group(1) for line in lines if (m := re.match(mapping["decision_row_regex"], line))}
    units, strays = _units(lines, mapping)

    start = next((i for i, line in enumerate(lines) if line.strip() == "# Execution Structure"), len(lines))
    rows, in_table = [], False
    for stripped in (line.strip() for line in lines[start + 1:]):
        in_table = stripped == TABLE_HEADER or (in_table and stripped.startswith("|"))
        cells = [c.strip() for c in stripped.strip("|").split("|")] if in_table else []
        m = ROW_ID.match(cells[0]) if len(cells) == 6 else None  # the header and |---| never match
        if not m:
            continue
        deps = [] if cells[4] in ("—", "-", "") else [d.strip() for d in cells[4].split(",")]
        rows.append({"id": int(m.group(1)), "cp": bool(m.group(2)), "task": cells[1],
                     "domain": cells[2], "type": cells[3], "dependencies": deps,
                     "deliverables": _deliverables(cells[5]),
                     "unit_tokens": sorted(set(re.findall(mapping["unit_token_regex"], cells[1]))),
                     "mixed_deliverables": _mixed_deliverables(cells[5])})
    return {
        "decisions": decisions,
        "units": units,
        "strays": strays,
        "rows": rows,
        "validity_fences": _fenced_blocks(text, blocks["validity"]["fence"]),
    }


# ----------------------------------------------------------------- validation

def _map_row(row: dict, plan: dict, schema: dict, blocked: Blocked) -> None:
    """Attach unit, binding, and checks to one row, from the Task cell and the unit's lines."""
    mapping = schema["plan_blocks"]["row_mapping"]
    rid, tokens = row["id"], row.pop("unit_tokens")
    exempt = row["domain"] in mapping["exempt_domains"] or row["type"] in mapping["exempt_types"]
    row.update(unit=None, binding=[], checks=[])
    if len(tokens) != 1:
        if not exempt:
            blocked.add(rid, "unit", f"Task cell names exactly one U{{n}} (found {len(tokens)})")
        return
    unit = plan["units"].get(tokens[0])
    if unit is None:
        if not exempt:
            blocked.add(rid, "unit", f"`{tokens[0]}` names no `### U<n>` change unit heading")
        return
    row["unit"] = tokens[0]

    binding = unit["binding"]
    if not binding:  # no line, or a line with nothing after the colon
        if not exempt:
            blocked.add(rid, "binding", f"{tokens[0]} has no `Binding decisions:` value; list D-ids or write `none`")
    elif binding != "none":
        ids = [b.strip() for b in binding.split(",") if b.strip()]
        for d in ids:
            if d not in plan["decisions"]:
                blocked.add(rid, "binding", f"`{d}` names no `| D<n> |` row in the decisions table")
        row["binding"] = ids

    line = unit["checks"] or ""
    commands = [c.strip() for c in re.findall(r"`([^`]+)`", line)]
    if unit["checks"] is not None and (not commands or re.sub(r"`[^`]+`|[\s,]", "", line)):
        blocked.add(rid, "checks", f"{tokens[0]}: backtick each command on the `Checks:` line, comma-separated")
    for command in commands:
        found = NOT_PLAIN.search(command)
        if found:
            blocked.add(rid, "checks", f"`{command}` is not plain per workflow/12-subagent-bash-hygiene.md "
                                       f"(found `{found.group(0)}`)")
        elif names_sql_cli(command):
            blocked.add(rid, "checks", f"`{command}`: a SQL CLI is not a check command; read through the data access adapter")
        else:
            row["checks"].append(command)


def parse_validity(raw: dict, plan: dict, schema: dict, blocked: Blocked) -> dict:
    spec = schema["plan_blocks"]["validity"]
    known = set(spec["required"]) | set(spec["optional"])
    for key in [k for k in raw if k not in known]:
        blocked.add(None, f"validity.{key}", "not a validity key")
    for key in [k for k in spec["required"] if k not in raw]:
        blocked.add(None, f"validity.{key}", "required")
    lists = ("slices", "prediction_columns", "forbidden_columns")
    out = {key: _mixed_to_list(value) if key in lists else value for key, value in raw.items()}

    for key in ("seed", "min_n", "wall_minutes"):
        if key in raw:
            if isinstance(raw[key], str) and re.fullmatch(r"-?\d+", raw[key]):
                out[key] = int(raw[key])
            else:
                blocked.add(None, f"validity.{key}", "must be an integer")
    if "metric_tolerance" in raw:
        try:
            out["metric_tolerance"] = float(raw["metric_tolerance"])
        except ValueError:
            blocked.add(None, "validity.metric_tolerance", "must be a number")

    metric = raw.get("metric")
    if metric is not None and metric not in spec["standard_metrics"]:
        definition = raw.get("metric_definition")
        if not (isinstance(definition, str) and MODULE_FUNCTION.match(definition)):
            blocked.add(None, "validity.metric", "not a standard metric; add metric_definition: <module>:<function>")
    direction = raw.get("metric_direction")
    if direction is not None and direction not in spec["metric_directions"]:
        blocked.add(None, "validity.metric_direction", f"one of {', '.join(spec['metric_directions'])}")

    slices = out.get("slices", [])
    if "slices" in raw and not slices:
        blocked.add(None, "validity.slices", "list the slice column names, one `- item` per line")
    for name in slices:
        if not IDENT.match(name):
            blocked.add(None, "validity.slices", f"`{name}` is not a column name")

    baseline = raw.get("baseline")
    required_columns = list(spec["prediction_columns_required"])
    if isinstance(baseline, str) and not re.fullmatch(r"-?\d+(\.\d+)?", baseline):
        required_columns.append(baseline)
    columns = out.get("prediction_columns", [])
    if "prediction_columns" in raw:
        for column in required_columns:
            if column not in columns:
                blocked.add(None, "validity.prediction_columns", f"missing `{column}`")

    all_deliverables = {d for row in plan["rows"] for d in row["deliverables"]}
    for key in ("predictions", "features"):
        if key in raw and raw[key] not in all_deliverables:
            blocked.add(None, f"validity.{key}", f"`{raw[key]}` is in no row's Deliverable")
    return out


def validate_plan(text: str, schema: dict) -> tuple[dict, list[str]]:
    blocked = Blocked()
    plan = parse_plan(text, schema)
    if not plan["rows"]:
        blocked.add(None, "rows", "no Execution Structure row found under `# Execution Structure`")
    for row in plan["rows"]:
        if row.pop("mixed_deliverables", False):
            blocked.add(row["id"], "Deliverable", "backtick every path in the cell or none of them")
        _map_row(row, plan, schema, blocked)
    for key, line in plan["strays"]:
        blocked.add(None, key, f"line not read (misspelled, repeated in its unit, or outside a `### U<n>` unit): {line}")

    has_model = any(row["type"] == "model-training" for row in plan["rows"])
    validity = None
    vfences = plan["validity_fences"]
    if has_model and len(vfences) != 1:
        blocked.add(None, "validity", f"a plan with a model-training row carries exactly one "
                                      f"`validity` block (found {len(vfences)})")
    elif not has_model and vfences:
        blocked.add(None, "validity", "a plan with no model-training row carries no validity block")
    elif has_model:
        raw = parse_block(vfences[0], blocked, "validity")
        validity = parse_validity(raw, plan, schema, blocked)

    result = {
        "rows": plan["rows"],
        "validity": validity,
        "units": sorted(plan["units"]),
        "decisions": sorted(plan["decisions"]),
    }
    return result, blocked.lines


# ---------------------------------------------------------------------- hashes

def normalize_sql(text: str) -> str:
    kept = [line for line in text.splitlines() if not line.lstrip().startswith("--")]
    return re.sub(r"\s+", " ", "\n".join(kept)).strip()


def feature_spec_digest(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def sql_digest(texts: list[str]) -> str:
    return hashlib.sha256("\n".join(normalize_sql(t) for t in texts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ row check

def _find_root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, check=True).stdout.strip()
        return Path(out)
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def _git_names(root: Path, *args: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                             check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_files_git(root: Path, base: str | None) -> list[str]:
    """`git diff --name-only {base}` plus untracked files, names only (workflow/04-verify.md Canonical Change List)."""
    tracked = _git_names(root, "diff", "--name-only", base) if base and base != "none" else []
    untracked = _git_names(root, "ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked) | set(untracked))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frontmatter_value(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


def check_deliverables(root: Path, row: dict, envelope: dict) -> tuple[list[dict], list[dict]]:
    """Disk paths must exist and be non-empty; workspace tables must be in `dataset_tables`."""
    evidence = envelope.get("evidence") if isinstance(envelope.get("evidence"), dict) else {}
    tables = {part.strip() for part in str(evidence.get("dataset_tables", "")).split(",") if part.strip()}
    claimed = " ".join(str(a) for a in envelope.get("artifacts") or [])
    results, artifacts = [], []
    for item in row["deliverables"]:
        if TABLE_DELIVERABLE.match(item):
            ok = item in tables
            results.append({"path": item, "kind": "table", "pass": ok,
                            "reason": None if ok else "not in the envelope's dataset_tables"})
            continue
        path = root / item
        if path.is_file() and path.stat().st_size > 0:
            sha = _sha256_file(path)
            stated = re.search(re.escape(item) + r"\S*\s+(?:sha256:)?([0-9a-f]{64})", claimed)
            ok = stated is None or stated.group(1) == sha
            results.append({"path": item, "kind": "file", "pass": ok, "sha256": sha,
                            "reason": None if ok else "sha256 differs from the envelope's artifacts"})
            artifacts.append({"path": item, "sha256": sha})
        elif path.is_dir():
            results.append({"path": item, "kind": "dir", "pass": True})
            artifacts.append({"path": item, "sha256": None})
        else:
            results.append({"path": item, "kind": "file", "pass": False,
                            "reason": "missing or empty on disk"})
    return results, artifacts


def _check_outcome(command: str, result: dict) -> dict:
    """exit 0 within the ceiling is the only pass signal; only a digest of stdout is kept."""
    sha = result.get("stdout_sha256")
    if result.get("stdout_file"):
        sha = hashlib.sha256(Path(result["stdout_file"]).read_bytes()).hexdigest()
    timed_out = bool(result.get("timed_out"))
    return {"cmd": command, "exit": result.get("exit"), "seconds": result.get("seconds"),
            "stdout_sha256": sha, "timed_out": timed_out,
            "pass": not timed_out and result.get("exit") == 0}


def _invariant_failure(key: str, value: str, schema: dict) -> str | None:
    """The key's `_invariant` from key_formats, judged on the observed value alone."""
    if key == "quality_checks":
        m = QUALITY.match(value)
        if not m:
            return "not `<passed>/<declared>`"
        passed, declared = int(m.group(1)), int(m.group(2))
        if declared == 0:
            return "declares no checks"
        return None if passed == declared else "not every declared check passed"
    if key == "row_reconciliation":
        m = RECONCILIATION.match(value)
        if not m:
            return "not `<artifact rows> == <source rows>`"
        left, right = (int(g.replace(",", "")) for g in m.groups())
        return None if left == right else "the two sides differ"
    if key == "data_snapshot":
        lowered = value.lower()
        refs = schema["key_formats"]["data_snapshot"]["floating_refs"]
        if any(re.search(r"(?<![\w])" + re.escape(ref) + r"(?![\w])", lowered) for ref in refs):
            return "a floating reference pins no partition; record the resolved snapshot"
    return None


def _judge_evidence(root: Path, row: dict, validity: dict | None, evidence: dict, schema: dict) -> list[dict]:
    """Invariants that hold for every plan. A recomputed digest stays in the item, never in a failure line."""
    judged = []
    for key in type_required_keys(schema, row["type"]):
        if evidence.get(key) is None or str(evidence[key]).strip() == "":  # as the hook: 0 is a value
            judged.append({"key": key, "invariant": "present", "observed": evidence.get(key),
                           "pass": False, "why": "missing"})
    missing = {item["key"] for item in judged}
    for key in ("quality_checks", "row_reconciliation", "data_snapshot"):
        if key in missing or evidence.get(key) is None:
            continue
        why = _invariant_failure(key, str(evidence[key]).strip(), schema)
        judged.append({"key": key, "invariant": key, "observed": evidence[key], "pass": why is None, "why": why})

    if row["type"] == "model-training" and validity:
        for key in ("seed", "split_boundary"):
            if key in validity and key not in missing:
                ok = str(evidence.get(key, "")).strip() == str(validity[key])
                judged.append({"key": key, "invariant": "validity", "observed": evidence.get(key),
                               "pass": ok, "why": None if ok else "differs from the plan's validity block"})

    recompute = []
    sql = [root / d for d in row["deliverables"] if d.endswith(".sql") and (root / d).is_file()]
    if sql:
        recompute.append(("query_hash", sql_digest([p.read_text(encoding="utf-8") for p in sql]),
                          "the row's SQL deliverables"))
    features = (validity or {}).get("features")
    if features in row["deliverables"] and (root / features).is_file():
        recompute.append(("feature_spec", feature_spec_digest((root / features).read_text(encoding="utf-8")),
                          "the validity features file"))
    for key, full, source in recompute:
        if key in missing:
            continue
        text = "" if evidence.get(key) is None else str(evidence[key]).strip()
        shaped = re.fullmatch(schema["key_formats"][key]["pattern"], text) is not None
        ok = shaped and full.startswith(text.lower())
        why = None if ok else ("not a 16-64 character hex digest" if not shaped
                               else f"does not re-derive from {source}; record `acceptance.py hash` output")
        judged.append({"key": key, "invariant": "recomputed", "observed": evidence.get(key),
                       "pass": ok, "recomputed": full, "why": why})
    return judged


def check_row(root: Path, plan: dict, row: dict, envelope: dict, results: list[dict], schema: dict) -> dict:
    """Judge one row. Returns the `row_check` part of the record plus the failure lines."""
    evidence = envelope.get("evidence") if isinstance(envelope.get("evidence"), dict) else {}
    by_cmd = {r.get("cmd"): r for r in results}
    lines = []

    deliverables, artifacts = check_deliverables(root, row, envelope)
    for d in deliverables:
        if not d["pass"]:
            lines.append(f"row {row['id']} | deliverable | {d['path']}: {d['reason']}")

    checks = []
    for command in row["checks"]:
        if command not in by_cmd:
            raise CliError("--check-results", f"no result for the unit Checks command `{command}`",
                           "run every command on the unit's Checks line and pass each outcome")
        outcome = _check_outcome(command, by_cmd[command])
        checks.append(outcome)
        if not outcome["pass"]:
            why = "timed out" if outcome["timed_out"] else f"exit {outcome['exit']}"
            lines.append(f"row {row['id']} | checks | `{command}`: {why}")

    judged = _judge_evidence(root, row, plan["validity"], evidence, schema)
    for item in judged:
        if not item["pass"]:
            lines.append(f"row {row['id']} | evidence.{item['key']} | {item['why']}")

    verdict = "FAIL" if lines else "PASS"
    return {"verdict": verdict, "deliverables": deliverables, "evidence": judged, "checks": checks,
            "ceiling_seconds": schema["limits"]["run_row_check_command_max_seconds"],
            "_artifacts": artifacts, "_lines": lines}


def write_record(path: Path, record: dict) -> None:
    """Temp file in the same directory, then os.replace: a torn record is worse than none."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _parse_instant(value: str) -> datetime:
    """ISO-8601 with `Z`, an offset, or neither; a naive value is read as UTC (python >= 3.9)."""
    moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _seconds_between(started: str | None, finished: str | None) -> int | None:
    if not (started and finished):
        return None
    return int((_parse_instant(finished) - _parse_instant(started)).total_seconds())


# ------------------------------------------------------------------- commands

def _read(path_arg: str, arg: str) -> str:
    path = Path(path_arg)
    if not path.is_file():
        raise CliError(arg, f"{path_arg} is not a readable file", "pass an existing path")
    return path.read_text(encoding="utf-8")


def _read_results(path_arg: str | None) -> list[dict]:
    if path_arg is None:
        return []
    try:
        return json.loads(_read(path_arg, "--check-results"))
    except json.JSONDecodeError as exc:
        raise CliError("--check-results", f"not JSON: {exc}", "write a JSON list of outcomes")


def _plan_row(root: Path, args, schema) -> tuple[Path, dict, dict]:
    plan_path = root / args.plan
    plan, errors = validate_plan(_read(str(plan_path), "--plan"), schema)
    if errors:
        raise CliError("--plan", "the plan does not parse: " + errors[0], "run `parse` and fix the plan")
    row = next((r for r in plan["rows"] if r["id"] == args.row), None)
    if row is None:
        raise CliError("--row", f"row {args.row} is not in the Execution Structure", "pass a table row id")
    return plan_path, plan, row


def cmd_parse(args, schema) -> int:
    result, lines = validate_plan(_read(args.plan, "--plan"), schema)
    if args.json:
        print(json.dumps({"errors": lines} if lines else result, ensure_ascii=False, indent=1))
    else:
        for line in lines:
            print(line)
    return 1 if lines else 0


def cmd_hash(args, schema) -> int:
    if args.features:
        print(feature_spec_digest(_read(args.features, "--features")))
    else:
        print(sql_digest([_read(p, "--sql") for p in args.sql]))
    return 0


def cmd_check(args, schema) -> int:
    root = _find_root()
    plan_path, plan, row = _plan_row(root, args, schema)
    message = _read(args.envelope_file, "--envelope-file")
    tags = TAG_RE.findall(message)
    envelope = parse_result_block(message)
    if not tags or tags[-1].strip() != "DONE" or envelope is None:
        raise CliError("--envelope-file", "the row check judges DONE envelopes only",
                       "handle RETRY/BLOCKED in Step 3g before calling check")
    results = _read_results(args.check_results)
    base = _frontmatter_value(_read(str(root / args.tracker), "--tracker"), "base_commit")

    rec_path = (root / ".ramo" / "todo" / f"{plan_path.stem}-evidence" / f"row-{args.row:02d}.json")
    prior = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else None
    if args.stage == "verify" and prior:
        # A fix envelope declares the keys its fix changed; every other key keeps its recorded
        # value, so a fix that touched one key is not failed for the keys it left alone.
        fixed = envelope.get("evidence") if isinstance(envelope.get("evidence"), dict) else {}
        envelope = dict(envelope, evidence={**prior.get("evidence", {}), **fixed})
    row_check = check_row(root, plan, row, envelope, results, schema)
    artifacts, lines = row_check.pop("_artifacts"), row_check.pop("_lines")

    wall = _seconds_between(args.started, args.finished)
    minutes = (plan["validity"] or {}).get("wall_minutes") if row["type"] == "model-training" else None
    expected = minutes * 60 if minutes else None
    factor = schema["limits"]["run_over_budget_factor"]
    history = list((prior or {}).get("prior_verdicts", []))
    if prior:
        history.append({"attempt": prior.get("attempt"), "verdict": prior["row_check"]["verdict"],
                        "written_by": prior.get("written_by"), "finished_at": prior.get("finished_at")})
    evidence = envelope.get("evidence") if isinstance(envelope.get("evidence"), dict) else {}
    record = {
        "record": schema["state_records"]["row_evidence"]["record"],
        "plan": args.plan, "tracker": args.tracker, "base_commit": base,
        "row": row["id"], "cp": row["cp"], "unit": row["unit"], "domain": row["domain"],
        "type": row["type"], "binding": row["binding"], "agent": args.agent,
        "attempt": args.attempt,
        "written_by": "ramo-run" if args.stage == "run" else f"ramo-verify:round{args.round or args.attempt}",
        "prior_verdicts": history, "status": "DONE",
        "started_at": args.started, "finished_at": args.finished, "wall_seconds": wall,
        "expected_wall_seconds": expected,
        "over_budget": bool(wall is not None and expected and wall > factor * expected),
        "evidence": evidence, "artifacts": artifacts,
        "changed_files_reported": list(envelope.get("changed_files") or []),
        "changed_files_git": changed_files_git(root, base),
        "concerns": list(envelope.get("concerns") or []),
        "row_check": row_check,
    }
    write_record(rec_path, record)

    if args.print == "json":
        print(json.dumps(record, ensure_ascii=False, indent=1))
    else:
        passed = lambda items: f"{sum(1 for i in items if i['pass'])}/{len(items)}"  # noqa: E731
        print(f"행 {row['id']} 수용 검사: {row_check['verdict']} (검사 {passed(row_check['checks'])}, "
              f"증거 {passed(row_check['evidence'])}, 산출물 {passed(row_check['deliverables'])}) "
              f"기록: {rec_path.relative_to(root)}")
        for line in lines:
            print(line)
    return 0 if row_check["verdict"] == "PASS" else 1


def tracker_status(text: str, row: int) -> str | None:
    """The row's Status cell in the tracker table (`| # | Task | Domain | Type | Status | Retries |`)."""
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and ROW_ID.match(cells[0]) and int(ROW_ID.match(cells[0]).group(1)) == row:
            return cells[4]
    return None


def cmd_recheck(args, schema) -> int:
    """verify Gates 1-3 for one row against its record: state precedence, then check_row. Writes nothing."""
    root = _find_root()
    plan_path, plan, row = _plan_row(root, args, schema)
    status = tracker_status(_read(str(root / args.tracker), "--tracker"), args.row)
    rec_path = root / ".ramo" / "todo" / f"{plan_path.stem}-evidence" / f"row-{args.row:02d}.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else None
    passed = bool(rec) and rec["row_check"]["verdict"] == "PASS"
    reopened = bool(rec) and str(rec.get("written_by", "")).startswith("ramo-verify")
    if status == "done" and not passed and not reopened:
        print(f"row {args.row} | state | state inconsistent: tracker says done, no PASS record "
              f"(recover with /ramo:run --row {args.row})")
        return 3
    if status != "done" and passed:
        print(f"row {args.row} | state | state inconsistent: record ahead of tracker ({status})")
        return 3
    if status != "done":
        raise CliError("--row", f"row {args.row} is `{status}`, not done", "recheck done rows only")
    results = _read_results(args.check_results)
    recorded = {"evidence": rec.get("evidence", {}),
                "artifacts": [f"{a['path']} {a['sha256']}" for a in rec.get("artifacts", []) if a.get("sha256")]}
    row_check = check_row(root, plan, row, recorded, results, schema)
    lines = row_check.pop("_lines")
    print(f"row {args.row} recheck: {row_check['verdict']}")
    for line in lines:
        print(line)
    return 0 if row_check["verdict"] == "PASS" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="acceptance.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    fmt = argparse.RawDescriptionHelpFormatter
    results_help = ("JSON list of {cmd, exit, seconds, timed_out, stdout_file | stdout_sha256}; "
                    "required when the row's unit has a Checks line")

    p = sub.add_parser("parse", formatter_class=fmt, help="validate a plan's row mapping, Checks lines, and validity",
                       epilog="example: acceptance.py parse --plan .ramo/plans/2026-09-24-trip-duration.md")
    p.add_argument("--plan", required=True)
    p.add_argument("--json", action="store_true", help="print the parsed rows and validity as JSON")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("hash", formatter_class=fmt, help="compute query_hash or feature_spec",
                       epilog="example: acceptance.py hash --sql sql/trip_dataset.sql\n"
                              "example: acceptance.py hash --features experiments/trip-duration/features.txt")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--sql", nargs="+", help="SQL deliverables, in Deliverable order")
    group.add_argument("--features", help="the validity block's features file")
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser("check", formatter_class=fmt, help="judge a row after its envelope returns",
                       epilog="example: acceptance.py check --plan .ramo/plans/2026-09-24-trip-duration.md --row 1 "
                              "--envelope-file /tmp/s/env-1.md --check-results /tmp/s/checks-1.json "
                              "--tracker .ramo/todo/2026-09-24-trip-duration.md --agent ramo-data-implement "
                              "--attempt 1 --stage run")
    p.add_argument("--envelope-file", required=True, help="the returned body, saved to scratch")
    p.add_argument("--agent", required=True)
    p.add_argument("--attempt", required=True, type=int)
    p.add_argument("--stage", required=True, choices=("run", "verify"))
    p.add_argument("--round", type=int, help="verify Fix round number (stage verify)")
    p.add_argument("--started")
    p.add_argument("--finished")
    p.add_argument("--print", default="ko", choices=("ko", "json"))
    p.set_defaults(func=cmd_check)
    check_parser = p

    p = sub.add_parser("recheck", formatter_class=fmt, help="verify Gates 1-3 for one done row (writes nothing)",
                       epilog="example: acceptance.py recheck --plan .ramo/plans/2026-09-24-trip-duration.md --row 1 "
                              "--check-results /tmp/s/recheck-1.json --tracker .ramo/todo/2026-09-24-trip-duration.md\n"
                              "exit: 0 PASS, 1 FAIL, 2 usage, 3 state inconsistent (BLOCKED)")
    p.set_defaults(func=cmd_recheck)
    for p in (check_parser, p):
        p.add_argument("--plan", required=True, help="repository-relative plan path")
        p.add_argument("--row", required=True, type=int)
        p.add_argument("--check-results", help=results_help)
        p.add_argument("--tracker", required=True, help="repository-relative tracker path")

    args = parser.parse_args(argv)
    try:
        schema = load_schema()
        if args.command != "hash" and gate_disabled(schema):  # parse, check, recheck alike
            print("gate_disabled")
            return 0
        return args.func(args, schema)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # a harness crash must never read as a FAIL (exit 1)
        print(f"error: internal: {type(exc).__name__}: {exc} (fix: report it; the row was not judged)",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
