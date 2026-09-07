# Current handoff

Date: 2026-09-07. Version: **0.3.51**. State: **organization handoff UI on feature branch**.

## Task 6 delivered

- Desk reads `/api/v1/org` and renders department id, persisted seat status, principal
  or `vacant`, and roster. It also reads the authenticated head inbox and provides an
  assignment form for assignable dispatches.
- Desk project dispatch uses an explicit `department_budgets` map parsed from labeled
  `department=¢` rows; it does not silently split a shared amount.
- Companion adds an Org tab with catalog/seats/roster, head inbox + assignment for
  `organization.write`, and explicit dormant-department activation.
- Companion project dispatch replaces the hard-coded 500¢ split/prompt flow with labeled
  brief, acceptance, and per-department budget controls.
- Client methods now cover org, head inbox, assign, and activate. Vacant/dormant state is
  displayed as returned and never promoted to healthy activity.
- Versions are aligned at 0.3.51 for Python and the web companion. The native Expo package
  retains its independent 0.3.8 version.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **248 passed**.
- `cd companion && npm run build`: passed; generateSW assets emitted.
- IDE diagnostics: no errors in edited Python/TypeScript/test files.
- `python3 scripts/check_bundle.py`: stopped only at the pre-existing nested
  `local repos/service-department/README.md` link to missing `./LICENSE`.

## Next implementation

Implement Task 7 cross-department work orders with explicit requesting/delivering
departments, budget owner, due date, acceptance criteria, and authorization. Do not infer
authority from org-chart edges and do not alter the nested local repository to satisfy the
root bundle checker.
