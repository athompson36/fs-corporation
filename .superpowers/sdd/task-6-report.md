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

Commit: `21effcf` — Surface org roster and head handoff in desk and companion (v0.3.51).

Delivered:
- Desk organization roster, honest seat state, head inbox/assignment, and per-department dispatch budget form.
- Companion Org tab, head inbox/assignment, dormant-department activation, and labeled per-department dispatch budgets.
- Python/web companion version 0.3.51 plus reconciled handoff, roadmap, data model, organization, decision, capability, verification, and design-status docs.
- Added source-level regression coverage for required Desk and companion API/UI wiring.

Verification:
- `.venv/bin/python -m unittest discover -s tests`: 248 tests passed.
- `cd companion && npm run build`: passed; generateSW output emitted.
- Generated Desk JavaScript parsed successfully with `node --check`.
- Edited-file IDE diagnostics: no errors.
- `python3 scripts/check_bundle.py`: failed only at the pre-existing nested `local repos/service-department/README.md` link to missing `./LICENSE`.

Concerns:
- The nested local repository remains untracked and untouched.
- `companion-native` remains at its independent package version 0.3.8.
- Task 7 cross-department work orders were not implemented.

## Important finding 6 follow-up

Status: Fixed in this follow-up commit on `feature/org-hierarchy-handoff`.

Delivered:
- Added companion `ApiClient` commands for appointing/vacating department heads and
  assigning/releasing position assignments through the existing organization endpoints.
- Added four labeled companion forms gated by `organization.write` through
  `canManageOrg`; no organization administration flow uses `window.prompt`.
- Added equivalent labeled CEO Desk forms and exposed assignment ids in the companion
  roster so release operations have a visible target.
- Expanded source-level regression coverage for both companion and Desk controls.

Verification:
- `.venv/bin/python -m unittest tests.test_companion_api tests.test_org_roster`:
  25 tests passed.
- `.venv/bin/python -m unittest discover -s tests`: 249 tests passed.
- `cd companion && npm run build`: passed; TypeScript and Vite production build completed.
- Edited-file IDE diagnostics: no errors.
