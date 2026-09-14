# Provider Invoice Allocations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.88 with provider invoice headers + allocations onto immutable `billed_costs`, variance visibility on API/desk/companion, without auto-adjustments or Stripe.

**Architecture:** Alembic `0030_provider_invoices`; helpers in `company/finance.py`; thin `Company` wrappers; FastAPI finance routes; desk `#budget` list/forms; companion Finance Browse + Manage `provider` group. Net billed unchanged by linking alone.

**Tech Stack:** Python/SQLite/Alembic, FastAPI desk HTML, React companion FinancePanel, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-provider-invoice-allocations-design.md` (owner-approved).
- Version **0.3.88**. Soften exact `0.3.87` pins to `0\.3\.\d+` where needed.
- Do **not** mutate `billed_costs.amount_cents`; do **not** auto-post `finance_adjustments`.
- Do **not** extend ADR-038 `invoices` table — use `provider_invoices` + `provider_invoice_allocations`.
- Auth writes: `company.pause` + same CEO/admin `_ceo` gate as create invoice.
- Each `billed_cost_id` on at most **one open** provider invoice; void releases lines.
- Sum of allocations ≤ `total_cents`. Unique `(provider, external_id)`.
- Surfaces: API + desk `#budget` + companion `FinancePanel.tsx`.
- Copy: “provider invoice” (not confused with internal window invoices).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/provider-invoice-allocations` from current `main` before Task 1.
- Work **in-place** on the feature branch (dirty tree has huge untracked `local repos/`).

## File map

| Path | Role |
|---|---|
| `alembic/versions/0030_provider_invoices.py` | Migration |
| `company/schema.py` | SCHEMA CREATE TABLE for :memory: |
| `company/migrate.py` | `HEAD_REVISION = "0030_provider_invoices"` |
| `company/finance.py` | Create/list/get/allocate/void + summary variance |
| `company/core.py` | Thin wrappers |
| `company/service.py` | Routes + desk HTML/JS |
| `companion/src/api/client.ts` | Client methods |
| `companion/src/FinancePanel.tsx` | Browse + Manage provider group |
| `tests/test_provider_invoices.py` | Core + API behavior |
| `tests/test_desk_provider_invoices.py` | Desk source contracts |
| Docs + versions | ADR-070, API contract, README, VERIFICATION, handoff, roadmap; **0.3.88** |

---

### Task 1: Migration + finance helpers + Company wrappers

**Files:**
- Create: `alembic/versions/0030_provider_invoices.py`
- Create: `tests/test_provider_invoices.py`
- Modify: `company/schema.py`, `company/migrate.py`, `company/finance.py`, `company/core.py`
- Soften: any tests asserting `HEAD_REVISION == "0029_work_order_measurements"` → `0030_provider_invoices` (or import `HEAD_REVISION`)

**Interfaces:**
- Produces:
  - `create_provider_invoice(company, actor, *, provider, external_id, total_cents, issued_at, note="") -> dict`
  - `list_provider_invoices(company) -> list[dict]` (each with `allocated_cents`, `unallocated_cents`, `variance_cents`)
  - `get_provider_invoice(company, invoice_id) -> dict` (header + `allocations: [...]`)
  - `allocate_provider_invoice(company, actor, invoice_id, *, billed_cost_id, allocated_cents) -> dict` (full detail)
  - `void_provider_invoice(company, actor, invoice_id) -> dict`
  - `finance_summary` gains `provider_invoice_variance_cents: int` (open invoices only)
  - Matching `Company.*` thin wrappers

- [ ] **Step 1: Create branch**

```bash
cd /Users/andrew/Documents/FS-Tech/fs-corporation
git checkout main
git pull --ff-only
git checkout -b feature/provider-invoice-allocations
```

- [ ] **Step 2: Write failing tests** `tests/test_provider_invoices.py`

```python
"""Provider invoice headers + allocations (0.3.88)."""
import unittest
from datetime import timedelta

from company.core import Company, now
from company.migrate import HEAD_REVISION
from tests.test_api import owner_client
from tests.test_core import install, policy


def _insert_billed(c, bid, amount, recorded_at=None, provider="openai"):
    stamp = recorded_at or now().isoformat()
    with c.tx():
        c.db.execute(
            "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
            (bid, stamp, amount, 100, provider, "live", "test", None),
        )


class ProviderInvoiceTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_head_revision(self):
        self.assertEqual(HEAD_REVISION, "0030_provider_invoices")

    def test_create_list_unique_external(self):
        inv = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-1",
            total_cents=500, issued_at=now().isoformat(), note="sept")
        self.assertEqual(inv["status"], "open")
        self.assertEqual(inv["total_cents"], 500)
        self.assertEqual(inv["allocated_cents"], 0)
        self.assertEqual(inv["unallocated_cents"], 500)
        self.assertEqual(inv["variance_cents"], 0)
        self.assertEqual(len(self.c.list_provider_invoices()), 1)
        with self.assertRaises(ValueError):
            self.c.create_provider_invoice(
                "human-ceo", provider="openai", external_id="inv-1",
                total_cents=1, issued_at=now().isoformat())

    def test_allocate_variance_and_guards(self):
        _insert_billed(self.c, "b1", 100)
        _insert_billed(self.c, "b2", 40)
        inv = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-2",
            total_cents=200, issued_at=now().isoformat())
        before_net = self.c.status()["billed_cost_cents"]
        detail = self.c.allocate_provider_invoice(
            "human-ceo", inv["id"], billed_cost_id="b1", allocated_cents=120)
        line = next(a for a in detail["allocations"] if a["billed_cost_id"] == "b1")
        self.assertEqual(line["estimated_cents"], 100)
        self.assertEqual(line["allocated_cents"], 120)
        self.assertEqual(line["variance_cents"], 20)
        self.assertEqual(detail["allocated_cents"], 120)
        self.assertEqual(detail["unallocated_cents"], 80)
        self.assertEqual(detail["variance_cents"], 20)
        self.assertEqual(self.c.status()["billed_cost_cents"], before_net)
        self.assertEqual(
            self.c.finance_summary()["provider_invoice_variance_cents"], 20)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b1", allocated_cents=1)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="missing", allocated_cents=1)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=100)
        other = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-3",
            total_cents=50, issued_at=now().isoformat())
        with self.assertRaises(PermissionError):
            self.c.allocate_provider_invoice(
                "human-ceo", other["id"], billed_cost_id="b1", allocated_cents=10)
        self.c.allocate_provider_invoice(
            "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=40)
        voided = self.c.void_provider_invoice("human-ceo", inv["id"])
        self.assertEqual(voided["status"], "void")
        with self.assertRaises(PermissionError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=1)
        # void releases lines for re-allocation on a new open invoice
        reopened = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-4",
            total_cents=40, issued_at=now().isoformat())
        self.c.allocate_provider_invoice(
            "human-ceo", reopened["id"], billed_cost_id="b2", allocated_cents=40)
        self.assertEqual(
            self.c.finance_summary()["provider_invoice_variance_cents"], 0)

    def test_api_create_allocate_void_and_scope(self):
        _insert_billed(self.c, "api-b1", 50)
        with owner_client(self.c) as client:
            r = client.post(
                "/api/v1/finance/provider-invoices",
                json={"provider": "openai", "external_id": "api-1",
                      "total_cents": 80, "issued_at": now().isoformat()},
                headers={"Idempotency-Key": "pi-1"})
            # Task 1 may stop before routes exist — if so move this method to Task 2.
            # Prefer implementing routes in Task 1 if owner_client tests live here.
            self.assertEqual(r.status_code, 200, r.text)
            iid = r.json()["id"]
            r2 = client.post(
                f"/api/v1/finance/provider-invoices/{iid}/allocations",
                json={"billed_cost_id": "api-b1", "allocated_cents": 55},
                headers={"Idempotency-Key": "pi-2"})
            self.assertEqual(r2.status_code, 200, r2.text)
            self.assertEqual(r2.json()["variance_cents"], 5)
            r3 = client.get(f"/api/v1/finance/provider-invoices/{iid}")
            self.assertEqual(r3.status_code, 200)
            r4 = client.post(
                f"/api/v1/finance/provider-invoices/{iid}/void",
                json={},
                headers={"Idempotency-Key": "pi-3"})
            self.assertEqual(r4.status_code, 200)
            self.assertEqual(r4.json()["status"], "void")


if __name__ == "__main__":
    unittest.main()
```

**Note:** If you split API to Task 2, keep only Company-level tests in Task 1 and move `test_api_*` to Task 2. Prefer **routes in Task 1** so one RED/GREEN cycle covers helpers + HTTP.

- [ ] **Step 3: Run tests — expect FAIL**

```bash
.venv/bin/python -m unittest tests.test_provider_invoices -v
```

Expected: FAIL (missing methods / tables / routes).

- [ ] **Step 4: Migration + SCHEMA**

`alembic/versions/0030_provider_invoices.py`:

```python
"""Provider invoices and allocations."""
from alembic import op

revision = "0030_provider_invoices"
down_revision = "0029_work_order_measurements"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_invoices(
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          provider TEXT NOT NULL,
          external_id TEXT NOT NULL,
          total_cents INTEGER NOT NULL,
          issued_at TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL,
          UNIQUE(provider, external_id))
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_invoice_allocations(
          id TEXT PRIMARY KEY,
          provider_invoice_id TEXT NOT NULL,
          billed_cost_id TEXT NOT NULL,
          allocated_cents INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          UNIQUE(provider_invoice_id, billed_cost_id))
        """
    )

def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
```

Append matching `CREATE TABLE` statements to `company/schema.py` (SCHEMA string).

Set `company/migrate.py`: `HEAD_REVISION = "0030_provider_invoices"`.

Update any tests that hard-assert `0029_work_order_measurements`.

- [ ] **Step 5: Implement helpers in `company/finance.py`**

Add (names must match Interfaces). Key behaviors:

- `money()` / int checks for cents; `_parse_iso` for `issued_at`.
- `create_provider_invoice`: `_ceo(actor)`; reject blank provider/external_id; `total_cents >= 0`; insert `status='open'`; event `finance.provider_invoice_created`; return list-item shape via `get_provider_invoice` or shared serializer.
- `_invoice_totals(company, invoice_id)` → allocated sum; variance = sum(`allocated − estimated`) over lines joined to `billed_costs`.
- `allocate_provider_invoice`: reject void status; reject unknown billed cost; reject if same `billed_cost_id` already on **any open** invoice (join allocations → invoices where status='open'); reject if `allocated + existing > total`; event `finance.provider_invoice_allocated`.
- `void_provider_invoice`: set status void; event `finance.provider_invoice_voided`; reject double-void.
- `finance_summary`: add  
  `provider_invoice_variance_cents` = sum of variances for **open** invoices only (0 if none).

- [ ] **Step 6: Company wrappers + API routes**

In `company/core.py` add thin wrappers mirroring other finance methods.

In `company/service.py` (near other finance routes):

```python
@app.get("/api/v1/finance/provider-invoices")
def finance_list_provider_invoices(...):
    scoped(ident, "company.read")
    return {"provider_invoices": company.list_provider_invoices()}

@app.get("/api/v1/finance/provider-invoices/{invoice_id}")
def finance_get_provider_invoice(...):
    scoped(ident, "company.read")
    return company.get_provider_invoice(invoice_id)

@app.post("/api/v1/finance/provider-invoices")
def finance_create_provider_invoice(...):
    scoped(ident, "company.pause")
    return run(..., lambda: (company.create_provider_invoice(
        ident["principal_id"],
        provider=payload["provider"],
        external_id=payload["external_id"],
        total_cents=payload["total_cents"],
        issued_at=payload["issued_at"],
        note=payload.get("note") or ""), 200))

@app.post("/api/v1/finance/provider-invoices/{invoice_id}/allocations")
def finance_allocate_provider_invoice(...):
    scoped(ident, "company.pause")
    return run(..., lambda: (company.allocate_provider_invoice(
        ident["principal_id"], invoice_id,
        billed_cost_id=payload["billed_cost_id"],
        allocated_cents=payload["allocated_cents"]), 200))

@app.post("/api/v1/finance/provider-invoices/{invoice_id}/void")
def finance_void_provider_invoice(...):
    scoped(ident, "company.pause")
    return run(..., lambda: (
        company.void_provider_invoice(ident["principal_id"], invoice_id), 200))
```

- [ ] **Step 7: Run tests — expect PASS**

```bash
.venv/bin/python -m unittest tests.test_provider_invoices tests.test_migrate tests.test_durable_finance -v
```

Expected: OK.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/0030_provider_invoices.py company/schema.py company/migrate.py \
  company/finance.py company/core.py company/service.py \
  tests/test_provider_invoices.py
# plus any HEAD_REVISION softens
git commit -m "$(cat <<'EOF'
feat(finance): persist provider invoices and allocations

EOF
)"
```

---

### Task 2: Desk + companion UI

**Files:**
- Modify: `company/service.py` (DESK_HTML + JS only)
- Modify: `companion/src/api/client.ts`
- Modify: `companion/src/FinancePanel.tsx`
- Create: `tests/test_desk_provider_invoices.py`

**Interfaces:**
- Consumes: Task 1 routes and list/detail JSON shapes.
- Produces: desk element ids + companion Manage group `provider`.

- [ ] **Step 1: Desk contract test**

```python
"""Desk source contracts for provider invoices."""
import unittest
from company.service import DESK_HTML


class DeskProviderInvoiceTests(unittest.TestCase):
    def test_provider_invoice_surface(self):
        self.assertIn("Provider invoices", DESK_HTML)
        self.assertIn("desk-finance-provider-invoice-submit", DESK_HTML)
        self.assertIn("desk-finance-provider-allocate-submit", DESK_HTML)
        self.assertIn("finance-provider-invoice-list", DESK_HTML)
        self.assertIn("/api/v1/finance/provider-invoices", DESK_HTML)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
.venv/bin/python -m unittest tests.test_desk_provider_invoices -v
```

- [ ] **Step 3: Desk HTML/JS**

In `#budget` section (near internal invoice list/forms):

- `<ul id="finance-provider-invoice-list"></ul>`
- Form create: provider, external_id, total_cents, issued_at (datetime-local), note; button `desk-finance-provider-invoice-submit`
- Form allocate: select provider invoice, select billed cost, allocated_cents; button `desk-finance-provider-allocate-submit`
- Expand/void chips on list items (reuse invoice expand pattern).
- Wire into existing finance pause gate id lists (`deskFinanceWriteControls` / init disabled) so submit chips start disabled and enable with `company.pause` like other finance writes.
- `loadFinance` fetches provider invoices; render allocated/unallocated/variance with `formatFinanceUsd`.
- Labels: **Provider invoice** / **Provider invoices**.

- [ ] **Step 4: Companion client + FinancePanel**

`client.ts`:

```typescript
listProviderInvoices() {
  return this.get<{ provider_invoices: Record<string, unknown>[] }>(
    "/api/v1/finance/provider-invoices");
}
getProviderInvoice(id: string) {
  return this.get<Record<string, unknown>>(
    `/api/v1/finance/provider-invoices/${encodeURIComponent(id)}`);
}
createProviderInvoice(payload: Record<string, unknown>) {
  return this.post("/api/v1/finance/provider-invoices", payload,
    `finance-provider-inv-${Date.now()}`);
}
allocateProviderInvoice(id: string, payload: Record<string, unknown>) {
  return this.post(
    `/api/v1/finance/provider-invoices/${encodeURIComponent(id)}/allocations`,
    payload, `finance-provider-alloc-${Date.now()}`);
}
voidProviderInvoice(id: string) {
  return this.post(
    `/api/v1/finance/provider-invoices/${encodeURIComponent(id)}/void`,
    {}, `finance-provider-void-${Date.now()}`);
}
```

`FinancePanel.tsx`:

- Browse: show provider invoices with expand (allocations + variance). Overview may show `provider_invoice_variance_cents` from summary if present.
- Manage: new group `{ id: "provider", label: "Provider" }` with create + allocate + void (gated by `canPause` / `company.pause` notice).
- Do not rename existing “Invoice” group (internal snapshots).

- [ ] **Step 5: Run tests + companion build**

```bash
.venv/bin/python -m unittest tests.test_desk_provider_invoices tests.test_provider_invoices -v
cd companion && npm run build
```

Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add company/service.py companion/src/api/client.ts companion/src/FinancePanel.tsx \
  tests/test_desk_provider_invoices.py
git commit -m "$(cat <<'EOF'
feat(ui): show provider invoice allocations on desk and companion

EOF
)"
```

---

### Task 3: Version 0.3.88 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `docs/decisions.md` (ADR-070), `docs/16-api-contract.md`, `README.md`, `VERIFICATION.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`
- Modify: design spec status → **implemented in v0.3.88**
- Commit plan file if still untracked: `docs/superpowers/plans/2026-09-14-provider-invoice-allocations.md`

**Interfaces:** none new.

- [ ] **Step 1: Bump versions to `0.3.88`**

- [ ] **Step 2: ADR-070** — summarize locks: new tables, immutable billed rows, variance informational, no Stripe, surfaces, Alembic 0030.

- [ ] **Step 3: API contract rows** for the five provider-invoice endpoints + summary field note.

- [ ] **Step 4: README / VERIFICATION / handoff / roadmap**

Handoff tip: pin to **ship commit SHA** with “(0.3.88 ship; branch HEAD may include handoff-only commits)” — do not thrash tip across commits.

Immediate next: owner-directed follow-ups / audit canvas refresh after merge+deploy.

- [ ] **Step 5: Full suite**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all OK; companion build OK.

- [ ] **Step 6: Commit**

```bash
git add company/__init__.py companion/package.json docs/decisions.md docs/16-api-contract.md \
  README.md VERIFICATION.md docs/18-handoff.md docs/14-roadmap.md \
  docs/superpowers/specs/2026-09-14-provider-invoice-allocations-design.md \
  docs/superpowers/plans/2026-09-14-provider-invoice-allocations.md
git commit -m "$(cat <<'EOF'
docs: ship provider invoice allocations as 0.3.88

EOF
)"
```

Optional follow-up commit only for handoff tip pin (same pattern as 0.3.87).

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Tables + Alembic 0030 | 1 |
| Create / unique external id | 1 |
| Allocate + variance + over-total + duplicate + open uniqueness + void release | 1 |
| Summary `provider_invoice_variance_cents` informational | 1 |
| API routes + auth | 1 |
| Desk UI | 2 |
| Companion Browse + Manage | 2 |
| Version 0.3.88 + ADR-070 + docs | 3 |
| No Stripe / no auto-adjust / no billed mutate | Global + tests |

## Plan self-review

- No TBD/placeholder steps.
- Function names consistent across tasks.
- API tests colocated with Task 1 routes (or moved wholly to Task 2 if split — prefer Task 1).
