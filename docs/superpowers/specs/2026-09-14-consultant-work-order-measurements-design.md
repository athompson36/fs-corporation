# Design: Consultant work-order measured before/after (0.3.87)

Date: 2026-09-14. Status: **implemented in v0.3.87** (deferred nits closed in **0.3.89**:
co-commit baseline/after with replay writes, `json_extract` list filter, denied-scope GET
test; see ADR-071).

## Program context

Final Ship 2 slice after finance **0.3.86**:

| Version | Contents |
|---|---|
| 0.3.86 | Finance open-next + pricing honesty (shipped) |
| **0.3.87 (this spec)** | Consultant measured before/after on work orders |

Owner locks: capture on authorize→complete (**A**); minimal ops counters (**A**); UI API+desk+companion Home Needs-you (**A** placement); approach snapshot table (**1**).

## Goal

Persist measured company counters at consultant work-order authorize (baseline) and complete-outcome (after), expose arithmetic deltas via API, and show them on desk `#consultant` and companion Home Needs-you — without inventing efficiency scores.

## Owner locks

| Topic | Choice |
|---|---|
| Approach | New `work_order_measurements` table + hooks |
| Baseline | On authorize path (`to_work_order` → `record_work_order_authorized`) |
| After | On `complete_work_order_outcome` |
| Metrics | `accepted_artifacts`, `open_tasks`, `open_dispatches`, `simulated_spend_cents`, `billed_cost_cents` |
| Scores | None invented — deltas only |
| UI | Desk `#consultant` + companion Home Needs-you |
| Complete control | CEO-gated (matches `complete_work_order_outcome` → `_ceo`) |
| Version | **0.3.87** |
| Alembic | **0029_work_order_measurements** (name flexible if 0029 taken) |

## Non-goals

- Invented efficiency scores, quality ratings, or AI judgment of outcomes.
- Auto-scheduled consultant reviews / cooldowns productization beyond existing reviews list.
- Changing proposal submit/decide/revise auth.
- Finance open-next / pricing-helper nits from 0.3.86.
- Companion Corporate Strategy placement.

## Problem

docs/19 and M7 call for measured before/after validation after approved consultant work. Today authorize/complete exist (`work_order_replays`) but no frozen company counters or UI deltas — operators cannot see whether a change moved real ops metrics.

## Behavior

### Schema

Table `work_order_measurements`:

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `work_order_id` | TEXT NOT NULL | FK logical to `work_orders` |
| `phase` | TEXT NOT NULL | `baseline` or `after` |
| `metrics_json` | TEXT NOT NULL | Frozen object |
| `created_at` | TEXT NOT NULL | ISO |
| `created_by` | TEXT NOT NULL | Actor |

Unique constraint on (`work_order_id`, `phase`) — one row per phase per work order.

### Snapshot helper

`capture_ops_metrics(company) -> dict[str, int]` returns exactly:

| Key | Definition |
|---|---|
| `accepted_artifacts` | `COUNT(*)` from `tasks` where `status='accepted'` |
| `open_tasks` | `COUNT(*)` from `tasks` where `status` not in (`accepted`, `cancelled`, `failed`) |
| `open_dispatches` | `COUNT(*)` from `project_dispatches` where `status` not in terminal set used by scorecard: `accepted`, `cancelled`, `canceled`, `closed`, `completed`, `failed`, `rejected` |
| `simulated_spend_cents` | `COALESCE(SUM(cost),0)` from `ledger` |
| `billed_cost_cents` | `billed_net_cents(company)` |

All values integers. No rates, percentages, or narrative scores.

### Hooks

1. **Baseline:** After successful `record_work_order_authorized` (including the call from `ConsultantDesk.to_work_order`), ensure a `baseline` row exists for that `work_order_id`. If already present, leave unchanged (idempotent).
2. **After:** At end of `complete_work_order_outcome` (after replay row + event), ensure an `after` row exists. Idempotent — do not overwrite.
3. Missing work order → fail closed (`ValueError`).
4. Emit audit events e.g. `work_order.measurement_baseline` / `work_order.measurement_after` with `{work_order_id, metrics}` (optional but preferred).

### Read API

**`GET /api/v1/work-orders/{work_order_id}/measurements`**  
Scope: `consultant.read` or `company.read`.  
Response:

```json
{
  "work_order_id": "...",
  "baseline": {"metrics": {...}, "created_at": "...", "created_by": "..."} | null,
  "after": {"metrics": {...}, "created_at": "...", "created_by": "..."} | null,
  "deltas": {"accepted_artifacts": 0, "...": 0} | null
}
```

`deltas` is null unless both phases exist; otherwise each key is `after[k] - baseline[k]`.

**`GET /api/v1/work-orders/measurements`**  
Same read scope. List recent consultant work orders with measurement summary (id, proposal_id if known, has_baseline, has_after, deltas or null) for desk/companion lists. Limit/default pagination consistent with nearby list endpoints (e.g. last 50 by authorize time).

**`POST /api/v1/work-orders/{id}/complete-outcome`**  
Unchanged auth (`company.pause` route scoping as today + `_ceo` in core). Response may include embedded `measurements` after write (nice-to-have; not required if GET is enough).

### Desk (`#consultant`)

- Keep existing proposal inbox list.
- Add **Work-order measures** subsection: for each listed measurement row, show work order id (short), linked proposal title when available, status (`baseline only` / `complete` with deltas).
- When baseline exists and after does not, show CEO **Complete outcome** chip posting `{status: "done"}` (or equivalent minimal outcome object) to complete-outcome; disable without CEO/`company.pause` session pattern consistent with other CEO mutates (server still enforces `_ceo`).
- Display deltas as signed integers per key when both phases exist — label as deltas, not “efficiency”.

### Companion (Home Needs-you)

- Cards for work orders awaiting after (Complete action when CEO scopes allow).
- Cards/rows for recently completed measurements showing deltas (read-only).
- Reuse Home Needs-you layout; wire via `api` client helpers.

## Tests

- Unit: snapshot keys/types; baseline on `to_work_order`; idempotent baseline; after on complete; idempotent after; deltas arithmetic; GET measurements; unauthorized read.
- Desk source contracts for measures subsection / complete markers.
- Companion: HomePanel markers or existing harness pattern if present.
- Alembic revision linear single head.

## Delivery

| Path | Role |
|---|---|
| `alembic/versions/0029_work_order_measurements.py` | Migration |
| `company/measurements.py` (new) | Snapshot + persist + read helpers |
| `company/core.py`, `company/consultant.py` | Hooks |
| `company/service.py` | Routes + desk HTML/JS |
| `companion/src/HomePanel.tsx`, `companion/src/api/client.ts` | Needs-you UI |
| Tests + docs | ADR-069, API contract, VERIFICATION, handoff, roadmap |
| Versions | **0.3.87** lockstep |

## Acceptance

1. Authorizing a consultant work order freezes baseline counters once.
2. Completing outcome freezes after once; GET returns deltas for all five keys.
3. No invented scores in API or UI copy.
4. Desk Consultant and companion Home show awaiting/complete states; Complete is CEO-gated.
5. Full unit suite green; companion build OK; version **0.3.87**.

## Spec self-review

- Metrics definitions are table-backed and match owner minimal set.
- Idempotent phases; no overwrite.
- UI placement matches lock A (desk consultant + Home Needs-you).
- Alembic required; no finance scope creep.
- Distinct from heuristic `company.consultant.review` CLI (unchanged).
