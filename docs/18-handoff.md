# Current handoff

Date: 2026-09-14. Version: **0.3.82**. State: **Desk Finance init-time mutate
disable on branch `feature/desk-finance-init-disable`** (merge pending). Tip:
**`022fffd`**.

## On branch (pending merge)

- `company/service.py` — Finance mutate controls ship `disabled` in markup;
  visible `#finance-scope-notice`; `setFinanceMutateEnabled(false)` at init;
  `applyFinancePauseFromSession()` / 403 paths unchanged.
- `tests/test_desk_finance_init_disable.py` — source contracts for init-time disable.
- ADR-064; version **0.3.82** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Companion tab/mode URL flash (0.3.81), Desk Finance polish
  (0.3.80), companion finance URL polish (0.3.79), Desk Finance surface (0.3.78).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: run full suite; expect OK.
- `cd companion && npm run build`: OK (package version 0.3.82).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: broader desk session use for other mutate UIs; permission-clamp
companion URL timing if a flash is found; or other companion/desk follow-ups.
