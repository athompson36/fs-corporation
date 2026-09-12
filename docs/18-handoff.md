# Current handoff

Date: 2026-09-12. Version: **0.3.75**. State: **Empty-list unknown-project URL
clear on branch `feature/empty-list-unknown-project-url`.** Tip: pending commit
hash.

## On feature/empty-list-unknown-project-url

- `companion/src/App.tsx` — `projectsLoaded` state; set `true` only on successful
  projects refresh; unknown-`?project=` clear gated on `projectsLoaded` (empty
  list after successful load clears silently).
- `tests/test_companion_url_sync.py` — contracts for loaded-gate and exact
  version **0.3.75**.
- ADR-057; version **0.3.75** (Python package and companion `package.json`
  lockstep).
- Prior: Manage visual groups (0.3.74), Companion URL sync (0.3.73), Projects
  list-row Clear-on-loading (0.3.72), Corporate clusters (0.3.71), Org polish
  (0.3.70).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: pending Task 3 run.
- `cd companion && npm run build`: pending Task 3 run (package version 0.3.75).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: merge `feature/empty-list-unknown-project-url` to `main` and
deploy to fs-dev; Manage/Browse URL sync; Finance ModeSwitch; or other
companion/desk follow-ups.
