# Current handoff

Date: 2026-09-07. Version: **0.3.52** (unchanged). State: **Corporate HQ Phase 7 implemented on feature/corporate-hq-phases**.

## Corporate HQ Phase 7 (no version bump)

- Alembic `0022_divisions` adds persisted industry packs, divisions, division/department
  links, and durable activation history
- four JSON packs cover software delivery, finance operations, investment research, and
  corporate consulting; software full mode maps every current catalog department id
- consultant authors, the CEO, and currently seated department heads may propose minimal or
  full divisions; only CEO/admin companions may activate or deactivate
- activation commits missing departments/positions, links, pack skills, company learning
  assignments, a division-tagged floorplan, status, history, and events atomically
- deactivation fails closed while linked departments have open dispatches or cross-department
  requests; it does not retire shared department records
- authenticated pack/division lifecycle endpoints are available; Desk Corporate upgrades
  lists packs/divisions and provides propose/CEO-activate controls
- Tests: 7 focused Phase 7 tests and 315 full-discovery tests pass on Python 3.14.3;
  Alembic reports `0022_divisions` as head
- `scripts/check_bundle.py` is blocked by a pre-existing untracked
  `local repos/service-department/README.md` link to its missing `LICENSE`; Phase 7 does not
  modify or commit that unrelated local repository tree

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
- Corporate HQ Phase 6 added approval-gated HR staffing proposals and atomic hires

## Verify

```bash
.venv/bin/python -m unittest tests.test_divisions tests.test_staffing_proposals tests.test_floorplans tests.test_api tests.test_migrate -v
.venv/bin/python -m unittest discover -s tests
PYTHONPATH=. .venv/bin/alembic heads
PYTHONPATH=. .venv/bin/python scripts/check_bundle.py
```

## Next

Define the next governed Corporate HQ increment before extending furnishing or movement;
retain separate proposer/decider authority and keep visual presence derived from persisted
activity sessions.
