---
name: ramo-mr
description: "Open a merge request (GitHub pull request or GitLab merge request, per vcs.provider) for the code an experiment produced — preflight, verify-PASS gate, MR body assembled from the plan and the cycle's own outputs, single creation call. Zero Agent() spawns."
argument-hint: "[plan file under .ramo/plans/, or nothing to use the active plan]"
allowed-tools: Read, Grep, Glob, Bash, Write, AskUserQuestion
---

## Language Setting

MR body prose follows `RAMO_DOCUMENTATION_LANGUAGE` (default `ko`). Paths, symbols, commands,
branch names, and the ticket key stay English in both directions.

# Merge Request

Execution contract: `.claude/rules/common/skill-contract.md` (cited, not restated).
Conventions this skill implements: `.claude/rules/workflow/06-create-mr.md` (cited, not
restated — read it, do not paraphrase it here).

<role>
You open one merge request for the code of one completed cycle. You spawn nothing: assembling
an MR body is transcription from artifacts that already exist, not judgement, and the roster is
a closed set that a mechanical step has no claim on.

Responsible for: the preflight, the verify-PASS precondition, the body, and one creation call.
NOT responsible for: approving the experiment (`ramo:verify` did that), writing documentation
(`ramo:doc` did that), or responding to review comments once the MR is open (not built yet).
</role>

## What this skill will not do

- **[HARD] It never opens an MR whose experiment did not reach verify PASS**, and it never
  writes or edits the marker that records that.
  WHY: a marker this skill could write is a marker this skill could fabricate, and the whole
  value of the precondition is that a different stage established it. `ramo-verify` Step 8
  writes it on PASS and nothing else does. Enforced by `pre_bash.py::_verify_marker_problem`,
  whose caller denies `gh pr create` and `glab mr create` when the marker is absent, stale, or
  not PASS. That this skill never writes the marker is model discipline, checkable on review:
  no step below writes to that path.
- It never merges. Opening is this pipeline's last outward step; merging is a person's.
- It never force-pushes and never rewrites published history.

## Step 0: Preflight

Read `vcs.provider` from `.claude/schema/harness.json` first. It selects one column of the
provider table, and every later step uses only that column. A missing value or anything other
than `github` / `gitlab` → `<ramo>BLOCKED</ramo>`; never infer the provider from the remote URL.

| | GitHub (`github`) | GitLab (`gitlab`) |
|---|---|---|
| CLI and auth check | `gh auth status` | `glab auth status` |
| Create | `gh pr create --title "{title}" --body-file {body-file} --base {base} --head {branch}` | `glab mr create --title "{title}" --description-file {body-file} --target-branch {base} --source-branch {branch}` |
| Repository template | `.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/` | `.gitlab/merge_request_templates/` |
| Draft | `--draft` flag on the create command | title prefix `Draft: ` |

Then three checks, each with its own failure, none of them guessed.

1. **Provider CLI reachable and authenticated.** The table's auth check. Non-zero →
   `<ramo>BLOCKED</ramo>` naming which half failed (binary absent vs not logged in). The
   harness ships the command, never the binary or the credential: this is an environment
   precondition exactly like the warehouse one in `.claude/skills/ramo-run/SKILL.md` Step 2a,
   and the same rule applies — report it, do not work around it.
2. **Plan resolved.** Explicit argument, else the single `status: active` plan under
   `.ramo/plans/` read by frontmatter, never by mtime
   (`.claude/rules/common/state-discipline.md`). Zero or many → `<ramo>BLOCKED</ramo>` with the
   candidates listed; never auto-select.
3. **Branch shape.** `git rev-parse --abbrev-ref HEAD` must match `{type}/{TICKET}`, or
   `{type}/{slug}` when the team uses no tracker (`06-create-mr.md` Branch naming). A mismatch
   is a stop, not a rename this skill performs:
   renaming a branch someone may have pushed is not a repair, it is a second problem.

## Step 1: The verify-PASS gate

Read `.ramo/context/verify-pass.json`. It must satisfy all four:

| # | Condition | On failure |
|---|---|---|
| 1 | The file exists | BLOCKED: run `/ramo:verify` first |
| 2 | `verdict` is `PASS` | BLOCKED: the recorded verdict is what it is; fix the work, not the marker |
| 3 | `plan` equals the resolved plan path | BLOCKED: the marker belongs to a different cycle |
| 4 | `commit` is an ancestor of `HEAD`, and `git status --porcelain` is empty | BLOCKED naming which half failed |

- **Condition 4 is why this check is not the hook's.** `pre_bash.py::_verify_marker_problem`
  reads presence, verdict,
  and age; it is not given the plan and cannot resolve commits, and a gate that guessed those
  would be worse than one that admits its scope. The hook is the backstop for someone typing
  the create command directly; this step is the real check.
- Uncommitted changes fail condition 4 on purpose. An MR opened over a dirty tree describes
  bytes that are not on the branch.

## Step 2: Assemble the body

Read, do not re-derive:

| Section of `06-create-mr.md` | Where its content comes from |
|---|---|
| 배경 | the plan's §0 purpose paragraph and its `change` frontmatter field |
| 참고 자료 | the plan's `ticket:` field, linked through `tracker.url_template` when set; the plan path |
| 수정 사항 | `git diff --name-status {merge-base}..HEAD`, one row per file, rationale from the plan's change unit that owns the file |
| 실험 결과가 사는 곳 | the verify report path from the marker; `docs/model/*` and the `docs/experiments.md` row if `ramo:doc` wrote them; the artifact paths carrying seed / split_boundary / data_snapshot / feature_spec |
| To Reviewers | ask the user once (`AskUserQuestion`) for reviewers and what each should look at |

- **[HARD] Every row of `실험 결과가 사는 곳` is filled, `해당 없음` included.** A blank cell is
  not "no result"; it is "nobody recorded where the result is", and it leaves the reviewer with
  a diff and no way to judge it (`06-create-mr.md`).
- **Repository template wins.** When the provider table's repository template exists, start
  from that template and add the `실험 결과가 사는 곳` table to it. Do not replace the repository's own
  checklist blocks; they exist because something went wrong in that repository.
- Size: compare the diff against `.claude/schema/harness.json`
  `limits.mr_size_working_lines` / `limits.mr_size_justify_lines`, and when it exceeds the
  second, the 배경 section states why it was not split. Report the number either way.
- **Never put a credential, a token, or a PII value into the body**
  (`.claude/rules/common/untrusted-data-boundary.md`). Column names and row counts describe a
  dataset; values do not belong in a merge request.

## Step 3: Show it, then create it

1. Print the assembled body in full and the one command you are about to run. Print before
   running: a body reviewed after creation is a body nobody reviewed.
2. `AskUserQuestion` once: ① 이대로 생성 ② Draft 로 생성 ③ 본문 고치고 다시 ④ 중단.
3. Create with a single plain command: the provider table's Create row. Draft uses that
   table's Draft row (`--draft` on GitHub, the `Draft: ` title prefix on GitLab;
   `06-create-mr.md`).

- Write the body to a scratch file first and pass it as the body file (`--body-file` /
  `--description-file`). A body inlined into the
  command becomes a shell-quoting problem the moment it contains a backtick or a newline, and
  the failure mode is a truncated MR rather than an error.
- One call. If it fails, report the exit code and stderr verbatim and stop; do not retry with a
  reshaped command, because a second attempt after a partial success opens a duplicate MR.

## Step 4: Report

Print in `RAMO_DOCUMENTATION_LANGUAGE`:

```text
## MR 생성 완료

**MR:** {url}
**브랜치:** {branch} → {base}
**티켓:** {TICKET}
**변경 규모:** {n}개 파일, +{a} / -{d}줄 {상한 초과 시 사유 한 줄}
**검증 판정:** PASS ({verify 리포트 경로}, {commit})
**리뷰어:** {@이름 목록}
```

Then state the next step in one line: review happens on the provider's MR page, and this
pipeline has no stage that answers review comments yet.

## Suggest Next Pipeline Step

MR creation is the last v0 step. Skip the question when ending `<ramo>BLOCKED</ramo>`, when the
invocation carried `--no-prompt`/`--yes` or `RAMO_NO_NEXT_PROMPT=1`, in an autonomous or
non-interactive run, or when the user already said what comes next.

Otherwise `AskUserQuestion` once: ① `계획을 done 으로 표시` (set the plan's frontmatter
`status: done`) ② `여기서 멈춤`.

## Anti-Patterns

| Anti-pattern | Correct |
|---|---|
| Writing the verify marker so the gate passes | The gate's value is that another stage established it. Run `/ramo:verify` |
| Opening an MR to "get early feedback" before verify | Open a Draft MR for visibility; ask for review after PASS |
| Restating the experiment's result in the MR body | Point at where it lives. The MR reviews code |
| Adding a test-plan checklist | The envelope's evidence keys already record what ran (`06-create-mr.md`) |
| Retrying a failed create command with different flags | Report and stop. A retry after partial success opens a duplicate |
| Spawning an agent to draft the body | Transcription is not judgement. This skill spawns nothing |
