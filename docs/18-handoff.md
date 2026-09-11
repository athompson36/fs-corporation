# Current handoff

Date: 2026-09-11. Version: **0.3.68**. State: **Projects Browse split + medium
shell polish implemented on `feature/projects-split-browse-polish`** (not yet
merged or deployed).

## On this branch

- Companion Projects Browse uses a responsive list|detail split
  (`project-browse-split`): list beside the workspace at ≥720px, stacked on
  narrow viewports.
- Detail pane holds the existing project identity and dispatch workspace.
  Empty detail copy is “Select a project”. **Clear selection** sets
  `selectedProject` to null. Manage remains local enroll and GitHub assign.
- Corporate, Workers and Organization received medium empty-state and
  section-head polish. Finance tabs are unchanged (no ModeSwitch).
- ADR-050; version **0.3.68** (Python package and companion `package.json`
  lockstep). No new APIs, URL sync or Alembic.
- Branch: `feature/projects-split-browse-polish`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **501 tests passed**.
- `cd companion && npm run build`: OK (package version 0.3.68).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: further Corporate polish, URL-synced project selection, or other.
