# Current handoff

Date: 2026-09-12. Version: **0.3.73**. State: **Companion URL sync on
`feature/companion-url-sync`** (branch-local; not yet merged or deployed).

## On branch `feature/companion-url-sync`

- `companion/src/urlState.ts` — pure `parseCompanionSearch` /
  `serializeCompanionSearch` helpers for `?tab=` and `?project=`.
- `companion/src/App.tsx` — boot from search; `history.replaceState` on tab or
  selection change; re-parse on `popstate`; clear unknown project ids silently
  after projects load; leaving Projects or Clear selection drops `project` and
  clears selection.
- Pairing `#fs-pair=` redeem and `clearPairingHash()` unchanged.
- ADR-055; version **0.3.73** (Python package and companion `package.json`
  lockstep).
- Prior 0.3.72 Projects list-row `span.muted` and Clear-on-loading, 0.3.71
  Corporate clusters, and all APIs unchanged.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **517 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.73).
- fs-dev still reports **0.3.72** until merge/deploy.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Merge `feature/companion-url-sync` to `main`, deploy to fs-dev, then
owner-directed: Manage visual groups or other companion/desk follow-ups.
