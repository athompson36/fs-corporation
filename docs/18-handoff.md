# Current handoff

Date: 2026-09-14. Version: **0.3.82**. State: **Desk Finance init-time mutate
disable merged to `main`, pushed, and deployed to fs-dev.** Tip: **`dd352ab`**.

## On main / fs-dev

- `company/service.py` — Finance mutate controls ship `disabled`;
  `#finance-scope-notice` visible from first paint; init
  `setFinanceMutateEnabled(false)`; session/403 paths unchanged.
- `tests/test_desk_finance_init_disable.py` — source contracts + version
  **0.3.82**.
- ADR-064; version **0.3.82** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: companion tab/mode URL flash (0.3.81), Desk Finance polish
  (0.3.80).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **556 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.82).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.82",...}`; desk
  serves visible `finance-scope-notice` and init `setFinanceMutateEnabled(false)`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed companion/desk follow-ups.
