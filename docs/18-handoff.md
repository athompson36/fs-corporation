# Current handoff

Date: 2026-09-12. Version: **0.3.79**. State: **Companion finance URL polish
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`72e4cea`**.

## On main / fs-dev

- `companion/src/FinancePanel.tsx` — Browse Close period no longer focuses Manage
  period input or calls `onManageGroupChange("periods")` after close.
- `companion/src/App.tsx` — cold-load and popstate resolve missing `group` via
  `defaultGroupFor(tab, mode)` instead of manage-biased `defaultManageGroup(tab)`.
- `companion/scripts/check-url-state.mts` — tsx behavioral harness for
  `parseCompanionSearch` / `serializeCompanionSearch` round-trips.
- `tests/test_companion_finance_url_polish.py` — source contracts; exact version
  **0.3.79**.
- `tests/test_url_state_behavior.py` — invokes harness from unittest discover.
- `tests/test_desk_finance_surface.py` — soft `0\.3\.\d+` version pin (desk
  Finance surface unchanged).
- ADR-061; version **0.3.79** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Finance surface (0.3.78), Finance Browse/Manage (0.3.77).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **542 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.79).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.79",...}`; companion
  bundle rebuilt (`index-ybfRBduj.js`).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: desk polish nits (403-only pause gate / openRoom reserved-only)
or other companion follow-ups.
