#!/usr/bin/env python3
# PreToolUse(Bash) 핸들러: mtime 상태 추측 차단 + 위험 SQL 명령 차단 + 에이전트 위생 클래스 게이트
"""PreToolUse handler for Bash (blocking: exit 2 prevents the tool call).

Four gates, in order:
1. mtime-as-state guessing (`ls -t` family): state lives in .ramo frontmatter,
   never in file mtimes. Scoped: only commands that also name a `.ramo/` path
   block, per rules/common/state-discipline.md.
2. dangerous SQL commands (the mechanical slice of rules/data/warehouse-access.md):
   SQL CLIs used directly, and writes aimed outside the workspace schema.
   Warehouse SQL travels two sanctioned paths -- reads through the data access
   adapter (`.claude/scripts/ramo-data.py`), writes through a build script that
   writes into the workspace schema -- and neither needs a SQL CLI. The adapter
   call is a plain `python3` command that names no CLI and carries no exec flag,
   so it passes this gate even when its --sql text holds a write keyword: the
   adapter itself refuses anything but a single read (exit 3), and judging its
   statement here too would put a second, lexically weaker copy of that check in
   front of the sanctioned path. A build script's statement runs inside the
   script, where this hook cannot see it. So only the shell bypass is
   mechanically blockable here, and a CLI name counts only in COMMAND POSITION
   (honest-grade note).
3. merge-request creation (`glab mr create` or `gh pr create`) without a fresh
   verify PASS marker. Opening an MR is the one outward-facing action this
   pipeline takes. A marker a hook checks before the creation command is the most
   portable form of this gate; it keys on verification rather than lint because a
   DS change's claim is its result, not its formatting.
4. bash hygiene class per agent (empirically verified by probe: subagent tool
   calls carry `agent_type` in the PreToolUse payload):
   Class A = no Bash at all, Class B = plain commands only, Class C = pass.

Main-session calls (no agent_type) get gates 1-3 only. Gate 3 in particular is a
main-session gate by design: `ramo-mr` spawns nothing, so the MR command comes from
the session itself.

Why the MR path is Bash and not a non-shell tool call: this handler is registered
on PreToolUse(Bash) and returns 0 immediately for every other tool name, so a
merge-request call made through any other tool would be invisible to it. Routing
the one blocking-gated action through the shell is what makes the gate exist at all.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (ROSTER, SQL_WRITE, log_event, read_payload, run,
                     sql_writes_confined_to_workspace, workspace_schema)

MTIME_GUESS = re.compile(r"\bls\s+(-[A-Za-z]*t[A-Za-z]*)(\s|$)")
# The state rule scopes the mtime ban to workflow state, so the gate must too. Without this
# path condition the gate denied unrelated listings and any heredoc whose body merely quoted
# the rule's own counter-example (observed repeatedly while authoring review reports).
STATE_DIR = re.compile(r"\.ramo/")

# `glab mr create` (GitLab) or `gh pr create` (GitHub) in command position, with or without a
# leading path; vcs.provider picks which one the mr skill runs, and the gate covers both so a
# switched provider cannot slip past it. Deliberately narrow: it matches creation only, never
# `glab mr view/list/note` or `gh pr view/list/comment`, because reading an MR needs no gate.
MR_CREATE = re.compile(r"(^|[;&|]\s*)(\S*/)?(?:glab\s+mr|gh\s+pr)\s+create\b")
VERIFY_MARKER = ".ramo/context/verify-pass.json"

SQL_CLI_NAMES = frozenset({"trino", "presto", "psql", "mysql", "bq", "hive", "beeline",
                           "impala-shell", "duckdb"})
# A flag, a SQL heredoc, or `query` in SUBCOMMAND POSITION (`bq query ...`). `query` used to sit
# here as a bare word, so the plain English word matched: any command whose text mentioned a
# query satisfied this half of the gate, and once the write-verb half was widened to the CTAS
# forms, authoring a markdown rule about warehouse writes was denied by the gate that rule
# documents -- a gate wider than its own rule, which this repository has shipped before.
# Deleting the word outright
# was wrong too: `bq query` is a real subcommand and an existing test caught the loss. Requiring
# a CLI name in front keeps that invocation and drops the prose.
SQL_EXEC_FLAG = re.compile(
    r"(\s(-e|--execute|-c|--command|-q|--query)\b"
    r"|<<\s*SQL"
    # derived from SQL_CLI_NAMES, never re-listed: two hand-kept copies of the same name set
    # is the drift that left the write-verb regexes disagreeing for months
    r"|\b(?:%s)\s+query\b)" % "|".join(re.escape(n) for n in sorted(SQL_CLI_NAMES)),
    re.IGNORECASE)

# A CLI name is evidence of a SQL invocation only in COMMAND POSITION: the first word of the
# command, or of a segment after | ; & && ||. Matching the name anywhere in the string is what
# denied an inline python import of a client module whose package path ends in a CLI name, and
# any command whose PATH argument merely contains one -- several false positives in an audit
# of real commands, some observed live while authoring the harness's own rules, against no
# missed true positives.
_SEGMENT = re.compile(r"\|\||&&|[|;&\n]")
_COMMAND_PREFIX = re.compile(
    r"(?:[A-Za-z_][A-Za-z0-9_]*=\S*|sudo|env|command|nohup|time|exec)\s+")
_FIRST_WORD = re.compile(r"\S+")


def command_words(command):
    """The word in command position, for the command and each of its segments.

    Only a PATH-LIKE word is reduced to its basename, so `/opt/homebrew/bin/psql` still
    counts as an invocation. A word that merely contains a slash is left whole: reducing
    those turned quoted prose such as a `notes/psql` label into a fake invocation, and this
    gate blocked its own audit command that way.
    """
    words = []
    for segment in _SEGMENT.split(command):
        segment = segment.strip().lstrip("({ \t")
        while True:
            prefix = _COMMAND_PREFIX.match(segment)
            if not prefix:
                break
            segment = segment[prefix.end():]
        first = _FIRST_WORD.match(segment)
        if not first:
            continue
        word = first.group(0).strip("'\"")
        if word.startswith(("/", "./", "../", "~/")):
            word = os.path.basename(word)
        words.append(word)
    return words


def names_sql_cli(command):
    return any(word in SQL_CLI_NAMES for word in command_words(command))


def sql_cli_receives_a_pipe(command):
    """True when a SQL CLI sits in command position of a segment fed by a pipe.

    `echo 'select 1' | psql` carries no exec flag, so the flag test alone read it as harmless
    while it is a raw CLI execution with the statement arriving on stdin. Scoped to the pipe's
    receiving end on purpose: a CLI name appearing as an argument (`rg psql docs/ | head`)
    never reaches command position, so widening here does not widen the argument case.
    """
    segments = _SEGMENT.split(command)
    for segment in segments[1:]:
        words = command_words(segment)
        if words and words[0] in SQL_CLI_NAMES:
            return True
    return False


# Receivers of a heredoc body, by what the body IS once it arrives.
_SHELL_RECEIVERS = frozenset({"bash", "sh", "zsh", "ksh", "dash", "eval", "ssh"})
_FILE_RECEIVERS = frozenset({"cat", "tee"})
_HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredoc_bodies(command):
    """Rewrite heredoc bodies according to who receives them.

    Three branches, because a heredoc body is three different things depending on its
    receiver, and treating them alike is what produced this gate's worst failures in both
    directions:

    * A shell (`bash`, `sh`, `ssh`, `eval`) or a SQL CLI receives it, or the tag is `SQL`:
      the body IS the text that runs. Left exactly as it is, newlines included, so a line
      beginning with `psql --command` is still read as a command in command position.
    * An interpreter (anything else that is not a file sink) receives it: the body is a
      program, and a line inside it is not a shell command. The text is KEPT so a write verb
      or an exec flag in it is still scanned, but the newlines stop counting as command
      boundaries -- that boundary is what turned a body line beginning with a CLI name into
      a fake invocation.
    * `cat`/`tee` receives it: the body is going into a file. Dropped entirely. This is the
      class observed repeatedly -- writing a defect record, a dataset changelog, and the
      defect record ABOUT the first two -- where prose quoting a DDL keyword was denied as a
      warehouse write.

    Deleting every body was the obvious repair and it is wrong: it opens `bash <<EOF` with a
    real invocation inside.
    """
    lines = command.split("\n")
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        start = _HEREDOC_START.search(line)
        out.append(line)
        index += 1
        if not start:
            continue
        tag = start.group(2)
        body = []
        while index < len(lines) and lines[index].strip() != tag:
            body.append(lines[index])
            index += 1
        terminator = lines[index] if index < len(lines) else None
        index += 1 if terminator is not None else 0

        words = command_words(line)
        receiver = words[-1] if words else ""
        if tag.upper() == "SQL" or receiver in _SHELL_RECEIVERS or receiver in SQL_CLI_NAMES:
            out.extend(body)
        elif receiver in _FILE_RECEIVERS:
            pass  # a file sink: the body is a document, not a command
        else:
            out[-1] = out[-1] + " " + " ".join(body)
        if terminator is not None:
            out.append(terminator)
    return "\n".join(out)


_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def strip_quoted_literals(text):
    """Blank quoted literals, keeping the quotes' word boundary.

    Read only by the CLI-name and exec-flag tests. `SQL_WRITE` and the write-target parser
    read the original, so `psql -c "DROP TABLE x"` still blocks: the CLI name and the flag
    are outside the quotes and the write verb is inside them.

    Residual, and it is symmetric: a statement written entirely inside a quoted string is
    textually identical to prose quoting one, so `python3 -c "print('psql -c CREATE TABLE
    prod.x')"` still blocks (its `-c` is outside the quotes) and a shell-out hidden inside an
    interpreter string is not seen. The exits are `RAMO_BASH_GATE_ENABLED=false` and the Write
    tool, which this gate does not see.
    """
    return _QUOTED.sub(" ", text)

# "plain" for Class B. The token list below is a MIRROR of the allow-grammar SSOT in
# rules/workflow/12-subagent-bash-hygiene.md; no shipped check compares them, so edit both.
# Pipelines and &&/; chains OF PLAIN COMMANDS are explicitly allowed by the SSOT — the gate
# exists to stop tokens that Claude Code's permission engine refuses to auto-approve (shell
# expansion and control flow), which is what makes a background sub-agent hang. Preventing
# writes is NOT this gate's job; a read-only agent's tools/disallowedTools do that.
NOT_PLAIN = re.compile(r"(\$|`|<\(|>\(|<<|\b(?:for|while|until|do|done|cd)\b)")


GATE_ENV = "RAMO_BASH_GATE_ENABLED"


def gate_disabled():
    """Session kill switch (workflow/08-hook-conventions.md HARD: blocking gates need one).

    Integration-wiring regression: this gate denied legitimate Class-B commands because the rule
    and the implementation disagreed, and the only remedy was editing this file in place --
    which breaks `ramo verify` (the seeded file no longer matches the manifest) for every
    consumer repository.
    """
    return os.environ.get(GATE_ENV, "").strip().lower() == "false"


def block(payload, reason_code, message):
    """Deny, and put the way out on the same screen as the denial.

    A gate this precise still has a residual class it cannot decide (see
    `strip_quoted_literals`), and a person meeting one of those had to go find the switch in a
    rule file. Naming it in the message costs one line and turns a dead end into a decision.
    """
    command = (payload.get("tool_input") or {}).get("command", "")
    log_event("PreToolUse", "block", reason_code, payload, verbose_extra={"command": command})
    print("%s\nIf this is a false positive, set %s=false for the session (kill switch, "
          "rules/workflow/08-hook-conventions.md), or write the file with the Write tool — "
          "this gate reads Bash only." % (message, GATE_ENV), file=sys.stderr)
    return 2


def _verify_marker_problem():
    """Return a reason string when the verify-PASS marker cannot authorize an MR, else None.

    Presence and age only. Matching the marker against the current plan and commit needs the
    plan's state, which this handler is not given and must not guess -- that check belongs to
    skills/ramo-mr/SKILL.md, and this function's docstring says so rather than implying the
    gate is complete.
    """
    path = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), VERIFY_MARKER)
    if not os.path.isfile(path):
        return "no verify PASS marker at %s" % VERIFY_MARKER
    try:
        with open(path, encoding="utf-8") as fh:
            marker = json.load(fh)
    except (OSError, ValueError) as exc:
        return "verify PASS marker is unreadable (%s)" % type(exc).__name__
    if marker.get("verdict") != "PASS":
        return "the recorded verify verdict is %r, not PASS" % marker.get("verdict")
    try:
        age = time.time() - float(marker.get("at_epoch", 0))
    except (TypeError, ValueError):
        return "verify PASS marker carries no readable timestamp"
    if age > _marker_max_age():
        return "the verify PASS marker is %d seconds old (limit %d)" % (age, _marker_max_age())
    return None


def _marker_max_age():
    """Schema value, with the schema's own number as the only source (limits block)."""
    schema = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."),
                          ".claude", "schema", "harness.json")
    try:
        with open(schema, encoding="utf-8") as fh:
            return int(json.load(fh)["limits"]["mr_gate_marker_max_age_seconds"])
    except (OSError, ValueError, KeyError, TypeError):
        # Fail closed. An unreadable schema must not silently widen a blocking gate, and
        # returning a duplicated literal here would put the number in two places, which is the
        # thing the schema's limits block exists to prevent. Age 0 means every marker reads as
        # stale, so the gate denies and says why; RAMO_BASH_GATE_ENABLED=false is the exit.
        return 0


def main():
    payload = read_payload()
    if payload.get("tool_name") != "Bash":
        log_event("PreToolUse", "pass", "not_bash", payload)
        return 0
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    if gate_disabled():
        log_event("PreToolUse", "pass", "gate_disabled", payload)
        return 0

    if MTIME_GUESS.search(command) and STATE_DIR.search(command):
        return block(payload, "mtime_state_guess",
                     "BLOCKED by ramo pre_bash gate: `ls -t` infers state from mtimes. "
                     "mtime is not state (git checkout / editors change it) — "
                     "rules/common/state-discipline.md. Read workflow state from "
                     ".ramo/plans/*.md frontmatter (status: active) instead.")

    # `scan_text` is what a statement would actually be; `probe_text` is that with quoted
    # literals blanked, and only the CLI-name and exec-flag tests read it. The mtime, MR, and
    # hygiene gates below keep the original: Class B's `<<` verdict must not change.
    scan_text = strip_heredoc_bodies(command)
    probe_text = strip_quoted_literals(scan_text)

    if (SQL_WRITE.search(scan_text)
            and (names_sql_cli(probe_text) or SQL_EXEC_FLAG.search(probe_text))
            and not sql_writes_confined_to_workspace(scan_text)):
        workspace = workspace_schema()
        return block(payload, "sql_write_outside_workspace",
                     "BLOCKED by ramo pre_bash gate: this statement writes outside the '%s' "
                     "workspace schema (rules/data/warehouse-access.md). Source tables are "
                     "read-only; warehouse writes are confined to that one schema, from a "
                     "build script. Qualify the target as %s.<name>, or read through "
                     "`python3 .claude/scripts/ramo-data.py query` instead of writing."
                     % (workspace, workspace))

    if MR_CREATE.search(command):
        stale = _verify_marker_problem()
        if stale:
            return block(payload, "mr_without_verify_pass",
                         "BLOCKED by ramo pre_bash gate: %s. An MR is the one outward-facing "
                         "step of this pipeline, and it opens only after `ramo:verify` reached "
                         "PASS on this working tree (rules/workflow/06-create-mr.md 'When to "
                         "open'). Run /ramo:verify, or use `Skill(\"ramo-mr\")`, which performs "
                         "the full check. This gate reads only the marker's presence and age; "
                         "the skill also matches the plan and the commit." % stale)

    if names_sql_cli(probe_text) and (SQL_EXEC_FLAG.search(probe_text)
                                      or sql_cli_receives_a_pipe(probe_text)):
        return block(payload, "raw_sql_cli",
                     "BLOCKED by ramo pre_bash gate: SQL CLIs used directly bypass both "
                     "sanctioned paths (rules/data/warehouse-access.md). Read through the "
                     "data access adapter (`python3 .claude/scripts/ramo-data.py query --sql "
                     "\"...\"`); write from a build script into the workspace schema. The CLI "
                     "shortcut is the one bypass this gate can see, which is why it closes it.")

    agent_type = payload.get("agent_type")
    if agent_type in ROSTER:
        bash_class = ROSTER[agent_type][1]
        if bash_class == "A":
            return block(payload, "hygiene_class_a",
                         "BLOCKED by ramo pre_bash gate: agent '%s' is bash hygiene Class A "
                         "(no shell). Report findings in your envelope instead of running "
                         "commands (rules/workflow/12-subagent-bash-hygiene.md)." % agent_type)
        if bash_class == "B" and NOT_PLAIN.search(command):
            return block(payload, "hygiene_class_b_not_plain",
                         "BLOCKED by ramo pre_bash gate: agent '%s' is bash hygiene Class B "
                         "(plain commands only). Pipes and &&/; chains of plain commands are "
                         "fine; the denied tokens are $ ` <( >( << and the words "
                         "for/while/until/do/done/cd. Rewrite without them "
                         "(rules/workflow/12-subagent-bash-hygiene.md)." % agent_type)

    log_event("PreToolUse", "pass", "", payload)
    return 0


if __name__ == "__main__":
    run("pre_bash", main)
