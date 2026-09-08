# Design: Auto remote worker placement (opt-in)

Date: 2026-09-08. Status: **implemented** (v0.3.60).

## Goal

When `FS_CORP_PREFER_REMOTE_WORKERS` is enabled, `dispatch-worker` without `worker_host_id` places work on a `ready` remote host (stable order). Explicit `worker_host_id` always wins. Default remains same-host.

## Locks

| Topic | Choice |
|---|---|
| Prefer remotes | Only when Settings/env flag is true (2) |
| Multi-ready pick | First by `(label, id)` (A) |
| No ready host | Fail closed (422) — no silent local fallback |

## Behavior

1. Payload includes `worker_host_id` → existing explicit remote enqueue (host must be ready).
2. Else if `effective_setting("FS_CORP_PREFER_REMOTE_WORKERS")` is true:
   - List hosts with `state == ready`, sort by label then id, pick first.
   - If none → `ValueError` / HTTP 422.
   - Enqueue remote job; result includes `worker_host_id` and `placement: "auto"`.
3. Else → same-host `resolve_worker_runtime` path unchanged.

## Settings

Add to catalog:

- Key: `FS_CORP_PREFER_REMOTE_WORKERS`
- Type: bool, default `false`, editable, not restart-required
- Description: Prefer ready remote worker hosts when dispatch omits worker_host_id

## Non-goals

- Round-robin / load balancing
- Auto placement overriding explicit id
- Silent fallback to local when prefer is on but no remotes ready
- Tracks A (remote container) and C (marketing) — separate specs

## Testing

- Flag off + no id → local (existing behavior)
- Flag on + ready host → remote job; chosen id is first by label
- Flag on + no ready → 422
- Explicit `worker_host_id` with flag on/off → that host

## Acceptance

1. Opt-in only; fail closed when prefer on and no ready host.
2. Explicit id unchanged.
3. ADR-043; version bump; handoff notes B done, next A.
