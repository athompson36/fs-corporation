# Design: Provider invoice allocations (0.3.88)

Date: 2026-09-14. Status: **approved (pending implement)**.

## Goal

Let the CEO record real provider invoices and allocate them onto immutable
`billed_costs` lines so operators can see estimate-vs-provider variance —
without inventing cents, mutating invoke rows, or auto-posting adjustments.

## Owner locks

| Topic | Choice |
|---|---|
| Intent | Link live `billed_costs` to recorded provider invoice amounts (reconcile) |
| Totals when amounts differ | Keep `billed_costs` immutable; show variance; change net only via existing void / partial_credit |
| Structure | Provider invoice header + many allocation rows |
| Surfaces | API + desk `#budget` + companion Finance Manage |
| Approach | New `provider_invoices` + `provider_invoice_allocations` (not extend ADR-038 `invoices`) |
| Auth | `company.pause` + same CEO/admin gate as create invoice / adjustments |
| Version | **0.3.88** |
| Alembic | **0030_provider_invoices** |

## Non-goals

- Stripe / live provider import / webhooks.
- Mutating `billed_costs.amount_cents`.
- Auto-posting finance adjustments from variance.
- Changing ADR-038 internal window-snapshot invoices, adjustments, or period close/open-next.
- Changing simulated spend / revenue semantics.
- Scheduled jobs.

## Problem

ADR-026/038 already separate estimated billed lines, internal invoices, and
refunds. Live invoke still estimates via optional token pricing (`amount_cents`
may be 0). Operators need an honest place to attach a **provider's** invoice
total to those lines and see variance without pretending the estimate was the
invoice.

## Data model

### `provider_invoices`

| Column | Notes |
|---|---|
| `id` | Text PK |
| `created_at`, `created_by` | Audit |
| `provider` | Required text (e.g. openai) |
| `external_id` | Provider's invoice id; **unique with provider** |
| `total_cents` | Integer ≥ 0 |
| `issued_at` | ISO timestamp |
| `note` | Optional text |
| `status` | `open` \| `void` |

Void is header-only: no further allocations; does not touch `billed_costs` or
`finance_adjustments`.

### `provider_invoice_allocations`

| Column | Notes |
|---|---|
| `id` | Text PK |
| `provider_invoice_id` | FK |
| `billed_cost_id` | FK to `billed_costs`; **unique per invoice** (one line once on that invoice) |
| `allocated_cents` | Integer ≥ 0 |
| `created_at`, `created_by` | Audit |

### Rules

1. Sum of allocations on an invoice must be ≤ `total_cents` (fail closed if over).
2. Per-allocation variance: `allocated_cents − billed_costs.amount_cents` (may be negative).
3. Invoice unallocated: `total_cents − sum(allocations)`.
4. Invoice variance (list/summary helper): sum of allocation variances (open invoices only for summary field).
5. Linking never posts adjustments. Net `billed_cost_cents` changes only through existing ADR-038 paths.
6. Each `billed_cost_id` may appear on **at most one non-void** provider invoice (reject allocate if already allocated on another open invoice). Voided invoices release their lines for re-allocation.

## API

### Reads (`company.read`)

- `GET /api/v1/finance/provider-invoices` — headers with `allocated_cents`, `unallocated_cents`, `variance_cents`.
- `GET /api/v1/finance/provider-invoices/{id}` — header + allocation lines each with `billed_cost_id`, `estimated_cents` (from `billed_costs.amount_cents`), `allocated_cents`, `variance_cents`.

### Writes (`company.pause` + CEO/admin gate; Idempotency-Key required)

- `POST /api/v1/finance/provider-invoices` — body: `provider`, `external_id`, `total_cents`, `issued_at`, optional `note`.
- `POST /api/v1/finance/provider-invoices/{id}/allocations` — body: `billed_cost_id`, `allocated_cents`. Reject: unknown billed cost, duplicate line on this invoice, line already allocated on another **open** invoice, over-total, void invoice.
- `POST /api/v1/finance/provider-invoices/{id}/void` — set `status=void`.

### Summary polish

Extend `GET /api/v1/finance/summary` with informational
`provider_invoice_variance_cents` (open invoices only). Does **not** change
`billed_cost_cents`, gross, or adjustment totals.

Audit events (examples): `finance.provider_invoice_created`,
`finance.provider_invoice_allocated`, `finance.provider_invoice_voided`.

## Surfaces

### Desk `#budget`

- List “Provider invoices” with expand for allocations + variance.
- Forms: Create provider invoice; Add allocation; Void.
- Same session pause / CEO gate pattern as other finance writes (0.3.82+).

### Companion Finance

- Browse: list + expand detail.
- Manage: new group `provider` (create / allocate / void) beside Invoice /
  Adjustment / Period.
- Copy must say “provider invoice” to avoid confusion with internal snapshots.

## Packaging

- Bump `company/__init__.py` and `companion/package.json` → **0.3.88**.
- ADR-070; API contract rows; README / VERIFICATION / handoff / roadmap.
- Soften exact prior version pins if any.

## Tests

- Create header; unique `(provider, external_id)`.
- Allocate; reject over-total, duplicate line, voided invoice, missing billed cost.
- Variance and unallocated math.
- Summary field informational (net billed unchanged by link alone).
- Scope denial on writes.
- Desk contract smoke for new element ids / copy.

## Out of scope follow-ups

- Importing provider CSV/PDF.
- Multi-currency.
- Splitting one billed line across multiple open provider invoices (rejected for v1).
