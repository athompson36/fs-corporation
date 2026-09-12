# Current handoff

Date: 2026-09-11. Version: **0.3.69**. State: **Corporate/Workers Browse section
consistency implemented on `feature/corporate-workers-browse-polish`** (not yet
merged or deployed).

## On this branch

- Corporate Browse lists use `section-head` titles and `panel-empty` empty
  states (Objectives, Industry packs, Divisions, Pending promotions, Staffing
  proposals, Cross-department requests, Open activity).
- Workers **Worker hosts** title sits outside the list card, matching Projects
  and Corporate Objectives. Manage remains create-host/token on Workers and
  enroll/assign on Projects.
- ADR-051; version **0.3.69** (Python package and companion `package.json`
  lockstep). No new APIs, URL sync, Corporate groups, Org restructure or Alembic.
- Branch: `feature/corporate-workers-browse-polish`. Projects Browse split from
  0.3.68 is unchanged.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **504 tests passed**.
- `cd companion && npm run build`: OK (package version 0.3.69).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Org hierarchy polish, URL-synced project selection, Corporate
Browse groups, or other companion/desk follow-ups.
