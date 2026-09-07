# Current handoff

Date: 2026-09-07. Version: **0.3.52** (unchanged). State: **Corporate HQ Phase 3 implemented on feature/corporate-hq-phases**.

## Corporate HQ Phase 3 (no version bump)

- Alembic `0018_worker_identity`: employee profile fields, `sprite_sets`, and
  `worker_sprites`; two validated sets seed from `config/sprite-sets.json`
- HR/CEO-only sprite and profile mutations, with catalog validation for body, palette,
  accessory layer, and accessory value
- Worker cards join persisted identity, strengths/viewpoint, acquired skills, active
  position assignments, and an optional sprite; missing sprites remain null with explicit
  neutral-placeholder metadata
- Authenticated organization-read card API and organization-write sprite/profile APIs;
  core HR/CEO authorization remains authoritative
- Headquarters floorplan rooms expose department employees and optional sprites; Desk
  renders clickable SVG markers and fetches worker cards
- Companion `ApiClient` exposes card, sprite, and profile methods
- Tests: 21 focused integration tests and 284 full-discovery tests pass on Python 3.14.3;
  companion production build passes

## Prior

- Corporate HQ Phase 2 persisted floorplans/rooms and requirement warnings
- 0.3.52 Phase 1 runtime department/position editing and `0016_department_editing`
- 0.3.51 org roster, head handoff, cross-department requests

## Verify

```bash
.venv/bin/python -m unittest tests.test_worker_identity tests.test_floorplans tests.test_migrate -v
.venv/bin/python -m unittest discover -s tests
(cd companion && npm run build)
```

## Next

Define the next Corporate HQ phase before extending room furnishing or sprite animation;
continue projecting only persisted workers and operational state.
