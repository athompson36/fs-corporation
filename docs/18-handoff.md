# Current handoff

Date: 2026-09-12. Version: **0.3.78**. State: **Desk Finance surface on branch
`feature/desk-finance-surface`** (Tasks 1–5 complete; pending merge/deploy). Tip:
**`b010a9a`**.

## On feature branch

- `company/service.py` — DESK_HTML rail `#budget` labeled **Finance**; structured
  overview from `/api/v1/finance/summary`; invoice/adjustment/period lists;
  create forms; in-row close period; `loadFinance()` + `formatFinanceUsd` +
  `setFinanceMutateEnabled`; pause gate on 403; no `budget-json`.
- `tests/test_desk_finance_surface.py` — source contracts; exact version **0.3.78**.
- `tests/test_finance_browse_manage.py` — soft `0\.3\.\d+` version pin (companion
  Finance Browse/Manage unchanged).
- ADR-060; version **0.3.78** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Finance Browse/Manage (0.3.77), mode/cluster/group URL sync
  (0.3.76), empty-list unknown-project URL clear (0.3.75).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **538 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.78).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: merge `feature/desk-finance-surface` to `main` and deploy to
fs-dev; or polish nits (dead `closePeriod` focus; cold-load `defaultGroupFor`
bias; behavioral URL tests) / other companion follow-ups.
