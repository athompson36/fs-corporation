# Current handoff

Date: 2026-09-07. Version: **0.3.52** (unchanged). State: **Corporate HQ Phase 5 implemented on feature/corporate-hq-phases**.

## Corporate HQ Phase 5 (no version bump)

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
- Tests: 29 focused integration/regression tests and 299 full-discovery tests pass on
  Python 3.14.3; Alembic reports `0020_career_ladder` as head

## Prior

- Corporate HQ Phase 4 added persisted live activity projection
- Corporate HQ Phase 3 added validated worker sprites and joined worker cards
- Corporate HQ Phase 2 persisted floorplans/rooms and requirement warnings
- 0.3.52 Phase 1 runtime department/position editing and `0016_department_editing`
- 0.3.51 org roster, head handoff, cross-department requests

## Verify

```bash
.venv/bin/python -m unittest tests.test_career_ladder tests.test_peopleops tests.test_api tests.test_worker_identity tests.test_migrate -v
.venv/bin/python -m unittest discover -s tests
PYTHONPATH=. .venv/bin/alembic heads
```

## Next

Define Corporate HQ Phase 6 before extending furnishing or movement; retain separate
proposer/decider authority and keep visual presence derived from persisted activity sessions.
