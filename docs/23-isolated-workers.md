# Isolated workers (M3)

Workers execute queued mock ChatDev work outside the control-plane process. They never receive SQLite paths, bearer tokens, or policy mutation APIs.

## Runtime modes

| Runtime | Status | Notes |
|---|---|---|
| `subprocess` | Implemented | Spawned child process; parent pumps a restricted gateway over a pipe |
| `container` | Fail-closed | Requires Docker and a built `fs-tech-ai-company-worker:local` image |

## Gateway allowlist

Workers may request only:

- `gateway_check` — authority recheck before effects
- `store_artifact` — write bytes under the task scratch root
- `execute_mock` — record a deterministic mock deliverable after checks pass
- `invoke_model` — mock profiles only; live providers remain `NotImplementedError`

Policy changes, pause, hire, QC, and other control-plane operations are denied.

## Control-plane API

```http
POST /api/v1/tasks/{task_id}/dispatch-worker
```

Payload fields (inside the standard command envelope):

- `worker_id` — lease owner (defaults to authenticated principal)
- `scratch_root` — writable directory for artifact bytes (defaults to a temp dir)
- `runtime` — `subprocess` (default) or `container`
- `approval` — optional approval id for gated actions

In-process `POST /api/v1/tasks/{task_id}/dispatch` remains available for local tests without isolation.

## Audit

`worker_runs` records runtime, scratch path, and completion status. Events: `worker.started`, `worker.finished`, `task.worker_completed`.

## Limits

Subprocess isolation is not a sandbox against a malicious process with host access. Container mode is the production path once an owner-built image exists. Live ChatDev, GitHub, and billed models still require owner credentials inside the gateway boundary.
