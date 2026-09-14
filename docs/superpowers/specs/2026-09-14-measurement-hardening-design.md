# Design: Work-order measurement hardening (0.3.89)

Date: 2026-09-14. Status: **implemented in v0.3.89**.

## Goal

Close three deferred nits from the 0.3.87 consultant measurement ship: co-commit
baseline/after with replay writes, structured list filter, and denied-scope GET
coverage — without changing metrics, UI, or inventing scores.

## Owner locks

| Topic | Choice |
|---|---|
| Scope | All three nits |
| List filter | SQLite `json_extract(payload, '$.source') = 'consultant'` (no migration) |
| Approach | Harden in place |
| Packaging | Version **0.3.89** + ADR + docs |
| Alembic | None |

## Non-goals

- New metrics or phases.
- Desk/companion UI changes (beyond version lockstep).
- New Alembic tables/columns on `work_orders`.
- Changing auth scopes (`consultant.read` OR `company.read` remains).
- Stripe / provider invoices / ChatDev.

## Behavior

### 1. Same-transaction measurement

Today `ensure_measurement` runs **after** the authorize/complete `tx()` closes, so
baseline/after can commit without the matching replay row if a later step fails.

**Change:** Call `ensure_measurement(..., "baseline")` inside
`record_work_order_authorized`'s `with self.tx():` alongside the replay insert +
event. Call `ensure_measurement(..., "after")` inside
`complete_work_order_outcome`'s `tx()` the same way.

On the **already-authorized** path (existing `authorized` replay; no new insert),
still call `ensure_measurement` for baseline (idempotent; may open its own tx when
depth is 0 — acceptable because no paired write).

`ensure_measurement` already joins an open transaction when `_tx_depth > 0`; keep that.

### 2. Structured list filter

In `list_measurements`, replace:

```sql
WHERE wo.payload LIKE '%"source":"consultant"%'
```

with:

```sql
WHERE json_extract(wo.payload, '$.source') = 'consultant'
```

Consultant work orders already store `{"source":"consultant","proposal_id":...}` in
payload (see `company/consultant.py`).

### 3. Denied-scope GET test

Add a test that a principal **without** `consultant.read` and **without**
`company.read` receives **403** on `GET /api/v1/work-orders/measurements`
(optionally also detail). Keep existing positive owner / `consultant.read` tests.

## Packaging

- Bump `company/__init__.py` and `companion/package.json` → **0.3.89**.
- ADR-071 summarizing the three hardenings.
- README / VERIFICATION / handoff / roadmap.
- Note on `docs/superpowers/specs/2026-09-14-consultant-work-order-measurements-design.md`
  that nits closed in **0.3.89**.

## Tests

- Co-commit: simulate failure after measurement would have run separately is optional;
  at minimum assert authorize creates baseline and complete creates after (existing),
  plus a focused test or assertion that measurement insert participates in the same
  tx path (e.g. call site structure / `_tx_depth` behavior, or rollback scenario if
  cheap).
- List: non-consultant work order with `"source"` elsewhere in payload text must not
  match; consultant orders still listed.
- Denied scope: 403 as above.
