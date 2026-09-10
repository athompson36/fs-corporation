# Current handoff

Date: 2026-09-09. Version: **0.3.64**. State: **Deeper marketing redesign merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.64`).

## On main / fs-dev

- Public `/welcome`: self-hosted Syne/Manrope fonts, constellation motif, intentional
  motion with `prefers-reduced-motion`, vertical scroll for short viewports; CTAs to `/`
  and `/desk`; no company data.
- Desk HQ: `campaign` furniture is podium + banner for persisted `market*` room types.
- ADR-045 consequences amended; no Alembic (head `0028_remote_worker_jobs`).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **478 tests passed**.
- `cd companion && npm run build`: **OK**.
- fs-dev health: **0.3.64**; `/welcome` + `/static/welcome.css` + fonts **200**.
- Do not commit `local repos/service-department/`.

## Next

**Owner-directed** — roadmap tracks through marketing redesign are complete; pick the next
priority (or say what to tackle).
