# Current handoff

Date: 2026-09-07. Version: **0.3.50**. State: **head dispatch handoff on feature branch**.

## Task 5 delivered

- `list_head_inbox` returns open dispatches for the seated head; CEO/admin companions
  can read all open dispatches.
- `assign_dispatch` requires an assignable dispatch, a live head seat plus
  `work.assign`/project/department grant (unless CEO/admin companion), and a rostered
  specialist or project-granted contractor. Successful assignment creates a real queue row.
- `GET /api/v1/inbox/head` and `POST /api/v1/dispatches/{id}/assign` enforce
  authenticated organization read/write scopes before core authorization.
- Vacating a head blocks that head's remaining open dispatches and cancels queue rows
  linked through `dispatch_assignments`.
- Added `tests/test_org_handoff.py` for inbox isolation, grant and roster denials,
  assignment queueing, vacancy cancellation, and API scope gates.

## Delivered in 0.3.50

- `GET /api/v1/local-repos` scans `local repos/` (or `FS_CORP_LOCAL_REPOS_DIR`)
- Desk + companion: Local candidates with Enroll; Diagnostics probes status endpoints +
  local-repos (unavailable on failure, no invented state)
- Companion package **0.3.50**

## Prior

- 0.3.49 GitHub assign-by-address; 0.3.48 billed/revenue; 0.3.47 PWA generateSW

## Verify

```bash
.venv/bin/python -m unittest tests.test_org_handoff tests.test_org_roster tests.test_production_slice -v
.venv/bin/python -m unittest discover -s tests
```

## Next implementation

Implement Task 6 desk/companion organization and head-inbox UI, then update the
version and remaining capability/roadmap documentation. Do not invent occupancy or
queue state in the UI.
