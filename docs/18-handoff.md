# Current handoff

Date: 2026-09-14. Version: **0.3.84**. State: **Desk corporate write forms
session gate merged to `main`, pushed, and deployed to fs-dev.** Tip:
**`c45649a`**.

## On main / fs-dev

- `company/service.py` — extended `setOrgMutateEnabled` / `orgWriteEnabled`;
  per-section `data-org-write-notice` in scorecard / cross-department /
  corporate-upgrades; Create objective / cross-dept / Propose submits ship
  `disabled`; Close/Accept use `data-org-write` + 403 fail-closed.
- `tests/test_desk_org_corporate_write_gate.py` — source contracts + version
  **0.3.84**.
- ADR-066; version **0.3.84** (Python package and companion `package.json`
  lockstep).
- Prior on `main`: Desk Organization session gate (0.3.83), Finance init
  disable (0.3.82).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **567 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.84).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.84",...}`; desk
  serves `desk-org-create-objective-submit` and `data-org-write-notice`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: division Activate / promotions / staffing / dispatch session
gates; or other companion/desk follow-ups.
