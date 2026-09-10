# Current handoff

Date: 2026-09-10. Version: **0.3.66**. State: **Work/People/Money Browse–Manage merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.66`).

## On main / fs-dev

- Companion panels use **Browse / Manage** for Projects, Corporate, Workers, and
  Organization (People). Finance keeps Overview · Invoices · Adjustments · Periods with
  clarifying lede (no nested Browse/Manage).
- Extracted `ModeSwitch`, `ProjectsPanel`, `CorporatePanel`, `OrgPanel`; Workers wrapped
  in place. `App.tsx` stays the data/wiring shell.
- ADR-048; version **0.3.66**; no Alembic. Merge: `8d7679a`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **491 tests passed**.
- `cd companion && npm run build`: **OK**.
- fs-dev health: **0.3.66**; `/`, `/welcome`, `/desk`, brand fonts **200**; live bundle
  includes ModeSwitch / ProjectsPanel / Browse · Manage.
- Do not commit `local repos/service-department/`.

## Next

Owner-directed: **desk information architecture alignment to the five companion domains**,
or deeper visual polish inside the new Browse/Manage panels.
