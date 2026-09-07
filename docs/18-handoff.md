# Current handoff

Date: 2026-09-07. Version: **0.3.48**. State: **M10-03 billed cost / revenue tables shipped**.

## Delivered in 0.3.48

- `billed_costs` and `revenue` tables (Alembic `0013_billed_cost_revenue`)
- Live `invoke_model` persists billed rows; tokens in `usage_tokens`; `cost_cents` only when
  priced via profile `cents_per_1k_tokens` or `FS_CORP_MODEL_CENTS_PER_1K_TOKENS`
- `record_revenue` (CEO-only); `status()` exposes `billed_cost_cents` / `revenue_cents`
  separate from `simulated_spend_cents`
- Desk budget panel shows the three totals distinctly

## Prior

- 0.3.47 companion PWA generateSW; 0.3.46 M10-02; 0.3.42–0.3.45 M10-01

## Verify

```bash
.venv/bin/python -m unittest tests.test_m10_finance tests.test_model_feed_live -v
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

Remaining **M10-03**: benchmark_results / model_profiles read path or removal; role
benchmark fixtures. Or **M10-04** UI (status surface, version display, desk keyboard,
`window.prompt` replacement).
