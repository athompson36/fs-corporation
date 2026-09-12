# Current handoff

Date: 2026-09-11. Version: **0.3.70**. State: **Org Browse/Manage polish merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`b965ee0`**.

## On main / fs-dev

- Organization Browse uses a **Departments** `section-head` above the catalog
  cards and keeps Head inbox `section-head` + `panel-empty` with inline assign.
- Organization Manage form titles sit in `section-head` outside each form card
  (create/appoint/vacate/assign/release/create position/reorder/activate/worker
  card). Fields, `runAction` handlers and scope notices are unchanged.
- ADR-052; version **0.3.70** (Python package and companion `package.json`
  lockstep). No new APIs, URL sync, Corporate groups, Manage grouping or Alembic.
- Prior: Corporate/Workers polish (0.3.69), Projects Browse split (0.3.68), desk
  IA five domains (0.3.67).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **506 tests passed** (pre-merge).
- `cd companion && npm run build`: OK (package version 0.3.70).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.70",...}`; companion
  bundle includes Departments / Create department / Appoint head / Worker card.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Corporate Browse groups/sub-tabs, Projects list-row HTML nit,
URL-synced project selection, or other companion/desk follow-ups.
