# Current handoff

Date: 2026-09-14. Version: **0.3.87**. State: **Consultant work-order measured
before/after merged to `main` (local; ahead of origin; not yet deployed).** Tip: **`9aa20b5`**
(merge of 0.3.87 ship `592cde7`).

## Merged on main (0.3.87)

- `company/measurements.py` — `capture_ops_metrics`, baseline/after persist, list/detail
  read helpers (five integer keys; idempotent phases).
- `alembic/versions/0029_work_order_measurements.py` — `work_order_measurements` table.
- Hooks on authorize and complete-outcome; `GET /api/v1/work-orders/measurements` and
  `GET /api/v1/work-orders/{id}/measurements`; desk `#consultant` Work-order measures +
  CEO Complete outcome; companion Home Needs-you awaiting after / delta cards.
- ADR-069; API contract; README + VERIFICATION; companion lockstep **0.3.87**.
- Prior: Finance open-next + pricing honesty (0.3.86), Desk remaining session gates (0.3.85).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **595 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- fs-dev health still reports **0.3.86** until deploy.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Push `main` and deploy to fs-dev when owner directs (Alembic **0029** on install).
Owner-directed follow-ups after Ship 2 / audit code-local.
