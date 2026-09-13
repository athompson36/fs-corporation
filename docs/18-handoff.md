# Current handoff

Date: 2026-09-12. Version: **0.3.80**. State: **Desk Finance polish merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`1085ac9`**.

## On main / fs-dev

- `company/service.py` — `applyFinancePauseFromSession()` via `GET /api/v1/session`;
  Finance mutate controls gated on `company.pause`; 403 still fail-closed;
  openRoom shows simulated spend + reserved; no unconditional
  `setFinanceMutateEnabled(true)`.
- `tests/test_desk_finance_polish.py` — session gate, openRoom, version **0.3.80**.
- `tests/test_desk_finance_surface.py` — `#budget`-scoped dump ban (allows
  `simulated_spend_cents` outside Money).
- `tests/test_companion_finance_url_polish.py` — soft `0\.3\.\d+` version pin.
- ADR-062; version **0.3.80** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: companion finance URL polish (0.3.79), Desk Finance surface
  (0.3.78).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **545 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.80).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.80",...}`; desk
  serves `applyFinancePauseFromSession` and openRoom `simulated_spend_cents`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: companion one-frame tab URL flash; init-time Finance disable
before session (desk nit); or other companion/desk follow-ups.
