# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **P1 Settings platform slice A merged to
`main`, pushed, and deploying to fs-dev.**

## P1 Settings platform slice A (on main)

- `company_settings` SQLite overlay + catalog; effective resolution overlay → env → default.
- APIs: `GET/PATCH /api/v1/settings`, `POST /api/v1/settings/reset`,
  `GET /api/v1/settings/secrets-status` (ADR-036).
- Companion Settings: Connection, **Runtime**, read-only **Host**, **Secrets** status.
- Rate-limit overlays apply at API process start (`restart_required`); default worker
  runtime catalog default is `subprocess` (fs-dev env still sets `container`).

## Also on main

- P0.2 M10 ops (idempotency prune, model/benchmark reads, companion forms, learning fetch).
- Dispatch options + recommend autofill (ADR-035).
- Companion iPhone scopes / paired-admin ops / five-tab layout (ADR-034).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **382 passed**
- `cd companion && npm run build`: passed

## Production roadmap

Next: **P2 Live ops** or expand Settings sections — see
[docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. After deploy: open https://192.168.4.100 companion Settings → Runtime / Secrets.
2. Owner chooses P2 vs Settings expansion.
3. Do not commit `local repos/service-department/`.
