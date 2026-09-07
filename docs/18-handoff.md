# Current handoff

Date: 2026-09-07. Version: **0.3.50**. State: **org dispatch rules on feature branch**.

## Task 4 delivered

- Project department activation is persistent and restricted to CEO/admin-companion actors.
- Dispatch requires explicit per-department budgets and rejects dormant departments.
- Dispatch status is `queued_for_head` for an occupied active seat or
  `blocked_vacant_head` for a vacancy; specialist assignment and head inbox are not yet implemented.
- Optional grant department scopes are inherited by delegated grants and fail closed on mismatch.
- Roster appointment/vacancy/assignment/release accept admin-companion actors; strangers remain denied.
- Critical review fix: companion dispatch now sends the required per-department budget
  mapping; the desk service route already used that contract.

## Delivered in 0.3.50

- `GET /api/v1/local-repos` scans `local repos/` (or `FS_CORP_LOCAL_REPOS_DIR`)
- Desk + companion: Local candidates with Enroll; Diagnostics probes status endpoints +
  local-repos (unavailable on failure, no invented state)
- Companion package **0.3.50**

## Prior

- 0.3.49 GitHub assign-by-address; 0.3.48 billed/revenue; 0.3.47 PWA generateSW

## Verify

```bash
.venv/bin/python -m unittest tests.test_org_roster tests.test_production_slice tests.test_companion_api tests.test_m6 -v
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

## Next implementation

Implement Task 5 head inbox and `assign_dispatch` with department grant, occupied-head,
roster, budget, and queue gates. Do not infer assignment from Task 4 dispatch status.
