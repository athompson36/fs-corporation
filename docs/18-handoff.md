# Current handoff

Date: 2026-09-08. Version: **0.3.62**. State: **Companion Finance UX polish merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.62`).

## On main / fs-dev

- `GET /api/v1/finance/billed-costs`: creditable billed lines with
  `remaining_creditable_cents`; default excludes fully credited rows; optional
  `include_fully_credited` and `limit`.
- Companion **Finance** sub-tabs: Overview · Invoices · Adjustments · Periods.
  Display uses `formatUsd`; API stays integer cents. Invoice expand via GET by id;
  refund picker (no paste-id); empty billed-cost list disables refund; confirm before
  period close; prefill next period. Segmented sub-nav with active state.
- ADR-038 consequences amended: companion may list creditable billed lines read-only.
- No new Alembic; head remains `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **474 tests passed**.
- `cd companion && npm run build`: **OK**.
- fs-dev health: **0.3.62**.
- Do not commit `local repos/service-department/`.

## Next

**TailscaleKit / second-host polish**, then deeper marketing redesign.
