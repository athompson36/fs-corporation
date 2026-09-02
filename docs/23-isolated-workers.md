# Isolated workers (M3)

Workers execute queued mock ChatDev work outside the control-plane process. They never receive SQLite paths, bearer tokens, or policy mutation APIs.

## Runtime modes

| Runtime | Status | Notes |
|---|---|---|
| `subprocess` | Implemented | Spawned child process; parent pumps a restricted gateway over a pipe |
| `container` | Implemented locally via file gateway | Requires Docker (or a test double) and a built `fs-corporation-worker:local` image; parent pumps `gw-request.json` / `gw-response.json` on the scratch volume |

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

Subprocess isolation is not a sandbox against a malicious process with host access. Container mode uses `network_mode: none` and a scratch-directory gateway so the child still cannot open the control-plane database. On fs-dev, `FS_CORP_DEFAULT_WORKER_RUNTIME=container` makes container the default when Docker/image/scratch are ready; `/api/v1/workers/status` reports whether `FS_CORP_WORKER_NIC_IP` (`.101`) is present and whether `FS_CORP_GATEWAY_EGRESS=worker_nic` policy routing is active for the API user. Workers still do not attach to that NIC. Live ChatDev, GitHub, and billed models still require owner credentials inside the gateway boundary.
