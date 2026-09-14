# Current handoff

Date: 2026-09-14. Version: **0.3.88**. State: **Provider invoice allocations on
`feature/provider-invoice-allocations` ready to merge.** Tip: pending ship commit
(0.3.88 ship; branch HEAD may include handoff-only commits).

## On branch (0.3.88)

- `company/finance.py` — `create_provider_invoice`, `allocate_provider_invoice`,
  `void_provider_invoice`, list/detail helpers; informational
  `provider_invoice_variance_cents` on `finance_summary`.
- `alembic/versions/0030_provider_invoices.py` — `provider_invoices` +
  `provider_invoice_allocations` tables.
- Five finance API routes under `/api/v1/finance/provider-invoices`; desk `#budget`
  list/forms/expand/void; companion Finance Browse + Manage `provider` group.
- ADR-070; API contract; README + VERIFICATION; companion lockstep **0.3.88**.
- Prior on main: Consultant measured before/after (0.3.87), Finance open-next (0.3.86).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **600 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed follow-ups from the refreshed feature-completion audit (canvas at
`canvases/feature-completion-audit.canvas.tsx`). Strongest remaining local-ish tracks:
provider CSV/PDF import, refunds beyond partial_credit, measurement deferred nits, or
ChatDev-in-worker depth. Live blockers stay credentials / second host / phone smoke.
Refresh audit canvas after merge+deploy.
