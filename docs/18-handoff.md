# Current handoff

Date: 2026-09-14. Version: **0.3.86**. State: **Finance open-next and pricing honesty
on branch `feature/finance-open-next-pricing`.** Tip: fill after Task 3 commit.

## On feature branch

- `company/finance.py` — `open_next_budget_period`; pricing honesty block in
  `finance_summary` when no rate source is configured.
- `company/service.py` — `POST /api/v1/finance/budget-periods/{period_id}/open-next`;
  desk `#budget` Open next + pricing hint under existing `company.pause` gate.
- `companion/src/FinancePanel.tsx` — Open next + overview hint.
- `tests/test_durable_finance.py`, `tests/test_desk_finance_open_next.py` — core + desk
  contracts.
- ADR-068; API contract open-next row; README + VERIFICATION honesty; companion lockstep
  **0.3.86**.
- Prior on `main`: Desk remaining session gates (0.3.85), corporate write gate (0.3.84),
  Org session gate (0.3.83), Finance init disable (0.3.82).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **587 tests, OK** (pre-merge).
- `cd companion && npm run build`: run at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Ship 2 remaining: consultant measured before/after (0.3.87; brainstorm/plan separately).
