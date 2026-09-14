# Design: Finance open-next period + pricing honesty (0.3.86)

Date: 2026-09-14. Status: **implemented in v0.3.86**.

## Program context

Ship 2 of audit completion (code-local option C):

| Version | Contents |
|---|---|
| **0.3.86 (this spec)** | Finance: pricing honesty + explicit open-next budget period; API + desk + companion |
| **0.3.87 (later)** | Consultant: baseline on work-order authorize → after on complete-outcome; minimal ops counters; API + desk + companion |

Owner locks for Ship 2: finance approach **B** then approach **1** (extend close + UI, not rollover-on-close); consultant capture **A**, metrics **A**, UI **B**, packaging **B**.

## Goal

Close remaining finance audit gaps without reinventing ADR-038 invoices/adjustments: show honest pricing status when billed cents stay `$0`, and let the CEO open the **next** budget period explicitly after close.

## Owner locks

| Topic | Choice |
|---|---|
| Approach | Extend existing period close + Finance UI |
| Open-next | Separate `POST …/open-next` (not side effect of close) |
| Auth | `company.pause` + same CEO/admin rules as close / set period |
| Defaults | Contiguous window, same scope + limit; body overrides allowed |
| Pricing | Honesty flag + hint on finance summary; never invent amounts |
| Surfaces | API + desk `#budget` + companion FinancePanel |
| Alembic | None |
| Version | **0.3.86** |

## Non-goals

- Consultant measured before/after (0.3.87).
- Live provider / Stripe invoices.
- Silent calendar auto-rollover on close (rejected earlier; ADR/finance UX polish).
- Changing invoice, adjustment, or close snapshot semantics.
- New companion tabs beyond FinancePanel polish.

## Problem

ADR-038 already delivers invoices, adjustments, and period close with billed snapshots. The audit still flagged “period rollover” and “billed stays 0 without pricing.” Operators need an explicit successor period and a clear explanation when pricing is unset — not a second ledger.

## Behavior

### Open next period

**Endpoint:** `POST /api/v1/finance/budget-periods/{period_id}/open-next`  
**Auth:** `scoped(…, "company.pause")` + same actor gate as `POST …/close` / `POST …/budget-periods`  
**Idempotency:** required via existing command `run()` / `Idempotency-Key`

**Preconditions (fail closed):**

1. `period_id` exists in `budget_periods`.
2. Period is closed (`budget_period_closures` row present).
3. No other **unclosed** budget period exists (at most one open period company-wide).
4. Reject if a period already exists with the computed (or overridden) `period_start` for that scope (duplicate successor) — prefer `PermissionError` / 403 or 409 consistent with neighboring finance errors.

**Defaults** (overridable in `payload`):

| Field | Default |
|---|---|
| `scope` | Closed period’s `scope` |
| `period_start` | Closed period’s `period_end` |
| `period_end` | `period_start` + (closed `period_end` − closed `period_start`) |
| `limit_cents` | Closed period’s `limit_cents` |

Validate `period_end > period_start` and integer `limit_cents >= 0` (reuse `money()`).

**Effect:** Create the period through the existing `set_budget_period` path (or shared helper so id/event rules stay one place). Emit audit event e.g. `budget.period_opened_next` with `{from_period_id, id, scope, period_start, period_end, limit_cents}`. Return the new period list item shape (`closed: false`, no closure).

**Not allowed:** Opening next as a side effect of `close_budget_period`.

### Pricing honesty

Extend `GET /api/v1/finance/summary` with:

```json
"pricing": {
  "model_cents_per_1k_configured": true,
  "hint": "Billed lines may stay $0 until FS_CORP_MODEL_CENTS_PER_1K_TOKENS or a profile rate is set."
}
```

- `model_cents_per_1k_configured` is `true` when the same resolution path live invoke uses for cents-per-1k is present (env and/or profile/settings rate — match existing `invoke_model` / pricing helpers; do not invent a second resolver).
- Always include `hint` string (stable copy) so clients can show or hide based on the boolean.
- Never write non-zero billed amounts from this field.

### Desk (`#budget` / DESK_HTML)

- On each **closed** period row, when finance mutate enabled, show **Open next period** chip (stable id or `data-finance-*` marker consistent with Close).
- On finance overview, when `pricing.model_cents_per_1k_configured === false`, show the hint (muted).
- Reuse `setFinanceMutateEnabled` / `company.pause` session gate; 403 → fail-closed as today.

### Companion (`FinancePanel.tsx`)

- Browse periods: **Open next period** beside closed rows when mutate scopes allow (same gate as Close / Set period).
- Overview: show pricing hint when configured flag is false.
- No new ModeSwitch groups required unless an empty cluster would break layout — prefer Overview + Periods only.

## Tests

- Extend `tests/test_durable_finance.py` (or adjacent module):
  - Happy path defaults contiguous + same limit/scope
  - Payload overrides
  - Reject unclosed source
  - Reject when another open period exists
  - Reject duplicate successor / unauthorized actor
  - Summary `pricing.model_cents_per_1k_configured` true/false under controlled env
- Desk source contracts for Open next + pricing hint (lightweight)
- Companion: panel/harness coverage for open-next call path and hint visibility if an existing Finance test harness exists; otherwise minimal render/contract check

## Delivery

| Path | Role |
|---|---|
| `company/finance.py` | `open_next_budget_period`, summary `pricing` |
| `company/core.py` / `company/service.py` | Thin wrappers + route |
| Desk `DESK_HTML` | Open next + hint |
| `companion/src/FinancePanel.tsx` | Open next + hint |
| Tests + docs | As above |
| `docs/16-api-contract.md`, ADR-068, VERIFICATION, handoff, roadmap | Honesty |
| `company/__init__.py` + `companion/package.json` | **0.3.86** |
| Alembic | **None** |

## Acceptance

1. After closing a period with no other open period, Open next creates a contiguous successor with same scope/limit by default.
2. Invalid states fail closed; close never auto-opens next.
3. Pricing hint appears when rate unset; billed amounts are never invented by this feature.
4. Desk and companion respect existing finance session mutate gate.
5. Unit tests green; companion build OK; version lockstep **0.3.86**.

## Spec self-review

- No Ship 0.3.87 behavior specified beyond program context.
- Open-next is explicit and separate from close.
- Pricing is honesty-only; reuses invoke pricing resolution.
- No Alembic; no provider billing.
- UI surfaces match owner lock B (API + desk + companion).
