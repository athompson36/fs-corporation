# Current handoff

Date: 2026-09-10. Version: **0.3.66**. State: **Work/People/Money Browse–Manage
implemented and verified locally** on `feature/work-people-money-browse-manage`; not merged,
pushed or deployed. fs-dev health remains **0.3.65**.

## Implemented locally

- Shared `ModeSwitch` gives Projects, Corporate, Workers and Organization local
  **Browse / Manage** modes, defaulting to Browse.
- Browse contains persisted lists/details and contextual row actions; Manage contains
  create/enroll/configure flows. Project detail and dispatch remain in Browse.
- Finance retains **Overview · Invoices · Adjustments · Periods** with no nested mode layer.
- `ProjectsPanel`, `CorporatePanel` and `OrgPanel` are extracted from `App`; source-contract
  tests follow the new component ownership.
- ADR-048 records the local-mode boundary. No API contract or Alembic revision changed.
- Release/documentation files changed: `company/__init__.py`, `companion/package.json`,
  README, docs 11/14/18/24, `docs/decisions.md`, and the implementation design/plan.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **491 tests passed**.
- `cd companion && npm run build`: **OK**.
- Build keeps the known `/static/fonts/*.woff2` runtime-resolution warnings; files are served
  by the backend rather than bundled by Vite.
- Suite emitted existing Starlette/httpx deprecation, SQLite ResourceWarning, missing local
  public/LAN configuration, and degraded worker-NIC warnings; no test failed.
- Do not commit `local repos/service-department/`.

## Next

Owner review/merge and deploy **0.3.66**, then verify fs-dev health and phone Browse/Manage
flows. After release, choose deep visual/master-detail project polish or align desk information
architecture to the five companion domains.
