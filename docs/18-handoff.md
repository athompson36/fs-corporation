# Current handoff

Date: 2026-09-12. Version: **0.3.72**. State: **`feature/projects-list-row-clear-loading`
local branch — not merged to `main` or deployed to fs-dev yet.** Prior tip on main/fs-dev:
**0.3.71** (`3e3c798`).

## On feature branch (0.3.72)

- Projects Browse list rows replace `<div className="muted">` with `<span
  className="muted">` inside list buttons; `.list-row .muted { display: block; }`
  preserves stacked brief/blockers layout.
- When `selectedProject && !projectDetail`, the loading card renders a
  `detail-toolbar` with the project id and **Clear selection**
  (`setSelectedProject(null)`) above a muted “Loading…” line — same control as
  loaded detail. Empty pane (“Select a project”) still has no Clear.
- Manage enroll/assign, Corporate clusters, Org/Corporate/Workers polish and all
  APIs unchanged.
- ADR-054; version **0.3.72** (Python package and companion `package.json`
  lockstep). Corporate clusters test relaxes version pin to `0.3.x` regex.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **514 tests, OK** (record after
  Task 3 run).
- `cd companion && npm run build`: OK (package version 0.3.72).
- fs-dev still reports **0.3.71** until merge and deploy.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Merge `feature/projects-list-row-clear-loading` to `main`, deploy fs-dev, then
owner-directed: URL-synced project selection, Manage visual groups, or other
companion/desk follow-ups.
