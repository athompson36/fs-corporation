# Current handoff

Date: 2026-09-12. Version: **0.3.74**. State: **Manage visual groups on branch
`feature/manage-visual-groups` (not yet on `main` / fs-dev).** Tip: `1b0d591`.

## On feature/manage-visual-groups

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
  empty and section-head titles.
- ADR-056; version **0.3.74** (Python package and companion `package.json`
  lockstep).
- Prior: Companion URL sync (0.3.73), Projects list-row Clear-on-loading
  (0.3.72), Corporate clusters (0.3.71), Org polish (0.3.70).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **522 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.74).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: merge `feature/manage-visual-groups` to `main` and deploy to
fs-dev; empty-list unknown-project URL edge nit; Manage/Browse URL sync; Finance
ModeSwitch; or other companion/desk follow-ups.
