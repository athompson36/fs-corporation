# Current handoff

Date: 2026-09-14. Version: **0.3.83**. State: **Desk Organization session
mutate gate merged to `main`, pushed, and deployed to fs-dev.** Tip:
**`493f9d8`**.

## On main / fs-dev

- `company/service.py` — `#org-scope-notice`; seven Organization Manage submits
  ship `disabled`; `setOrgMutateEnabled`; shared `/api/v1/session` applies
  `company.pause` (Finance) and `organization.write` (Org); `submitOrgCommand`
  403 → disable org.
- `tests/test_desk_org_session_gate.py` — source contracts + version **0.3.83**.
- ADR-065; version **0.3.83** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Finance init-time disable (0.3.82), companion tab URL
  flash (0.3.81).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **562 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.83).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.83",...}`; desk
  serves `org-scope-notice` and `setOrgMutateEnabled`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed companion/desk follow-ups (e.g. other desk sections that still
only 403-gate).
