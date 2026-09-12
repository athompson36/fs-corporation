# Desk Finance Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace desk Money `#budget` JSON dump with a full Finance surface (summary, lists, create forms, close-period) at v0.3.78.

**Architecture:** In-place expand the `#budget` glass section in `company/service.py` DESK_HTML: rail/title label **Finance**, structured overview from `/api/v1/finance/summary`, list ULs + create forms, desk JS `loadFinance()` called from `load()`, mutations via existing finance APIs with `Idempotency-Key`, pause gate disables mutate controls on 403.

**Tech Stack:** Desk HTML/JS inside `DESK_HTML` (`company/service.py`), existing `/api/v1/finance/*`, Python unittest source contracts.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-desk-finance-surface-design.md` (owner-approved).
- Keep `id="budget"` and `href="#budget"`; visible label **Finance**.
- No desk ModeSwitch / ManageClusters / URL sync. No new APIs or Alembic.
- Replace `budget-json` entirely (do not keep dashboard credit JSON in this section).
- Version **0.3.78**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-finance-surface` from current `main` before Task 1.
- Soften older exact version pins to `0\.3\.\d+`; exact `0.3.78` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `tests/test_desk_finance_surface.py` | Source contracts for desk Finance (0.3.78) |
| `company/service.py` | DESK_HTML markup + desk JS |
| `company/__init__.py`, `companion/package.json` | Version **0.3.78** |
| `tests/test_finance_browse_manage.py` | Soften exact `0.3.77` pin |
| Docs | UX, ADR-060, roadmap, handoff; mark design spec implemented |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_desk_finance_surface.py`

**Interfaces:**
- Consumes: none
- Produces: RED contracts Tasks 2–5 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-finance-surface
```

- [ ] **Step 2: Write the test module**

```python
"""Desk Finance surface (v0.3.78)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskFinanceSurfaceTests(unittest.TestCase):
    def test_rail_and_heading_finance_keep_budget_id(self):
        self.assertIn('href="#budget"', DESK_HTML)
        self.assertIn('id="budget"', DESK_HTML)
        self.assertRegex(DESK_HTML, r'href="#budget">\s*Finance\s*<')
        self.assertRegex(DESK_HTML, r'id="budget"[^>]*>\s*<h2>\s*Finance\s*</h2>')
        self.assertNotIn('href="#budget">Budget<', DESK_HTML)
        self.assertNotIn("<h2>Budget</h2>", DESK_HTML)

    def test_no_budget_json_dump(self):
        self.assertNotIn("budget-json", DESK_HTML)
        self.assertNotIn("simulated_spend_cents", DESK_HTML)

    def test_finance_markup_ids(self):
        for marker in (
            "finance-overview",
            "finance-invoice-list",
            "finance-adjustment-list",
            "finance-period-list",
            "finance-invoice-form",
            "finance-adjustment-form",
            "finance-period-form",
            "finance-scope-notice",
            "finance-load-error",
            "desk-finance-invoice-start",
            "desk-finance-invoice-end",
            "desk-finance-adjustment-kind",
            "desk-finance-billed-cost",
            "desk-finance-adjustment-amount",
            "desk-finance-adjustment-reason",
            "desk-finance-period-start",
            "desk-finance-period-end",
            "desk-finance-period-limit",
        ):
            self.assertIn(marker, DESK_HTML)

    def test_finance_api_and_helpers(self):
        self.assertIn("/api/v1/finance/summary", DESK_HTML)
        self.assertIn("/api/v1/finance/invoices", DESK_HTML)
        self.assertIn("/api/v1/finance/adjustments", DESK_HTML)
        self.assertIn("/api/v1/finance/budget-periods", DESK_HTML)
        self.assertIn("/api/v1/finance/billed-costs", DESK_HTML)
        self.assertIn("loadFinance", DESK_HTML)
        self.assertIn("formatFinanceUsd", DESK_HTML)
        self.assertIn("setFinanceMutateEnabled", DESK_HTML)
        self.assertIn("desk-finance-", DESK_HTML)
        self.assertIn("Close period", DESK_HTML)

    def test_version_0_3_78(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.78"', init)
        self.assertIn('"version": "0.3.78"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_desk_finance_surface -v`

Expected: FAIL (Budget label / `budget-json` / missing markers / version not 0.3.78).

- [ ] **Step 4: Commit**

```bash
git add tests/test_desk_finance_surface.py
git commit -m "$(cat <<'EOF'
test: desk Finance surface contracts (0.3.78)

EOF
)"
```

---

### Task 2: Desk HTML shell (rail + section markup)

**Files:**
- Modify: `company/service.py` (DESK_HTML rail link ~line 127; `#budget` section ~321–324)

**Interfaces:**
- Consumes: Task 1 id/marker names
- Produces: Static markup containers and form shells; JS wiring comes in Tasks 3–4

- [ ] **Step 1: Update Money rail label**

Replace:

```html
<a href="#budget">Budget</a>
```

with:

```html
<a href="#budget">Finance</a>
```

- [ ] **Step 2: Replace the `#budget` section body**

Replace the entire:

```html
<section class="glass" id="budget"><h2>Budget</h2>
<p class="muted">Simulated credits, billed cost, and revenue are separate totals.</p>
<pre id="budget-json">Loading…</pre>
</section>
```

with:

```html
<section class="glass" id="budget"><h2>Finance</h2>
<p class="muted">Persisted finance totals and lists; create invoice, adjustment, and period below. API amounts are cents; display is USD.</p>
<p id="finance-load-error" class="muted" hidden></p>
<p id="finance-scope-notice" class="muted" hidden>Mutations require company.pause.</p>
<h3>Overview</h3>
<div id="finance-overview" class="muted">Loading…</div>
<h3>Invoices</h3>
<ul id="finance-invoice-list"></ul>
<h3>Adjustments</h3>
<ul id="finance-adjustment-list"></ul>
<h3>Periods</h3>
<ul id="finance-period-list"></ul>
<form id="finance-invoice-form" class="compact">
<h3>Create invoice</h3>
<label for="desk-finance-invoice-start">Period start</label>
<input id="desk-finance-invoice-start" type="datetime-local" required/>
<label for="desk-finance-invoice-end">Period end</label>
<input id="desk-finance-invoice-end" type="datetime-local" required/>
<div class="row">
<button type="button" class="chip" id="desk-finance-invoice-month">This calendar month</button>
<button type="submit" class="chip" id="desk-finance-invoice-submit">Create invoice</button>
<span class="muted" id="finance-invoice-status"></span>
</div>
</form>
<form id="finance-adjustment-form" class="compact">
<h3>Post adjustment</h3>
<label for="desk-finance-adjustment-kind">Kind</label>
<select id="desk-finance-adjustment-kind">
<option value="partial_credit">partial_credit</option>
<option value="void">void</option>
</select>
<label for="desk-finance-billed-cost">Creditable billed cost</label>
<select id="desk-finance-billed-cost" required></select>
<label for="desk-finance-adjustment-amount">Amount cents (partial_credit)</label>
<input id="desk-finance-adjustment-amount" type="number" min="1" step="1"/>
<label for="desk-finance-adjustment-reason">Reason</label>
<input id="desk-finance-adjustment-reason" required/>
<button type="submit" class="chip" id="desk-finance-adjustment-submit">Post adjustment</button>
<span class="muted" id="finance-adjustment-status"></span>
</form>
<form id="finance-period-form" class="compact">
<h3>Set budget period</h3>
<label for="desk-finance-period-start">Start</label>
<input id="desk-finance-period-start" type="datetime-local" required/>
<label for="desk-finance-period-end">End</label>
<input id="desk-finance-period-end" type="datetime-local" required/>
<label for="desk-finance-period-limit">Limit cents</label>
<input id="desk-finance-period-limit" type="number" min="0" step="1" value="500000" required/>
<div class="row">
<button type="button" class="chip" id="desk-finance-period-30d">Next 30 days</button>
<button type="submit" class="chip" id="desk-finance-period-submit">Set period</button>
<span class="muted" id="finance-period-status"></span>
</div>
</form>
</section>
```

- [ ] **Step 3: Remove dashboard JSON write from `load()`**

Delete this block inside `async function load()` (keep the surrounding `dash` fetch if still used for other metrics — only remove the `budget-json` assignment):

```javascript
  document.getElementById('budget-json').textContent = JSON.stringify({
    simulated_spend_cents: company.simulated_spend_cents,
    billed_cost_cents: company.billed_cost_cents,
    revenue_cents: company.revenue_cents,
    reserved_cents: company.reserved_cents,
    note: 'Simulated credits stay separate from billed cost and revenue'
  });
```

If `company` from `dashj` becomes unused after this deletion, remove only the unused locals that this block required — do **not** remove the dashboard fetch if metrics still need it. Prefer leaving `const company = dashj.company || {};` if still referenced; otherwise drop unused bindings to avoid lint noise (desk has no JS linter — leave harmless locals if unsure).

- [ ] **Step 4: Run markup-focused tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_desk_finance_surface.DeskFinanceSurfaceTests.test_rail_and_heading_finance_keep_budget_id \
  tests.test_desk_finance_surface.DeskFinanceSurfaceTests.test_no_budget_json_dump \
  tests.test_desk_finance_surface.DeskFinanceSurfaceTests.test_finance_markup_ids \
  -v
```

Expected: those three PASS. `test_finance_api_and_helpers` and `test_version_0_3_78` still FAIL.

Also run desk IA / API contracts that require `#budget`:

```bash
.venv/bin/python -m unittest tests.test_desk_ia_five_domains -v
.venv/bin/python -m unittest tests.test_api -v -k budget
```

Expected: PASS (`href="#budget"` preserved).

- [ ] **Step 5: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): Finance section markup replacing budget JSON

EOF
)"
```

---

### Task 3: loadFinance + render lists/overview/expand

**Files:**
- Modify: `company/service.py` (DESK_HTML `<script>` — helpers + `loadFinance` + call from `load()`)

**Interfaces:**
- Consumes: markup ids from Task 2
- Produces: `formatFinanceUsd`, `loadFinance`, invoice expand; Tasks 4 attaches form handlers

- [ ] **Step 1: Add helpers and finance state near other desk JS helpers** (after `function pad` / before `load` is fine)

```javascript
function formatFinanceUsd(cents) {
  const n = Number(cents);
  if (!Number.isFinite(n)) return '$—';
  return new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(n / 100);
}
function toFinanceLocalValue(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const p = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
    + 'T' + p(d.getHours()) + ':' + p(d.getMinutes());
}
function fromFinanceLocalValue(local) {
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) throw new Error('Invalid datetime');
  return d.toISOString();
}
let financeBilledCosts = [];
let financeExpandedInvoiceId = '';
function setFinanceMutateEnabled(enabled) {
  const notice = document.getElementById('finance-scope-notice');
  notice.hidden = !!enabled;
  [
    'desk-finance-invoice-submit',
    'desk-finance-adjustment-submit',
    'desk-finance-period-submit',
    'desk-finance-invoice-month',
    'desk-finance-period-30d',
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  });
  document.querySelectorAll('[data-finance-close]').forEach(btn => {
    btn.disabled = !enabled;
  });
}
function renderFinanceOverview(summary) {
  const el = document.getElementById('finance-overview');
  if (!summary) {
    el.textContent = 'No finance summary loaded.';
    return;
  }
  const open = summary.open_budget_period;
  el.innerHTML = '';
  const lines = [
    'Gross billed: ' + formatFinanceUsd(summary.billed_cost_gross_cents),
    'Adjustments: ' + formatFinanceUsd(summary.billed_adjustment_cents),
    'Net billed: ' + formatFinanceUsd(summary.billed_cost_cents),
    'Revenue: ' + formatFinanceUsd(summary.revenue_cents),
  ];
  lines.forEach(text => {
    const div = document.createElement('div');
    div.textContent = text;
    el.appendChild(div);
  });
  const openLine = document.createElement('p');
  openLine.className = 'muted';
  if (open) {
    openLine.textContent = 'Open period: ' + open.period_start + ' → ' + open.period_end
      + ' · limit ' + formatFinanceUsd(open.limit_cents);
  } else {
    openLine.textContent = 'No open budget period.';
  }
  el.appendChild(openLine);
}
async function toggleFinanceInvoice(invoiceId) {
  const list = document.getElementById('finance-invoice-list');
  const existing = list.querySelector('[data-invoice-detail="' + invoiceId + '"]');
  if (financeExpandedInvoiceId === invoiceId) {
    financeExpandedInvoiceId = '';
    if (existing) existing.remove();
    return;
  }
  financeExpandedInvoiceId = invoiceId;
  list.querySelectorAll('[data-invoice-detail]').forEach(node => node.remove());
  const detail = document.createElement('li');
  detail.dataset.invoiceDetail = invoiceId;
  detail.className = 'muted';
  detail.textContent = 'Loading lines…';
  const parentBtn = list.querySelector('[data-invoice-id="' + invoiceId + '"]');
  if (parentBtn && parentBtn.parentElement) {
    parentBtn.parentElement.insertAdjacentElement('afterend', detail);
  } else {
    list.appendChild(detail);
  }
  try {
    const res = await fetch('/api/v1/finance/invoices/' + encodeURIComponent(invoiceId), {headers});
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof body === 'string' ? body : (body.detail || res.statusText));
    const lines = ((body.body || {}).lines) || body.lines || [];
    detail.textContent = '';
    if (!lines.length) {
      detail.textContent = 'No line items.';
      return;
    }
    lines.forEach(line => {
      const row = document.createElement('div');
      row.textContent = (line.provider || '') + ' · ' + formatFinanceUsd(line.amount_cents)
        + ' · ' + (line.billed_cost_id || '');
      detail.appendChild(row);
    });
  } catch (error) {
    detail.textContent = error instanceof Error ? error.message : String(error);
  }
}
function renderFinanceInvoices(invoices) {
  const list = document.getElementById('finance-invoice-list');
  list.innerHTML = '';
  if (!(invoices || []).length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No invoices yet.';
    list.appendChild(li);
    return;
  }
  invoices.forEach(invoice => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip';
    btn.dataset.invoiceId = invoice.id;
    btn.textContent = String(invoice.id).slice(0, 8) + '… · ' + formatFinanceUsd(invoice.total_cents);
    btn.addEventListener('click', () => { void toggleFinanceInvoice(String(invoice.id)); });
    const meta = document.createElement('div');
    meta.className = 'muted';
    meta.textContent = (invoice.period_start || '') + ' → ' + (invoice.period_end || '')
      + ' · ' + (invoice.line_count || 0) + ' lines';
    li.appendChild(btn);
    li.appendChild(meta);
    list.appendChild(li);
  });
}
function renderFinanceAdjustments(adjustments) {
  const list = document.getElementById('finance-adjustment-list');
  list.innerHTML = '';
  if (!(adjustments || []).length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No adjustments yet.';
    list.appendChild(li);
    return;
  }
  adjustments.forEach(item => {
    const li = document.createElement('li');
    li.innerHTML = '<strong></strong><div class="muted"></div>';
    li.querySelector('strong').textContent = item.kind || '';
    li.querySelector('div').textContent = (item.billed_cost_id || '') + ' · '
      + formatFinanceUsd(item.amount_cents) + ' · ' + (item.reason || '');
    list.appendChild(li);
  });
}
function renderFinancePeriods(periods) {
  const list = document.getElementById('finance-period-list');
  list.innerHTML = '';
  if (!(periods || []).length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No budget periods.';
    list.appendChild(li);
    return;
  }
  periods.forEach(period => {
    const li = document.createElement('li');
    const meta = document.createElement('div');
    meta.textContent = (period.period_start || '') + ' → ' + (period.period_end || '')
      + ' · limit ' + formatFinanceUsd(period.limit_cents)
      + (period.closed_at ? ' · closed' : ' · open');
    li.appendChild(meta);
    if (!period.closed_at) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip';
      btn.dataset.financeClose = String(period.id);
      btn.textContent = 'Close period';
      btn.addEventListener('click', () => { void closeFinancePeriod(period); });
      li.appendChild(btn);
    }
    list.appendChild(li);
  });
  setFinanceMutateEnabled(document.getElementById('finance-scope-notice').hidden);
}
function fillFinanceBilledCosts(costs) {
  financeBilledCosts = costs || [];
  const select = document.getElementById('desk-finance-billed-cost');
  const prev = select.value;
  select.innerHTML = '';
  if (!financeBilledCosts.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No creditable lines';
    select.appendChild(opt);
    return;
  }
  financeBilledCosts.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = (item.provider || '') + ' · ' + formatFinanceUsd(item.amount_cents)
      + ' · remaining ' + formatFinanceUsd(item.remaining_creditable_cents);
    select.appendChild(opt);
  });
  if (financeBilledCosts.some(item => item.id === prev)) select.value = prev;
}
async function loadFinance() {
  const err = document.getElementById('finance-load-error');
  err.hidden = true;
  err.textContent = '';
  try {
    const [summaryRes, invRes, adjRes, perRes, costRes] = await Promise.all([
      fetch('/api/v1/finance/summary', {headers}),
      fetch('/api/v1/finance/invoices', {headers}),
      fetch('/api/v1/finance/adjustments', {headers}),
      fetch('/api/v1/finance/budget-periods', {headers}),
      fetch('/api/v1/finance/billed-costs', {headers}),
    ]);
    const summary = await summaryRes.json().catch(() => null);
    const invoices = await invRes.json().catch(() => ({}));
    const adjustments = await adjRes.json().catch(() => ({}));
    const periods = await perRes.json().catch(() => ({}));
    const costs = await costRes.json().catch(() => ({}));
    if (![summaryRes, invRes, adjRes, perRes, costRes].every(r => r.ok)) {
      throw new Error('Finance data could not be loaded.');
    }
    renderFinanceOverview(summary);
    renderFinanceInvoices(invoices.invoices || []);
    renderFinanceAdjustments(adjustments.adjustments || []);
    renderFinancePeriods(periods.periods || []);
    fillFinanceBilledCosts(costs.billed_costs || []);
  } catch (error) {
    renderFinanceOverview(null);
    renderFinanceInvoices([]);
    renderFinanceAdjustments([]);
    renderFinancePeriods([]);
    fillFinanceBilledCosts([]);
    err.hidden = false;
    err.textContent = 'Finance data could not be loaded: '
      + (error instanceof Error ? error.message : String(error));
  }
}
```

Add a stub so Task 3 runs without Task 4 handlers blowing up on close clicks:

```javascript
async function closeFinancePeriod(period) {
  console.warn('closeFinancePeriod not wired', period && period.id);
}
```

Task 4 replaces this stub with the real implementation.

- [ ] **Step 2: Call `loadFinance` from `load()`**

Near the end of `async function load()` (after org/dashboard work is fine; before HQ SVG work is also fine), add:

```javascript
  await loadFinance();
```

- [ ] **Step 3: Run helper/API contracts**

Run: `.venv/bin/python -m unittest tests.test_desk_finance_surface.DeskFinanceSurfaceTests.test_finance_api_and_helpers -v`

Expected: PASS (version test still FAIL).

- [ ] **Step 4: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): load and render Finance overview and lists

EOF
)"
```

---

### Task 4: Mutations, close period, pause gate

**Files:**
- Modify: `company/service.py` (replace `closeFinancePeriod` stub; add form listeners; wire pause gate)

**Interfaces:**
- Consumes: `loadFinance`, `formatFinanceUsd`, `fromFinanceLocalValue`, `toFinanceLocalValue`, `setFinanceMutateEnabled`, `financeBilledCosts`
- Produces: working create/close flows

- [ ] **Step 1: Replace `closeFinancePeriod` stub and add `postFinanceCommand`**

```javascript
async function postFinanceCommand(path, payload, idempotencyKey) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({payload}),
  });
  const text = await res.text();
  let body = text;
  try { body = text ? JSON.parse(text) : {}; } catch (e) { body = text; }
  if (res.status === 403) {
    setFinanceMutateEnabled(false);
  }
  if (!res.ok) {
    const detail = (body && body.detail) ? body.detail : text;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return body;
}
async function closeFinancePeriod(period) {
  if (!window.confirm('Close this budget period? Snapshot will be frozen.')) return;
  try {
    await postFinanceCommand(
      '/api/v1/finance/budget-periods/' + encodeURIComponent(String(period.id)) + '/close',
      {},
      'desk-finance-close-' + period.id + '-' + Date.now(),
    );
    document.getElementById('desk-finance-period-start').value =
      toFinanceLocalValue(String(period.period_end));
    document.getElementById('finance-period-status').textContent = ' Period closed.';
    await loadFinance();
  } catch (error) {
    document.getElementById('finance-period-status').textContent =
      ' ' + (error instanceof Error ? error.message : String(error));
  }
}
```

- [ ] **Step 2: Wire form listeners** (near other `addEventListener('submit')` blocks)

```javascript
document.getElementById('desk-finance-invoice-month').addEventListener('click', () => {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 1, 0, 0);
  document.getElementById('desk-finance-invoice-start').value = toFinanceLocalValue(start.toISOString());
  document.getElementById('desk-finance-invoice-end').value = toFinanceLocalValue(end.toISOString());
});
document.getElementById('desk-finance-period-30d').addEventListener('click', () => {
  const start = new Date();
  const end = new Date(start);
  end.setDate(end.getDate() + 30);
  document.getElementById('desk-finance-period-start').value = toFinanceLocalValue(start.toISOString());
  document.getElementById('desk-finance-period-end').value = toFinanceLocalValue(end.toISOString());
});
document.getElementById('desk-finance-adjustment-kind').addEventListener('change', () => {
  const kind = document.getElementById('desk-finance-adjustment-kind').value;
  document.getElementById('desk-finance-adjustment-amount').disabled = kind !== 'partial_credit';
});
document.getElementById('finance-invoice-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = document.getElementById('finance-invoice-status');
  try {
    await postFinanceCommand(
      '/api/v1/finance/invoices',
      {
        period_start: fromFinanceLocalValue(document.getElementById('desk-finance-invoice-start').value),
        period_end: fromFinanceLocalValue(document.getElementById('desk-finance-invoice-end').value),
      },
      'desk-finance-inv-' + Date.now(),
    );
    status.textContent = ' Invoice created.';
    event.target.reset();
    await loadFinance();
  } catch (error) {
    status.textContent = ' ' + (error instanceof Error ? error.message : String(error));
  }
});
document.getElementById('finance-adjustment-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = document.getElementById('finance-adjustment-status');
  try {
    const kind = document.getElementById('desk-finance-adjustment-kind').value;
    const billedCostId = document.getElementById('desk-finance-billed-cost').value;
    const reason = document.getElementById('desk-finance-adjustment-reason').value.trim();
    if (!billedCostId) throw new Error('Select a creditable billed cost.');
    if (!reason) throw new Error('Reason is required.');
    const payload = {kind, billed_cost_id: billedCostId, reason};
    if (kind === 'partial_credit') {
      const amount = Number(document.getElementById('desk-finance-adjustment-amount').value);
      const selected = financeBilledCosts.find(item => item.id === billedCostId);
      if (!Number.isFinite(amount) || amount <= 0) throw new Error('Partial credit must be greater than zero.');
      if (selected && amount > selected.remaining_creditable_cents) {
        throw new Error('Partial credit exceeds the remaining creditable amount.');
      }
      payload.amount_cents = amount;
    }
    await postFinanceCommand(
      '/api/v1/finance/adjustments',
      payload,
      'desk-finance-adj-' + Date.now(),
    );
    status.textContent = ' Adjustment recorded.';
    document.getElementById('desk-finance-adjustment-amount').value = '';
    document.getElementById('desk-finance-adjustment-reason').value = '';
    await loadFinance();
  } catch (error) {
    status.textContent = ' ' + (error instanceof Error ? error.message : String(error));
  }
});
document.getElementById('finance-period-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = document.getElementById('finance-period-status');
  try {
    await postFinanceCommand(
      '/api/v1/finance/budget-periods',
      {
        scope: 'company',
        period_start: fromFinanceLocalValue(document.getElementById('desk-finance-period-start').value),
        period_end: fromFinanceLocalValue(document.getElementById('desk-finance-period-end').value),
        limit_cents: Number(document.getElementById('desk-finance-period-limit').value),
      },
      'desk-finance-period-' + Date.now(),
    );
    status.textContent = ' Budget period set.';
    await loadFinance();
  } catch (error) {
    status.textContent = ' ' + (error instanceof Error ? error.message : String(error));
  }
});
setFinanceMutateEnabled(true);
document.getElementById('desk-finance-adjustment-amount').disabled =
  document.getElementById('desk-finance-adjustment-kind').value !== 'partial_credit';
```

- [ ] **Step 3: Run desk finance + desk IA tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_desk_finance_surface tests.test_desk_ia_five_domains -v
```

Expected: all desk finance tests except version PASS (or all PASS if Task 5 already bumped — normally version still FAIL).

- [ ] **Step 4: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): Finance create/close mutations and pause gate

EOF
)"
```

---

### Task 5: Version 0.3.78 + docs

**Files:**
- Modify: `company/__init__.py`
- Modify: `companion/package.json`
- Modify: `tests/test_finance_browse_manage.py` (soften exact `0.3.77`)
- Modify: `docs/11-user-experience.md`
- Modify: `docs/decisions.md` (ADR-060 index + detail)
- Modify: `docs/14-roadmap.md`
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-12-desk-finance-surface-design.md` (status → implemented)
- Modify: `README.md` if version/capability row lists desk Budget

**Interfaces:**
- Consumes: completed Tasks 2–4 behavior
- Produces: release docs + green `test_version_0_3_78`

- [ ] **Step 1: Bump versions**

`company/__init__.py`:

```python
__version__ = "0.3.78"
```

`companion/package.json`:

```json
"version": "0.3.78",
```

- [ ] **Step 2: Soften prior finance browse exact pin**

In `tests/test_finance_browse_manage.py` `test_version_lockstep`, replace exact `0.3.77` asserts with:

```python
self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

- [ ] **Step 3: Docs**

- `docs/11-user-experience.md`: Money is **Finance** (section id remains `#budget`); desk surfaces finance summary/lists/forms like companion capabilities without ModeSwitch.
- `docs/decisions.md` index row:

```markdown
| ADR-060 | 2026-09-12 | Desk Finance surface | Expand `#budget` into Finance label + summary/lists/forms/close; keep id; no ModeSwitch; no new APIs. |
```

Add ADR-060 detail section summarizing the decision (desk-native parity; keep `#budget`; replace JSON dump).

- `docs/14-roadmap.md`: add checked M8/companion-adjacent item for Desk Finance surface (0.3.78); update status blurb + **Immediate next** to post-ship polish / owner-directed.
- `docs/18-handoff.md`: rewrite for 0.3.78 on feature branch (or on `main` if merging later); list desk Finance markers; verification commands.
- Spec status → `implemented in v0.3.78`.
- `README.md`: only if it still says desk Money is Budget JSON — align wording.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build OK at 0.3.78.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json tests/test_finance_browse_manage.py \
  tests/test_desk_finance_surface.py docs/11-user-experience.md docs/decisions.md \
  docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-desk-finance-surface-design.md README.md
git commit -m "$(cat <<'EOF'
docs: Desk Finance surface and release 0.3.78

EOF
)"
```

(Only `git add README.md` if it actually changed.)

---

## Plan self-review

1. **Spec coverage:** Structure (§1) → Task 2; data/mutations (§2) → Tasks 3–4; verification/docs/version (§3) → Tasks 1+5; non-goals respected (no ModeSwitch, no `#finance` rename, no new APIs).
2. **Placeholders:** none intentionally left.
3. **Type/name consistency:** markup ids and helper names match across Tasks 1–4 (`loadFinance`, `formatFinanceUsd`, `setFinanceMutateEnabled`, `desk-finance-*`).

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-12-desk-finance-surface.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
