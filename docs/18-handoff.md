# Current handoff

Date: 2026-09-12. Version: **0.3.81**. State: **Companion tab/mode URL flash on
branch `feature/companion-tab-url-flash`.** Tip: **`43ee390`**.

## On feature/companion-tab-url-flash

- `companion/src/urlState.ts` — `stateAfterTabChange` / `stateAfterModeChange`
  pure helpers.
- `companion/src/App.tsx` — `selectTab` / `handlePanelModeChange` batch sibling
  resets; all five mode-capable panels wired; lagging tab/mode reset effects removed.
- `companion/scripts/check-url-state.mts` — transition sequence harness cases 1–5.
- `tests/test_companion_tab_url_flash.py` — source contracts + version **0.3.81**.
- `tests/test_desk_finance_polish.py` — soft `0\.3\.\d+` version pin (lockstep).
- ADR-063; version **0.3.81** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Finance polish (0.3.80), companion finance URL polish
  (0.3.79), Desk Finance surface (0.3.78).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: run full suite before merge.
- `cd companion && npm run build`: OK (package version 0.3.81).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Do not claim fs-dev deploy until merged and installed.

## Next

Desk init-time Finance disable before session fetch (desk nit); permission-clamp
timing only if a flash is observed; or owner-directed companion/desk follow-ups.
