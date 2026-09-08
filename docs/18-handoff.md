# Current handoff

Date: 2026-09-08. Version: **0.3.61**. State: **remote ChatDev egress policy implemented on
`feature/remote-chatdev-egress`**; not merged, pushed, or deployed.

## Implemented on this branch

- ADR-046: every remote claim carries `egress: {mode, docker_network}` without allowlist
  hostnames or file paths.
- Allowlist claims use the named network only when the agent has a non-empty local allowlist
  and Docker reports the network; otherwise completion fails with `remote_egress_unready`.
- Missing/blank, `bridge`, and `host` names coerce to none at claim; mock ignores egress;
  none-mode containers retain `--network none`.
- No new Alembic; head `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **471 passed**.
- `cd companion && npm run build`: passed for **0.3.61** (`generateSW`, 7 precache entries).
- Changed: claim policy/agent commits plus version, README, verification, API, roadmap,
  ADR-046, handoff, implementation plan, and implemented design spec.
- Do not commit `local repos/service-department/`.

## Next

Implement **P3 finance**. Merge, push, and deploy 0.3.61 only on owner request.
