# Current handoff

Date: 2026-09-14. Version: **0.3.88**. State: **Provider invoice allocations merged to
`main` (pushing/deploying).** Tip: **`daed4c2`** (merge of 0.3.88 ship `ddbfdde`).

## Merged on main (0.3.88)

- Alembic **0030** — `provider_invoices` + `provider_invoice_allocations`.
- `company/finance.py` — create/list/get/allocate/void; summary
  `provider_invoice_variance_cents` (informational; does not change net billed).
- API under `/api/v1/finance/provider-invoices`; desk `#budget` + companion Finance
  Browse/Manage `provider`; urlState allowlists.
- ADR-070. Immutable `billed_costs`; no Stripe; no auto-adjustments.
- Prior: consultant measurements 0.3.87, finance open-next 0.3.86, desk gates 0.3.85.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **600 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Deploy to fs-dev (Alembic **0030**). Refresh feature-completion audit canvas after
deploy. Owner-directed follow-ups.
