#!/usr/bin/env python3
# SessionStart 핸들러: .ramo/plans 의 active 계획 요약 주입(재개 1차 경로) + 훅 사망 가시화
"""SessionStart handler.

stdout on exit 0 is added to the session context (documented behavior), which
makes this the primary resume path: surface the active plan so a fresh session
can pick up where the last one stopped. The secondary path is each workflow
skill's Step 0 reading .ramo/plans directly (works even if this hook is dead).

Also surfaces recent handler crashes (hook-errors.log) so a dead gate is seen,
not silently absent (no gate goes on a hook that has no path for reporting its own death).
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import log_event, parse_frontmatter_simple, project_dir, read_payload, run


def main():
    payload = read_payload()
    root = project_dir()
    ramo_dir = os.path.join(root, ".ramo")
    if not os.path.isdir(ramo_dir):
        log_event("SessionStart", "pass", "no_ramo_dir", payload)
        return 0

    lines = []

    error_log = os.path.join(ramo_dir, "logs", "hook-errors.log")
    if os.path.isfile(error_log):
        with open(error_log, encoding="utf-8") as f:
            errors = f.read().splitlines()
        if errors:
            lines.append(
                "[ramo] WARNING: %d hook handler error(s) recorded since last cleanup "
                "(last: %s). Gates may not have been enforced; see .ramo/logs/hook-errors.log"
                % (len(errors), errors[-1])
            )

    active = []
    for path in sorted(glob.glob(os.path.join(ramo_dir, "plans", "*.md"))):
        with open(path, encoding="utf-8") as f:
            fm = parse_frontmatter_simple(f.read())
        if fm.get("status") == "active":
            active.append((path, fm))

    if active:
        lines.append("[ramo] Active plan(s) found — resume from here:")
        for path, fm in active:
            rel = os.path.relpath(path, root)
            lines.append(
                "- %s (ticket: %s, updated: %s)"
                % (rel, fm.get("ticket", "?"), fm.get("updated", "?"))
            )
        lines.append(
            "Read the plan body and its execution-structure table to continue; "
            "do not guess state from file mtimes."
        )
        log_event("SessionStart", "pass", "active_plan_injected", payload,
                  extra={"active_plans": len(active)})
    else:
        log_event("SessionStart", "pass", "no_active_plan", payload)

    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    run("session_start", main)
