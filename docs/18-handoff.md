# Current handoff

Date: 2026-09-14. Version: **0.3.83**. State: **Desk Organization session mutate
gate on `feature/desk-org-session-gate`** (not merged to `main`; no fs-dev deploy
claim). Tip: **`c00ff86`**.

## On feature/desk-org-session-gate

- `company/service.py` — Organization Manage in `#departments` ships seven submit
  chips `disabled`; `#org-scope-notice` visible from first paint; init
  `setOrgMutateEnabled(false)`; shared `GET /api/v1/session` applies Finance
  (`company.pause`) and Org (`organization.write`); `submitOrgCommand` 403
  backup disables org mutates.
- `tests/test_desk_org_session_gate.py` — source contracts + version **0.3.83**.
- ADR-065; version **0.3.83** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Finance init-time mutate disable (0.3.82), companion
  tab/mode URL flash (0.3.81), Desk Finance polish (0.3.80).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **562 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.83).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed companion/desk follow-ups.
