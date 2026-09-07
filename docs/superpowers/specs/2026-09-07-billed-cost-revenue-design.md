# Design: Billed cost and revenue (M10-03)

Date: 2026-09-07. Status: **implemented** (v0.3.48).

## Goal

Persist **actual billed cost** and **real revenue** in integer minor units, kept strictly
separate from simulated credits (`ledger` / `simulated_spend_cents`). Live
`invoke_model` currently returns a value labeled `cost_cents` that is actually a
token count and never writes to the database.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Honesty | Never store token counts as USD cents |
| Live invoke | Always insert a `billed_costs` row on successful live invoke |
| Amount when unpriced | `amount_cents = 0`; tokens in `usage_tokens` |
| Pricing | Optional `cents_per_1k_tokens` on profile or `FS_CORP_MODEL_CENTS_PER_1K_TOKENS` |
| Mock invoke | No `billed_costs` row |
| Revenue | Explicit `record_revenue` writer; no auto-ingest |
| Totals | Separate `billed_cost_cents` / `revenue_cents` on `status()`; never add into simulated |

## Schema

Alembic `0013_billed_cost_revenue` + `company/schema.py`:

```sql
CREATE TABLE IF NOT EXISTS billed_costs(
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  usage_tokens INTEGER NOT NULL,
  provider TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  source TEXT NOT NULL,
  task_id TEXT
);

CREATE TABLE IF NOT EXISTS revenue(
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  source TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);
```

Both amount columns use existing `money()` (nonnegative int).

## Provider return shape

Live `complete()` returns:

- `usage_tokens` — nonnegative int from provider usage
- `cost_cents` — priced minor units only (`usage_tokens * rate // 1000` when rate > 0, else `0`)

Mock path unchanged: `cost_cents: 0`, no usage field required.

## Write / read paths

1. `Company.invoke_model` live success → `INSERT billed_costs` + event `cost.billed` inside `tx()`; return provider dict (with honest `cost_cents` / `usage_tokens`).
2. `Company.record_revenue(actor, amount_cents, source, note="")` — CEO-only; event `revenue.recorded`.
3. `Company.status()` adds `billed_cost_cents` and `revenue_cents` as table sums.
4. Desk budget copy labels billed / revenue distinctly from simulated.

## Out of scope

Refunds, period rollover of billed totals, vendor invoice import, benchmark_results consumer/removal, role benchmark fixtures.

## Acceptance

- Live invoke (mocked `complete`) writes one billed row; mock writes none.
- Unpriced live call → `amount_cents == 0`, `usage_tokens` preserved.
- Priced call → `amount_cents` matches formula.
- Revenue sum never included in `simulated_spend_cents`.
- Migration head `0013_billed_cost_revenue`; `HEAD_REVISION` updated.
