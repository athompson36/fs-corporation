# Current handoff

Date: 2026-09-12. Version: **0.3.78**. State: **Desk Finance surface merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`a1be7cb`**.

## On main / fs-dev

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
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.78",...}`; desk
  serves `href="#budget">Finance` and `finance-overview`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: polish nits (dead `closePeriod` focus; cold-load
`defaultGroupFor` bias; behavioral URL tests; 403-only pause gate / openRoom
reserved-only) or other companion follow-ups.
