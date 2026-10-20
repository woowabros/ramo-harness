#!/usr/bin/env python3
# SubagentStop 핸들러: <ramo> 태그 폐집합 + result 필드 + verdict + 재현성 필드의 envelope 게이트
"""SubagentStop handler — the hook half of envelope enforcement (path 1 of 2;
the orchestrator's own parsing of the returned body is path 2).

Empirically verified by probe on Claude Code 2.1.x:
- SubagentStop fires and its stdin carries `agent_type` and
  `last_assistant_message` (the subagent's final output text)
- exit 2 feeds stderr back to the subagent, which continues and re-sends;
  the retry carries `stop_hook_active: true`

A later probe: the Agent() `name` argument arrives in the `agent_type`
field, and the payload carries no other key naming the agent (every
SubagentStop log record shares one identifying key; two live spawns of the
same subagent_type differing only in `name` split into roster-matched and
non_roster_agent). Judging roster membership on `agent_type` alone
therefore exempted every named spawn from the gates below, which is what
run-stage spawns hit. `resolve_roster` recovers the key from the name, and a
message that claims an envelope is judged even when recovery fails.

Loop guard: when `stop_hook_active` is true we never exit 2 again — one
mechanical retry via the hook, then the orchestrator path takes over.

Enforced for ramo roster agents (recovered by name when needed) and for any agent
whose message claims a <ramo> envelope; everything else passes through.
Reproducibility is required only on DONE (RETRY/BLOCKED are incomplete work).
Task type is self-declared as `task_type` inside the evidence mapping
(the orchestrator cross-checks it against the plan's task list).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    ENVELOPE_TAG,
    EVIDENCE_KEY_PATTERNS,
    EVIDENCE_TASK_TYPES,
    RESULT_REQUIRED_FIELDS,
    ROSTER,
    STATUS_VALUES,
    log_event,
    read_payload,
    run,
)

TAG_RE = re.compile(r"<%s>(.*?)</%s>" % (ENVELOPE_TAG, ENVELOPE_TAG), re.DOTALL)
RESULT_RE = re.compile(r"```result\s*\n(.*?)```", re.DOTALL)


def parse_scalar(value):
    value = value.strip()
    if value in ("[]", "{}"):
        return []
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    value = value.strip('"').strip("'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_result_block(message):
    """YAML-lite parser for the fenced result block (stdlib, tolerant)."""
    blocks = RESULT_RE.findall(message)
    if not blocks:
        return None
    data = {}
    current_key = None
    for raw in blocks[-1].splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip()
            value = value.strip()
            data[key] = parse_scalar(value) if value else None
            current_key = key
        elif current_key:
            if line.startswith("- "):
                if not isinstance(data.get(current_key), list):
                    data[current_key] = []
                data[current_key].append(parse_scalar(line[2:]))
            else:
                key2, sep, value2 = line.partition(":")
                if sep:
                    if not isinstance(data.get(current_key), dict):
                        data[current_key] = {}
                    data[current_key][key2.strip()] = parse_scalar(value2)
    return data


def check_evidence(result, violations):
    ev = result.get("evidence")
    if not isinstance(ev, dict):
        return False
    task_type = ev.get("task_type")
    if task_type not in EVIDENCE_TASK_TYPES:
        violations.append(
            "evidence.task_type must be one of %s (closed set owned by domains.<name>.evidence "
            "in .claude/schema/harness.json)"
            % "/".join(sorted(EVIDENCE_TASK_TYPES)))
        return True
    for key in EVIDENCE_TASK_TYPES[task_type]:
        if key not in ev or ev[key] in (None, ""):
            violations.append(
                "evidence.%s is required for %s (required_keys are declared by the owning "
                "domain in .claude/schema/harness.json)" % (key, task_type))
    if "seed" in ev and ev.get("seed") is not None and not isinstance(ev["seed"], int):
        violations.append("evidence.seed must be an integer")
    for key, pattern in EVIDENCE_KEY_PATTERNS.items():
        if ev.get(key) is not None and not re.fullmatch(pattern, str(ev[key])):
            violations.append("evidence.%s must match %s" % (key, pattern))
    return True


def resolve_roster(agent_type):
    """Recover the roster key when a spawn's `name` argument displaced `agent_type`.

    Longest match first, so `ramo-data-implement` is never read as a shorter roster key
    it happens to contain. Returns None when nothing in the roster is named.
    """
    if agent_type in ROSTER:
        return agent_type
    for key in sorted(ROSTER, key=len, reverse=True):
        if key in agent_type:
            return key
    return None


GATE_ENV = "RAMO_ENVELOPE_GATE_ENABLED"


def gate_disabled():
    """Session kill switch, mirroring pre_bash.py.

    workflow/08-hook-conventions.md requires one of every blocking gate, and this gate had
    none: it can deny a sub-agent's final message, and the only remedy available to a consumer
    repository meeting a false block was editing this file in place, which breaks `ramo verify`
    for every consumer. The switch name is single-sourced in schema/harness.json
    (`hooks.events.SubagentStop.kill_switch`); the constant above is a mirror of it, kept in
    step by hand.
    """
    return os.environ.get(GATE_ENV, "").strip().lower() == "false"


def main():
    payload = read_payload()
    if gate_disabled():
        log_event("SubagentStop", "pass", "gate_disabled", payload)
        return 0
    agent_type = payload.get("agent_type") or ""
    message = payload.get("last_assistant_message") or ""
    roster_key = resolve_roster(agent_type)
    if roster_key is None and not TAG_RE.search(message):
        # Genuinely foreign agent claiming nothing: no seat, no contract, no judgment.
        log_event("SubagentStop", "pass", "non_roster_agent", payload)
        return 0
    if roster_key is None:
        # Backstop: an unrecoverable name cannot buy an exemption from the contract it
        # invokes. The seat-specific rules (verdict vocabulary, write access) stay off
        # because the seat is unknown; the common contract still applies.
        access = verdict_values = verdict_required = None
    else:
        access, _bash_class, verdict_values, verdict_required = ROSTER[roster_key]
    violations = []

    tags = TAG_RE.findall(message)
    status = tags[-1].strip() if tags else None
    if status is None:
        violations.append("missing <%s>STATUS</%s> tag" % (ENVELOPE_TAG, ENVELOPE_TAG))
    elif status not in STATUS_VALUES:
        violations.append("status '%s' outside closed set %s" % (status, "/".join(STATUS_VALUES)))

    result = parse_result_block(message)
    if result is None:
        violations.append("missing ```result fenced block")
    else:
        for field in RESULT_REQUIRED_FIELDS:
            if field not in result:
                violations.append("result field missing: %s" % field)

        verdict = result.get("verdict")
        if roster_key is None:
            pass  # unknown seat: no verdict vocabulary is knowable for it
        elif verdict_values is None:
            if "verdict" in result:
                violations.append("agent '%s' must omit the verdict field" % roster_key)
        elif verdict_required == "always":
            if verdict not in verdict_values:
                violations.append("agent '%s' requires verdict in %s"
                                  % (roster_key, "/".join(verdict_values)))
        elif "verdict" in result and verdict not in verdict_values:
            violations.append("verdict '%s' outside %s" % (verdict, "/".join(verdict_values)))

        if access == "read-only" and result.get("changed_files") not in ([], None):
            violations.append("read-only agent must report changed_files: []")

        has_evidence = check_evidence(result, violations)
        if (status == "DONE" and roster_key is not None
                and roster_key.endswith("-implement") and not has_evidence
                and result.get("concerns") in ([], None)):
            violations.append(
                "implement agents must include an evidence mapping (with task_type) "
                "on DONE, or justify its absence in concerns")

    if not violations:
        log_event("SubagentStop", "pass", "", payload)
        return 0

    if payload.get("stop_hook_active"):
        # loop guard: one hook retry only; the orchestrator parsing path takes over
        log_event("SubagentStop", "pass", "loop_guard_violations_remain", payload,
                  extra={"violation_count": len(violations)})
        return 0

    log_event("SubagentStop", "block", "envelope_violation", payload,
              extra={"violation_count": len(violations)})
    print(
        "BLOCKED by ramo envelope gate — fix and re-send your FINAL message:\n- "
        + "\n- ".join(violations)
        + "\nContract: end with <ramo>DONE|RETRY|BLOCKED</ramo> plus a ```result block "
          "(fields: %s)." % ", ".join(RESULT_REQUIRED_FIELDS),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    run("subagent_stop", main)
