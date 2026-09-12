# Current handoff

Date: 2026-09-12. Version: **0.3.77**. State: **Finance Browse/Manage merged to
`main`, pushed, and deployed to fs-dev.** Tip: **`5b21dcd`**.

## On main / fs-dev

- `companion/src/urlState.ts` — `finance` in `MODE_CAPABLE_TABS`; mode-aware
  browse/manage group tables; finance serializes `group` in both modes.
- `companion/src/FinancePanel.tsx` — ModeSwitch + ManageClusters; Browse lists
  (Overview · Invoices · Adjustments · Periods); Manage forms (Invoice ·
  Adjustment · Period); Close period stays Browse in-row.
- `companion/src/App.tsx` — controlled Finance props; mode-change group reset.
- `tests/test_finance_browse_manage.py` — contracts; exact version **0.3.77**.
- Legacy tests flipped: Finance now requires ModeSwitch/ManageClusters
  (`test_work_people_money_browse_manage.py`, `test_projects_split_browse_polish.py`).
- `tests/test_mode_cluster_group_url_sync.py` — soft `0\.3\.\d+` version pin.
- ADR-059; version **0.3.77** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: mode/cluster/group URL sync (0.3.76), empty-list unknown-project
  URL clear (0.3.75), Manage visual groups (0.3.74), Companion URL sync (0.3.73).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **533 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.77).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.77",...}`; companion
  bundle rebuilt (`index-Ca-CDgRT.js`).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: desk Finance surface; remaining polish nits (dead `closePeriod`
focus; cold-load `defaultGroupFor` bias; behavioral URL tests); or other
companion follow-ups.
