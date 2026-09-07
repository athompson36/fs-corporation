# Current handoff

Date: 2026-09-07. Version: **0.3.52** (unchanged). State: **Corporate HQ Phase 4 implemented on feature/corporate-hq-phases**.

## Corporate HQ Phase 4 (no version bump)

- Alembic `0019_activity_projection` adds event-bound `activity_sessions`; unique
  `started_event_id` and event foreign keys prevent replay duplication and orphan sessions
- `_event` transactionally reduces queue leases, worker starts, quality inspections,
  dispatch assignment/blocking, cross-department requests, and owner context requests
- acceptance/response/worker/task terminal events close matching sessions; explicit
  `close_stale_sessions()` reconciles terminal queue/task/request state
- `GET /api/v1/activity` requires `company.read`; SSE frames retain `seq`/`kind`/`at`
  and add `room_id` only when a projected room exists
- Desk polls open activity every 10 seconds and draws persisted room badges; pulse classes
  are omitted when `prefers-reduced-motion` is active
- Tests: 40 focused integration/regression tests and 291 full-discovery tests pass on
  Python 3.14.3

## Prior

- Corporate HQ Phase 3 added validated worker sprites and joined worker cards
- Corporate HQ Phase 2 persisted floorplans/rooms and requirement warnings
- 0.3.52 Phase 1 runtime department/position editing and `0016_department_editing`
- 0.3.51 org roster, head handoff, cross-department requests

## Verify

```bash
.venv/bin/python -m unittest tests.test_activity_projection tests.test_worker_identity tests.test_floorplans tests.test_cross_department_requests tests.test_owner_requests tests.test_migrate tests.test_service_edges -v
.venv/bin/python -m unittest discover -s tests
PYTHONPATH=. .venv/bin/alembic heads
```

## Next

Define Corporate HQ Phase 5 before extending furnishing or movement; keep any visual
presence derived from persisted activity sessions rather than inferred model availability.
