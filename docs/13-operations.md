# Operations and recovery

## Local starter

Run `python3 -m company demo`, `status` or `audit` from the repository root. `--db PATH` selects the database. All actions are offline. State is saved immediately through SQLite transactions. The completed demo can be repeated without duplicating its finished project. Use a new database path to restart the fixture from scratch.

Use `python3 -m unittest discover -s tests -v` for logic checks and `python3 scripts/check_bundle.py` for package/config links. The demo CLI still uses the standard library. The loopback control service requires `pip install -e .` (FastAPI, Uvicorn, Alembic).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m company backup --dest .local/company.backup.db
python3 -m company restore --dest .local/company.backup.db --db .local/restored.db
alembic upgrade head
```

By default the control service **refuses non-loopback binds** during local development. For Tailscale-only dev access, start with `--allow-remote` on a tailnet IP (see [24-mobile-companion.md](24-mobile-companion.md)); that shortcut is not the fs-dev production path.

**Production (fs-dev)** keeps the API on **`127.0.0.1:8000`** under systemd. **Caddy** listens on HTTPS (443) at the LAN edge, serves the companion PWA, and reverse-proxies `/api/*` to loopback. UFW must not expose port 8000 on external interfaces. See [25-fs-dev-deployment.md](25-fs-dev-deployment.md).

Owner bootstrap writes `.local/owner.token` (mode 600) in dev; production uses `/etc/fs-corporation/owner.token`. `.env.example` is a future live-integration template and is not loaded by the core. Alembic revisions through `0009_slo_observations` add skill, QC, employee, worker, companion, feed, push, and SLO tables; restore from backup rather than downgrading.

## Budgets

Reference costs are nonnegative integer USD cents in a synthetic lifetime ledger. Do not display them as actual billed API spend. Production tracks estimate, reservation, actual reconciliation and credits/refunds separately. Enforce company, department, project and task caps transactionally. Period rollover is explicit and auditable, never achieved by amending policy.

Use maximum output tokens, request limits and timeouts to bound model calls. Actual provider bills can arrive late; retain a reconciliation margin and stop dispatch if unreconciled exposure reaches the limit. A failed call may still be billed.

## Pausing and revocation

The core's CEO pause blocks new mock dispatch and construction. Existing idempotent task lookups may still return their prior result; that does not rerun an action. Policy removal/expiry blocks subsequent execution. Production additionally cancels queued work, signals running leases and records unavoidable in-flight results.

## Backups

Use SQLite's backup API for a consistent local copy. Do not blindly copy an actively written database file. Include configuration and artifact manifests in a real backup policy; keep secrets in a dedicated secret store. Test restore to a new path and verify status/audit before switching over. Do not upload project secrets or private artifacts in a generic starter ZIP.

## Production worker reliability

Durable leases with heartbeat and expiry; transactional outbox; explicit max attempts; exponential retry with jitter; poison-message quarantine; dependency cancellation; bounded provider concurrency. Classify failures as validation, permission, transient provider, quota, execution, review or cancellation. Retry only recoverable failures and recheck authority before effects.

## Observability

Correlate company, project, task, attempt, actor, policy version, model profile, source signal and external action. Track accepted deliverables, review burden, latency, errors, cost/reservation exposure, blocked work and tool denials. Provide human-readable status and exportable audit records.

`GET /api/v1/slos` lists the catalog (`api.health_availability`, `api.request_latency_ms`, `worker.dispatch_success`, `queue.blocked_count`). Each item is `unmeasured` until the CEO records a sourced, windowed observation via `POST /api/v1/slos/{id}/observations`. Do not invent production capacity numbers or mark an SLO met/breached without a recorded sample.

## Incident runbook

Pause dispatch → revoke affected capabilities/keys → isolate workers → preserve evidence → identify completed external effects → reconcile repository/service state → restore/rollback approved artifacts → test → explicitly resume. Do not erase history or reset budgets to hide an incident.
