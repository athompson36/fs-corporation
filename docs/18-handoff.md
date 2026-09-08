# Current handoff

Date: 2026-09-08. Version: **0.3.58**. State: **Track A remote container-on-agent
merged to `main`, pushed, and deploying to fs-dev.**

## On main / fs-dev

- Claim returns worker `envelope`; host-token `gateway` + `renew`; optional complete
  `runtime=remote_container` (ADR-044).
- Remote gateway allowlist: `gateway_check`, `execute_mock`, `store_artifact` only (no
  `invoke_model` relay).
- Failed remote complete releases non-cancelled queue leases for re-dispatch.
- Agent opt-in: `FS_CORP_REMOTE_WORKER_RUNTIME=container` → `--network none` + relayed
  gateway; default remains mock-complete. Fail closed without Docker/image.
- No new Alembic; head remains `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **455 passed** before merge.
- Do not commit `local repos/service-department/`.

## Next

1. **Track C — marketing layout** (approach approved: C1 `/welcome` FastAPI landing, then
   C2 marketing HQ furniture kind). Design sections / spec not written yet.
2. Track B automatic placement may still be in git stash / `feature/auto-remote-placement`;
   not part of 0.3.58.
