# Finance Open-Next Period + Pricing Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.86 with explicit `open-next` budget period after close, finance summary pricing honesty, and desk + companion UI — without reinventing ADR-038 invoices.

**Architecture:** Add `open_next_budget_period` in `company/finance.py` reusing `set_budget_period`; extend `finance_summary` with a pricing honesty block resolved like live invoke rates; wire one POST route; desk/companion call it under existing `company.pause` mutate gates.

**Tech Stack:** Python company core/finance/FastAPI desk HTML, React companion FinancePanel, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-finance-open-next-pricing-design.md` (owner-approved).
- Version **0.3.86**. Soften exact `0.3.85` pins to `0\.3\.\d+` where needed.
- Open-next is **not** a side effect of close.
- Auth: `company.pause` + same CEO/admin actor rules as close / set period.
- Defaults: contiguous window, same scope + limit; payload overrides allowed.
- Pricing: honesty only — never invent billed amounts. Hint copy exactly:
  `Billed lines may stay $0 until FS_CORP_MODEL_CENTS_PER_1K_TOKENS or a profile rate is set.`
- Surfaces: API + desk `#budget` + companion `FinancePanel.tsx`.
- Alembic: **none**.
- No consultant / 0.3.87 work.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/finance-open-next-pricing` from current `main` before Task 1.
- Work in-place on the feature branch.

## File map

| Path | Role |
|---|---|
| `company/finance.py` | `open_next_budget_period`, pricing block in `finance_summary` |
| `company/core.py` | Thin wrappers `open_next_budget_period`, ensure summary path |
| `company/service.py` | Route + DESK_HTML open-next + pricing hint |
| `companion/src/FinancePanel.tsx` | Open next + overview hint |
| `tests/test_durable_finance.py` | Core behavior |
| `tests/test_desk_finance_open_next.py` (new) | Desk source contracts |
| Docs + versions | ADR-068, API contract, VERIFICATION, handoff, roadmap; **0.3.86** |

---

### Task 1: RED/GREEN finance open-next + pricing summary

**Files:**
- Modify: `company/finance.py`, `company/core.py`
- Modify: `tests/test_durable_finance.py`
- Modify: `company/service.py` (API route only in this task — or Task 2; prefer route here so API tests can use `owner_client`)

**Interfaces:**
- Produces:
  - `open_next_budget_period(company, actor, period_id, *, scope=None, period_start=None, period_end=None, limit_cents=None) -> dict` (period list item shape)
  - `finance_summary` includes `pricing: {model_cents_per_1k_configured: bool, hint: str}`
  - `Company.open_next_budget_period(...)` thin wrapper
  - `POST /api/v1/finance/budget-periods/{period_id}/open-next`

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/finance-open-next-pricing
```

- [ ] **Step 2: Write failing tests in `tests/test_durable_finance.py`**

Append (adjust imports if needed):

```python
class OpenNextPeriodTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def _closed_period(self, start_offset_days=-40, end_offset_days=-10, limit=5000):
        start = (now() + timedelta(days=start_offset_days)).isoformat()
        end = (now() + timedelta(days=end_offset_days)).isoformat()
        pid = self.c.set_budget_period("human-ceo", "company", start, end, limit)
        self.c.close_budget_period("human-ceo", pid)
        return pid, start, end, limit

    def test_open_next_defaults_contiguous(self):
        pid, start, end, limit = self._closed_period()
        nxt = self.c.open_next_budget_period("human-ceo", pid)
        self.assertFalse(nxt["closed"])
        self.assertEqual(nxt["scope"], "company")
        self.assertEqual(nxt["period_start"], end)
        start_dt = __import__("datetime").datetime.fromisoformat(start)
        end_dt = __import__("datetime").datetime.fromisoformat(end)
        expected_end = (end_dt + (end_dt - start_dt)).isoformat()
        self.assertEqual(nxt["period_end"], expected_end)
        self.assertEqual(nxt["limit_cents"], limit)

    def test_open_next_overrides(self):
        pid, _, end, _ = self._closed_period()
        new_end = (now() + timedelta(days=60)).isoformat()
        nxt = self.c.open_next_budget_period(
            "human-ceo", pid,
            period_start=end,
            period_end=new_end,
            limit_cents=9000,
            scope="company",
        )
        self.assertEqual(nxt["limit_cents"], 9000)
        self.assertEqual(nxt["period_end"], new_end)

    def test_open_next_rejects_unclosed(self):
        start = (now() - timedelta(days=1)).isoformat()
        end = (now() + timedelta(days=30)).isoformat()
        pid = self.c.set_budget_period("human-ceo", "company", start, end, 5000)
        with self.assertRaises(PermissionError):
            self.c.open_next_budget_period("human-ceo", pid)

    def test_open_next_rejects_when_other_open_exists(self):
        pid, _, end, _ = self._closed_period()
        # another open period covering "now"
        self.c.set_budget_period(
            "human-ceo", "company",
            (now() - timedelta(days=1)).isoformat(),
            (now() + timedelta(days=30)).isoformat(),
            1000,
        )
        with self.assertRaises(PermissionError):
            self.c.open_next_budget_period("human-ceo", pid)

    def test_open_next_rejects_duplicate_successor(self):
        pid, _, end, _ = self._closed_period()
        self.c.open_next_budget_period("human-ceo", pid)
        with self.assertRaises(PermissionError):
            self.c.open_next_budget_period("human-ceo", pid)

    def test_open_next_rejects_non_ceo(self):
        pid, _, _, _ = self._closed_period()
        with self.assertRaises(PermissionError):
            self.c.open_next_budget_period("other-actor", pid)


class FinancePricingHonestyTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_summary_pricing_unset(self):
        import os
        old = os.environ.pop("FS_CORP_MODEL_CENTS_PER_1K_TOKENS", None)
        self.addCleanup(
            lambda: os.environ.__setitem__("FS_CORP_MODEL_CENTS_PER_1K_TOKENS", old)
            if old is not None else os.environ.pop("FS_CORP_MODEL_CENTS_PER_1K_TOKENS", None)
        )
        summary = self.c.finance_summary()
        self.assertIn("pricing", summary)
        self.assertFalse(summary["pricing"]["model_cents_per_1k_configured"])
        self.assertIn("FS_CORP_MODEL_CENTS_PER_1K_TOKENS", summary["pricing"]["hint"])

    def test_summary_pricing_env_set(self):
        import os
        os.environ["FS_CORP_MODEL_CENTS_PER_1K_TOKENS"] = "5"
        self.addCleanup(lambda: os.environ.pop("FS_CORP_MODEL_CENTS_PER_1K_TOKENS", None))
        summary = self.c.finance_summary()
        self.assertTrue(summary["pricing"]["model_cents_per_1k_configured"])
```

Also add API smoke with `owner_client` if pattern exists in this file; otherwise company-level tests suffice for Task 1 and route is verified in Task 2 desk/API.

- [ ] **Step 3: Run RED**

```bash
.venv/bin/python -m unittest tests.test_durable_finance.OpenNextPeriodTests tests.test_durable_finance.FinancePricingHonestyTests -v
```

Expected: FAIL (missing methods / pricing key).

- [ ] **Step 4: Implement `open_next_budget_period` in `company/finance.py`**

```python
PRICING_HINT = (
    "Billed lines may stay $0 until FS_CORP_MODEL_CENTS_PER_1K_TOKENS "
    "or a profile rate is set."
)

def model_cents_per_1k_configured(company) -> bool:
    """True when invoke pricing can resolve a configured rate source (env/settings or profile)."""
    import os
    raw = (os.environ.get("FS_CORP_MODEL_CENTS_PER_1K_TOKENS") or "").strip()
    if raw:
        return True
    try:
        eff = company.effective_setting("FS_CORP_MODEL_CENTS_PER_1K_TOKENS")
        if eff is not None and str(eff).strip() not in ("", "0"):
            # Treat non-empty effective setting as configured; "0" alone is unset-equivalent for honesty
            if str(eff).strip() != "0":
                return True
    except Exception:
        pass
    # Any model profile with an explicit cents_per_1k_tokens field
    for row in company.db.execute("SELECT body FROM model_profiles"):
        # adapt to actual schema — if profiles are JSON files/table, match invoke_model profile load
        ...
    return False
```

**Important:** Inspect how profiles are stored (`list_model_profiles` / fixtures) and mark configured if any profile dict has `cents_per_1k_tokens is not None`. Prefer calling a tiny shared helper next to `price_tokens` usage rather than inventing a second resolver. If profile scan is hard, env + `effective_setting` alone is acceptable if tests pass and invoke path uses the same sources — document in report.

```python
def open_next_budget_period(
    company, actor: str, period_id: str, *,
    scope=None, period_start=None, period_end=None, limit_cents=None,
) -> dict:
    company._ceo(actor)
    period = company.db.execute(
        "SELECT * FROM budget_periods WHERE id=?", (period_id,)
    ).fetchone()
    if not period:
        raise ValueError("Budget period not found")
    if not company.db.execute(
        "SELECT 1 FROM budget_period_closures WHERE budget_period_id=?",
        (period_id,),
    ).fetchone():
        raise PermissionError("Budget period is not closed")
    # reject if any unclosed period exists
    for row in company.db.execute("SELECT id FROM budget_periods"):
        closed = company.db.execute(
            "SELECT 1 FROM budget_period_closures WHERE budget_period_id=?",
            (row["id"],),
        ).fetchone()
        if not closed:
            raise PermissionError("An open budget period already exists")
    from datetime import datetime
    start = period_start or period["period_end"]
    if period_end is None:
        a = datetime.fromisoformat(period["period_start"])
        b = datetime.fromisoformat(period["period_end"])
        end = (datetime.fromisoformat(start) + (b - a)).isoformat()
    else:
        end = period_end
    if datetime.fromisoformat(end) <= datetime.fromisoformat(start):
        raise ValueError("period_end must be after period_start")
    lim = company.money(limit_cents) if limit_cents is not None else int(period["limit_cents"])
    # money() may be module-level — use existing import in finance.py / company helpers
    sc = scope or period["scope"]
    # duplicate successor: set_budget_period uses digest id — if INSERT OR REPLACE would clobber, reject first
    from company.core import digest  # or local
    candidate_id = digest({"scope": sc, "period_start": start})
    existing = company.db.execute(
        "SELECT id FROM budget_periods WHERE id=?", (candidate_id,)
    ).fetchone()
    if existing:
        raise PermissionError("Successor budget period already exists")
    new_id = company.set_budget_period(actor, sc, start, end, lim)
    company._event(
        "budget.period_opened_next",
        {"from_period_id": period_id, "id": new_id, "scope": sc,
         "period_start": start, "period_end": end, "limit_cents": lim},
        actor_id=actor,
    )
    for item in list_budget_periods(company):
        if item["id"] == new_id:
            return item
    raise ValueError("Opened period not found")
```

Fix helper details to match real imports (`money`, `digest`, `_event`). Prefer implementing open-next **without** double-calling set if `set_budget_period` already emits `budget.period_set` — still emit `budget.period_opened_next` after success.

Extend `finance_summary` return with:

```python
"pricing": {
    "model_cents_per_1k_configured": model_cents_per_1k_configured(company),
    "hint": PRICING_HINT,
},
```

- [ ] **Step 5: Core wrappers**

In `company/core.py`:

```python
def open_next_budget_period(self, actor, period_id, **fields):
    from company.finance import open_next_budget_period
    return open_next_budget_period(self, actor, period_id, **fields)

def finance_summary(self):
    from company.finance import finance_summary
    return finance_summary(self)
```

(Only add `finance_summary` wrapper if missing — grep first.)

- [ ] **Step 6: API route**

Next to close route in `company/service.py`:

```python
@app.post("/api/v1/finance/budget-periods/{period_id}/open-next")
def finance_open_next_budget_period(
        period_id: str, body: Command,
        authorization: str | None = Header(default=None),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    ident = principal(authorization)
    scoped(ident, "company.pause")
    payload = envelope(ident, body)
    return run(ident, idempotency_key, payload | {"period_id": period_id}, lambda: (
        company.open_next_budget_period(
            ident["principal_id"],
            period_id,
            scope=payload.get("scope"),
            period_start=payload.get("period_start"),
            period_end=payload.get("period_end"),
            limit_cents=payload.get("limit_cents"),
        ), 200))
```

- [ ] **Step 7: GREEN tests**

```bash
.venv/bin/python -m unittest tests.test_durable_finance -v
```

Expected: OK.

- [ ] **Step 8: Commit**

```bash
git add company/finance.py company/core.py company/service.py tests/test_durable_finance.py
git commit -m "$(cat <<'EOF'
feat(finance): open-next budget period and pricing honesty summary

Allow CEO to open a contiguous successor after close and expose whether
model cents-per-1k pricing is configured without inventing billed amounts.
EOF
)"
```

---

### Task 2: Desk + companion UI

**Files:**
- Modify: `company/service.py` (`DESK_HTML` — `renderFinanceOverview`, `renderFinancePeriods`, `openFinanceNextPeriod`)
- Modify: `companion/src/FinancePanel.tsx`
- Create: `tests/test_desk_finance_open_next.py`

**Interfaces:**
- Consumes: Task 1 API + summary `pricing`
- Produces: Open next chips; pricing hint visibility

- [ ] **Step 1: Desk overview pricing hint**

In `renderFinanceOverview`, after open period line:

```javascript
  if (summary.pricing && summary.pricing.model_cents_per_1k_configured === false) {
    const hint = document.createElement('p');
    hint.className = 'muted';
    hint.id = 'finance-pricing-hint';
    hint.textContent = summary.pricing.hint
      || 'Billed lines may stay $0 until FS_CORP_MODEL_CENTS_PER_1K_TOKENS or a profile rate is set.';
    el.appendChild(hint);
  }
```

- [ ] **Step 2: Desk Open next on closed periods**

Fix period closed detection to use API `period.closed` (boolean). Keep Close when `!period.closed`. Add Open next when `period.closed`:

```javascript
    const closed = !!period.closed;
    meta.textContent = ... + (closed ? ' · closed' : ' · open');
    if (!closed) {
      // existing Close button with data-finance-close
    } else {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip';
      btn.dataset.financeOpenNext = String(period.id);
      btn.textContent = 'Open next period';
      btn.addEventListener('click', () => { void openFinanceNextPeriod(period); });
      li.appendChild(btn);
    }
```

```javascript
async function openFinanceNextPeriod(period) {
  try {
    await postFinanceCommand(
      '/api/v1/finance/budget-periods/' + encodeURIComponent(String(period.id)) + '/open-next',
      {},
      'desk-finance-open-next-' + period.id + '-' + Date.now(),
    );
    document.getElementById('finance-period-status').textContent = ' Next period opened.';
    await loadFinance();
  } catch (error) {
    document.getElementById('finance-period-status').textContent =
      ' ' + (error instanceof Error ? error.message : String(error));
  }
}
```

Ensure `setFinanceMutateEnabled` disables `[data-finance-open-next]` the same way as `[data-finance-close]` (extend the querySelectorAll list).

- [ ] **Step 3: Companion FinancePanel**

1. Extend summary type with optional `pricing?: { model_cents_per_1k_configured: boolean; hint: string }`.
2. Overview: if `summary.pricing && !summary.pricing.model_cents_per_1k_configured`, render `<p className="muted">{summary.pricing.hint}</p>`.
3. Periods: when `canPause && period.closed`, show button Open next period calling:

```typescript
async function openNextPeriod(period: Record<string, unknown>) {
  // same post pattern as closePeriod → POST .../open-next
}
```

- [ ] **Step 4: Desk contract tests**

Create `tests/test_desk_finance_open_next.py`:

```python
"""Desk finance open-next + pricing hint (v0.3.86)."""
from __future__ import annotations
import unittest
from company.service import DESK_HTML

class DeskFinanceOpenNextTests(unittest.TestCase):
    def test_open_next_markers(self):
        self.assertIn("openFinanceNextPeriod", DESK_HTML)
        self.assertIn("data-finance-open-next", DESK_HTML)
        self.assertIn("/open-next", DESK_HTML)

    def test_pricing_hint_render(self):
        self.assertIn("finance-pricing-hint", DESK_HTML)
        self.assertIn("model_cents_per_1k_configured", DESK_HTML)

    def test_set_finance_disables_open_next(self):
        idx = DESK_HTML.find("function setFinanceMutateEnabled")
        chunk = DESK_HTML[idx:idx+1200]
        self.assertIn("data-finance-open-next", chunk)
```

- [ ] **Step 5: Run tests + companion build**

```bash
.venv/bin/python -m unittest tests.test_durable_finance tests.test_desk_finance_open_next -v
cd companion && npm run build
```

Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add company/service.py companion/src/FinancePanel.tsx tests/test_desk_finance_open_next.py
git commit -m "$(cat <<'EOF'
feat(ui): desk and companion open-next period and pricing hint

Surface finance open-next and unset pricing honesty on CEO desk and
companion Finance overview/periods.
EOF
)"
```

---

### Task 3: Version 0.3.86 + docs

**Files:**
- `company/__init__.py`, `companion/package.json` → **0.3.86**
- Soften `tests/test_desk_remaining_session_gates.py` version pin to regex if exact `0.3.85`
- `docs/decisions.md` ADR-068
- `docs/16-api-contract.md` open-next row
- `README.md`, `VERIFICATION.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`
- Mark design spec implemented

- [ ] **Step 1: Bump versions + soften prior pin**

- [ ] **Step 2: ADR-068 + API contract**

Index + detail: explicit open-next after close; pricing honesty on summary; no Alembic; no auto-rollover.

API table row:

`POST /finance/budget-periods/{id}/open-next` | Open successor period after close | company.pause

- [ ] **Step 3: VERIFICATION / README / handoff**

Narrow or remove “period rollover of billed totals” as open gap (close already snapshots; open-next covers successor). Keep “Real provider invoices” as not implemented.

- [ ] **Step 4: Full suite + companion build**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 5: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs: ship finance open-next and pricing honesty as 0.3.86

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| open-next API + defaults/overrides/fail-closed | Task 1 |
| pricing on finance_summary | Task 1 |
| Desk Open next + hint + finance gate | Task 2 |
| Companion Open next + hint | Task 2 |
| Docs / version 0.3.86 | Task 3 |
| No 0.3.87 / no Alembic / no Stripe | Honored |

Placeholder scan: profile schema inspection left as implementer check in Task 1 Step 4 — resolve against real `model_profiles` storage before merging.
