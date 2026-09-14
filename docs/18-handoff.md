# Current handoff

Date: 2026-09-14. Version: **0.3.87**. State: **Consultant work-order measured
before/after on `main` and deployed to fs-dev.** Tip: **`60914c9`**
(0.3.87 merge record; ship `592cde7`).

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
- fs-dev health: `{"ok":true,"version":"0.3.87",...}`; Alembic **0029** applied.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed follow-ups from the refreshed feature-completion audit (canvas at
`canvases/feature-completion-audit.canvas.tsx`). Strongest remaining local-ish tracks:
real invoice/refund modeling (no invented cents), measurement deferred nits, or
ChatDev-in-worker depth. Live blockers stay credentials / second host / phone smoke.

