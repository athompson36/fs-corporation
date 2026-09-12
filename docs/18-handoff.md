# Current handoff

Date: 2026-09-12. Version: **0.3.74**. State: **Manage visual groups merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`bce7048`**.

## On main / fs-dev

- `companion/src/useWideViewport.ts` — shared `matchMedia("(min-width: 720px)")`
  hook for Corporate Browse and Manage panels.
- `companion/src/ManageClusters.tsx` — hybrid Manage chrome (labeled scroll ≥
  720px; segmented group tabs below).
- `companion/src/OrgPanel.tsx` — Manage groups Catalog · Seats · Positions ·
  Lookup.
- `companion/src/CorporatePanel.tsx` — Manage groups Goals · Structure ·
  Coordination · Ops; Browse uses shared hook.
- `companion/src/ProjectsPanel.tsx` — Manage groups Enroll · GitHub.
- `companion/src/WorkersPanel.tsx` — Manage groups Hosts · Token with honest
  empty and section-head titles; remounts to Token after host create.
- ADR-056; version **0.3.74** (Python package and companion `package.json`
  lockstep).
- Prior: Companion URL sync (0.3.73), Projects list-row Clear-on-loading
  (0.3.72), Corporate clusters (0.3.71), Org polish (0.3.70).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **522 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.74).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.74",...}`; companion
  bundle `index-BZ9AYJrL.js` includes `Organization manage groups` /
  `manage-cluster-tabs`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: empty-list unknown-project URL edge nit; Manage/Browse URL sync;
Finance ModeSwitch; or other companion/desk follow-ups.
