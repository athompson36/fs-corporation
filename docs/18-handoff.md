# Current handoff

Date: 2026-09-09. Version: **0.3.64**. State: **Deeper marketing redesign on
`feature/deeper-marketing-redesign`** (Task 1 + Task 2 complete; not yet merged to `main`).

## On feature/deeper-marketing-redesign

- Public `/welcome`: self-hosted Syne/Manrope woff2 fonts via `assets/welcome.css`; full-bleed
  constellation motif; intentional motion with `prefers-reduced-motion` respected; vertical scroll
  so CTAs stay reachable on small viewports.
- Desk HQ: `campaign` furniture glyph upgraded to podium + banner (persisted `market*` room types
  only).
- Companion remains at `/`; no Alembic (head `0028_remote_worker_jobs`).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **478 tests passed**.
- `cd companion && npm run build`: **OK**.
- Do not commit `local repos/service-department/`.

## Next

**Owner-directed backlog** — roadmap is clear; ask the owner for the next priority.
