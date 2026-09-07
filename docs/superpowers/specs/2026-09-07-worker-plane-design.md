# Design: Same-host worker plane on `.101`

Date: 2026-09-07. Status: **implemented** (v0.3.41).

## Goal

Make the reserved NIC (`FS_CORP_WORKER_NIC_IP`, typically `192.168.4.101`) a first-class **same-host worker plane** in status and ops docs: identity + health for operators, without changing container isolation or blocking dispatch when the NIC is missing.

Builds on ADR-016 / ADR-019 and [2026-09-02-gateway-egress-design.md](2026-09-02-gateway-egress-design.md). This is **not** a second physical host.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Topology | Same host: `.100` = LAN edge/API (Caddy); `.101` = worker plane identity + (when enabled) API gateway egress |
| Soft vs strict | Soft — missing/absent NIC does **not** refuse `runtime=container` or default container dispatch |
| Approach | Status API + runbook + verify helper (not remote Docker, not binding Docker to `.101`) |

## Architecture

```text
fs-dev (one machine)
├── eno1 192.168.4.100  — Caddy / companion edge
├── eno2 192.168.4.101  — worker plane identity
│                         (+ optional FS_CORP_GATEWAY_EGRESS=worker_nic for fs-corp UID)
├── systemd API 127.0.0.1:8000
└── Docker workers --network none + scratch gateway
    labels: fs.corp.worker_nic=<FS_CORP_WORKER_NIC_IP>
```

Containers remain `network_mode: none`. They do not listen on `.101`. The plane is an **operator identity and health signal**, plus the existing egress policy path for the API process.

## Components

### 1. `worker_plane` on `GET /api/v1/workers/status`

Always include:

```json
"worker_plane": {
  "mode": "same_host_nic",
  "ip": "192.168.4.101",
  "present": true,
  "state": "healthy",
  "reasons": []
}
```

| `state` | Condition |
|---|---|
| `healthy` | `FS_CORP_WORKER_NIC_IP` set and assigned on a local interface |
| `degraded` | IP set but not present on host |
| `unset` | env empty / whitespace |

`ip` is the configured string when set; `null` when unset. `present` is boolean (`false` when unset). `reasons` is a string list only when not `healthy` (e.g. `"FS_CORP_WORKER_NIC_IP unset"`, `"worker NIC IP not on host"`).

**Compatibility:** keep top-level `worker_nic_ip` / `worker_nic_present` when the env is set (same values as today). `worker_plane` is the structured view; do not remove the flat fields in this slice.

**Soft dispatch:** `container_dispatch_ready` stays Docker + scratch writable + image present only. Plane health does not affect that flag or `resolve_worker_runtime()`.

Implementation: `worker_plane_summary()` in `company/worker_status.py`, merged into `status_summary()`. Reuse `host_has_ipv4()`.

### 2. Verify helper

Extend `scripts/verify_fs_dev_workers.py`:

- Always print full `status_summary()` JSON (includes `worker_plane`).
- Exit `0` when `container_dispatch_ready`; exit `2` when not.
- If plane `state != "healthy"`, print a clear warning to stderr; do **not** change exit code by default.
- Optional `--require-plane`: if plane is not `healthy`, exit `3` (for operators who want a hard check later). Default off.

### 3. Docs

- `docs/25-fs-dev-deployment.md` — same-host worker plane on `.101`; distinguish from future dedicated second host.
- `docs/23-isolated-workers.md` — document `worker_plane`.
- `docs/16-api-contract.md` — field on `/workers/status`.
- Roadmap / handoff / README / capability notes as needed when implementing.
- Explicit non-claim: this slice does **not** deliver a separate worker machine.

## Error handling

- No new fail-closed paths for dispatch.
- Gateway egress readiness remains under `gateway_egress` (ADR-019); plane `degraded` is independent of `egress_active`.
- No new required env vars; plane IP is `FS_CORP_WORKER_NIC_IP`.

## Tests

`tests/test_worker_status.py` (extend):

1. NIC present → `worker_plane.state == "healthy"`, `present` true, empty `reasons`.
2. NIC set, `host_has_ipv4` false → `degraded` + reason; `container_dispatch_ready` may still be true when Docker/scratch/image stubs say so.
3. NIC unset → `state == "unset"`, `ip` null, `present` false.
4. Flat `worker_nic_*` still match when env set.

Optional: small unit check that `verify_fs_dev_workers` main returns 0 with degraded plane when dispatch ready (patch summary).

## Non-goals

- Second physical host / `DOCKER_HOST` remote dispatch
- Binding Docker daemon or worker containers to `.101` sockets
- Changing `--network none`, gateway allowlist, or ChatDev image egress
- Fail-closed container refusal when NIC absent
- TailscaleKit

## Acceptance

1. `GET /api/v1/workers/status` includes `worker_plane` with states above.
2. Soft mode: missing NIC does not block container dispatch readiness or default container runtime.
3. `scripts/verify_fs_dev_workers.py` surfaces plane; default exit ignores plane health; `--require-plane` exits 3 when not healthy.
4. Docs clarify same-host plane vs future second host.
5. Version **0.3.41**; handoff updated.

## Verify (after implement)

```bash
.venv/bin/python -m unittest tests.test_worker_status -v
.venv/bin/python scripts/verify_fs_dev_workers.py
# on fs-dev with both NICs:
curl -sH "Authorization: Bearer $TOKEN" http://192.168.4.100/api/v1/workers/status | jq .worker_plane
```
