# Task 6 report — Extract CorporatePanel

## Status

Complete on `feature/work-people-money-browse-manage`.

## Changes

- Extracted the Corporate tab from `companion/src/App.tsx` into `companion/src/CorporatePanel.tsx`.
- Added a `ModeSwitch` with Browse as the default.
- Browse contains the persisted scorecard, objectives and close action, industry packs,
  divisions and activate/deactivate actions, promotion decisions, staffing decisions,
  cross-department acceptance, and activity.
- Manage contains objective, division, and cross-department creation forms plus default
  floorplan and staffing scan actions.
- Preserved action statuses, organization-write gating, the scope notice, and all existing
  API-backed behavior. Added the requested division deactivate control using the existing
  client method.

## Verification

- Corporate acceptance test:
  `.venv/bin/python -m unittest tests.test_work_people_money_browse_manage.WorkPeopleMoneyBrowseManageTests.test_corporate_panel_browse_manage -v`
  — passed (1 test).
- `cd companion && npm run build` — passed.
- IDE diagnostics for `CorporatePanel.tsx` and `App.tsx` — no errors.
- Build retained the pre-existing unresolved-at-build-time font notices; Vite leaves those
  absolute static paths for runtime resolution.

## Commit

- `978b44d feat(companion): extract CorporatePanel with Browse/Manage`

## Concerns

- No functional blocker identified.
- Existing unrelated untracked planning/spec files and `local repos/service-department/`
  were not modified or committed.
