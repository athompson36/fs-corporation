# Current handoff

Date: 2026-09-08. Version: **0.3.56**. State: **Remote pull agent on
`feature/remote-worker-agent` (ready to merge when owner asks).**

## On this branch

- Alembic `0028_remote_worker_jobs`; explicit `worker_host_id` enqueue (ADR-042).
- Host-token list/claim/complete; `scripts/remote_worker_agent.py` mock loop.
- Same-host dispatch unchanged when `worker_host_id` omitted.

## Verification

- Run: `.venv/bin/python -m unittest discover -s tests`
- Do not commit `local repos/service-department/`.

## Next

1. Merge / push / deploy when owner requests (migration `0028`).
2. Follow-on: remote container gateway on agent; auto placement; marketing layout.
