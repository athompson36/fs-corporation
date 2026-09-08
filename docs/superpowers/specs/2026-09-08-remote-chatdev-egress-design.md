# Design: Remote ChatDev egress policy on claim

Date: 2026-09-08. Status: **implemented** in v0.3.61.

## Goal

When a remote pull agent runs containers (`FS_CORP_REMOTE_WORKER_RUNTIME=container`), apply the
**same company ChatDev egress setting** as same-host workers: the claim carries an egress
policy; the agent attaches an allowlisted Docker network only when locally ready; otherwise
it **fails the job**. When policy is `none`, behavior stays `--network none`.

Sequence after this track: P3 finance → TailscaleKit/second-host polish → deeper marketing.

## Locks

| Topic | Choice |
|---|---|
| Policy source | Control plane embeds egress on claim (B) |
| Agent not ready for allowlist | Fail job — complete `failed` (A) |
| When allowlist is sent | Always mirror company `FS_CORP_CHATDEV_WORKER_EGRESS` (A) |
| Approach | Claim embeds policy; agent validates then `docker run` (1) |
| Forbidden network names at CP | Coerce claim to `mode=none`, `docker_network=null` (not 422) |

## Non-goals

- Sending allowlist hostnames (or allowlist file contents) to the agent
- Remote `bridge` / `host` Docker networks
- Heartbeat-based placement for egress-ready hosts
- Changing same-host `ContainerWorkerRuntime` semantics
- Tracks 2–4 (finance, TailscaleKit, marketing redesign)
- Expanding remote gateway allowlist (`invoke_model` stays denied on relay)

## Claim `egress` object

Added to the host-token claim response (alongside `envelope`):

```json
{
  "mode": "none" | "allowlist",
  "docker_network": null | "string"
}
```

Construction:

1. `mode` = `egress_mode(company)` (`none` | `allowlist`; anything else → `none`).
2. If `mode == "allowlist"`: set `docker_network` from `FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK`.
3. If that name is missing/blank or in `{bridge, host}` (case-insensitive): coerce to
   `mode=none`, `docker_network=null`.
4. Never include `https_hosts` or allowlist file paths.

## Agent behavior (container runtime only)

| Claim policy | Action |
|---|---|
| `mode=none` | `docker run … --network none` (unchanged default) |
| `mode=allowlist` | Require: local allowlist file loads with ≥1 host; Docker network named
  `docker_network` exists; name not empty/bridge/host. Then `--network <docker_network>`.
  Otherwise `complete` with `status=failed` and a clear reason (no silent `none`). |
| Mock runtime | Ignore `egress`; keep mock-complete |

Still never forward `CHATDEV_ALLOW_CONTROL_PLANE`. Host-token gateway relay unchanged
(`gateway_check`, `execute_mock`, `store_artifact` only).

## Testing

- Claim returns `egress` with `mode`/`docker_network` keys; coerce cases covered.
- Agent: allowlist + ready → docker cmd includes expected `--network NAME`.
- Agent: allowlist + missing file/network → failed complete (no mock).
- Agent: `mode=none` → `--network none`.
- Mock path ignores egress.
- Prefer no live Docker/ChatDev in CI.

## Acceptance

1. Claim always carries `egress` mirroring company mode (with forbidden-name coerce).
2. Allowlist path uses the named network only when the agent is locally ready; else failed.
3. Mock / `mode=none` remain `--network none`.
4. No allowlist hostnames on the wire; ADR-046; version **0.3.61**; handoff next → P3 finance.

## Out of band

- Branch: `feature/remote-chatdev-egress` from `main`.
- No Alembic revision.
