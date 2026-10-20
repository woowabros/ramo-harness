#!/usr/bin/env python3
# 훅 핸들러 공용 모듈: schema 미러 상수, key-name-only JSONL 로깅(0600), fail-open 래퍼
"""Shared constants and helpers for ramo hook handlers.

stdlib-only (python >= 3.9): this is the hook hot path.

CONSTANT MIRROR CONTRACT: the vocabulary below is mirrored from
.claude/schema/harness.json, which IS seeded (harness/MANIFEST carries it) and is readable at
runtime. The mirror exists for latency, not availability: these handlers run on every matching
tool call, and opening and parsing the schema on the hot path costs more than the duplication.
No shipped check compares the two, so keep them in step by hand: edit the schema first, then
this file.

The earlier version of this note claimed the schema is absent from seeded repositories. That was
false and it mattered: a false reason invites someone to fix the wrong thing, and SOT-4 forbids a
contract that asserts what is not so.

SQL_WRITE and the write-target parser below read the ORIGINAL command text. Their caller
`pre_bash.py` decides what "original" means for a heredoc first (`strip_heredoc_bodies`) and
blanks quoted literals only for its CLI-name and exec-flag tests (`strip_quoted_literals`), so
a write verb quoted in prose no longer satisfies the gate while `psql -c "DROP TABLE x"` still
does.

Log privacy: key names only. Never log payload values, output previews,
absolute paths, cwd, or transcript_path.
"""
import json
import os
import re
import sys
import time

_T0 = time.time()  # interpreter-side start; dispatch_lag_ms approximates handler wall time

# --- mirrored from .claude/schema/harness.json (envelope) ---
ENVELOPE_TAG = "ramo"
STATUS_VALUES = ("DONE", "RETRY", "BLOCKED")
RESULT_REQUIRED_FIELDS = (
    "summary", "artifacts", "changed_files", "concerns",
    "blockers", "retryable", "next_step_hint",
)
# Task type -> required evidence keys, flattened from domains.<name>.evidence plus
# envelope.evidence.fallback_task_type. Flattening is lossless because task types are unique
# across domains, and the handler is given only the self-declared task_type -- it cannot know
# the domain. Domain ownership is enforced at the schema layer and by the orchestrator's
# cross-check against the plan's Domain column, not here.
EVIDENCE_TASK_TYPES = {
    "data-extraction": ("data_snapshot", "query_hash"),
    "dataset-build": ("data_snapshot", "query_hash", "dataset_tables",
                      "quality_checks", "row_reconciliation"),
    "data-analysis": ("data_snapshot", "query_hash", "findings_ref"),
    "model-training": ("seed", "split_boundary", "data_snapshot", "feature_spec"),
    "code-change": ("test_command", "red_evidence", "coverage_line"),
    "other": (),
}
# Evidence keys whose value must match a pattern (envelope.evidence.key_formats).
EVIDENCE_KEY_PATTERNS = {
    "query_hash": r"^[0-9a-f]{16,64}$",
    "feature_spec": r"^[0-9a-f]{16,64}$",
    "dataset_tables": r"^.*:(intermediate|experiment).*$",
    "quality_checks": r"^[0-9]+/[0-9]+\b.*$",
    "row_reconciliation": r"^[0-9][0-9,]*\s*==\s*[0-9][0-9,]*$",
}

# --- mirrored from .claude/schema/harness.json (agents.roster) ---
# name -> (access, bash_class, verdict_values or None, verdict_required)
# verdict_required: "always" | "only-as-plan-reviewer" | None (must omit)
ROSTER = {
    "ramo-plan-writer":     ("write-partial", "B", None, None),
    "ramo-plan-evaluator":  ("read-only", "A", ("APPROVE", "REJECT"), "always"),
    "ramo-plan-improver":   ("write-partial", "B", None, None),
    "ramo-critique":        ("read-only", "A", ("APPROVE", "REJECT"), "always"),
    "ramo-audit":           ("read-only", "A", ("APPROVE", "REJECT"), "always"),
    "ramo-explore":         ("read-only", "B", None, None),
    "ramo-data-explore":    ("read-only", "B", None, None),
    "ramo-model-explore":   ("read-only", "B", None, None),
    "ramo-doc-writer":      ("write-partial", "C", None, None),
    "ramo-data-design":     ("read-only", "B", ("APPROVE", "REJECT"), "only-as-plan-reviewer"),
    "ramo-data-implement":  ("write", "C", None, None),
    "ramo-data-verify":     ("read-only", "B", ("PASS", "FAIL"), "always"),
    "ramo-model-design":    ("read-only", "A", ("APPROVE", "REJECT"), "only-as-plan-reviewer"),
    "ramo-model-implement": ("write", "C", None, None),
    "ramo-model-verify":    ("read-only", "B", ("PASS", "FAIL"), "always"),
    "ramo-wiki-writer":     ("read-only", "A", None, None),
    "ramo-wiki-reviewer":   ("read-only", "A", ("APPROVE", "REJECT"), "always"),
    "ramo-wiki-reader":     ("read-only", "A", None, None),
    "ramo-research-reader": ("read-only", "A", None, None),
}

# --- mirrored from .claude/schema/harness.json (limits) ---
FILE_SIZE_SPLIT_LINES = 800

# --- mirrored from .claude/schema/harness.json (data) ---
# Warehouse writes are confined to one workspace schema. Matched on the schema segment, not
# the catalog: an engine can expose the same schema under more than one catalog (an attached
# database file, a warehouse catalog), and the read path and the write path need not resolve
# the same one. This is the default; a project's ramo-data.json overrides it (workspace_schema()).
WORKSPACE_SCHEMA = "workspace"
DATA_CONFIG_NAME = "ramo-data.json"

# One verb source for both write regexes below. They used to be two hand-maintained keyword
# lists and had already drifted: SQL_WRITE matched none of `CREATE OR REPLACE TABLE`,
# `CREATE OR REPLACE VIEW`, or `INSERT OVERWRITE` -- the three forms this project's own
# dataset step actually uses -- so pre_bash's workspace-confinement gate never fired for a
# CTAS and was masked only by the separate raw-SQL-CLI block.
_WRITE_VERB = (
    r"create\s+(?:or\s+replace\s+)?(?:table|schema|view)(?:\s+if\s+not\s+exists)?"
    r"|drop\s+(?:table|schema|view)(?:\s+if\s+exists)?"
    r"|truncate\s+table"
    r"|insert\s+(?:into|overwrite(?:\s+table)?)"
    r"|delete\s+from"
    r"|alter\s+table"
    r"|update(?=\s+[\w.\"`]+\s+set\b)"
)

# Verb only: "does this text contain a write at all". pre_bash uses it as the first of three
# conditions before denying a command.
SQL_WRITE = re.compile(r"\b(?:%s)" % _WRITE_VERB, re.IGNORECASE)

# Verb plus the target identifier: "which schema does the write land in".
_WRITE_TARGET = re.compile(r"\b(?:%s)\s+([A-Za-z_\"`][\w.\"`]*)" % _WRITE_VERB, re.IGNORECASE)


def sql_write_targets(text):
    """Schema segment of every write target in `text`; "" when the name is unqualified.

    An unqualified name resolves against whatever catalog/schema the session happens to
    carry, so it is never evidence that the write lands in the workspace.

    Two callers with deliberately different strictness read this:

    * post_write.py warns and has no gate to bypass, so it calls this directly and accepts
      recall over precision. Its `if target` filter is what keeps an unqualified name -- the
      shape a keyword quoted in prose produces -- from ever becoming a warning.
    * pre_bash.py denies, so it requires SQL_WRITE plus a CLI name or an exec flag first.
      Precision matters more when the consequence is a block.

    The asymmetry is the point, not an accident; both now share `_WRITE_VERB`, so they can
    no longer disagree about what counts as a write.
    """
    targets = []
    for match in _WRITE_TARGET.finditer(text):
        ident = match.group(1).replace('"', "").replace("`", "")
        # A trailing dot means the name was cut short by something the identifier class does
        # not accept -- in practice a placeholder such as `analytics.workspace.<name>`. Read it
        # as a name whose last segment is unknown, not as a shorter name: dropping the empty
        # tail slid the catalog into the schema position and reported a workspace write as a
        # write to `analytics`.
        truncated = ident.endswith(".")
        parts = [part for part in ident.split(".") if part]
        if truncated:
            parts.append("")
        if len(parts) >= 3:
            targets.append(parts[-2])
        elif len(parts) == 2:
            targets.append(parts[0])
        else:
            targets.append("")
    return targets


def workspace_schema():
    """The workspace schema the write-confinement judgment compares against.

    A project's `ramo-data.json` (project root) may name its own `workspace_schema`, the same
    key the data access adapter reads, so the hook and the adapter agree on one value. With no
    file, an unreadable one, or no usable key, the mirrored schema default applies. Callers
    reach this only once a SQL write is being judged, so no other command pays for the read.
    """
    try:
        with open(os.path.join(project_dir(), DATA_CONFIG_NAME), encoding="utf-8") as fh:
            value = json.load(fh).get("workspace_schema")
    except (OSError, ValueError, AttributeError):
        return WORKSPACE_SCHEMA
    return value if isinstance(value, str) and value else WORKSPACE_SCHEMA


def sql_writes_confined_to_workspace(text):
    """True only when at least one write target parsed and all of them name the workspace."""
    targets = sql_write_targets(text)
    if not targets:
        return False
    workspace = workspace_schema()
    return all(target == workspace for target in targets)


def project_dir():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def read_payload():
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def _open_0600(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    return os.fdopen(fd, "a")


HOOK_LOG_VERBOSE_ENV = "RAMO_HOOK_LOG_VERBOSE"


def _verbose_logging_enabled():
    return os.environ.get(HOOK_LOG_VERBOSE_ENV, "").strip().lower() == "true"


def log_event(event, decision, reason_code="", payload=None, extra=None, verbose_extra=None):
    """Append a key-name-only record to .ramo/logs/hooks-YYYYMMDD.jsonl.

    `verbose_extra` is the ONE opt-in exception to key-names-only (08-hook-conventions.md
    Logging Contract): a caller may pass values that only land in the log when the session
    has explicitly set RAMO_HOOK_LOG_VERBOSE=true. Default off preserves the existing
    privacy stance; the opt-in exists because key-names-only makes a blocked command's own
    text unrecoverable after the fact, a known audit limitation.
    """
    try:
        log_dir = os.environ.get("RAMO_LOG_DIR") or os.path.join(project_dir(), ".ramo", "logs")
        os.makedirs(log_dir, exist_ok=True)
        rec = {
            "ts": round(time.time(), 3),
            "event": event,
            "decision": decision,           # pass | block | warn | error
            "reason_code": reason_code,     # short machine code, never a value
            "dispatch_lag_ms": round((time.time() - _T0) * 1000, 1),
        }
        if payload is not None:
            rec["keys"] = sorted(payload.keys())
            if payload.get("agent_type"):
                rec["agent_type"] = payload["agent_type"]
            if payload.get("tool_name"):
                rec["tool_name"] = payload["tool_name"]
        if extra:
            rec.update(extra)
        if verbose_extra and _verbose_logging_enabled():
            rec["verbose"] = verbose_extra
        path = os.path.join(log_dir, "hooks-%s.jsonl" % time.strftime("%Y%m%d"))
        with _open_0600(path) as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass  # logging must never break the hook


def record_handler_error(handler_name, exc):
    """Make hook deaths visible: session_start surfaces this file next session."""
    try:
        log_dir = os.environ.get("RAMO_LOG_DIR") or os.path.join(project_dir(), ".ramo", "logs")
        os.makedirs(log_dir, exist_ok=True)
        with _open_0600(os.path.join(log_dir, "hook-errors.log")) as f:
            f.write("%s %s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"),
                                    handler_name, type(exc).__name__))
    except OSError:
        pass


def run(handler_name, main):
    """Fail-open wrapper: exit 0/2 are contract, anything else must not block."""
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - deliberate fail-open boundary
        record_handler_error(handler_name, exc)
        log_event(handler_name, "error", type(exc).__name__)
        sys.exit(1)


def parse_frontmatter_simple(text):
    """Minimal 'key: value' frontmatter reader (stdlib; no nested structures)."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm
