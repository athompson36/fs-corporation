# Current handoff

Date: 2026-09-08. Version: **0.3.53**. State: **P2 live ops merged to `main`, pushing, and deploying to fs-dev.**

## P2 Live ops (on main)

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

- `.venv/bin/python -m unittest discover -s tests`: **396 passed**
- `cd companion && npm run build`: passed
- Do not commit `local repos/service-department/`.

## Next

1. Smoke companion Settings → Feeds / Models / Secrets on https://192.168.4.100.
2. ChatDev egress on fs-dev only after restricted Docker network + allowlist file exist.
3. **P3 Durable finance** (invoice/refunds/period rollover).
