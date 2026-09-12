# Design: Desk Finance surface

Date: 2026-09-12. Status: **approved for implementation** (target **v0.3.78**).

## Goal

Replace the CEO desk Money `#budget` JSON dump with a full **Finance** surface —
structured summary, lists, create forms, and in-row close period — parity with
companion Finance capabilities, delivered as desk-native long scroll (no
Browse/Manage ModeSwitch).

## Owner locks

| Topic | Choice |
|---|---|
| Track | Desk Finance surface (not companion polish nits) |
| Depth | Companion parity — lists **and** create invoice / adjustment / period |
| Chrome | Desk-native long scroll (Projects-style); no desk ModeSwitch / clusters |
| Identity | Keep `id="budget"` and `href="#budget"`; visible rail + `<h2>` label **Finance** |
| Totals | Replace `budget-json` with structured `/api/v1/finance/summary` overview |
| Approach | In-place expand `#budget` in `company/service.py` HTML + desk JS |
| Version | **0.3.78** (Python package + companion `package.json` lockstep) |

## Non-goals

- New finance APIs, Alembic, or money-rule changes (ADR-038 math unchanged).
- Renaming section id to `#finance`.
- Desk Browse/Manage ModeSwitch, ManageClusters, or `?mode=`/`?group=` URL sync.
- Companion FinancePanel / URL changes; deferred polish nits.
- PDF / Stripe / payment rails; extracting desk markup to a separate template.
- Sharing React companion code into the desk.

## Section structure (`#budget`)

Order top → bottom inside the single glass section:

1. Lede (persisted finance totals and lists; create actions below; API cents /
   display USD).
2. **Overview** — gross billed, adjustments, net billed, revenue, open period
   (or “No open budget period”).
3. **Invoices** — list; expand loads line detail via `GET …/invoices/{id}`.
4. **Adjustments** — list.
5. **Periods** — list; **Close period** in-row (confirm) when principal has
   `company.pause`.
6. **Create invoice** — period start/end (`datetime-local`) + submit.
7. **Post adjustment** — kind (void / partial_credit), billed-cost picker,
   amount (partial only), reason.
8. **Set budget period** — start/end, limit cents; optional “next 30 days”
   helper; after close, prefill start from closed `period_end`.

Reuse desk chrome: `glass`, `compact` forms, `chip` buttons, `muted`, empty-state
copy. No new visual system.

Rail under Money: `<a href="#budget">Finance</a>`. Heading: `<h2>Finance</h2>`.

## Data & mutations

All existing endpoints; desk bearer `headers` + `Idempotency-Key` like other
desk POSTs (`desk-finance-*` prefixes).

| Action | Endpoint | Scope |
|---|---|---|
| Overview | `GET /api/v1/finance/summary` | `company.read` |
| Lists | `GET …/invoices`, `…/adjustments`, `…/budget-periods`, `…/billed-costs` | `company.read` |
| Invoice detail | `GET …/invoices/{id}` | `company.read` |
| Create invoice | `POST …/invoices` `{period_start, period_end}` ISO | `company.pause` |
| Post adjustment | `POST …/adjustments` | `company.pause` |
| Set period | `POST …/budget-periods` | `company.pause` |
| Close period | `POST …/budget-periods/{id}/close` | `company.pause` |

Behavior:

- Load finance data during desk `load()` (or a dedicated refresh called from
  `load()`). Remove writes to `budget-json`.
- After successful mutations, refresh finance lists/summary.
- Display amounts with a small cents→USD helper; payloads remain integer cents.
- Without `company.pause`: keep create/close controls visible but disabled;
  show a short muted scope notice under the mutate block (desk-native; same
  idea as companion `scopeNotice`).
- On load failure: show an explicit error line in Overview; leave list
  containers empty (no invented totals). On mutation failure: status text next
  to that form/button; keep last good lists/summary until the next successful
  refresh.

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | Desk HTML `#budget` markup; rail label; JS load/render/forms |
| `tests/test_desk_finance_surface.py` (new) | Source contracts: Finance label + `#budget`; no `budget-json`; finance API strings; form/close markers; version **0.3.78** |
| `tests/test_desk_ia_five_domains.py` | Keep `#budget` order asserts; allow Finance rail label if asserted |
| `tests/test_api.py` | Keep `href="#budget"` if present; update “Budget” text asserts if any |
| `company/__init__.py`, `companion/package.json` | Version **0.3.78** |
| Docs | UX (Money is Finance, id `#budget`), ADR, roadmap, handoff; mark this spec implemented when shipped |

Branch: `feature/desk-finance-surface`.

## Verification

- Source contracts as above; full `unittest discover -s tests`.
- No companion build requirement beyond version lockstep string if unchanged UX.
- Manual on desk: overview loads; expand invoice; create invoice/adjustment/
  period; close period + prefill; missing-pause notice; `#budget` bookmark still
  lands on Money.

## Follow-ups (deferred)

- Companion polish nits (dead `closePeriod` focus; cold-load `defaultGroupFor`;
  behavioral URL tests).
- Optional later: nested Money rail sub-anchors; desk ModeSwitch (explicitly
  out of this release).
