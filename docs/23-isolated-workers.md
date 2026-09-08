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
- `invoke_model` — mock profiles always; a live provider runs only when its credential env var is present in the control-plane process, and raises `NotImplementedError` otherwise. Container workers have no network, so a live call is served by the parent gateway, never from inside the container.

Policy changes, pause, hire, QC, and other control-plane operations are denied.

## Control-plane API

```http
POST /api/v1/tasks/{task_id}/dispatch-worker
```

Payload fields (inside the standard command envelope):

- `worker_id` — lease owner (defaults to authenticated principal)
- `scratch_root` — writable directory for artifact bytes (defaults to a temp dir)
- `runtime` — `subprocess` or `container`. Omitted, it follows `FS_CORP_DEFAULT_WORKER_RUNTIME` (`subprocess` unless set); fs-dev sets `container` and fails closed with 422 when container dispatch is not ready.
- `approval` — optional approval id for gated actions

In-process `POST /api/v1/tasks/{task_id}/dispatch` remains available for local tests without isolation.

## Audit

`worker_runs` records runtime, scratch path, and completion status. Events: `worker.started`, `worker.finished`, `task.worker_completed`.

## Limits

Subprocess isolation is not a sandbox against a malicious process with host access. Container mode uses `network_mode: none` and a scratch-directory gateway so the child still cannot open the control-plane database. On fs-dev, `FS_CORP_DEFAULT_WORKER_RUNTIME=container` makes container the default when Docker/image/scratch are ready; `/api/v1/workers/status` reports `worker_plane` (same-host NIC identity: `healthy` / `degraded` / `unset`), whether `FS_CORP_WORKER_NIC_IP` (`.101`) is present as flat `worker_nic_*`, and whether `FS_CORP_GATEWAY_EGRESS=worker_nic` policy routing is active for the API user. Workers still do not attach to that NIC; plane health is soft and does not block container dispatch. Live ChatDev, GitHub, and billed models still require owner credentials inside the gateway boundary.

## Remote pull agent (v1)

Registered hosts (`worker_hosts`) may receive work when `dispatch-worker` includes
`worker_host_id` and the host is `ready`. The control plane enqueues `remote_worker_jobs`;
`scripts/remote_worker_agent.py` heartbeats, claims, and mock-completes with the host token.
Omitting `worker_host_id` keeps same-host subprocess/container dispatch. Remote Docker on the
agent host is not implemented yet (ADR-042).

Optional ChatDev in the worker image: build with `--build-arg CHATDEV_ENABLE=1` (or `FS_CORP_WORKER_CHATDEV=1` via `install.sh`). The image records `org.fs_corporation.chatdev_enable` and `org.fs_corporation.chatdev_pin` labels; `GET /api/v1/chatdev/status` exposes them as `worker_image_chatdev` without running a container. Default builds stay mock-only (`enabled: false`). Container dispatch does not forward `CHATDEV_ALLOW_CONTROL_PLANE` from the host; the worker entrypoint sets `CHATDEV_HOME` only when `/opt/chatdev/runtime/sdk.py` exists.
