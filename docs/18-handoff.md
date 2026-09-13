# Current handoff

Date: 2026-09-12. Version: **0.3.80**. State: **Desk Finance polish on
`feature/desk-finance-polish`, pending merge to `main`.** Tip: **`556f1ff`**.

## On feature/desk-finance-polish

- `company/service.py` — `applyFinancePauseFromSession()` fetches
  `/api/v1/session` before `loadFinance()`; enables Finance mutations only when
  scopes include `company.pause`; fail closed on session error; no unconditional
  `setFinanceMutateEnabled(true)` at init; 403 in `postFinanceCommand` remains
  backup.
- `company/service.py` — `openRoom` restores simulated + reserved spend line
  (`simulated_spend_cents`, `reserved_cents`).
- `tests/test_desk_finance_polish.py` — session gate, openRoom, version **0.3.80**
  contracts.
- `tests/test_desk_finance_surface.py` — `#budget`-scoped dump ban (soft version).
- `tests/test_companion_finance_url_polish.py` — soft `0\.3\.\d+` version pin.
- ADR-062; version **0.3.80** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Companion finance URL polish (0.3.79), Desk Finance surface
  (0.3.78), Finance Browse/Manage (0.3.77).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **545 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.80).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Merge `feature/desk-finance-polish` to `main`, deploy to fs-dev, or owner-directed
companion follow-ups (one-frame tab-change URL flash).
