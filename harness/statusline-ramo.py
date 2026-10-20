#!/usr/bin/env python3
# 세션의 모델·이펏·컨텍스트·사용량 한도·비용과 지금 활성인 ramo 계획을 4줄로 그리는 statusline
"""Statusline renderer for a ramo-seeded repository.

Claude Code runs the command in `settings.json` `statusLine` and pipes the session
state to it as JSON on stdin; whatever the command prints becomes the panel.

Two properties this file must never lose:

- **stdlib only.** The same reason the hook handlers take no dependency
  (rules/workflow/08-hook-conventions.md): this runs in a consumer repository with no
  guaranteed virtualenv. A statusline that installs `jq` project-locally and prepends it
  to PATH to render itself carries a whole apparatus that is unnecessary here.
- **Invoked through its own shebang.** `lib/seed.sh` copies with `cp -p`, so the mode
  survives seeding, and `ramo init` cannot complete without python3 (its preflight blocks
  that), so the interpreter is always present in a seeded repository.
- **Never raise, never block.** Any failure prints nothing and exits 0. Observed in
  testing: a shell statusline rendered against a fixture payload wrote
  `/dev/tty: Device not configured` and a base-conversion error straight into the
  panel. A statusline that reports its own breakage is worse than one that stays quiet.
"""
import json
import os
import pathlib
import sys

RESET = "\033[0m"
BOLD = "\033[1m"

# Catppuccin, 24-bit. Kept as literals rather than a palette dict: every one of them is
# referenced exactly once or twice, and naming them by role reads better at the call site.
TEAL = (148, 226, 213)
YELLOW = (249, 226, 175)
OVERLAY = (108, 112, 134)
SUBTEXT = (166, 173, 200)

NO_COLOR = bool(os.environ.get("NO_COLOR"))


def paint(text, rgb, bold=False):
    if NO_COLOR:
        return text
    return "%s\033[38;2;%d;%d;%dm%s%s" % (BOLD if bold else "", rgb[0], rgb[1], rgb[2],
                                          text, RESET)


def _lerp(start, end, t):
    """t in [0, 1] along the segment start -> end, per channel."""
    return tuple(int(s + (e - s) * t) for s, e in zip(start, end))


def _ramp(pct, stops):
    """Piecewise-linear colour ramp. `stops` is [(upper_pct, from_rgb, to_rgb), ...];
    the last stop's colour is held for everything above it."""
    pct = max(0, min(100, pct))
    low = 0
    for upper, frm, to in stops:
        if pct < upper:
            span = upper - low
            return _lerp(frm, to, (pct - low) / span if span else 0.0)
        low = upper
    return stops[-1][2]


# Context deepens into red as it fills: Mocha Maroon -> Latte Maroon -> Latte Red, held.
CONTEXT_STOPS = [(40, (235, 160, 172), (230, 69, 83)),
                 (80, (230, 69, 83), (210, 15, 57))]
# The two rate limits keep their own hues so a glance tells them apart from context.
FIVE_HOUR_STOPS = [(40, (180, 190, 254), (114, 135, 253)),
                   (80, (114, 135, 253), (30, 102, 245)),
                   (100, (30, 102, 245), (210, 15, 57))]
SEVEN_DAY_STOPS = [(40, (249, 226, 175), (223, 142, 29)),
                   (80, (223, 142, 29), (64, 160, 43)),
                   (100, (64, 160, 43), (210, 15, 57))]

BAR_WIDTH = 10


def bar(pct, stops, width=BAR_WIDTH):
    """Each filled block carries the colour of its own position, so the bar itself is
    the gradient rather than a single-colour meter."""
    pct = max(0, min(100, pct))
    filled = int(round(pct / 100 * width))
    out = []
    for i in range(width):
        if i < filled:
            block_pct = (i + 1) / width * 100
            out.append(paint("█", _ramp(block_pct, stops)))
        else:
            out.append(paint("░", OVERLAY))
    return "".join(out)


def sep():
    return paint("│", OVERLAY)


def project_root(payload):
    root = os.environ.get("CLAUDE_PROJECT_DIR") or \
        (payload.get("workspace") or {}).get("current_dir") or "."
    # resolve() so a relative fallback still yields a directory name to show
    try:
        return pathlib.Path(root).resolve()
    except OSError:
        return pathlib.Path(root)


def harness_version(root):
    """`harness/VERSION` first, then the seeded record.

    A consumer repository has only `.seed-info`, written by lib/seed.sh at init. The
    harness's own repository has both, and its `.seed-info` is stale by construction: its
    `.claude/` tree is kept in step with `harness/` by copy, not by re-running
    `ramo init`, so the recorded version stops tracking the payload.
    """
    for candidate in (root/"harness"/"VERSION",):
        try:
            return candidate.read_text().strip()
        except OSError:
            pass
    try:
        for line in (root/".claude"/"hooks"/"ramo"/".seed-info").read_text().splitlines():
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def active_plan(root):
    """The `status: active` plan in .ramo/plans/, by frontmatter.

    Never by mtime: `git checkout`, opening a file, or an editor autosave all move mtime
    without changing state (rules/common/state-discipline.md). Frontmatter is the state.
    """
    plans = root/".ramo"/"plans"
    try:
        candidates = sorted(plans.glob("*.md"))
    except OSError:
        return None
    for path in candidates:
        try:
            head = path.read_text(errors="ignore").split("---")[1]
        except (OSError, IndexError):
            continue
        for line in head.splitlines():
            if line.strip() == "status: active":
                return path.stem
    return None


def duration(ms):
    seconds = int(ms) // 1000
    if seconds < 60:
        return "%ds" % seconds
    if seconds < 3600:
        return "%dm" % (seconds // 60)
    return "%dh%02dm" % (seconds // 3600, seconds % 3600 // 60)


def render(payload):
    root = project_root(payload)
    lines = []

    # --- line 1: identity and where we are in the pipeline
    head = []
    version = harness_version(root)
    head.append(paint("ramo " + version if version else "ramo", SUBTEXT))
    head.append("📁 " + paint(root.name or str(root), TEAL))
    worktree = (payload.get("worktree") or {}).get("name")
    if worktree and worktree != root.name:
        head.append(paint("⑂ " + worktree, SUBTEXT))
    plan = active_plan(root)
    if plan:
        head.append(paint("▶ " + plan, YELLOW))
    lines.append((" %s " % sep()).join(head))

    # --- line 2: context, cost, elapsed
    ctx = payload.get("context_window") or {}
    pct = ctx.get("used_percentage")
    second = []
    if isinstance(pct, (int, float)):
        pct = int(round(pct))
        second.append("%s %s" % (bar(pct, CONTEXT_STOPS),
                                 paint("%d%%" % pct, _ramp(pct, CONTEXT_STOPS), bold=True)))
    cost = (payload.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)) and cost > 0:
        second.append(paint("$%.2f" % cost, SUBTEXT))
    elapsed = (payload.get("cost") or {}).get("total_duration_ms")
    if isinstance(elapsed, (int, float)) and elapsed > 0:
        second.append(paint(duration(elapsed), SUBTEXT))
    if second:
        lines.append((" %s " % sep()).join(second))

    # --- line 3: rate limits
    limits = payload.get("rate_limits") or {}
    third = []
    for label, key, stops in (("5H", "five_hour", FIVE_HOUR_STOPS),
                              ("7D", "seven_day", SEVEN_DAY_STOPS)):
        used = (limits.get(key) or {}).get("used_percentage")
        if isinstance(used, (int, float)):
            used = int(round(used))
            third.append("%s %s" % (paint(label, OVERLAY),
                                    paint("%d%%" % used, _ramp(used, stops), bold=True)))
    if third:
        lines.append((" %s " % sep()).join(third))

    # --- line 4: model and effort
    model = (payload.get("model") or {}).get("display_name")
    if model:
        fourth = "⚡ " + paint(model, TEAL, bold=True)
        effort = payload.get("effortLevel")
        if effort:
            fourth += " " + paint("[%s]" % str(effort).upper(), YELLOW)
        lines.append(fourth)

    return "\n".join(lines)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0  # no payload is not a sparse payload: we were told nothing, so say nothing
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        out = render(payload)
    except Exception:
        return 0  # a statusline never reports its own breakage into the panel
    if out:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
