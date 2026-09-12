# Current handoff

Date: 2026-09-11. Version: **0.3.71**. State: **Corporate Browse clusters on
`feature/corporate-browse-clusters` — not merged to `main` or deployed to fs-dev
until branch finish.**

## On feature/corporate-browse-clusters (local)

- Corporate Browse groups lists into **Strategy · Structure · People ·
  Coordination** clusters with `cluster-head` labels — **Strategy** (CEO
  scorecard, Objectives), **Structure** (Industry packs, Divisions), **People**
  (Pending promotions, Staffing proposals), **Coordination** (Cross-department
  requests, Open activity). At viewport width ≥720px all clusters render as
  labeled scroll sections; below 720px a segmented tablist switches among
  clusters (default Strategy) while keeping the cluster label in the active pane.
- Corporate Manage adds `section-head` titles outside form cards for Corporate
  operations, Create objective, Propose division and Create cross-department
  request. Fields, `runAction` handlers and scope notices are unchanged.
- ADR-053; version **0.3.71** (Python package and companion `package.json`
  lockstep). No new APIs, URL sync, Manage grouping or Alembic.
- Prior on `main`/fs-dev: Org Browse/Manage polish (0.3.70), Corporate/Workers
  Browse section-head consistency (0.3.69), Projects Browse split (0.3.68), desk
  IA five domains (0.3.67).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **510 tests, OK** (~22s;
  includes `test_corporate_browse_clusters`).
- `cd companion && npm run build`: **OK** (fs-corporation-companion@0.3.71).
- fs-dev remains at **0.3.70** until this branch merges and deploys.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: merge and deploy 0.3.71, Projects list-row HTML nit,
URL-synced project selection, Manage visual groups, or other companion/desk
follow-ups.
