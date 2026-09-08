# P3 Durable Finance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship internal invoices, append-only void/partial-credit adjustments, budget-period close snapshots, and companion Finance UX — without mixing into simulated spend or deleting billed rows.

**Architecture:** New tables `invoices`, `finance_adjustments`, `budget_period_closures` (Alembic `0025`); helpers for gross/net billed; CEO finance APIs under `/api/v1/finance/*`; companion Finance section. `billed_cost_cents` becomes net; expose gross + adjustments separately.

**Tech Stack:** Python 3.12+, FastAPI, SQLite/`Company`, Alembic, unittest, companion React/TypeScript.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-p3-durable-finance-design.md` (approved).
- Slice order: **A → B → C → D**.
- `billed_costs` immutable; adjustments append-only; integer cents via `money()`.
- Finance writes: `_ceo` + `company.pause` on mutating routes.
- Never mix into `simulated_spend_cents`.
- Defer choose_model benchmarks + work-order replay.
- Branch: `feature/p3-durable-finance`; do not commit `local repos/service-department/`.

## File map

| File | Responsibility |
|---|---|
| Create `company/finance.py` | Invoice/adjustment/period helpers + net math |
| Modify `company/schema.py` | DDL for three tables |
| Create `alembic/versions/0025_durable_finance.py` | Migration |
| Modify `company/migrate.py` | `HEAD_REVISION` |
| Modify `company/core.py` | Thin wrappers; `status()` nets |
| Modify `company/service.py` | `/api/v1/finance/*` routes |
| Modify companion client + `App.tsx` | Finance UI |
| Tests | `tests/test_durable_finance.py` + companion assertions |
| Docs | api-contract, data-model, operations, companion, ADR-038, handoff |

---

### Task A1: Schema + invoice create/list/get

**Files:** `company/finance.py`, `company/schema.py`, `alembic/versions/0025_durable_finance.py`, `company/migrate.py`, `company/core.py`, `tests/test_durable_finance.py`

- [ ] Failing tests: empty window rejected; invoice captures billed lines in `[start,end)`; list/get
- [ ] Migration `0025` creating all three tables (adjustments/closures unused until B/C)
- [ ] `create_invoice(actor, period_start, period_end)`, `list_invoices()`, `get_invoice(id)`
- [ ] Commit `Add internal finance invoices and migration 0025.`

### Task A2: Invoice HTTP routes

- [ ] `GET/POST /api/v1/finance/invoices`, `GET …/invoices/{id}`
- [ ] API tests via `owner_client`
- [ ] Commit `Expose finance invoice HTTP routes.`

### Task B1: Adjustments + status nets

- [ ] `post_adjustment(actor, kind, billed_cost_id, reason, amount_cents=None, invoice_id=None)`
- [ ] remaining_creditable; void uses remaining; double-void fails
- [ ] `status()`: `billed_cost_cents`=net, add gross + adjustment fields
- [ ] Routes GET/POST `/api/v1/finance/adjustments` + summary
- [ ] Commit `Add finance adjustments and net billed totals.`

### Task C1: Budget period close

- [ ] `close_budget_period(actor, period_id)` → snapshot JSON; fail if already closed
- [ ] `list_budget_periods()` with closed flag
- [ ] POST create wraps `set_budget_period`; POST `…/{id}/close`
- [ ] Commit `Add auditable budget period closures.`

### Task D1: Companion Finance + docs

- [ ] Client methods + Finance section (summary, invoices, adjustments, periods)
- [ ] Source assertions; `npm run build`
- [ ] Docs + ADR-038 + handoff
- [ ] Commit `Add companion Finance UI and P3 docs.`

## Verification

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```
