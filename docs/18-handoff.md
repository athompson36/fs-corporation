# Current handoff

Date: 2026-09-14. Version: **0.3.84**. State: **Desk corporate write forms
session gate on `feature/desk-org-corporate-write-gate`** (not merged to `main`;
no fs-dev deploy claim). Tip: **`3780654`**.

## On feature/desk-org-corporate-write-gate

- `company/service.py` — extends `organization.write` fail-closed gate to
  `#scorecard`, `#cross-department`, and `#corporate-upgrades`: three static
  submits + dynamic Close/Accept; per-section `data-org-write-notice`; extended
  `setOrgMutateEnabled` + `orgWriteEnabled`; 403 backup on Close/Accept.
- `tests/test_desk_org_corporate_write_gate.py` — source contracts + version
  **0.3.84**.
- ADR-066; version **0.3.84** (Python package and companion `package.json`
  lockstep).
- Prior on branch: Desk Organization session mutate gate (0.3.83 on `main`).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **567 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.84).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed companion/desk follow-ups (e.g. promotions/staffing session
gates).
