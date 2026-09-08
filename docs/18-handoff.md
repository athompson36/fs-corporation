# Current handoff

Date: 2026-09-08. Version: **0.3.53**. State: **P3 durable finance on `feature/p3-durable-finance`.**

## P3 Durable finance (this branch)

- Alembic `0025_durable_finance`: `invoices`, `finance_adjustments`, `budget_period_closures`.
- APIs under `/api/v1/finance/*`; `status().billed_cost_cents` is **net** (ADR-038).
- Companion More → **Finance**: summary, invoices, refunds, budget periods.
- Deferred: choose_model benchmarks + work-order replay ledger.

## Also on main

- P2 live ops; P1 Settings; P0 M10 / dispatch recommend.

## Verification

- Run full unittest + companion build before merge.
- Do not commit `local repos/service-department/`.

## Next

1. Merge/push/deploy when owner requests.
2. Smoke Finance tab on fs-dev.
3. **P4 Scale and presence** or thin P3 follow-on (benchmarks / work-order replay).
