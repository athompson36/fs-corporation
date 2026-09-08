# Current handoff

Date: 2026-09-08. Version: **0.3.62**. State: **Companion Finance UX polish on
`feature/finance-ux-polish`** (not yet merged to `main` / fs-dev).

## On feature/finance-ux-polish

- `GET /api/v1/finance/billed-costs`: creditable billed lines with
  `remaining_creditable_cents`; default excludes fully credited rows; optional
  `include_fully_credited` and `limit`.
- Companion **Finance** sub-tabs: Overview · Invoices · Adjustments · Periods.
  Display uses `formatUsd`; API stays integer cents. Invoice expand via GET by id;
  refund picker (no paste-id); empty billed-cost list disables refund; confirm before
  period close; prefill next period.
- ADR-038 consequences amended: companion may list creditable billed lines read-only.
- No new Alembic; ADR-038 net/gross adjustment math unchanged.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **474 tests passed**.
- `cd companion && npm run build`: **OK** (TypeScript and Vite production build;
  35 modules transformed).
- Do not commit `local repos/service-department/`.

## Next

**TailscaleKit / second-host polish**, then deeper marketing redesign.
