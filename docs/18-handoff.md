# Current handoff

Date: 2026-09-08. Version: **0.3.59**. State: **Track C marketing layout merged to
`main`, pushed, and deploying to fs-dev.**

## On main / fs-dev

- Public `GET /welcome` (cosmic-glass FastAPI landing; CTAs to `/` and `/desk`; rate-limit
  exempt). Caddy proxies `/welcome` before the SPA catch-all.
- Desk HQ maps room types containing `market` to `campaign` furniture (ADR-045).
- Companion remains at `/`. No new Alembic; head `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **458 passed** before merge.
- Do not commit `local repos/service-department/`.

## Next

1. Recover and review **Track B automatic remote-host placement** (stash /
   `feature/auto-remote-placement`) if still desired.
2. Otherwise owner picks the next roadmap item.
