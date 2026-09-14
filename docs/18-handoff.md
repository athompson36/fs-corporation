# Current handoff

Date: 2026-09-14. Version: **0.3.89**. State: **Measurement hardening on
`feature/measurement-hardening`; `main` remains 0.3.88.** Tip: **`f59f10c`**
(0.3.89 ship; branch HEAD may include handoff-only commits).

## Shipped on feature branch (0.3.89)

- Co-commit `ensure_measurement` baseline/after inside authorize/complete `tx()` blocks.
- `json_extract(wo.payload, '$.source') = 'consultant'` list filter (replaces LIKE).
- Denied-scope GET test: 403 without `consultant.read` or `company.read`.
- ADR-071. No Alembic; no UI/auth change.
- Prior on `main`: provider invoice allocations 0.3.88, consultant measurements 0.3.87.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **603 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Merge `feature/measurement-hardening` to `main` and deploy fs-dev when owner-ready.
Strongest remaining local-ish tracks: ChatDev-in-worker depth, provider CSV/PDF import,
or furnished-art / scheduled consultant triggers. Live blockers stay credentials / second
host / phone smoke.
