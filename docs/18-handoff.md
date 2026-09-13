# Current handoff

Date: 2026-09-12. Version: **0.3.81**. State: **Companion tab/mode URL flash
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`157b99f`**.

## On main / fs-dev

- `companion/src/urlState.ts` — `stateAfterTabChange` / `stateAfterModeChange`
  pure helpers.
- `companion/src/App.tsx` — `selectTab` / `handlePanelModeChange` batch sibling
  resets; all five mode-capable panels wired; same-tab re-tap no-ops; lagging
  tab/mode reset effects removed.
- `companion/scripts/check-url-state.mts` — transition sequence harness cases 1–5.
- `tests/test_companion_tab_url_flash.py` — source contracts + version **0.3.81**.
- `tests/test_desk_finance_polish.py` — soft `0\.3\.\d+` version pin (lockstep).
- ADR-063; version **0.3.81** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Finance polish (0.3.80), companion finance URL polish
  (0.3.79), Desk Finance surface (0.3.78).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **551 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.81).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.81",...}`; companion
  build `fs-corporation-companion@0.3.81` served after install.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: desk init-time Finance disable before session fetch; or other
companion/desk follow-ups.
