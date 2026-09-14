# Current handoff

Date: 2026-09-14. Version: **0.3.89**. State: **Measurement hardening on `main` and
deployed to fs-dev.** Tip: **`d69fe8d`** (merge record; ship `2834239`).

## Merged on main (0.3.89)

- Co-commit `ensure_measurement` with new authorize/complete replay inserts.
- List filter: `json_extract(payload, '$.source') = 'consultant'`.
- Denied-scope GET test for measurements list.
- ADR-071. No Alembic. Companion lockstep **0.3.89**.
- Prior: provider invoices 0.3.88, consultant measurements 0.3.87.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **603 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- fs-dev health: `{"ok":true,"version":"0.3.89",...}`; no new Alembic (still **0030**).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed follow-ups (ChatDev-in-worker depth, provider CSV/PDF import, etc.).
