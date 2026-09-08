# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **P2 live ops on `feature/p2-live-ops`
(feeds + Models + ChatDev egress allowlist + secrets VAPID file honesty + consultant reviews read).**

## P2 on this branch

- Feed pause/revoke + companion Settings → Feeds (watchlists remain template-only).
- Companion Settings → Models (read-only profiles; global cents via Runtime).
- `FS_CORP_CHATDEV_WORKER_EGRESS` + host allowlist file; workers stay `--network none`
  unless mode=allowlist, file valid, and `FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK` set (ADR-037).
- Secrets-status treats VAPID `*_FILE` as configured.
- `GET /api/v1/consultant/reviews` for cooldown rows (no fake before/after metrics).

## Also on main

- P1 Settings platform (ADR-036).
- P0.2 M10 ops; dispatch recommend (ADR-035); companion scopes (ADR-034).

## Verification

- Targeted: `tests.test_feed_lifecycle`, `tests.test_chatdev_egress`, companion feed source test,
  `npm run build` — run full suite before merge.
- Do not commit `local repos/service-department/`.

## Next

1. Merge/push `feature/p2-live-ops` when owner requests; deploy to fs-dev.
2. On fs-dev ChatDev egress: create restricted Docker network + allowlist file before enabling mode.
3. **P3 Durable finance** (invoice/refunds/period rollover) — see production build-out plan.
