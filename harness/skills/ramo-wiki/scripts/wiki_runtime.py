#!/usr/bin/env python3
# 위키 발행 트랜잭션 상태 머신: STAGING -> VALIDATING -> READY -> COMMITTING -> COMMITTED
"""Wiki publish transaction runtime.

stdlib-only (python >= 3.9), matching harness/rules/workflow/08-hook-conventions.md HARD 3 --
this script is seeded into every consumer repo and cannot assume a virtualenv.

State machine (NEEDS_REPAIR budget = 2 attempts):
  STAGING -> VALIDATING -> READY -> COMMITTING -> COMMITTED
  VALIDATING -> NEEDS_REPAIR -> VALIDATING     (attempt 1, attempt 2)
  VALIDATING -> NEEDS_REPAIR -> NEEDS_HUMAN    (attempt 3 would exceed budget)
  any state    -> ABORTED                      (a contract violation, not a budget end)

**Sealing happens at `stage`, not at `begin`.** `begin` opens the transaction and `--sources`
is optional there. Measured reason: an orchestrator that guesses the source set before the
draft exists guesses wrong, and the old order killed two legitimate drafts for citing a
committed file the caller had not listed. When `--sources` IS given, it stays a strict closed
set the draft may not leave (a caller who knows the set keeps the tighter gate); when omitted,
the draft's own cited paths become the sealed set at `stage`. Either way every cited path must
resolve to a committed file, which is the check that actually protects the wiki.

commit refuses without BOTH a PASS validation-report and an APPROVE review-record -- the
deterministic commit refusal condition -- and then applies a third gate an earlier version
taught us to add: the sources sealed at `stage` must still be byte-identical, or the reviewer
approved a document describing bytes that no longer exist (ATTESTATION_MISMATCH). Every path
into ABORTED or NEEDS_HUMAN records its cause in state.json and keeps the directory, because
an earlier version's aborts left no explanation behind. A REJECT verdict from record-review
does NOT write a review-record (mapping rule in foundation-transaction-lifecycle.md): it goes
straight to NEEDS_REPAIR, same budget as a validation failure.

**Budget exhaustion is NEEDS_HUMAN, not ABORTED.** Running out of repair attempts means the
loop cannot close the gap, which is a different fact from a contract violation: the draft is
usually most of a good document, and ABORTED discarded it. NEEDS_HUMAN keeps the draft and
prints its path with every rejection reason, so a person picks up from the last attempt
instead of from nothing.

Simplification from an earlier version (recorded, not silent): one target per transaction,
not a multi-file manifest. The "scope frozen after begin, no partial publish" invariant this
guards still holds trivially -- there is only ever the one target `begin` recorded.

Transaction state lives under .ramo/context/wiki-tx/<tx-id>/ -- context/ is one of the five
fixed .ramo/ directories (state-discipline.md; no new sixth directory), and it is exactly the
right kind of volatile: an in-flight transaction is working-session state, not durable evidence. The
directory is removed on COMMITTED, and kept on ABORTED so the recorded cause survives.
"""
from __future__ import annotations

import argparse
import glob as globmod
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPAIR_BUDGET = 2
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = SCRIPT_DIR.parent / "schemas"
SUBTYPES = ("lesson", "constraint", "note", "overview")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_REQUIRED = ("type", "title", "description", "category", "status",
                         "created", "updated", "tags")
STATUS_VALUES = ("draft", "stable", "deprecated")


class CliError(Exception):
    """Carries the three elements every user-facing error must have (a fix for an earlier
    version's bare error codes):
    which argument, why it is wrong, how to fix it."""

    def __init__(self, arg: str, why: str, fix: str):
        super().__init__(f"{arg}: {why} (fix: {fix})")


def cli_fail(arg: str, why: str, fix: str):
    raise CliError(arg, why, fix)


# --------------------------------------------------------------------- schema

def load_schema(subtype: str) -> dict:
    if subtype not in SUBTYPES:
        cli_fail("--subtype", f"got '{subtype}', must be one of {'|'.join(SUBTYPES)}",
                  f"use --subtype {SUBTYPES[0]}")
    path = SCHEMAS_DIR / f"{subtype}.json"
    if not path.is_file():
        cli_fail("--subtype", f"schema file not found: {path}",
                  "reinstall the harness payload (schemas/<subtype>.json is a MANIFEST entry)")
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------- frontmatter parsing

def parse_frontmatter_and_body(text: str, source_arg: str = "--body-file"):
    """Deliberately narrow YAML-subset parser (stdlib only, no PyYAML in a seeded asset).

    Understands exactly what wiki frontmatter needs: scalar `key: value` lines, block lists
    of scalars (`key:` then `  - item` lines), and block lists of small dicts (`sources:`
    then `  - resource: x` / `    id: y`). Anything else raises CliError naming the line.
    """
    if not text.startswith("---\n"):
        cli_fail(source_arg, "no frontmatter block (must start with '---')",
                  "add a '---' frontmatter block at the top of the file")
    end = text.find("\n---", 4)
    if end == -1:
        cli_fail(source_arg, "frontmatter block is not closed with a second '---'",
                  "close the frontmatter block with a line containing only '---'")
    raw_lines = text[4:end].split("\n")
    body = text[end + 4:].lstrip("\n")

    data: dict = {}
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not m:
            cli_fail(source_arg, f"unparsable frontmatter line: {line!r}",
                      "use 'key: value' or 'key:' followed by indented '- ' list items")
        key, inline = m.group(1), m.group(2).strip()
        if inline == "[]":
            data[key] = []
            i += 1
            continue
        if inline:
            data[key] = inline.strip('"')
            i += 1
            continue
        # block list follows
        items = []
        i += 1
        while i < len(raw_lines) and raw_lines[i].startswith("  - "):
            item_line = raw_lines[i][4:]
            dm = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", item_line)
            if dm:
                item = {dm.group(1): dm.group(2).strip().strip('"')}
                i += 1
                while i < len(raw_lines) and raw_lines[i].startswith("    "):
                    sm = re.match(r"^    ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw_lines[i])
                    if not sm:
                        break
                    item[sm.group(1)] = sm.group(2).strip().strip('"')
                    i += 1
                items.append(item)
            else:
                items.append(item_line.strip().strip('"'))
                i += 1
        data[key] = items
    return data, body


# ------------------------------------------------------------------- validation

def _resolve_source(root: Path, resource: str, tracked: set) -> bool:
    if any(ch in resource for ch in "*?["):
        hits = globmod.glob(str(root / resource), recursive=True)
        return any(Path(h).is_file() and str(Path(h).relative_to(root)) in tracked for h in hits)
    return resource in tracked


def _expand_source(root: Path, resource: str, tracked: set) -> list:
    """Every tracked file a declared source resolves to, sorted. A glob seals its whole
    current match set, so a file appearing later under the same pattern changes the seal --
    the evidence set did change, and the reviewer read the older one."""
    if any(ch in resource for ch in "*?["):
        hits = globmod.glob(str(root / resource), recursive=True)
        rels = [Path(h).relative_to(root).as_posix() for h in hits if Path(h).is_file()]
        return sorted(r for r in rels if r in tracked)
    return [resource] if resource in tracked else []


def seal_sources(root: Path, resources: list) -> dict:
    """Hash every file the declared sources resolve to, plus one aggregate over all of them.

    The working tree is hashed, not the index: the reviewer reads the working tree, so that is
    the byte set an attestation must pin. Returns
    {"files": {path: sha256}, "attestation": sha256, "unresolved": [...]}.
    """
    tracked = _git_ls_files(root)
    files, unresolved = {}, []
    for resource in resources:
        expanded = _expand_source(root, resource, tracked)
        if not expanded:
            unresolved.append(resource)
            continue
        for rel in expanded:
            files[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    canonical = json.dumps(sorted(files.items()), ensure_ascii=False, separators=(",", ":"))
    return {"files": files,
            "attestation": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "unresolved": unresolved}


def _git_ls_files(root: Path) -> set:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"],
                              capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return set(out.stdout.splitlines())


def validate_candidate(root: Path, subtype: str, candidate_path: Path,
                        declared_sources: list | None = None) -> dict:
    """Deterministic gate. Returns {"result": "PASS"} or {"result": "FAIL", "errors": [...]}.

    Every error is {"check", "message"} where message already carries which/why/how (the
    same 3-part discipline as CliError, since these reach a human via the same channel).
    """
    schema = load_schema(subtype)
    errors = []

    text = candidate_path.read_text(encoding="utf-8")
    try:
        fm, body = parse_frontmatter_and_body(text, "candidate")
    except CliError as exc:
        return {"result": "FAIL", "errors": [{"check": "frontmatter-parse", "message": str(exc)}]}

    for key in FRONTMATTER_REQUIRED:
        if not str(fm.get(key, "")).strip():
            errors.append({"check": "frontmatter-required",
                            "message": f"frontmatter is missing '{key}' "
                                       f"(fix: add '{key}: <value>' to the frontmatter block)"})

    if str(fm.get("category", "")).strip() != subtype:
        errors.append({"check": "category-matches-subtype",
                        "message": f"frontmatter category is '{fm.get('category')}', "
                                   f"must equal the transaction subtype '{subtype}' "
                                   f"(fix: set 'category: {subtype}')"})

    status = str(fm.get("status", "")).strip()
    if status and status not in STATUS_VALUES:
        errors.append({"check": "status-closed-set",
                        "message": f"status '{status}' is outside {STATUS_VALUES} "
                                   f"(fix: use one of {', '.join(STATUS_VALUES)})"})

    features = fm.get("document_features") or []
    if isinstance(features, list):
        unknown = [f for f in features if f not in schema["conditional_features"]]
        if unknown:
            errors.append({"check": "features-known",
                            "message": f"document_features {unknown} not declared for "
                                       f"subtype '{subtype}' "
                                       f"(fix: use one of {list(schema['conditional_features'])})"})
    else:
        features = []

    required_sections = list(schema["required_sections"])
    for feat in features:
        extra = schema["conditional_features"].get(feat, {}).get("extra_section")
        if extra:
            required_sections.append(extra)
    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    missing_sections = [s for s in required_sections if s not in headings]
    if missing_sections:
        errors.append({"check": "required-sections",
                        "message": f"missing section(s) {missing_sections} "
                                   f"(fix: add '## <section>' headings for each)"})

    sources = fm.get("sources") or []
    if not sources:
        errors.append({"check": "sources-present",
                        "message": "frontmatter has no 'sources' entries "
                                   "(fix: add at least one 'sources: [{resource: <path>}]')"})
    else:
        tracked = _git_ls_files(root)
        unresolved = []
        for src in sources:
            resource = src.get("resource", "") if isinstance(src, dict) else ""
            if not resource:
                errors.append({"check": "sources-shape",
                                "message": f"a sources entry has no 'resource' key: {src!r} "
                                           "(fix: 'sources: [{resource: <committed path or glob>}]')"})
                continue
            if not _resolve_source(root, resource, tracked):
                unresolved.append(resource)
        if unresolved:
            errors.append({"check": "sources-resolve",
                            "message": f"source(s) do not resolve to a committed file: "
                                       f"{unresolved} (fix: commit the file, or fix the path/glob "
                                       f"-- see foundation-dead-document-prevention.md)"})
        if declared_sources:
            cited = [src.get("resource", "") for src in sources if isinstance(src, dict)]
            outside = sorted({c for c in cited if c and c not in set(declared_sources)})
            if outside:
                errors.append({"check": "sources-closed-set",
                                "message": f"candidate cites source(s) outside the set sealed at "
                                           f"begin: {outside} (declared: {sorted(declared_sources)}) "
                                           f"(fix: cite only the declared sources, or abort and "
                                           f"begin a new transaction declaring the wider set)"})

    return {"result": "FAIL", "errors": errors} if errors else {"result": "PASS", "errors": []}


# -------------------------------------------------------------------- tx state

def _find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if out.returncode != 0:
        cli_fail("--root", "not inside a git work tree and --root was not given",
                  "run from inside the target repo, or pass --root <dir>")
    return Path(out.stdout.strip())


def _tx_dir(root: Path, tx_id: str) -> Path:
    return root / ".ramo" / "context" / "wiki-tx" / tx_id


def _load_state(root: Path, tx_id: str) -> dict:
    state_file = _tx_dir(root, tx_id) / "state.json"
    if not state_file.is_file():
        cli_fail("--tx", f"no such transaction: {tx_id}",
                  "run 'begin' first, or check the tx-id from its output")
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_state(root: Path, tx_id: str, state: dict):
    state_file = _tx_dir(root, tx_id) / "state.json"
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(state_file)


def _require_state(state: dict, *allowed: str):
    if state["state"] not in allowed:
        cli_fail("--tx", f"transaction is in state {state['state']}, expected one of {allowed}",
                  "check 'status --tx <tx-id>' for the current state and next valid action")


def _needs_human_state(root: Path, tx_id: str, state: dict, reason: str, failed_checks=None):
    """Budget exhausted: keep the draft and hand it to a person.

    Distinct from _abort_state on purpose. An abort means a contract was violated and the
    candidate must not exist; running out of repair rounds means the loop could not close the
    gap, and the draft at that point is usually most of a good document. The measured cost of
    conflating them was two drafts discarded after two rounds each, with nothing left to
    resume from.
    """
    state["state"] = "NEEDS_HUMAN"
    state["needs_human_reason"] = reason
    state["failed_checks"] = sorted(failed_checks) if failed_checks else []
    state["handed_over_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    _save_state(root, tx_id, state)
    candidate = _tx_dir(root, tx_id) / "candidate.md"
    print(f"NEEDS_HUMAN: repair budget of {REPAIR_BUDGET} exhausted ({reason})", file=sys.stderr)
    print(f"  draft kept at: {candidate}", file=sys.stderr)
    print(f"  state and every rejection reason: {_tx_dir(root, tx_id) / 'state.json'}",
          file=sys.stderr)
    print("  the draft is not discarded -- a person repairs it and re-runs 'stage', or "
          "aborts deliberately", file=sys.stderr)


def _abort_state(root: Path, tx_id: str, state: dict, reason: str, failed_checks=None):
    """Record WHY a transaction died and keep the directory.

    An earlier version wrote {"attempt":0,"status":"ABORTED"} and nothing else, so a
    post-hoc "why did this abort" was unanswerable from the record -- its own
    ATTESTATION_MISMATCH abort was known only because a later reviewer described it in prose.
    """
    state["state"] = "ABORTED"
    state["abort_reason"] = reason
    state["failed_checks"] = sorted(failed_checks) if failed_checks else []
    state["aborted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    _save_state(root, tx_id, state)


# ------------------------------------------------------------------------ CLI

def cmd_begin(args):
    root = _find_root(args.root)
    if args.subtype not in SUBTYPES:
        cli_fail("--subtype", f"got '{args.subtype}', must be one of {'|'.join(SUBTYPES)}",
                  f"use --subtype {SUBTYPES[0]}")
    if not SLUG_RE.match(args.slug):
        cli_fail("--slug", f"got '{args.slug}', must match {SLUG_RE.pattern}",
                  "use lowercase-kebab, e.g. --slug trip-distance-leakage")
    schema = load_schema(args.subtype)
    target = f"wiki/{schema['path_segment']}/{args.slug}.md"
    if (root / target).exists():
        cli_fail("--slug", f"target already exists: {target}",
                  "choose a different --slug (editing an existing wiki document "
                  "is not supported by this runtime)")

    # `--sources` is optional: sealing moved to `stage` (see the module docstring). When given
    # it stays a strict closed set the draft may not leave; when omitted the draft defines it.
    resources = [s.strip() for chunk in (args.sources or []) for s in chunk.split(",") if s.strip()]
    if resources:
        probe = seal_sources(root, resources)
        if probe["unresolved"]:
            cli_fail("--sources", f"source(s) do not resolve to a committed file: "
                                  f"{probe['unresolved']}",
                      "commit the file first, or fix the path/glob, or omit --sources entirely "
                      "and let the draft's own citations define the sealed set at stage")

    if args.dry_run:
        # A probe over --sources still reports what those paths resolve to: that is the whole
        # point of the flag. The real seal is taken at stage, over the draft's own citations.
        payload = {"accepted": True, "target": target, "subtype": args.subtype,
                    "declared_sources": resources or None, "sealed_at": "stage"}
        if resources:
            probe = seal_sources(root, resources)
            payload["sealed_files"] = sorted(probe["files"])
            payload["attestation"] = probe["attestation"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    tx_id = f"{args.slug}-{hashlib.sha256(f'{args.slug}{time.time()}'.encode()).hexdigest()[:8]}"
    tx_dir = _tx_dir(root, tx_id)
    tx_dir.mkdir(parents=True)
    state = {"tx_id": tx_id, "subtype": args.subtype, "slug": args.slug, "target": target,
              "state": "STAGING", "attempt": 0, "last_failed_check": None,
              "declared_sources": resources or None,
              "sources": None, "sealed_files": None,
              "sources_attestation_sha256": None, "sealed_at": None}
    _save_state(root, tx_id, state)
    print(tx_id)


def cmd_stage(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    _require_state(state, "STAGING", "NEEDS_REPAIR", "NEEDS_HUMAN")
    body_path = Path(args.body_file)
    if not body_path.is_file():
        cli_fail("--body-file", f"not found: {body_path}", "pass a path to the candidate markdown file")
    candidate = _tx_dir(root, args.tx) / "candidate.md"
    text = body_path.read_text(encoding="utf-8")
    candidate.write_text(text, encoding="utf-8")

    # Seal here, not at begin. The set is the draft's own cited paths, unioned with whatever
    # `begin` declared; a declared set additionally stays a closed set the draft may not leave
    # (checked by validate's sources-closed-set), so the union never widens that gate.
    cited = []
    try:
        fm, _ = parse_frontmatter_and_body(text, "--body-file")
        for src in (fm.get("sources") or []):
            if isinstance(src, dict) and src.get("resource"):
                cited.append(str(src["resource"]).strip())
    except CliError:
        pass  # a malformed candidate is validate's finding to report, not stage's to raise
    resources = sorted(set(cited) | set(state.get("declared_sources") or []))
    if not resources:
        cli_fail("--body-file", "the candidate cites no sources and begin declared none",
                  "add at least one 'sources: [{resource: <committed path>}]' entry to the "
                  "candidate's frontmatter -- the sealed set is what makes the claims checkable")
    # An unresolved citation is NOT a stage-level failure: validate's `sources-resolve` check
    # reports it alongside every other finding, and one list beats one error at a time. Stage
    # seals what resolves and records the rest so the report can name them.
    seal = seal_sources(root, resources)
    state["unresolved_sources"] = sorted(seal["unresolved"])
    state["sources"] = resources
    state["sealed_files"] = seal["files"]
    state["sources_attestation_sha256"] = seal["attestation"]
    state["sealed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    state["state"] = "VALIDATING"
    _save_state(root, args.tx, state)
    unresolved = f"; {len(seal['unresolved'])} cited path(s) unresolved" if seal["unresolved"] else ""
    # Echo the pairing so a batch mistake is visible now rather than at review. `validate` only
    # compares category to subtype, so two candidates of the same subtype can be swapped and
    # still pass every check; the candidate title is the one thing that differs. Falls back to
    # the file name when the draft carries no title.
    try:
        fm, _ = parse_frontmatter_and_body(text, "--body-file")
        title = str(fm.get("title") or "").strip() or body_path.name
    except CliError:
        title = body_path.name
    print(f"tx {args.tx} ({state.get('subtype', '?')}) <- candidate title: {title}")
    print(f"staged; sealed {len(seal['files'])} file(s){unresolved}; "
          f"run: python3 {Path(__file__).name} validate --tx {args.tx}")


def cmd_validate(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    _require_state(state, "VALIDATING")
    candidate = _tx_dir(root, args.tx) / "candidate.md"
    # The closed-set check reads what `begin` DECLARED, not what `stage` sealed: the sealed set
    # is the union (declared + the draft's own citations), so checking against it would make the
    # gate vacuous. A caller who declared nothing has no closed set to violate.
    report = validate_candidate(root, state["subtype"], candidate,
                                 state.get("declared_sources"))
    report_file = _tx_dir(root, args.tx) / "validation-report.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if report["result"] == "PASS":
        state["state"] = "READY"
        _save_state(root, args.tx, state)
        print("PASS")
        return

    failed_checks = sorted({e["check"] for e in report["errors"]})
    previously_failed = set(state["last_failed_check"] or [])
    escalate = previously_failed & set(failed_checks)
    state["last_failed_check"] = failed_checks
    state["attempt"] += 1
    if state["attempt"] > REPAIR_BUDGET:
        _needs_human_state(root, args.tx, state,
                            "validation still failing", failed_checks)
        for e in report["errors"]:
            print(f"  - {e['check']}: {e['message']}", file=sys.stderr)
        sys.exit(1)

    state["state"] = "NEEDS_REPAIR"
    _save_state(root, args.tx, state)
    print(f"FAIL (attempt {state['attempt']}/{REPAIR_BUDGET})", file=sys.stderr)
    for e in report["errors"]:
        print(f"  - {e['check']}: {e['message']}", file=sys.stderr)
    if escalate:
        print("ESCALATE: USER_DECISION_REQUIRED -- the same check(s) failed twice unchanged "
              "(" + ", ".join(sorted(escalate)) + "); "
              "a repair loop will not fix this, ask the user rather than retrying again", file=sys.stderr)
    sys.exit(1)


def cmd_record_review(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    if args.verdict == "APPROVE":
        _require_state(state, "READY")
        report_path = Path(args.report_file)
        if not report_path.is_file():
            cli_fail("--report-file", f"not found: {report_path}", "pass the reviewer's report file")
        record = {"verdict": "APPROVE", "report": report_path.read_text(encoding="utf-8")}
        (_tx_dir(root, args.tx) / "review-record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print("review-record written (APPROVE); transaction is commit-ready")
        return

    # REJECT: no review-record is written (mapping rule, foundation-transaction-lifecycle.md) -- straight to repair.
    _require_state(state, "READY", "VALIDATING")
    state["attempt"] += 1
    if state["attempt"] > REPAIR_BUDGET:
        _needs_human_state(root, args.tx, state,
                            "reviewer verdict still REJECT",
                            [args.reason] if getattr(args, "reason", None) else None)
        sys.exit(1)
    state["state"] = "NEEDS_REPAIR"
    _save_state(root, args.tx, state)
    print(f"REJECT (attempt {state['attempt']}/{REPAIR_BUDGET}); run 'stage' again with a repaired body")


WIKI_INDEX_MARKER_BEGIN = "<!-- AUTO-GENERATED by ramo-wiki wiki_runtime.py commit -- do not edit by hand -->"


def render_index(root: Path, pending: tuple | None = None) -> str:
    """Render the index text for the wiki as it will look, including a not-yet-written doc.

    Returned rather than written: commit renders the index BEFORE it swaps anything, so a
    candidate whose frontmatter cannot be parsed fails while the live wiki is still
    untouched. Writing the index after publishing the body -- the earlier shape -- left the
    body published with a stale index whenever this step raised.

    `pending` is (subtype, rel_path, frontmatter_dict) for the document being committed.

    A generated index inherits the language of what it catalogs (its rows are Korean
    deliverable summaries), not the language of the generator code -- same precedent as
    docs/index.md (harness/rules/common/language-settings.md).
    """
    rows = []
    for subtype in SUBTYPES:
        schema = load_schema(subtype)
        seg_dir = root / "wiki" / schema["path_segment"]
        entries = []
        if seg_dir.is_dir():
            for path in sorted(seg_dir.glob("*.md")):
                fm, _ = parse_frontmatter_and_body(path.read_text(encoding="utf-8"), str(path))
                entries.append((path.relative_to(root).as_posix(), fm))
        if pending and pending[0] == subtype:
            entries = [e for e in entries if e[0] != pending[1]] + [(pending[1], pending[2])]
        for rel, fm in sorted(entries):
            tags = fm.get("tags") or ""
            first_tag = str(tags).split(",")[0].strip() if tags else ""
            rows.append((subtype, rel, fm.get("title", ""), fm.get("description", ""),
                          first_tag, fm.get("status", ""), fm.get("updated", "")))
    # The 요약 column carries `description` alone. It used to carry the title as well, so every
    # row said the same thing twice and the column that was supposed to let a reader skip
    # opening the document told them nothing new. 주제 groups by the first tag, which is what
    # replaces the subject-folder split the wiki deliberately does not have (its folders are
    # by kind: a lesson is a recurring failure, a constraint is a rule to obey).
    lines = [WIKI_INDEX_MARKER_BEGIN, "", "# 위키 색인", "",
             "| 유형 | 주제 | 경로 | 제목 | 요약 | 상태 | 갱신일 |",
             "|---|---|---|---|---|---|---|"]
    for subtype, rel, title, description, first_tag, status, updated in sorted(
            rows, key=lambda r: (r[0], r[4], r[1])):
        lines.append(f"| {subtype} | {first_tag} | {rel} | {title} | {description} | "
                      f"{status} | {updated} |")
    if not rows:
        lines.append("| (없음) | | | | | | |")
    return "\n".join(lines) + "\n"


def cmd_commit(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    _require_state(state, "READY")
    tx_dir = _tx_dir(root, args.tx)

    report_file = tx_dir / "validation-report.json"
    review_file = tx_dir / "review-record.json"
    missing = []
    if not report_file.is_file() or json.loads(report_file.read_text())["result"] != "PASS":
        missing.append("a PASS validation-report (run 'validate --tx " + args.tx + "')")
    if not review_file.is_file() or json.loads(review_file.read_text())["verdict"] != "APPROVE":
        missing.append("an APPROVE review-record (run 'record-review --verdict APPROVE ...')")
    if missing:
        cli_fail("--tx", f"cannot commit: missing {'; '.join(missing)}",
                  "obtain both reports before committing")

    # Third gate: the sources the reviewer read must still be byte-identical. Two PASSing
    # reports say nothing about a source edited between review and publish, and that is a
    # real observed abort in an earlier version, not a hypothetical.
    if state.get("sources"):
        current = seal_sources(root, state["sources"])
        if current["attestation"] != state.get("sources_attestation_sha256"):
            sealed = state.get("sealed_files") or {}
            changed = sorted(p for p in set(sealed) | set(current["files"])
                              if sealed.get(p) != current["files"].get(p))
            _abort_state(root, args.tx, state, "ATTESTATION_MISMATCH",
                          ["sources-attestation"])
            state_path = _tx_dir(root, args.tx) / "state.json"
            print("ATTESTATION_MISMATCH: source(s) changed after begin, so the reviewer "
                  "approved a document describing different bytes: " + ", ".join(changed),
                  file=sys.stderr)
            print(f"transaction ABORTED; reason recorded in {state_path}. Re-run the whole "
                  f"transaction once the code has stopped moving.", file=sys.stderr)
            sys.exit(1)

    state["state"] = "COMMITTING"
    _save_state(root, args.tx, state)

    # Both files are rendered and staged before either is swapped, and preimages are kept so
    # a failure halfway through the swap restores the previous pair. The publish is two files
    # (the document and the index), so "one target per transaction" was never literally true
    # -- the index was simply outside the guarantee.
    target = root / state["target"]
    index = root / "wiki" / "index.md"
    candidate_text = (tx_dir / "candidate.md").read_text(encoding="utf-8")
    fm, _ = parse_frontmatter_and_body(candidate_text, "candidate")
    index_text = render_index(root, (state["subtype"], state["target"], fm))

    preimages = {p: p.read_bytes() for p in (target, index) if p.exists()}
    target.parent.mkdir(parents=True, exist_ok=True)
    index.parent.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for path, text in ((target, candidate_text), (index, index_text)):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            staged.append((tmp, path))
        for tmp, path in staged:
            tmp.replace(path)
    except OSError as exc:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)
        for path, blob in preimages.items():
            path.write_bytes(blob)
        for path in (target, index):
            if path not in preimages and path.exists():
                path.unlink()
        _abort_state(root, args.tx, state, f"publish swap failed and was rolled back: {exc}",
                      ["publish-swap"])
        print(f"commit failed and the wiki was restored to its previous state: {exc}",
              file=sys.stderr)
        sys.exit(1)

    state["state"] = "COMMITTED"
    _save_state(root, args.tx, state)
    import shutil
    shutil.rmtree(tx_dir, ignore_errors=True)
    print(state["target"])


def cmd_abort(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    if state["state"] == "COMMITTED":
        cli_fail("--tx", "transaction is already COMMITTED", "nothing to abort")
    if not args.reason:
        cli_fail("--reason", "required: an abort with no recorded reason is unauditable",
                  "pass --reason '<why this transaction is being discarded>'")
    _abort_state(root, args.tx, state, args.reason)
    print(f"aborted ({args.reason}); reason recorded in "
          f"{(_tx_dir(root, args.tx) / 'state.json')}")


def cmd_status(args):
    root = _find_root(args.root)
    state = _load_state(root, args.tx)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="wiki_runtime.py", description=__doc__.splitlines()[0])
    parser.add_argument("--root", help="target repo root (default: git rev-parse --show-toplevel)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("begin", help="open a transaction, sealing the evidence set (example: "
                                      "begin --subtype lesson --slug trip-distance-leakage "
                                      "--sources src/trip_duration/features.py,tests/test_features.py)")
    p.add_argument("--subtype", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--sources", action="append", metavar="PATH_OR_GLOB",
                    help="optional. Committed path or glob; repeatable or comma-separated. "
                         "When given it is a closed set the candidate may not leave. Sealing "
                         "itself happens at stage (from the draft's own citations, unioned "
                         "with this) and is re-checked at commit")
    p.add_argument("--dry-run", action="store_true",
                    help="report whether this target and source set would be accepted, "
                         "without opening a transaction")
    p.set_defaults(func=cmd_begin)

    p = sub.add_parser("stage", help="attach candidate body (example: stage --tx <tx-id> --body-file draft.md)")
    p.add_argument("--tx", required=True)
    p.add_argument("--body-file", required=True)
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("validate", help="run the deterministic gate (example: validate --tx <tx-id>)")
    p.add_argument("--tx", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("record-review", help="record the semantic review (example: record-review --tx <tx-id> --verdict APPROVE --report-file review.md)")
    p.add_argument("--tx", required=True)
    p.add_argument("--verdict", required=True, choices=["APPROVE", "REJECT"])
    p.add_argument("--report-file", required=False)
    p.set_defaults(func=cmd_record_review)

    p = sub.add_parser("commit", help="publish (example: commit --tx <tx-id>)")
    p.add_argument("--tx", required=True)
    p.set_defaults(func=cmd_commit)

    p = sub.add_parser("abort", help="discard a transaction (example: abort --tx <tx-id> --reason 'duplicate of X')")
    p.add_argument("--tx", required=True)
    p.add_argument("--reason", required=False)
    p.set_defaults(func=cmd_abort)

    p = sub.add_parser("status", help="print transaction state (example: status --tx <tx-id>)")
    p.add_argument("--tx", required=True)
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if args.command == "record-review" and args.verdict == "APPROVE" and not args.report_file:
        cli_fail("--report-file", "required when --verdict APPROVE", "pass the reviewer's report file")
    try:
        args.func(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
