---
title: Update Protocol
impact: CRITICAL
tags: foundation, updates, lifecycle
---

## Update Protocol

Documents are living artifacts — updated in place, never replaced. Every update follows
a strict protocol to prevent data loss, stale cross-references, and invisible
regressions. Overwriting a document without reading it first is the most common cause of
documentation drift.

### Protocol Steps (in order)

1. **Read the existing document first** — never write without reading the current state.
2. **Update `updated:` and `generated:`** — set `updated:` to today; refresh
   `generated: { by, at }` with the writing actor; leave `created:` unchanged. Existing
   `verified:` events stay (content change without re-confirmation is a legitimate,
   visible state — the trust tier derivation handles it).
3. **Preserve existing structure** — do not reorganize sections unless the template
   itself changed.
4. **Replace, do not accumulate** — delete superseded text in the same commit; git
   history is the archive (`.claude/rules/common/sot-authoring.md` SOT-3).
5. **Add a changelog entry** — required for `data` and `model` category documents
   (extraction contracts and evaluation protocols are consumed downstream; their history
   must be auditable in place):
   ```markdown
   | 2026-08-21 | Snapshot policy changed from daily to hourly partitions | Yes |
   ```
6. **Check cross-references** — if this document is listed in another document's
   `depends-on`, review the dependent document for accuracy.

### When Each Step Applies

| Step | data | model | analysis | feature | pipeline | other |
|------|------|-------|----------|---------|----------|-------|
| Read first | always | always | always | always | always | always |
| Update `updated:`/`generated:` | always | always | always | always | always | always |
| Preserve structure | always | always | always | always | always | always |
| Soft-deprecate instead of delete | exempt classes only* | exempt classes only* | exempt classes only* | exempt classes only* | exempt classes only* | exempt classes only* |
| Changelog entry | required | required | optional | optional | optional | no |
| Check cross-references | always | always | always | always | always | always |

\* Soft deprecation is required for exactly these document classes: ADRs (immutable
decision records, superseded via `status: superseded` + `superseded-by:` / `supersedes:`)
and CHANGELOG/release notes (append-only by nature). Every other document follows step 4:
replace, do not accumulate.

**Incorrect (overwriting without reading, stale `updated:`, no changelog trail):**

```markdown
---
title: Yellow Trips Snapshot
category: data
status: stable
created: 2026-07-01
updated: 2026-07-01    # Wrong: not updated to today's date
---

# Yellow Trips Snapshot

Hourly partitions added.
```

Why this fails: `updated:` gives no signal the document changed; the daily-partition
content vanished with no changelog row recording when or why; the writer never read the
existing document.

**Correct (read first, refreshed metadata, superseded text removed, changelog carries history):**

```markdown
---
title: Yellow Trips Snapshot
category: data
status: stable
created: 2026-07-01
updated: 2026-08-21
generated: { by: ramo-doc-writer/claude-sonnet-5, at: 2026-08-21T04:12:00Z }
---

# Yellow Trips Snapshot

Snapshots are hourly partitions (`pickup_date`, `pickup_hour`) since 2026-08-21.

## Changelog

| Date | Change | Breaking |
|------|--------|----------|
| 2026-08-21 | Snapshot policy changed from daily to hourly partitions | Yes |
| 2026-07-01 | Initial documentation | No |
```

**Incorrect (cross-reference check skipped):** updating
`docs/data/trips-snapshot.md` to add a `pickup_hour` partition column without checking
`docs/model/trip-duration-card.md`, whose training-data section names the daily partition —
the model card now silently contradicts the dataset doc.

**Correct:** after the update, read the dataset doc's `depends-on` and dependents; any
document listing it must be reviewed in the same pass.
