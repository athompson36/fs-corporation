# Current handoff

Date: 2026-09-12. Version: **0.3.73**. State: **Companion URL sync merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`6746a44`**.

## On main / fs-dev

- `companion/src/urlState.ts` — pure `parseCompanionSearch` /
  `serializeCompanionSearch` helpers for `?tab=` and `?project=`.
- `companion/src/App.tsx` — boot from search; `history.replaceState` on tab or
  selection change; re-parse on `popstate`; clear unknown project ids silently
  after projects load; leaving Projects or Clear selection drops `project` and
  clears selection.
- Pairing `#fs-pair=` redeem and `clearPairingHash()` unchanged.
- ADR-055; version **0.3.73** (Python package and companion `package.json`
  lockstep).
- Prior: Projects list-row Clear-on-loading (0.3.72), Corporate clusters
  (0.3.71), Org polish (0.3.70).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **517 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.73).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.73",...}`; companion
  bundle includes `replaceState` / `popstate`; `urlState.ts` on host.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Manage visual groups, empty-list unknown-project edge nit, or
other companion/desk follow-ups.
