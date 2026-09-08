# Current handoff

Date: 2026-09-08. Version: **0.3.53**. State: **P3 durable finance merged to `main`,
pushing, and deploying to fs-dev.**

## P3 Durable finance (on main)

- Alembic `0025_durable_finance`: `invoices`, `finance_adjustments`, `budget_period_closures`.
- APIs under `/api/v1/finance/*`; `status().billed_cost_cents` is **net** (ADR-038).
- Companion More → **Finance**: summary, invoices, refunds, budget periods.
- Deferred: choose_model benchmarks + work-order replay ledger.

## Also on main

- P2 live ops; P1 Settings; P0 M10 / dispatch recommend.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **403 passed**
- `cd companion && npm run build`: passed
- Do not commit `local repos/service-department/`.

## Next

1. Smoke Finance tab on https://192.168.4.100.
2. **P4 Scale and presence** or thin P3 follow-on (benchmarks / work-order replay).
