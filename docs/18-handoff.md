# Current handoff

Date: 2026-09-07. Version: **0.3.52** (unchanged). State: **Corporate HQ Phase 6 implemented on feature/corporate-hq-phases**.

## Corporate HQ Phase 6 (no version bump)

- Alembic `0021_staffing_proposals` adds typed, evidence-backed staffing proposals,
  a unique pending kind/department/position key, and a durable 15-minute scan cooldown
- HR/CEO scans persisted vacant-head dispatches, high unassigned dispatch queues,
  unmet floorplan room requirements, and overdue employee training; scans only propose
  and never hire
- HR/CEO may create manual proposals; only CEO/admin companion may decide; approved hire
  proposals require employee id, display name, and background evidence and commit the
  proposal decision, employee, career level, training, and events atomically
- approved promote proposals remain staffing decisions only; Phase 5 promotion APIs retain
  separate evidence and decision authority
- authenticated list/create/scan/decision endpoints are available; Desk People lists pending
  proposals with approve/reject controls
- Tests: 27 focused integration/regression tests and 308 full-discovery tests pass on
  Python 3.14.3; Alembic reports `0021_staffing_proposals` as head

## Prior

- Alembic `0020_career_ladder` adds scoped career levels, current employee levels, and
  immutable promotion evidence/decisions; `config/career-ladders.json` seeds Engineering
  Developer, Senior Developer, and Staff levels
- new hires receive the lowest department level when a ladder exists; current-level quality
  standards and full ladder summaries are available from the core and authenticated API
- promotion evaluation counts accepted employee/producer artifacts, exact-hash QC passes,
  certified skills, and latest review score/trend; evidence preserves artifact hashes
- HR/CEO may propose, but only CEO/admin companion may approve or reject; approval updates
  the current level and creates missing required-skill training assignments transactionally
- Desk worker cards show current ladder level and People minimally lists pending promotions

- Corporate HQ Phase 4 added persisted live activity projection
- Corporate HQ Phase 3 added validated worker sprites and joined worker cards
- Corporate HQ Phase 2 persisted floorplans/rooms and requirement warnings
- 0.3.52 Phase 1 runtime department/position editing and `0016_department_editing`
- 0.3.51 org roster, head handoff, cross-department requests

## Verify

```bash
.venv/bin/python -m unittest tests.test_staffing_proposals tests.test_career_ladder tests.test_api tests.test_migrate -v
.venv/bin/python -m unittest discover -s tests
PYTHONPATH=. .venv/bin/alembic heads
PYTHONPATH=. .venv/bin/python scripts/check_bundle.py
```

## Next

Define Corporate HQ Phase 7 before extending furnishing or movement; retain separate
proposer/decider authority and keep visual presence derived from persisted activity sessions.
