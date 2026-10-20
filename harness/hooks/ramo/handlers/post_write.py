#!/usr/bin/env python3
# PostToolUse(Write|Edit) 핸들러: 파일 크기·python 문법 경고 (비차단, additionalContext 경유)
"""PostToolUse handler for Write|Edit (non-blocking by design).

Channel choice: warnings go out as hookSpecificOutput.additionalContext JSON
on exit 0, NOT as exit 2 stderr. Rationale: PostToolUse exit 2 cannot undo an
already-executed tool, and non-zero exits pollute the blocked=true metric with
non-gate noise (the failure mode an earlier lint-on-write hook showed).
additionalContext is the documented non-blocking feedback channel.

Checks:
- file over the split limit (mirrored FILE_SIZE_SPLIT_LINES, = verify's
  deterministic gate number) -> advise splitting now, not at verify time
- *.py syntax check via compile() (stdlib, no subprocess) -> surface typos early
- *.py / *.sql warehouse write aimed outside the workspace schema -> surface it at
  authoring time. This is DETECTION, not prevention: the statement executes from
  inside a script, where no gate can reach it, and a target with no schema
  qualifier is invisible here. The rule states that grade honestly.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (FILE_SIZE_SPLIT_LINES, log_event, read_payload, run,
                     sql_write_targets, workspace_schema)


def main():
    payload = read_payload()
    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    warnings = []

    if file_path and os.path.isfile(file_path):
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            content = None
        if content is not None:
            n_lines = content.count("\n") + 1
            if n_lines > FILE_SIZE_SPLIT_LINES:
                warnings.append(
                    "[ramo] %s is %d lines (> %d). Split it now; verify enforces this "
                    "as a deterministic gate later."
                    % (os.path.basename(file_path), n_lines, FILE_SIZE_SPLIT_LINES)
                )
            if file_path.endswith(".py"):
                try:
                    compile(content, file_path, "exec")
                except SyntaxError as exc:
                    warnings.append(
                        "[ramo] %s has a Python syntax error at line %s: %s"
                        % (os.path.basename(file_path), exc.lineno, exc.msg)
                    )
            if file_path.endswith((".py", ".sql")):
                targets = {target for target in sql_write_targets(content) if target}
                workspace = workspace_schema() if targets else ""
                stray = sorted(target for target in targets if target != workspace)
                if stray:
                    warnings.append(
                        "[ramo] %s aims a warehouse write at schema(s) %s. Writes are confined "
                        "to '%s'; source data is read-only "
                        "(.claude/rules/data/warehouse-access.md). Detection only -- the "
                        "statement runs inside the script, where no gate reaches it."
                        % (os.path.basename(file_path), ", ".join(stray), workspace)
                    )

    if warnings:
        log_event("PostToolUse", "warn", "size_syntax_or_write_target", payload,
                  extra={"warning_count": len(warnings)})
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(warnings),
            }
        }))
    else:
        log_event("PostToolUse", "pass", "", payload)
    return 0


if __name__ == "__main__":
    run("post_write", main)
