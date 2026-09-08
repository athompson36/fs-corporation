# Companion Finance UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship companion Finance sub-tabs (Overview · Invoices · Adjustments · Periods), dollar display, invoice detail, billed-cost picker, and clearer period flow — plus `GET /api/v1/finance/billed-costs` — without changing ADR-038 money rules.

**Architecture:** Thin `list_billed_costs` helper reuses `remaining_creditable`. Companion extracts `FinancePanel.tsx` with internal sub-nav; API stays integer cents; UI formats `$x.xx`. No Alembic.

**Tech Stack:** Python 3.12+, FastAPI, existing `company.finance` / `Company`, unittest, companion React/TypeScript (Vite).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-finance-ux-polish-design.md` (approved).
- Version **0.3.62**; amend ADR-038 consequences only (no new ADR number).
- No Alembic; HEAD remains `0028_remote_worker_jobs`.
- Do not mutate `billed_costs`; do not mix into `simulated_spend_cents`.
- Adjustments: select-only from creditable lines; no paste-id fallback.
- Branch: `feature/finance-ux-polish` from `main`.
- Do not commit `local repos/service-department/`.

## File map

| File | Responsibility |
|---|---|
| `company/finance.py` | `list_billed_costs(...)` |
| `company/core.py` | Thin `list_billed_costs` wrapper |
| `company/service.py` | `GET /api/v1/finance/billed-costs` |
| `tests/test_durable_finance.py` | Domain + HTTP tests for billed-costs list |
| `companion/src/api/client.ts` | `financeBilledCosts`, `financeInvoice(id)` |
| `companion/src/financeMoney.ts` | `formatUsd(cents)` |
| `companion/src/FinancePanel.tsx` | Finance UI + sub-tabs |
| `companion/src/App.tsx` | Drop inline Finance; render `<FinancePanel />` |
| `tests/test_companion_api.py` | Source assertions for new wiring |
| Docs / versions | API contract, companion, ADR-038, roadmap, handoff, `0.3.62` |

---

### Task 1: `list_billed_costs` + HTTP route

**Files:**
- Modify: `company/finance.py`
- Modify: `company/core.py` (near other finance wrappers ~766–799)
- Modify: `company/service.py` (finance routes ~2760; add `Query` to FastAPI import)
- Test: `tests/test_durable_finance.py`

**Interfaces:**
- Produces: `list_billed_costs(company, *, limit: int = 100, include_fully_credited: bool = False) -> list[dict]`
- Each dict keys: `id`, `recorded_at`, `amount_cents`, `remaining_creditable_cents`, `provider`, `profile_id`, `source`, `task_id`
- HTTP: `GET /api/v1/finance/billed-costs?include_fully_credited=0&limit=100` → `{"billed_costs": [...]}` · scope `company.read`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_durable_finance.py`:

```python
class BilledCostsListTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        t = now().isoformat()
        _insert_billed(self.c, "bc-full", 100, t)
        _insert_billed(self.c, "bc-part", 80, t)
        self.c.post_finance_adjustment(
            "human-ceo", kind="void", billed_cost_id="bc-full", reason="gone")
        self.c.post_finance_adjustment(
            "human-ceo", kind="partial_credit", billed_cost_id="bc-part",
            amount_cents=30, reason="partial")

    def test_default_excludes_fully_credited(self):
        rows = self.c.list_billed_costs()
        ids = [r["id"] for r in rows]
        self.assertIn("bc-part", ids)
        self.assertNotIn("bc-full", ids)
        part = next(r for r in rows if r["id"] == "bc-part")
        self.assertEqual(part["remaining_creditable_cents"], 50)
        self.assertEqual(part["amount_cents"], 80)

    def test_include_fully_credited(self):
        rows = self.c.list_billed_costs(include_fully_credited=True)
        ids = [r["id"] for r in rows]
        self.assertIn("bc-full", ids)
        full = next(r for r in rows if r["id"] == "bc-full")
        self.assertEqual(full["remaining_creditable_cents"], 0)


# Inside FinanceApiTests:
    def test_billed_costs_http(self):
        t0 = now().isoformat()
        _insert_billed(self.c, "http-bc", 40, t0)
        res = self.client.get("/api/v1/finance/billed-costs", headers=self.h)
        self.assertEqual(res.status_code, 200, res.text)
        ids = [r["id"] for r in res.json()["billed_costs"]]
        self.assertIn("http-bc", ids)
```

- [ ] **Step 2: Run tests — expect fail**

```bash
.venv/bin/python -m unittest tests.test_durable_finance.BilledCostsListTests tests.test_durable_finance.FinanceApiTests.test_billed_costs_http -v
```

Expected: FAIL (`list_billed_costs` missing / 404).

- [ ] **Step 3: Implement helper**

Add to `company/finance.py` after `remaining_creditable`:

```python
def list_billed_costs(
    company,
    *,
    limit: int = 100,
    include_fully_credited: bool = False,
) -> list[dict]:
    try:
        lim = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    if lim < 1:
        raise ValueError("limit must be >= 1")
    if lim > 500:
        lim = 500
    out: list[dict] = []
    for row in company.db.execute(
        "SELECT * FROM billed_costs ORDER BY recorded_at DESC"
    ):
        remaining = remaining_creditable(company, row["id"])
        if not include_fully_credited and remaining <= 0:
            continue
        out.append({
            "id": row["id"],
            "recorded_at": row["recorded_at"],
            "amount_cents": int(row["amount_cents"]),
            "remaining_creditable_cents": remaining,
            "provider": row["provider"],
            "profile_id": row["profile_id"],
            "source": row["source"],
            "task_id": row["task_id"],
        })
        if len(out) >= lim:
            break
    return out
```

- [ ] **Step 4: Wire Company + route**

In `company/core.py` with other finance wrappers:

```python
def list_billed_costs(self, *, limit=100, include_fully_credited=False):
    from company.finance import list_billed_costs
    return list_billed_costs(
        self, limit=limit, include_fully_credited=include_fully_credited)
```

In `company/service.py`:

```python
from fastapi import FastAPI, Header, HTTPException, Query, Request
```

Near other finance GETs:

```python
@app.get("/api/v1/finance/billed-costs")
def finance_list_billed_costs(
    authorization: str | None = Header(default=None),
    include_fully_credited: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
):
    ident = principal(authorization)
    scoped(ident, "company.read")
    return {
        "billed_costs": company.list_billed_costs(
            limit=limit, include_fully_credited=include_fully_credited),
    }
```

- [ ] **Step 5: Re-run tests — expect pass**

```bash
.venv/bin/python -m unittest tests.test_durable_finance.BilledCostsListTests tests.test_durable_finance.FinanceApiTests.test_billed_costs_http -v
```

Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add company/finance.py company/core.py company/service.py tests/test_durable_finance.py
git commit -m "$(cat <<'EOF'
Add finance billed-costs list API for companion picker.

EOF
)"
```

---

### Task 2: Companion client + `formatUsd` + `FinancePanel`

**Files:**
- Create: `companion/src/financeMoney.ts`
- Create: `companion/src/FinancePanel.tsx`
- Modify: `companion/src/api/client.ts`
- Modify: `companion/src/App.tsx` (remove finance state/forms/section; render panel)
- Test: `tests/test_companion_api.py`

**Interfaces:**
- Consumes: Task 1 HTTP + existing finance routes
- Produces: `formatUsd(cents: number): string`; `FinancePanel` props below; client methods `financeBilledCosts`, `financeInvoice`

`FinancePanel` props:

```typescript
type FinancePanelProps = {
  api: ApiClient; // exported from companion/src/api/client.ts
  scopes: string[];
  canPause: boolean;
  scopeNotice: (action: string, scope: string) => React.ReactNode;
  runAction: (
    key: string,
    okMessage: string,
    run: () => Promise<void>,
  ) => Promise<void>;
  status: (key: string) => React.ReactNode;
};
```

- [ ] **Step 1: Update companion source assertions (fail first)**

Replace `test_companion_wires_finance` in `tests/test_companion_api.py` with:

```python
def test_companion_wires_finance(self):
    root = Path(__file__).resolve().parents[1] / "companion" / "src"
    client = (root / "api" / "client.ts").read_text()
    app = (root / "App.tsx").read_text()
    panel = (root / "FinancePanel.tsx").read_text()
    money = (root / "financeMoney.ts").read_text()
    self.assertIn("/api/v1/finance/summary", client)
    self.assertIn("financeBilledCosts", client)
    self.assertIn("financeInvoice", client)
    self.assertIn("createFinanceInvoice", client)
    self.assertIn("postFinanceAdjustment", client)
    self.assertIn("closeFinanceBudgetPeriod", client)
    self.assertIn('["finance", "Finance"]', app)
    self.assertIn("tab === \"finance\"", app)
    self.assertIn("FinancePanel", app)
    self.assertIn("export function formatUsd", money)
    self.assertIn("Overview", panel)
    self.assertIn("Invoices", panel)
    self.assertIn("Adjustments", panel)
    self.assertIn("Periods", panel)
    self.assertIn("financeBilledCosts", panel)
    self.assertIn("remaining_creditable", panel)
    self.assertIn("confirm(", panel)
    self.assertNotIn("adj-billed", app)
```

- [ ] **Step 2: Run assertion test — expect fail**

```bash
.venv/bin/python -m unittest tests.test_companion_api.CompanionApiTests.test_companion_wires_finance -v
```

Expected: FAIL (missing `FinancePanel.tsx`).

- [ ] **Step 3: Add `formatUsd` + client methods**

`companion/src/financeMoney.ts`:

```typescript
/** Display-only. API bodies remain integer USD cents. */
export function formatUsd(cents: number): string {
  const n = Number(cents);
  if (!Number.isFinite(n)) return "$—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n / 100);
}
```

In `companion/src/api/client.ts` after `financeInvoices()`:

```typescript
  financeInvoice(invoiceId: string) {
    return this.get<Record<string, unknown>>(
      `/api/v1/finance/invoices/${encodeURIComponent(invoiceId)}`,
    );
  }

  financeBilledCosts(opts?: { includeFullyCredited?: boolean; limit?: number }) {
    const q = new URLSearchParams();
    if (opts?.includeFullyCredited) q.set("include_fully_credited", "true");
    if (opts?.limit != null) q.set("limit", String(opts.limit));
    const suffix = q.toString() ? `?${q}` : "";
    return this.get<{ billed_costs: Record<string, unknown>[] }>(
      `/api/v1/finance/billed-costs${suffix}`,
    );
  }
```

- [ ] **Step 4: Create `FinancePanel.tsx`**

Implement a panel that:

1. State: `subTab: "overview" | "invoices" | "adjustments" | "periods"`; summary/invoices/adjustments/periods/billedCosts; `expandedInvoice` detail; form fields for invoice/adjustment/period; `datetime-local` values converted to ISO via `new Date(value).toISOString()` when submitting (reject empty).
2. `loadAll` on mount: `Promise.all` of `financeSummary`, `financeInvoices`, `financeAdjustments`, `financeBudgetPeriods`, `financeBilledCosts()`.
3. Sub-nav buttons labeled exactly `Overview`, `Invoices`, `Adjustments`, `Periods`.
4. **Overview:** show `formatUsd` for gross/adj/net/revenue; show open period from summary if present; note “API amounts are cents; display is USD.”
5. **Invoices:** list rows; click expands → `api.financeInvoice(id)` → render `body.lines`; create form with two `datetime-local` inputs + button “This calendar month” that sets start to first of month 00:00 local and end to first of next month 00:00 local.
6. **Adjustments:** list; `<select>` of billed costs (`id` value; label includes provider + `formatUsd(amount)` + remaining); show remaining for selection; kind void|partial_credit; disable submit when `billedCosts.length === 0` with muted “No creditable lines.”; client-block partial if `amount > remaining` or `<= 0`.
7. **Periods:** list; Close calls `window.confirm("Close this budget period? Snapshot will be frozen.")` before `closeFinanceBudgetPeriod`; on success set `periodStart` from closed `period_end` (convert ISO to `datetime-local` value if practical, else leave ISO in a text field that still posts ISO — prefer converting); switch `subTab` to `"periods"` and focus set form; set form with datetime-local + limit + “Next 30 days” preset.

Keep styles using existing companion classes (`card`, `muted`, `actions`, `primary`). Do not invent totals.

Skeleton structure (fill handlers fully in the real file):

```tsx
import { FormEvent, useCallback, useEffect, useState } from "react";
import { formatUsd } from "./financeMoney";
// import ApiClient type / class from "./api/client"

type SubTab = "overview" | "invoices" | "adjustments" | "periods";

export function FinancePanel(props: /* FinancePanelProps */) {
  const { api, canPause, scopeNotice, runAction, status } = props;
  const [subTab, setSubTab] = useState<SubTab>("overview");
  // ... load + forms ...
  return (
    <section>
      <nav className="actions" aria-label="Finance sections">
        <button type="button" onClick={() => setSubTab("overview")}>Overview</button>
        <button type="button" onClick={() => setSubTab("invoices")}>Invoices</button>
        <button type="button" onClick={() => setSubTab("adjustments")}>Adjustments</button>
        <button type="button" onClick={() => setSubTab("periods")}>Periods</button>
      </nav>
      {subTab === "overview" && (/* ... */)}
      {subTab === "invoices" && (/* ... */)}
      {subTab === "adjustments" && (/* ... */)}
      {subTab === "periods" && (/* ... */)}
    </section>
  );
}
```

Helper for `datetime-local` ↔ ISO (include in same file):

```typescript
function toDatetimeLocalValue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromDatetimeLocalValue(local: string): string {
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) throw new Error("Invalid datetime");
  return d.toISOString();
}
```

- [ ] **Step 5: Wire `App.tsx`**

- Import `FinancePanel`.
- Remove finance-only `useState` / `loadFinance` / invoice-adjustment-period form handlers / the large `{tab === "finance" && (...)}` block body.
- Replace with:

```tsx
{tab === "finance" && (
  <FinancePanel
    api={api}
    scopes={scopes}
    canPause={canPause(scopes)}
    scopeNotice={scopeNotice}
    runAction={runAction}
    status={status}
  />
)}
```

Ensure `runAction` / `status` / `scopeNotice` signatures match; adapt with thin wrappers in `App.tsx` if needed rather than rewriting global helpers.

Remove obsolete ids `invoice-start`, `adj-billed` from `App.tsx` (they live in the panel if still needed for a11y — panel may use new ids; assertions no longer require them in `App.tsx`).

- [ ] **Step 6: Build + assertion test**

```bash
cd companion && npm run build
cd .. && .venv/bin/python -m unittest tests.test_companion_api.CompanionApiTests.test_companion_wires_finance -v
```

Expected: build OK; unittest OK.

- [ ] **Step 7: Commit**

```bash
git add companion/src/financeMoney.ts companion/src/FinancePanel.tsx companion/src/api/client.ts companion/src/App.tsx tests/test_companion_api.py
git commit -m "$(cat <<'EOF'
Add companion FinancePanel with billed-cost picker UX.

EOF
)"
```

---

### Task 3: Docs, ADR-038 note, version 0.3.62

**Files:**
- Modify: `docs/16-api-contract.md` (finance table)
- Modify: `docs/24-mobile-companion.md` (Finance section)
- Modify: `docs/decisions.md` (ADR-038 consequences + table line if needed)
- Modify: `docs/14-roadmap.md` / handoff
- Modify: `docs/18-handoff.md`
- Modify: `company/__init__.py` → `0.3.62`
- Modify: `companion/package.json` → `0.3.62`
- Modify: spec status line to **implemented** when shipping (optional in this task)
- Update plan checkbox status if desired

- [ ] **Step 1: API contract**

Add row after finance summary / before invoices (or after adjustments):

```markdown
| GET /finance/billed-costs | Creditable billed lines + remaining_creditable_cents | company.read |
```

- [ ] **Step 2: Companion + ADR + handoff**

In `docs/24-mobile-companion.md`, note Finance sub-tabs Overview / Invoices / Adjustments / Periods and that display uses `formatUsd` while API stays cents.

ADR-038 consequences — append:

```markdown
Companion lists creditable `billed_costs` via `GET /finance/billed-costs` for refund UX; this is read-only and does not change adjustment math.
```

`docs/18-handoff.md`: version **0.3.62**; Finance UX polish shipped; **Next:** TailscaleKit / second-host polish, then deeper marketing redesign.

Roadmap: check or note companion Finance UX polish done; fix stale “Next: P3 finance” if still present.

- [ ] **Step 3: Version bump**

```python
# company/__init__.py
__version__ = "0.3.62"
```

```json
"version": "0.3.62"
```

in `companion/package.json`.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests pass; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add docs/16-api-contract.md docs/24-mobile-companion.md docs/decisions.md docs/14-roadmap.md docs/18-handoff.md company/__init__.py companion/package.json docs/superpowers/specs/2026-09-08-finance-ux-polish-design.md
git commit -m "$(cat <<'EOF'
Document Finance UX polish and release 0.3.62.

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| `GET /finance/billed-costs` + remaining | 1 |
| Default exclude fully credited; include flag; limit | 1 |
| `FinancePanel` sub-tabs Overview/Invoices/Adjustments/Periods | 2 |
| `formatUsd` display-only | 2 |
| Invoice expand via GET by id | 2 |
| datetime-local + month preset | 2 |
| Refund select; no paste-id; empty list disables | 2 |
| Confirm before close; prefill next period | 2 |
| Docs / ADR-038 sentence / 0.3.62 / handoff → TailscaleKit | 3 |
| No Alembic; money rules unchanged | Global + 1–3 |

## Verification (merge gate)

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```
