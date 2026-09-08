# Current handoff

Date: 2026-09-08. Version: **0.3.59**. State: **Track C marketing layout is complete
on `feature/marketing-layout`**. It has not been merged, pushed, or deployed.

## On the feature branch

- Public `GET /welcome` returns a cosmic-glass FastAPI landing with CTAs to the companion
  at `/` and CEO desk at `/desk`; it is authentication- and rate-limit-exempt.
- fs-dev Caddy proxies exact path `/welcome` to FastAPI before the companion SPA catch-all.
- Desk HQ maps persisted room types containing `market` to geometric `campaign` furniture.
- ADR-045 records the choice. The companion remains at `/`; no operational state is invented.
- No new Alembic; head remains `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **458 passed**.
- `cd companion && npm run build`: **passed** for companion 0.3.59 (`generateSW`).
- The suite emitted existing FastAPI/httpx deprecation, SQLite resource, owner-config, and
  missing local worker-NIC warnings; none failed the run.
- Do not commit `local repos/service-department/`.

## Next

1. Recover and review **Track B automatic remote-host placement** if it remains in a stash
   or on `feature/auto-remote-placement`.
2. If Track B is unavailable or intentionally deferred, the owner selects the next roadmap item.
