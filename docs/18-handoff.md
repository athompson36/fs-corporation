# Current handoff

Date: 2026-09-08. Version: **0.3.56**. State: **Remote pull agent merged to `main`,
pushed, and deployed to fs-dev.**

## On main / fs-dev

- Alembic `0028_remote_worker_jobs`; explicit `worker_host_id` enqueue (ADR-042).
- Host-token claim/complete; `scripts/remote_worker_agent.py`.
- Default dispatch remains same-host.

## Verification

- Health **200**, version **0.3.56**; alembic **`0028_remote_worker_jobs`**.
- Do not commit `local repos/service-department/`.
- On `feature/remote-container-on-agent`, Task 4 review fixes make the gateway
  pump renew idle leases, detect dead containers promptly, and convert
  post-claim container setup errors into failed completions.
- Review-fix verification: focused **26 tests passed**; full **452 tests passed**.

## Next

1. Follow-ons: remote container-on-agent, auto placement, or marketing layout.
