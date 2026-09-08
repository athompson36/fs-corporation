# Design: P3 Durable finance

Date: 2026-09-08. Status: **approved** (owner 2026-09-08). Plan: `docs/superpowers/plans/2026-09-08-p3-durable-finance.md`.

## Goal

Give the owner durable, auditable finance controls on top of ADR-026 billed cost / revenue:

1. **Internal invoices** — window snapshots of billed usage (not Stripe/provider import).
2. **Refunds** — void whole billed rows **or** partial credit adjustments; never delete billed rows.
3. **Period rollover** — explicit CEO close/open of budget periods with frozen snapshots.
4. **Companion Finance UX** — list/create invoices, post refunds, manage budget periods.

Defer to a later thin follow-on: `choose_model` benchmark use and work-order replay ledger.

Owner choices locked in brainstorming:

| Topic | Choice |
|---|---|
| Invoice meaning | Internal owner invoices (window snapshots) |
| Packaging | Full plan; implement A→D; defer benchmarks + replay |
| Refunds | Both void whole rows **and** partial credits |
| Architecture | Append-only adjustments; billed_costs immutable |

## Non-goals

- Stripe / provider invoice import or live payment rails.
- Mixing billed/refund totals into `simulated_spend_cents`.
- Deleting or rewriting `billed_costs` rows.
- Silent calendar auto-rollover.
- Forecast engine, PDF polish, choose_model benchmarks, work-order replay (follow-on).

## Slice map

```mermaid
flowchart LR
  A[A Invoices] --> B[B Refunds]
  B --> C[C Period rollover]
  C --> D[D Companion Finance UX]
```

| Slice | Deliverable |
|---|---|
| **A** | `invoices` table + create/list/get; snapshot of billed line ids + amounts in window |
| **B** | `finance_adjustments` (void / partial_credit); net billed on `status()` |
| **C** | Close budget period with snapshot; open next; events |
| **D** | Companion Finance section (invoices, refunds, periods) |

## Architecture

### Principles

- Integer USD cents via existing `money()`.
- `billed_costs` remains append-only for live invokes.
- Net billed = `SUM(billed_costs.amount_cents)` − `SUM(finance_adjustments.amount_cents)` where adjustments are active.
- Void: adjustment `kind=void` credits the **remaining** uncredited amount on that billed row (usually full `amount_cents` if no prior partials); row stays; further void when remaining is 0 fails closed.
- Partial credit: `0 < amount_cents ≤ remaining_creditable` for that `billed_cost_id`.
- Both kinds **require** `billed_cost_id` (no unlinked company-level credits in P3).
- Revenue table unchanged; refunds are not revenue.

### Tables (Alembic `0025_durable_finance`)

```sql
CREATE TABLE IF NOT EXISTS invoices(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  line_count INTEGER NOT NULL,
  body TEXT NOT NULL,  -- JSON: lines[{billed_cost_id, amount_cents, recorded_at, provider, profile_id}]
  status TEXT NOT NULL  -- open | voided (invoice void is rare; optional later — P3: open only)
);

CREATE TABLE IF NOT EXISTS finance_adjustments(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  kind TEXT NOT NULL,  -- void | partial_credit
  billed_cost_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,  -- positive magnitude subtracted from net
  reason TEXT NOT NULL,
  invoice_id TEXT  -- optional link
);

CREATE TABLE IF NOT EXISTS budget_period_closures(
  id TEXT PRIMARY KEY,
  budget_period_id TEXT NOT NULL,
  closed_at TEXT NOT NULL,
  closed_by TEXT NOT NULL,
  snapshot TEXT NOT NULL  -- JSON: limit_cents, simulated_spend, billed_gross, billed_net, revenue, period_start/end
);
```

Existing `budget_periods` kept. Closure does not delete the period row; it records a snapshot and marks the period closed via snapshot presence (or add `status` column on `budget_periods` — prefer **additive** `budget_period_closures` + query “open = no closure row”).

### Net billed helper

```python
def billed_gross_cents(company) -> int: ...
def billed_adjustment_cents(company) -> int: ...
def billed_net_cents(company) -> int:  # gross - adjustments
```

`status()` exposes:

- `billed_cost_cents` → **net** (breaking honesty fix: document as net of refunds; keep name for API stability)
- `billed_cost_gross_cents` (new)
- `billed_adjustment_cents` (new)
- `revenue_cents` unchanged

### APIs (all finance writes: `_ceo` + appropriate scope)

| Method | Path | Scope | Behavior |
|---|---|---|---|
| GET | `/api/v1/finance/summary` | company.read | gross/net/adjustments/revenue + open budget period |
| GET | `/api/v1/finance/invoices` | company.read | list |
| GET | `/api/v1/finance/invoices/{id}` | company.read | detail + lines |
| POST | `/api/v1/finance/invoices` | company.pause | create from `period_start`/`period_end` (ISO); include billed rows in `[start,end)` not fully voided |
| GET | `/api/v1/finance/adjustments` | company.read | list |
| POST | `/api/v1/finance/adjustments` | company.pause | `{kind, billed_cost_id, amount_cents?, reason, invoice_id?}`; void ignores amount (uses full remaining) |
| GET | `/api/v1/finance/budget-periods` | company.read | periods + closed flag/snapshot |
| POST | `/api/v1/finance/budget-periods` | company.pause | wrap existing `set_budget_period` |
| POST | `/api/v1/finance/budget-periods/{id}/close` | company.pause | write closure snapshot; fail if already closed |

Reuse desk paths if any exist; prefer `/finance/*` as the companion contract.

### Events

`invoice.created`, `finance.void`, `finance.partial_credit`, `budget.period_closed` (and existing `budget.period_set`).

## Companion UX (slice D)

Settings or dedicated **Finance** under More:

- Summary cards: gross / net / adjustments / revenue (from API only).
- Invoices: create (start/end), list, open detail.
- Adjustments: form void or partial credit (billed id, amount if partial, reason).
- Budget periods: list, set new, close open period.

No `window.prompt`. Mutate controls gated to CEO scopes (`company.pause` + owner `_ceo` as today for revenue).

## Failure modes

| Case | Result |
|---|---|
| Invoice window with no lines | Allowed with `total_cents=0` **or** reject — **reject empty** (ValueError) |
| Void already fully voided / over-credited row | Fail closed |
| Partial credit amount ≤ 0 or > remaining | Fail closed |
| Non-CEO finance write | 403 |
| Close already-closed period | Fail closed |
| Adjustment without reason | Fail closed |

## Testing

- A: create invoice captures correct lines/total; empty window rejected; GET detail.
- B: void then net; partial then remaining; double-void fails; status fields.
- C: close writes snapshot; second close fails; list shows closed.
- D: companion source assertions; `npm run build`.
- Full unittest discover before merge.

## Docs / governance

- Update `docs/03-data-model.md`, `docs/16-api-contract.md`, `docs/13-operations.md`, `docs/24-mobile-companion.md`, capability/roadmap, handoff.
- ADR-038: append-only finance adjustments + invoice snapshots; `billed_cost_cents` means net.

## Acceptance

1. Owner can create an internal invoice for a window and read it back with line fidelity.
2. Owner can void or partially credit a billed row; nets update; billed rows remain.
3. Owner can close a budget period with an auditable snapshot and open a new period.
4. Companion Finance surfaces the above without inventing totals.
5. Docs state benchmarks/work-order replay remain follow-on.
