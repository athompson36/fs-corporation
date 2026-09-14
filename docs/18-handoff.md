# Current handoff

Date: 2026-09-14. Version: **0.3.85**. State: **Desk remaining session gates on
branch `feature/desk-remaining-session-gates`.** Tip: *(fill after commit)*.

## On feature/desk-remaining-session-gates

- `company/service.py` — extended `setOrgMutateEnabled` for People/division dynamic
  chips and staffing scan; added `setDispatchEnrollEnabled` / `dispatchEnrollEnabled`
  composed with dormancy submit gating; session apply sets Finance (`company.pause`),
  Org (`organization.write`), and Dispatch (`project.enroll`).
- `tests/test_desk_remaining_session_gates.py` — source contracts + version **0.3.85**.
- `tests/test_desk_org_corporate_write_gate.py` — softened version lockstep regex.
- ADR-067; version **0.3.85** (Python package and companion `package.json`
  lockstep); README + VERIFICATION honesty refresh.
- Prior on branch: Desk corporate write forms session gate (0.3.84), Organization
  session gate (0.3.83), Finance init disable (0.3.82).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **576 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.85).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Ship 2 finance B + consultant B (brainstorm/plan separately).
