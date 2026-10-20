# Data Rules — Registry

Domain knowledge for the data domain (warehouse access, SQL extraction, snapshots, data
quality). Grid agents `ramo-data-design` / `ramo-data-explore` / `ramo-data-implement` /
`ramo-data-verify` cite these files by path (domain knowledge lives here, never inline in agent
bodies).

**Two of these files are accumulation registries and start empty.** The four-way split behind
that: domain definitions (B) and table pitfalls (C) live here because nothing else holds them,
while a table map (A) and a verified query pattern (D) do not — the adapter's `search` answers the
first and a team's shared query store is the right home for the second, and a stale copy of either
beats the live source. Seeding B or C speculatively is worse than leaving them empty: an invented
domain fact reads as a verified one.

| File | Loading | Description |
|------|---------|-------------|
| `eda.md` | `paths:` `.ramo/eda/*.md` (+ cited by ramo-eda and ramo-data-explore) | Read-only exploration path, bounded sampling, the prediction-anchor boundary that separates feature candidates from leakage candidates, re-obtainability |
| `warehouse-access.md` | `paths:` **/*.sql (+ cited by data agents) | Adapter precondition, two sanctioned paths (adapter reads / build-script writes), authoring sequence, writes confined to the workspace schema, no PII, snapshot + query_hash describe the source |
| `engines/duckdb.md` | `paths:` `ramo-data.json`, dataset py (+ cited by `warehouse-access.md`) | The bundled DuckDB adapter: install, `ramo-data.json` keys, what the sandbox refuses, how a build script writes workspace tables |
| `engines/trino.md` | `paths:` `ramo-data.json` (+ cited by `warehouse-access.md`) | Public Trino engine facts, and how to implement the adapter's command contract and exit codes over a DB-API cursor |
| `dataset-materialization.md` | `paths:` sql, extract/dataset py, notebooks | The two dataset shapes, no hardcoded credentials, idempotent re-runs, batched download, row-count reconciliation |
| `data-quality.md` | `paths:` sql, extract/dataset/check py, notebooks | Ten standard check classes, snapshot-pinned expectations, positive controls, artifact-only vs source-reconciling split |
| `domain-definitions.md` | `paths:` sql, py, notebooks | (B) Domain facts a query must encode. Starts empty; grows one entry at a time |
| `table-pitfalls.md` | `paths:` sql, py, notebooks | (C) Traps that produce a plausible wrong answer. Starts empty; grows one entry at a time |

## See Also

- `../INDEX.md` — root catalog
- `../model/INDEX.md` — model-domain registry
