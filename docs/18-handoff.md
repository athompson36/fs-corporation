# Current handoff

Date: 2026-09-14. Version: **0.3.86**. State: **Finance open-next + pricing honesty
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`dc408f0`** (merge).

## On main / fs-dev

- `company/finance.py` — `open_next_budget_period`; `finance_summary.pricing` honesty
  (`model_cents_per_1k_configured` + hint).
- `POST /api/v1/finance/budget-periods/{id}/open-next` — `company.pause` + CEO.
- Desk `#budget` + companion FinancePanel — Open next on closed periods; pricing hint.
- ADR-068; version **0.3.86** lockstep.
- Prior: Desk remaining session gates (0.3.85).

## Verification

- Focused finance tests OK after merge; ship suite was **587 tests, OK**.
- fs-dev: `GET /api/v1/health` → version **0.3.86** after deploy + install.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Ship 2 remainder: consultant measured before/after (**0.3.87**).
