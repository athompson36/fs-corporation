# Current handoff

Date: 2026-09-11. Version: **0.3.70**. State: **Org Browse/Manage section-head
consistency implemented on `feature/org-browse-manage-polish`** (not yet
merged or deployed).

## On this branch

- Organization Browse uses a **Departments** `section-head` above the catalog
  cards and keeps Head inbox `section-head` + `panel-empty` with inline assign.
- Organization Manage form titles sit in `section-head` outside each form card
  (create/appoint/vacate/assign/release/create position/reorder/activate/worker
  card). Fields, `runAction` handlers and scope notices are unchanged.
- ADR-052; version **0.3.70** (Python package and companion `package.json`
  lockstep). No new APIs, URL sync, Corporate groups, Manage grouping or Alembic.
- Branch: `feature/org-browse-manage-polish`. Corporate/Workers polish from
  0.3.69 and Projects Browse split from 0.3.68 are unchanged.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **506 tests passed**.
- `cd companion && npm run build`: OK (package version 0.3.70).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Corporate Browse groups/sub-tabs, Projects list-row HTML nit,
URL-synced project selection, or other companion/desk follow-ups.
