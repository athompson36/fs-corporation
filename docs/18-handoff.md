# Current handoff

Date: 2026-09-14. Version: **0.3.87**. State: **Consultant work-order measured
before/after on branch `feature/consultant-work-order-measurements`.** Tip: **`592cde7`**
(0.3.87 ship; branch HEAD may include handoff-only commits).

## On feature branch

- `company/measurements.py` — `capture_ops_metrics`, baseline/after persist, list/detail
  read helpers (five integer keys; idempotent phases).
- `alembic/versions/0029_work_order_measurements.py` — `work_order_measurements` table.
- `company/core.py`, `company/consultant.py` — hooks on authorize and complete-outcome.
- `company/service.py` — `GET /api/v1/work-orders/measurements` and
  `GET /api/v1/work-orders/{id}/measurements`; desk `#consultant` Work-order measures +
  CEO Complete outcome chip.
- `companion/src/HomePanel.tsx`, `companion/src/api/client.ts` — Home Needs-you awaiting
  after / delta cards.
- `tests/test_work_order_measurements.py`, `tests/test_desk_consultant_measurements.py`.
- ADR-069; API contract measurement rows; README + VERIFICATION honesty; companion lockstep
  **0.3.87**.
- Prior on `main`: Finance open-next + pricing honesty (0.3.86), Desk remaining session
  gates (0.3.85).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **595 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Ship 2 / audit code-local complete; owner-directed follow-ups.
