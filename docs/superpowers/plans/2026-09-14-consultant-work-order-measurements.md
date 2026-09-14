# Consultant Work-Order Measurements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.87 with frozen baseline/after ops metrics on consultant work orders, GET APIs with deltas, and desk `#consultant` + companion Home Needs-you surfaces — no invented efficiency scores.

**Architecture:** Alembic `0029_work_order_measurements`; `company/measurements.py` for snapshot + persist + read; hook baseline in `record_work_order_authorized` and after in `complete_work_order_outcome`; FastAPI read/list routes; desk and HomePanel UI.

**Tech Stack:** Python/SQLite/Alembic, FastAPI desk HTML, React companion, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-consultant-work-order-measurements-design.md` (owner-approved).
- Version **0.3.87**. Soften exact `0.3.86` pins to `0\.3\.\d+` where needed.
- Metrics keys exactly: `accepted_artifacts`, `open_tasks`, `open_dispatches`, `simulated_spend_cents`, `billed_cost_cents` (integers only).
- No invented efficiency scores — deltas only (`after - baseline`).
- One row per (`work_order_id`, `phase`); phases `baseline` | `after`; idempotent (never overwrite).
- Baseline on authorize path; after on complete-outcome.
- UI: desk `#consultant` + companion Home Needs-you.
- Complete outcome remains `_ceo` + route `company.pause`.
- Update `company.migrate.HEAD_REVISION` to `0029_work_order_measurements` and soften tests that assert `0028_remote_worker_jobs`.
- Also add table to `company/schema.py` for fresh SQLite installs.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/consultant-work-order-measurements` from current `main` before Task 1.
- Work in-place on the feature branch.

## File map

| Path | Role |
|---|---|
| `alembic/versions/0029_work_order_measurements.py` | Migration |
| `company/migrate.py` | `HEAD_REVISION` |
| `company/schema.py` | Bootstrap CREATE |
| `company/measurements.py` | Snapshot + persist + read |
| `company/core.py` | Hooks in authorize/complete |
| `company/service.py` | Routes + desk UI |
| `companion/src/api/client.ts`, `HomePanel.tsx`, `App.tsx` as needed | Needs-you |
| Tests + docs | Contracts, ADR-069, API, VERIFICATION, handoff |

---

### Task 1: Migration + measurements module + hooks (RED/GREEN)

**Files:**
- Create: `alembic/versions/0029_work_order_measurements.py`, `company/measurements.py`, `tests/test_work_order_measurements.py`
- Modify: `company/migrate.py`, `company/schema.py`, `company/core.py`
- Soften: `tests/test_staffing_proposals.py`, `tests/test_scorecard.py`, `tests/test_divisions.py`, `tests/test_career_ladder.py` HEAD_REVISION asserts → `0029_work_order_measurements` or import `HEAD_REVISION` dynamically

**Interfaces:**
- Produces:
  - `capture_ops_metrics(company) -> dict[str, int]`
  - `ensure_measurement(company, actor, work_order_id, phase) -> dict`
  - `get_measurements(company, work_order_id) -> dict` with baseline/after/deltas
  - `list_measurements(company, limit=50) -> list`
  - Hooks from `record_work_order_authorized` / `complete_work_order_outcome`

- [ ] **Step 1: Create branch**

```bash
git checkout main && git pull --ff-only
git checkout -b feature/consultant-work-order-measurements
```

- [ ] **Step 2: Write failing tests** `tests/test_work_order_measurements.py`

```python
"""Work-order baseline/after ops measurements (v0.3.87)."""
import unittest

from company.consultant import ConsultantDesk
from company.core import Company
from company.measurements import METRIC_KEYS, capture_ops_metrics
from tests.test_core import install, policy
from tests.test_m1 import PROPOSAL


class CaptureOpsMetricsTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_keys_and_ints(self):
        m = capture_ops_metrics(self.c)
        self.assertEqual(set(m), set(METRIC_KEYS))
        for k in METRIC_KEYS:
            self.assertIsInstance(m[k], int)


class MeasurementLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.desk = ConsultantDesk(self.c)

    def _authorize(self):
        pid = self.desk.submit("consultant", PROPOSAL)
        self.desk.decide("human-ceo", pid, "approved", "ok")
        return self.desk.to_work_order("human-ceo", pid)

    def test_baseline_on_to_work_order(self):
        oid = self._authorize()
        got = self.c.get_work_order_measurements(oid)
        self.assertIsNotNone(got["baseline"])
        self.assertIsNone(got["after"])
        self.assertIsNone(got["deltas"])
        self.assertEqual(set(got["baseline"]["metrics"]), set(METRIC_KEYS))

    def test_baseline_idempotent(self):
        oid = self._authorize()
        first = self.c.get_work_order_measurements(oid)["baseline"]["created_at"]
        self.c.record_work_order_authorized(
            "human-ceo", oid,
            dict(self.c.db.execute("SELECT workflow_digest FROM work_orders WHERE id=?", (oid,)).fetchone())["workflow_digest"],
            outcome={"status": "authorized"},
        )
        second = self.c.get_work_order_measurements(oid)["baseline"]["created_at"]
        self.assertEqual(first, second)

    def test_after_and_deltas(self):
        oid = self._authorize()
        before = self.c.get_work_order_measurements(oid)["baseline"]["metrics"]
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done", "artifact": "patch"})
        got = self.c.get_work_order_measurements(oid)
        self.assertIsNotNone(got["after"])
        self.assertIsNotNone(got["deltas"])
        for k in METRIC_KEYS:
            self.assertEqual(
                got["deltas"][k],
                got["after"]["metrics"][k] - before[k],
            )

    def test_after_idempotent(self):
        oid = self._authorize()
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done"})
        a1 = self.c.get_work_order_measurements(oid)["after"]["created_at"]
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done", "again": True})
        a2 = self.c.get_work_order_measurements(oid)["after"]["created_at"]
        self.assertEqual(a1, a2)
```

Note: if second `complete_work_order_outcome` always inserts a new replay row, that is fine — after measurement must still not change.

- [ ] **Step 3: Run RED**

```bash
.venv/bin/python -m unittest tests.test_work_order_measurements -v
```

Expected: FAIL (import / missing APIs).

- [ ] **Step 4: Alembic + schema + HEAD_REVISION**

`alembic/versions/0029_work_order_measurements.py`:

```python
"""Work-order baseline/after ops measurements."""
from alembic import op

revision = "0029_work_order_measurements"
down_revision = "0028_remote_worker_jobs"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order_measurements(
          id TEXT PRIMARY KEY,
          work_order_id TEXT NOT NULL,
          phase TEXT NOT NULL,
          metrics_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          UNIQUE(work_order_id, phase))
        """
    )

def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
```

Update `company/migrate.py`: `HEAD_REVISION = "0029_work_order_measurements"`.

Append matching `CREATE TABLE` to `company/schema.py`.

Update the four tests that assert `HEAD_REVISION == "0028_remote_worker_jobs"` to assert `"0029_work_order_measurements"`.

- [ ] **Step 5: Implement `company/measurements.py`**

```python
METRIC_KEYS = (
    "accepted_artifacts",
    "open_tasks",
    "open_dispatches",
    "simulated_spend_cents",
    "billed_cost_cents",
)
TERMINAL_DISPATCH = frozenset({
    "accepted", "cancelled", "canceled", "closed", "completed", "failed", "rejected",
})
CLOSED_TASKS = frozenset({"accepted", "cancelled", "failed"})

def capture_ops_metrics(company) -> dict:
    from company.finance import billed_net_cents
    accepted = company.db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='accepted'").fetchone()[0]
    open_tasks = company.db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('accepted','cancelled','failed')"
    ).fetchone()[0]
    # open_dispatches: count rows whose status not in TERMINAL_DISPATCH
    ...
    return {
        "accepted_artifacts": int(accepted),
        "open_tasks": int(open_tasks),
        "open_dispatches": int(open_dispatches),
        "simulated_spend_cents": int(...ledger sum...),
        "billed_cost_cents": int(billed_net_cents(company)),
    }

def ensure_measurement(company, actor, work_order_id, phase: str) -> dict:
    assert phase in ("baseline", "after")
    if not company.db.execute("SELECT 1 FROM work_orders WHERE id=?", (work_order_id,)).fetchone():
        raise ValueError("Work order not found")
    existing = company.db.execute(
        "SELECT * FROM work_order_measurements WHERE work_order_id=? AND phase=?",
        (work_order_id, phase),
    ).fetchone()
    if existing:
        return _row(existing)
    metrics = capture_ops_metrics(company)
    rid = str(uuid.uuid4())
    # insert in company.tx() if not already in one; prefer caller's tx when hooked inside complete
    ...
    company._event(f"work_order.measurement_{phase}", {"work_order_id": work_order_id, "metrics": metrics}, actor_id=actor)
    return ...

def get_measurements(company, work_order_id) -> dict:
    ...
    deltas = None
    if baseline and after:
        deltas = {k: after["metrics"][k] - baseline["metrics"][k] for k in METRIC_KEYS}
    return {"work_order_id": work_order_id, "baseline": baseline, "after": after, "deltas": deltas}

def list_measurements(company, limit=50) -> list:
    # Join work_orders; prefer consultant-sourced via payload JSON source=consultant when available
    ...
```

- [ ] **Step 6: Core wrappers + hooks**

```python
# company/core.py
def get_work_order_measurements(self, work_order_id):
    from company.measurements import get_measurements
    return get_measurements(self, work_order_id)

def list_work_order_measurements(self, limit=50):
    from company.measurements import list_measurements
    return list_measurements(self, limit=limit)
```

At end of `record_work_order_authorized` (after insert/return path for both existing and new):

```python
from company.measurements import ensure_measurement
ensure_measurement(self, actor, work_order_id, "baseline")
```

At end of `complete_work_order_outcome` (after replay insert/event):

```python
ensure_measurement(self, actor, work_order_id, "after")
```

Careful with transactions: if `ensure_measurement` opens its own `tx()`, nesting must be safe (Company.tx reentrant or call insert inside existing `with self.tx()`). Prefer inserting measurement **inside** the same `tx()` block as the authorizing/completing write when possible.

- [ ] **Step 7: GREEN**

```bash
.venv/bin/python -m unittest tests.test_work_order_measurements tests.test_work_order_replay tests.test_migrate -v
```

Expected: OK.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/0029_work_order_measurements.py company/migrate.py company/schema.py \
  company/measurements.py company/core.py tests/test_work_order_measurements.py \
  tests/test_staffing_proposals.py tests/test_scorecard.py tests/test_divisions.py tests/test_career_ladder.py
git commit -m "$(cat <<'EOF'
feat(consultant): persist work-order baseline and after ops metrics

Freeze accepted/open/spend counters on authorize and complete so deltas
can be read without inventing efficiency scores.
EOF
)"
```

---

### Task 2: API routes + desk + companion UI

**Files:**
- Modify: `company/service.py` (routes + DESK_HTML)
- Modify: `companion/src/api/client.ts`, `companion/src/HomePanel.tsx`, `companion/src/App.tsx` (wire fetch/state)
- Create: `tests/test_desk_consultant_measurements.py`

**Interfaces:**
- Consumes: Task 1 getters
- Produces: GET endpoints; desk measures list + Complete; Home Needs-you cards

- [ ] **Step 1: API routes** (near existing work-order routes)

```python
@app.get("/api/v1/work-orders/{work_order_id}/measurements")
def work_order_measurements(...):
    ident = principal(authorization)
    # allow consultant.read OR company.read — implement as: pass if either scope present
    ...
    return company.get_work_order_measurements(work_order_id)

@app.get("/api/v1/work-orders/measurements")
def work_order_measurements_list(...):
    ident = principal(authorization)
    ...
    return {"items": company.list_work_order_measurements()}
```

Route ordering: register **list** path `/work-orders/measurements` **before** parameterized `/work-orders/{work_order_id}/...` if FastAPI would otherwise capture `"measurements"` as an id — check existing order; put list route above `{work_order_id}` routes if needed.

- [ ] **Step 2: Desk markup**

Extend `#consultant` section:

```html
<section class="glass" id="consultant">
<h2>Consultant inbox</h2>
<ul id="consultant-list"></ul>
<h3>Work-order measures</h3>
<ul id="consultant-measures-list"></ul>
</section>
```

- [ ] **Step 3: Desk JS**

- `renderConsultantMeasures(items)` — for each item show id/title, baseline/after status, deltas text when present; if `has_baseline && !has_after`, add Complete chip calling `postFinanceCommand`-style POST to complete-outcome with `{outcome: {status: "done"}}` and idempotency key; on 403 fail closed for CEO mutates if a session helper exists, else alert.
- Load in `load()`: `GET /api/v1/work-orders/measurements`.
- Gate Complete visually with session CEO/`company.pause` if easy (mirror finance); server enforces `_ceo`.

- [ ] **Step 4: Companion**

- `client.ts`: `listWorkOrderMeasurements()`, `getWorkOrderMeasurements(id)`, `completeWorkOrderOutcome(id, outcome)`.
- `App.tsx`: fetch measurements with home data; pass into `HomePanel`.
- `HomePanel.tsx`: after decisions/inbox blocks, render **Work-order measures** cards:
  - Awaiting after → Complete button when `canPause(scopes)` (CEO path uses company.pause on route).
  - With deltas → muted lines of key: delta (signed).
- Copy must say “deltas” / metric names — never “efficiency score”.

- [ ] **Step 5: Desk contracts**

```python
# tests/test_desk_consultant_measurements.py
self.assertIn('id="consultant-measures-list"', DESK_HTML)
self.assertIn("renderConsultantMeasures", DESK_HTML)
self.assertIn("/work-orders/measurements", DESK_HTML)
self.assertIn("complete-outcome", DESK_HTML)
```

- [ ] **Step 6: Verify**

```bash
.venv/bin/python -m unittest tests.test_work_order_measurements tests.test_desk_consultant_measurements tests.test_work_order_replay -v
cd companion && npm run build
```

- [ ] **Step 7: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(ui): show consultant work-order measurement deltas on desk and home

EOF
)"
```

---

### Task 3: Version 0.3.87 + docs

**Files:** versions, ADR-069, `docs/16-api-contract.md`, README, VERIFICATION, handoff, roadmap, mark design implemented; commit plan+spec if untracked.

- [ ] **Step 1:** Bump `company/__init__.py` + `companion/package.json` → **0.3.87**; soften `0.3.86` exact pins.
- [ ] **Step 2:** ADR-069 + API contract rows for GET measurements / list.
- [ ] **Step 3:** VERIFICATION current-ship; handoff Next = audit complete / owner-directed; update audit canvas optional (skip unless easy).
- [ ] **Step 4:**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 5:** Commit docs ship.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Alembic table + unique phase | Task 1 |
| capture_ops_metrics five keys | Task 1 |
| Baseline/after hooks + idempotent | Task 1 |
| GET detail + list + deltas | Task 2 |
| Desk consultant measures + Complete | Task 2 |
| Companion Home Needs-you | Task 2 |
| Version/docs ADR-069 | Task 3 |
| No invented scores | All |

Placeholder scan: open_dispatches SQL left as implementer fill in Step 5 — use `status NOT IN (...)` with TERMINAL_DISPATCH tuple.
