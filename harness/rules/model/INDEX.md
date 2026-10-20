# Model Rules — Registry

Domain knowledge for the model domain (training, tuning, evaluation, model cards). Grid agents
`ramo-model-design` / `ramo-model-implement` / `ramo-model-verify` cite these files by path (domain
knowledge lives here, never inline in agent bodies).

| File | Loading | Description |
|------|---------|-------------|
| `model-family-selection.md` | `paths:` `.ramo/plans/*.md` (+ cited by ramo-plan Step 1b) | Default family per problem case, the one-line record when a default applies, the single AskUserQuestion when the plan deviates |
| `feature-engineering.md` | `paths:` feature/train/model py, experiments, notebooks (+ cited by model agents) | Transform map per model family, five derivation types, all-exclusions verdict is a defect |
| `eval-metric-slice.md` | `paths:` train/eval/model py, experiments, notebooks (+ cited by model agents) | Declared metrics/slices/baseline; aggregate-only reporting never passes |
| `leakage.md` | `paths:` train/split/feature py, experiments, notebooks (+ cited by model agents) | Temporal boundary, target leakage, group leakage checklists |
| `training-budget.md` | `paths:` train/model py, experiments, notebooks (+ cited by model agents) | Early stopping declares its `min_delta`, wall-clock derived from a measured per-iteration cost, first fit leaves a loss curve, search and confirmation budgets split |

## See Also

- `../INDEX.md` — root catalog
- `../data/INDEX.md` — data-domain registry
