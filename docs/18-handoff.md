# Current handoff

Date: 2026-09-14. Version: **0.3.85**. State: **Desk remaining session gates
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`17d175c`** (post-deploy
handoff; merge `eed1154`).

## On main / fs-dev

- `company/service.py` — extended `setOrgMutateEnabled` for People/division dynamic
  chips and staffing scan; added `setDispatchEnrollEnabled` / `dispatchEnrollEnabled`
  composed with dormancy submit gating; session apply sets Finance (`company.pause`),
  Org (`organization.write`), and Dispatch (`project.enroll`).
- `tests/test_desk_remaining_session_gates.py` — source contracts + version **0.3.85**.
- ADR-067; README + VERIFICATION honesty; companion lockstep **0.3.85**.
- Prior on `main`: Desk corporate write gate (0.3.84), Org session gate (0.3.83),
  Finance init disable (0.3.82).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **576 tests, OK** (pre-merge).
- Gate module recheck after merge: `tests.test_desk_remaining_session_gates` OK.
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.85",...}` after
  `deploy_to_fs_dev.sh` + `sudo bash ~/fs-corporation-deploy/run-install.sh`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Ship 2 finance B + consultant B (brainstorm/plan separately).
