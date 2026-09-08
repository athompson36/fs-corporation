# Design: Companion Finance UX polish

Date: 2026-09-08. Status: **implemented** (v0.3.62 on `feature/finance-ux-polish`).

## Goal

Make the companion **Finance** tab operable for day-to-day CEO use without changing ADR-038
money rules: sub-tabs, honest dollar display, invoice line detail, billed-cost picker, and a
clearer budget-period flow. Totals remain API-only; the UI never invents operational or
financial state.

Original P3 durable finance (invoices, adjustments, period close, `/api/v1/finance/*`, companion
tab) already shipped. This track is **UX polish + one read API**.

Sequence after this track: TailscaleKit / second-host polish → deeper marketing redesign.

## Locks (owner brainstorming)

| Topic | Choice |
|---|---|
| Intent | Polish companion Finance UX (not new money model) |
| Depth | Heavy — layout refactor / sub-tabs + medium polish |
| Sub-tabs | Overview · Invoices · Adjustments · Periods |
| Billed-line source | `GET /api/v1/finance/billed-costs` with `remaining_creditable_cents` |
| Approach | Companion-first + thin list API (no workspace aggregate) |

## Non-goals

- Desk Finance surface
- PDF invoices, Stripe / provider import, payment rails
- Alembic / schema changes; mutating `billed_costs`
- Changing net/gross/adjustment math or mixing into `simulated_spend_cents`
- Silent calendar auto-rollover
- Forecast engine
- A new ADR number (amend ADR-038 consequences only)

## Architecture

### Backend

Add `list_billed_costs(company, *, limit=100, include_fully_credited=False)` in
`company/finance.py`, reusing `remaining_creditable`.

- Default: only rows with `remaining_creditable_cents > 0`, newest `recorded_at` first.
- Optional query `include_fully_credited=1` includes remaining `0` for audit.
- Cap with `limit` (default 100, max 500).

Each item:

```json
{
  "id": "...",
  "recorded_at": "...",
  "amount_cents": 0,
  "remaining_creditable_cents": 0,
  "provider": "...",
  "profile_id": "...",
  "source": "...",
  "task_id": null
}
```

Route:

| Method | Path | Scope | Behavior |
|---|---|---|---|
| GET | `/api/v1/finance/billed-costs` | company.read | List as above; query `include_fully_credited`, `limit` |

No finance write-path changes. Existing invoice/adjustment/period routes unchanged.

Thin wrappers on `Company` + route in `company/service.py`.

### Companion

Extract Finance UI from `App.tsx` into `companion/src/FinancePanel.tsx`,
receiving `api`, scopes, and existing status/action helpers.

Internal sub-nav (not top-level companion tabs):

1. **Overview** — gross / adjustments / net / revenue from `GET /finance/summary`; open budget
   period when present. Copy clarifies integer cents vs `$` display.
2. **Invoices** — list; expand/select loads `GET /finance/invoices/{id}` and shows snapshot
   lines. Create form uses `datetime-local` (and optional month preset) → ISO for
   `POST /finance/invoices`.
3. **Adjustments** — list; form selects from billed-costs list (remaining > 0). Show remaining
   on the selected line. Void ignores amount; partial requires amount ≤ remaining (client
   block). Server remains authoritative. If no creditable lines: disable submit and show
   “no creditable lines” (no paste-id fallback in this slice).
4. **Periods** — list with open/closed; **confirm** before close; set form with datetime +
   presets; after successful close, focus/prefill next period (`period_start` = closed
   `period_end`).

Shared `formatUsd(cents: number): string` for display only. API request/response bodies stay
integer USD cents.

On Finance tab enter (and after mutations): parallel load summary, invoices, adjustments,
periods, billed-costs.

Mutate controls remain gated on `company.pause` (+ existing CEO enforcement server-side).

### Data flow

```text
Finance tab → Promise.all(summary, invoices, adjustments, periods, billed-costs)
           → render sub-tab from API fields only
mutate     → existing POST → reload parallel set
```

## Failure modes

| Case | Result |
|---|---|
| Missing `company.read` | Load fails; show error; do not invent zero totals |
| Non-CEO mutate | 403; forms gated in UI |
| Empty creditable list | Adjustments submit disabled + explicit message |
| Partial ≤ 0 or > remaining | Client block; server `ValueError` |
| Close already-closed period | Server fail closed; confirm only offered for open |
| Invalid / empty datetime | Do not POST |
| Invoice empty window | Existing server reject |

## Testing

- `tests/test_durable_finance.py`: remaining math on list; default excludes fully credited;
  `include_fully_credited`; HTTP via `owner_client`.
- `tests/test_companion_api.py`: client method `financeBilledCosts`, import/path
  `FinancePanel`, and sub-tab labels Overview / Invoices / Adjustments / Periods.
- `cd companion && npm run build`
- `.venv/bin/python -m unittest discover -s tests` before merge

## Docs / version

- `docs/16-api-contract.md` — add billed-costs row
- `docs/24-mobile-companion.md` — Finance sub-tabs honesty
- `docs/14-roadmap.md` / capability notes — mark finance UX polish
- `docs/18-handoff.md` — next → TailscaleKit / second-host
- Amend ADR-038 consequences with one sentence: companion may list creditable billed lines
  via read API (no new money model)
- Version **0.3.62** (`company/__init__.py`, companion package if versioned there)

Do not commit `local repos/service-department/`.

## Acceptance

1. Finance tab exposes Overview / Invoices / Adjustments / Periods; totals only from API.
2. Invoice expand shows persisted snapshot lines.
3. Refund picker lists only remaining > 0 by default; void/partial still server-authoritative.
4. Period close requires confirm; next-period form prefills from closed end.
5. No Alembic; ADR-038 net/gross rules unchanged.
6. Docs and handoff point to TailscaleKit track next.
