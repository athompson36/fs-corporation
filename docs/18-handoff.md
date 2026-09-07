# Current handoff

Date: 2026-09-07. Version: **0.3.52**. State: **Phase 1 department editing on feature/corporate-hq-phases**.

## Delivered in 0.3.52 (Phase 1)

- Runtime department/position CRUD: create, update, retire, reorder
- Non-destructive `seed_catalog` preserves custom and edited seed rows
- `department_revisions` audit trail; Alembic `0016_department_editing`
- Desk + companion create-department forms; org list shows origin/status/order

## Prior

- 0.3.51 org roster, head handoff, cross-department requests

## Verify

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

## Next

Phase 2 floorplans and department rooms per corporate HQ plan.
