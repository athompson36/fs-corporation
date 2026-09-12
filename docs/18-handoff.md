# Current handoff

Date: 2026-09-12. Version: **0.3.72**. State: **Projects list-row Clear-on-loading
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`ee0065a`**.

## On main / fs-dev

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
  lockstep).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **514 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.72).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.72",...}`; companion
  bundle includes Clear selection / Loading… / detail-toolbar.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: URL-synced project selection, Manage visual groups, or other
companion/desk follow-ups.
