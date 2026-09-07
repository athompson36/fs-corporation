# Org Hierarchy, Rules, and Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship grant-backed org roster, compiled seat/activation/roster checks, and dispatch → head inbox → assign → queue handoff without inventing operational state.

**Architecture:** New tables + `company/org.py` for roster/handoff commands; `Company` delegates and tightens `dispatch_project_brief`. Grants remain the only permission source; seats/`reports_to` are routing facts. FastAPI routes + thin desk/companion UI. Alembic `0014` + `schema.py` for `:memory:` tests.

**Tech Stack:** Python 3.12, SQLite, Alembic, FastAPI, unittest, React companion, desk HTML in `company/service.py`.

**Spec:** `docs/superpowers/specs/2026-09-07-org-hierarchy-handoff-design.md`

## Global Constraints

- Grants/delegations authorize; org edges never authorize alone
- Fail closed: vacant head, dormant dept without project activation, roster miss, missing grant scope
- No auto-grants on appoint or dispatch; no auto model runs on dispatch
- Execution-plane workers ≠ org employees
- Integer cents via `money()`; idempotent appoint/assign/dispatch under `Idempotency-Key`
- Actor identity from bearer → principal, never request-body actor
- Forward-only Alembic; update `schema.py` and `HEAD_REVISION`
- Building/HQ is event projection only — no invented busy workers
- Do not commit unless the user asks (except when a task step says commit and the user chose plan execution that includes commits)

## File map

| File | Responsibility |
|---|---|
| `company/schema.py` | DDL for new tables + optional grant field |
| `alembic/versions/0014_org_hierarchy.py` | File-backed migration |
| `company/migrate.py` | `HEAD_REVISION = "0014_org_hierarchy"` |
| `company/org.py` | Roster + activation + inbox + assign_dispatch helpers used by `Company` |
| `company/core.py` | Wire methods; tighten `dispatch_project_brief` + `seed_catalog` vacant seats; vacate blocks queue |
| `company/service.py` | API routes + desk org/inbox UI |
| `tests/test_org_roster.py` | Milestone 1–2 tests |
| `tests/test_org_handoff.py` | Milestone 3 tests |
| `tests/test_production_slice.py` | Update dispatch payload for per-dept budgets |
| `companion/` | Org + handoff UI |
| Docs / version | matrix, roadmap, handoff, decisions, `__version__` → `0.3.51` when UI ships |

---

### Task 1: Schema + migration (vacant seats on seed)

**Files:**
- Modify: `company/schema.py`
- Create: `alembic/versions/0014_org_hierarchy.py`
- Modify: `company/migrate.py` (`HEAD_REVISION`)
- Modify: `company/core.py` (`seed_catalog`)
- Test: `tests/test_org_roster.py`, `tests/test_migrate.py` (existing head check)

**Interfaces:**
- Produces tables: `department_seats`, `position_assignments`, `project_department_activations`, extended `project_dispatches` columns, `dispatch_assignments`
- Produces: after `seed_catalog`, every department has exactly one seat row with `status='vacant'` (or `'dormant'` if `initially_active=0`) and `principal_id=NULL`

- [ ] **Step 1: Write failing test for vacant seats after seed**

Create `tests/test_org_roster.py`:

```python
"""Org roster, rules, and handoff (grant-backed)."""
from __future__ import annotations
import unittest
from pathlib import Path

from company.core import Company
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class OrgRosterSeedTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_seed_catalog_creates_vacant_or_dormant_seats(self):
        self.c.seed_catalog(CATALOG)
        seats = list(self.c.db.execute(
            "SELECT department_id, principal_id, status, title FROM department_seats ORDER BY department_id"))
        self.assertGreaterEqual(len(seats), 13)
        eng = next(s for s in seats if s["department_id"] == "engineering")
        self.assertIsNone(eng["principal_id"])
        self.assertEqual(eng["status"], "vacant")
        self.assertEqual(eng["title"], "CTO")
        product = next(s for s in seats if s["department_id"] == "product")
        self.assertEqual(product["status"], "dormant")
        self.assertIsNone(product["principal_id"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect FAIL (no table)**

```bash
.venv/bin/python -m unittest tests.test_org_roster.OrgRosterSeedTests -v
```

Expected: FAIL with `no such table: department_seats` (or similar).

- [ ] **Step 3: Add DDL to `company/schema.py`**

Append before the closing `"""` of `SCHEMA` (after `revenue` table):

```sql
CREATE TABLE IF NOT EXISTS department_seats(
  id TEXT PRIMARY KEY, department_id TEXT NOT NULL UNIQUE REFERENCES departments(id),
  principal_id TEXT, title TEXT NOT NULL,
  status TEXT NOT NULL, appointed_by TEXT, appointed_at TEXT, vacated_at TEXT);
CREATE TABLE IF NOT EXISTS position_assignments(
  id TEXT PRIMARY KEY, position_id TEXT NOT NULL REFERENCES positions(id),
  department_id TEXT NOT NULL REFERENCES departments(id), principal_id TEXT NOT NULL,
  status TEXT NOT NULL, reports_to_seat_id TEXT REFERENCES department_seats(id),
  assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL, released_at TEXT);
CREATE TABLE IF NOT EXISTS project_department_activations(
  project_id TEXT NOT NULL REFERENCES projects(id),
  department_id TEXT NOT NULL REFERENCES departments(id),
  activated_by TEXT NOT NULL, activated_at TEXT NOT NULL,
  PRIMARY KEY(project_id, department_id));
CREATE TABLE IF NOT EXISTS dispatch_assignments(
  id TEXT PRIMARY KEY, dispatch_id TEXT NOT NULL REFERENCES project_dispatches(id),
  assignee TEXT NOT NULL, assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL,
  queue_task_id TEXT, status TEXT NOT NULL);
```

Replace the `project_dispatches` CREATE block with status + head fields:

```sql
CREATE TABLE IF NOT EXISTS project_dispatches(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, department_id TEXT NOT NULL,
  work_order_id TEXT NOT NULL, brief TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL, budget_cents INTEGER NOT NULL,
  due_at TEXT, created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued_for_head',
  head_principal_id TEXT, head_inbox_at TEXT);
```

Add to `GRANT_OPTIONAL`:

```python
GRANT_OPTIONAL = {"approval_rights", "departments"}
```

- [ ] **Step 4: Alembic migration `0014_org_hierarchy.py`**

```python
"""Org seats, assignments, project department activation, dispatch handoff columns."""
from alembic import op

revision = "0014_org_hierarchy"
down_revision = "0013_billed_cost_revenue"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS department_seats(
          id TEXT PRIMARY KEY, department_id TEXT NOT NULL UNIQUE,
          principal_id TEXT, title TEXT NOT NULL,
          status TEXT NOT NULL, appointed_by TEXT, appointed_at TEXT, vacated_at TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS position_assignments(
          id TEXT PRIMARY KEY, position_id TEXT NOT NULL,
          department_id TEXT NOT NULL, principal_id TEXT NOT NULL,
          status TEXT NOT NULL, reports_to_seat_id TEXT,
          assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL, released_at TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_department_activations(
          project_id TEXT NOT NULL, department_id TEXT NOT NULL,
          activated_by TEXT NOT NULL, activated_at TEXT NOT NULL,
          PRIMARY KEY(project_id, department_id))
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_assignments(
          id TEXT PRIMARY KEY, dispatch_id TEXT NOT NULL,
          assignee TEXT NOT NULL, assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL,
          queue_task_id TEXT, status TEXT NOT NULL)
        """
    )
    # SQLite: add columns if missing (file DBs created before this revision)
    cols = {r[1] for r in op.get_bind().execute("PRAGMA table_info(project_dispatches)").fetchall()}
    if "status" not in cols:
        op.execute(
            "ALTER TABLE project_dispatches ADD COLUMN status TEXT NOT NULL DEFAULT 'queued_for_head'"
        )
    if "head_principal_id" not in cols:
        op.execute("ALTER TABLE project_dispatches ADD COLUMN head_principal_id TEXT")
    if "head_inbox_at" not in cols:
        op.execute("ALTER TABLE project_dispatches ADD COLUMN head_inbox_at TEXT")


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
```

If `op.get_bind().execute` style differs in this repo’s Alembic, use the same pattern as other migrations (`op.execute` only) and a small raw sqlite3 connection for PRAGMA — match `0011_pairing_access_level.py`.

- [ ] **Step 5: Set `HEAD_REVISION = "0014_org_hierarchy"` in `company/migrate.py`**

- [ ] **Step 6: Update `seed_catalog` in `company/core.py`**

After inserting each department (inside the loop), upsert a seat:

```python
seat_status = "vacant" if d["initially_active"] else "dormant"
seat_id = f"seat:{d['id']}"
existing = self.db.execute(
    "SELECT id, principal_id, status FROM department_seats WHERE department_id=?",
    (d["id"],)).fetchone()
if not existing:
    self.db.execute(
        "INSERT INTO department_seats VALUES(?,?,?,?,?,?,?,?)",
        (seat_id, d["id"], None, d["head"], seat_status, None, None, None))
elif existing["principal_id"] is None and existing["status"] in {"vacant", "dormant"}:
    self.db.execute(
        "UPDATE department_seats SET title=?, status=? WHERE department_id=?",
        (d["head"], seat_status, d["id"]))
```

Do not overwrite an `active` seat’s `principal_id` on re-seed.

- [ ] **Step 7: Run tests**

```bash
.venv/bin/python -m unittest tests.test_org_roster.OrgRosterSeedTests tests.test_migrate -v
```

Expected: PASS.

- [ ] **Step 8: Commit** (when user/execution allows)

```bash
git add company/schema.py company/migrate.py company/core.py \
  alembic/versions/0014_org_hierarchy.py tests/test_org_roster.py
git commit -m "Add org seat schema and vacant seats on catalog seed."
```

---

### Task 2: Appoint / vacate head + position assign / release + `list_org`

**Files:**
- Create: `company/org.py`
- Modify: `company/core.py` (thin wrappers)
- Modify: `tests/test_org_roster.py`

**Interfaces:**
- Consumes: `department_seats`, `position_assignments`, `Company._ceo` / `_ceo_or_admin_companion`, `Company._event`, `Company.tx`
- Produces:
  - `Company.appoint_head(actor, department_id, principal_id) -> dict`
  - `Company.vacate_head(actor, department_id) -> dict`
  - `Company.assign_position(actor, position_id, principal_id, reports_to_seat_id=None) -> dict`
  - `Company.release_position(actor, assignment_id) -> dict`
  - `Company.list_org() -> dict` with `departments[]` each containing `seat` + `assignments[]`

- [ ] **Step 1: Failing tests**

Append to `tests/test_org_roster.py`:

```python
class OrgAppointTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.addCleanup(self.c.close)

    def test_appoint_and_vacate_head(self):
        row = self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["principal_id"], "eng-cto")
        seat = self.c.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?", ("engineering",)).fetchone()
        self.assertEqual(seat["principal_id"], "eng-cto")
        vacated = self.c.vacate_head("human-ceo", "engineering")
        self.assertEqual(vacated["status"], "vacant")
        self.assertIsNone(vacated["principal_id"])

    def test_non_ceo_cannot_appoint_without_later_grant_hook(self):
        # Milestone 1: CEO-only; milestone 2 may allow org.appoint_head grant
        with self.assertRaises(PermissionError):
            self.c.appoint_head("stranger", "engineering", "eng-cto")

    def test_assign_and_release_position(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        aid = self.c.assign_position(
            "human-ceo", "engineering:Developer", "dev-1")["id"]
        row = self.c.db.execute(
            "SELECT * FROM position_assignments WHERE id=?", (aid,)).fetchone()
        self.assertEqual(row["principal_id"], "dev-1")
        self.assertEqual(row["status"], "active")
        self.c.release_position("human-ceo", aid)
        row = self.c.db.execute(
            "SELECT * FROM position_assignments WHERE id=?", (aid,)).fetchone()
        self.assertEqual(row["status"], "released")

    def test_list_org_shows_vacant_honestly(self):
        org = self.c.list_org()
        eng = next(d for d in org["departments"] if d["id"] == "engineering")
        self.assertEqual(eng["seat"]["status"], "vacant")
        self.assertIsNone(eng["seat"]["principal_id"])
```

- [ ] **Step 2: Run — expect FAIL (methods missing)**

```bash
.venv/bin/python -m unittest tests.test_org_roster.OrgAppointTests -v
```

- [ ] **Step 3: Implement `company/org.py`**

```python
"""Grant-backed org roster helpers (seats and position assignments are not authority)."""
from __future__ import annotations
import uuid
from company.core import now  # if circular, pass clock/event via Company methods only


def appoint_head(company, actor, department_id, principal_id):
    company._ceo(actor)
    if not principal_id or not str(principal_id).strip():
        raise ValueError("principal_id required")
    dept = company.db.execute(
        "SELECT id, head_title, initially_active FROM departments WHERE id=?",
        (department_id,)).fetchone()
    if not dept:
        raise ValueError("Unknown department")
    with company.tx():
        seat = company.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?", (department_id,)).fetchone()
        if not seat:
            raise ValueError("Seat missing; seed catalog first")
        status = "active"
        company.db.execute(
            """UPDATE department_seats
               SET principal_id=?, title=?, status=?, appointed_by=?, appointed_at=?, vacated_at=NULL
               WHERE department_id=?""",
            (principal_id.strip(), dept["head_title"], status, actor, now().isoformat(), department_id))
        company._event("org.head_appointed", {
            "department_id": department_id, "principal_id": principal_id.strip(),
        }, actor_id=actor)
    return dict(company.db.execute(
        "SELECT * FROM department_seats WHERE department_id=?", (department_id,)).fetchone())


def vacate_head(company, actor, department_id):
    company._ceo(actor)
    dept = company.db.execute(
        "SELECT id, initially_active FROM departments WHERE id=?", (department_id,)).fetchone()
    if not dept:
        raise ValueError("Unknown department")
    with company.tx():
        seat = company.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?", (department_id,)).fetchone()
        if not seat:
            raise ValueError("Seat missing; seed catalog first")
        new_status = "vacant" if dept["initially_active"] else "dormant"
        # Block queued work for former head (milestone 2 expands with dispatch cancel)
        if seat["principal_id"]:
            company.db.execute(
                "UPDATE queue SET status='cancelled' WHERE actor=? AND status='queued'",
                (seat["principal_id"],))
        company.db.execute(
            """UPDATE department_seats
               SET principal_id=NULL, status=?, vacated_at=?, appointed_by=appointed_by
               WHERE department_id=?""",
            (new_status, now().isoformat(), department_id))
        company._event("org.head_vacated", {"department_id": department_id}, actor_id=actor)
    return dict(company.db.execute(
        "SELECT * FROM department_seats WHERE department_id=?", (department_id,)).fetchone())


def assign_position(company, actor, position_id, principal_id, reports_to_seat_id=None):
    company._ceo(actor)
    pos = company.db.execute(
        "SELECT id, department_id, title FROM positions WHERE id=?", (position_id,)).fetchone()
    if not pos:
        raise ValueError("Unknown position")
    if not principal_id or not str(principal_id).strip():
        raise ValueError("principal_id required")
    if reports_to_seat_id:
        seat = company.db.execute(
            "SELECT id FROM department_seats WHERE id=?", (reports_to_seat_id,)).fetchone()
        if not seat:
            raise ValueError("Unknown reports_to_seat_id")
    aid = str(uuid.uuid4())
    with company.tx():
        company.db.execute(
            "INSERT INTO position_assignments VALUES(?,?,?,?,?,?,?,?,?)",
            (aid, position_id, pos["department_id"], principal_id.strip(), "active",
             reports_to_seat_id, actor, now().isoformat(), None))
        company._event("org.position_assigned", {
            "id": aid, "position_id": position_id, "principal_id": principal_id.strip(),
        }, actor_id=actor)
    return dict(company.db.execute(
        "SELECT * FROM position_assignments WHERE id=?", (aid,)).fetchone())


def release_position(company, actor, assignment_id):
    company._ceo(actor)
    with company.tx():
        row = company.db.execute(
            "SELECT * FROM position_assignments WHERE id=?", (assignment_id,)).fetchone()
        if not row or row["status"] != "active":
            raise ValueError("Active assignment not found")
        company.db.execute(
            "UPDATE position_assignments SET status='released', released_at=? WHERE id=?",
            (now().isoformat(), assignment_id))
        company._event("org.position_released", {"id": assignment_id}, actor_id=actor)
    return dict(company.db.execute(
        "SELECT * FROM position_assignments WHERE id=?", (assignment_id,)).fetchone())


def list_org(company):
    departments = []
    for d in company.db.execute(
            "SELECT id,name,head_title,mission,room_type,initially_active FROM departments ORDER BY id"):
        seat = company.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?", (d["id"],)).fetchone()
        assignments = [dict(r) for r in company.db.execute(
            """SELECT * FROM position_assignments
               WHERE department_id=? AND status='active' ORDER BY assigned_at""",
            (d["id"],))]
        departments.append({
            **dict(d),
            "seat": dict(seat) if seat else {
                "department_id": d["id"], "principal_id": None,
                "status": "vacant", "title": d["head_title"],
            },
            "assignments": assignments,
        })
    return {"departments": departments}
```

Prefer implementing these as methods on `Company` in `core.py` if importing `now` from `core` causes circular imports — then keep `org.py` free of Company imports by accepting callables, **or** put the functions in `org.py` and have `Company` methods call them with `self` after defining `now` in a tiny `company/timeutil.py`. Simplest path that matches this repo: **implement as `Company` methods in `core.py`** and keep `org.py` only if the file stays under ~200 lines without circular imports. If circular, put all Task 2 logic on `Company` and skip a separate module until a later split.

Recommended concrete choice for this repo: **put methods on `Company` in `core.py`** for Task 2–3 to avoid import cycles; create `company/org.py` only when extracting pure helpers (`department_is_dispatchable`, `require_seated_head`). Update the file map accordingly during implementation.

- [ ] **Step 4: Run appoint tests — PASS**

```bash
.venv/bin/python -m unittest tests.test_org_roster -v
```

- [ ] **Step 5: Commit**

```bash
git add company/core.py company/org.py tests/test_org_roster.py
git commit -m "Add appoint/vacate head and position assignment roster APIs."
```

---

### Task 3: FastAPI org routes

**Files:**
- Modify: `company/service.py`
- Test: `tests/test_org_roster.py` (APITestCase using existing service test helpers)

**Interfaces:**
- `GET /api/v1/org` — scope `organization.read` → `list_org()`
- `POST /api/v1/org/heads` — body `{department_id, principal_id}` or `{department_id, vacate: true}`; scope: reuse `organization.read` is wrong — use CEO principal check inside core + scope `company.pause` is wrong. Prefer new scopes only if identity scopes already support extension; otherwise require CEO token and call `appoint_head` / `vacate_head` after `principal()`. Match pattern: many CEO ops use `project.enroll` or `company.pause`. **Use `project.enroll` for appoint/vacate/assign in v1** (CEO mobile already has it) OR add `organization.write` to `COMPANION_SCOPES` admin set. Prefer adding `"organization.write"` to admin companion scopes in `schema.py` / pairing scopes list.

- [ ] **Step 1: Failing API test** — follow `tests/test_companion_api.py` / `tests/test_m1.py` client pattern:

```python
# In tests/test_org_roster.py — use FastAPI TestClient + owner token like other service tests
def test_org_get_and_appoint_via_api(self):
    # seed catalog, GET /api/v1/org → engineering seat vacant
    # POST /api/v1/org/heads with department_id=engineering, principal_id=eng-cto
    # GET again → active
    ...
```

Copy the exact TestClient bootstrap from `tests/test_impact_briefs_api.py` or nearest org read test.

- [ ] **Step 2: Implement routes** near departments list in `service.py`:

```python
@app.get("/api/v1/org")
def org_get(authorization: str | None = Header(default=None)):
    ident = principal(authorization)
    scoped(ident, "organization.read")
    return company.list_org()

@app.post("/api/v1/org/heads")
def org_heads(body: Command, authorization: str | None = Header(default=None),
              idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    ident = principal(authorization)
    scoped(ident, "organization.write")  # add to companion admin scopes
    payload = envelope(ident, body)
    def go():
        if payload.get("vacate"):
            return company.vacate_head(ident["principal_id"], payload["department_id"]), 200
        return company.appoint_head(
            ident["principal_id"], payload["department_id"], payload["principal_id"]), 200
    return run(ident, idempotency_key, payload, go)

@app.post("/api/v1/org/assignments")
def org_assignments(...):
    # assign: position_id, principal_id; release: assignment_id + release: true
    ...
```

Add `"organization.write"` wherever companion admin scopes are defined (`COMPANION_SCOPES` / pairing redeem).

- [ ] **Step 3: Tests PASS + commit**

```bash
.venv/bin/python -m unittest tests.test_org_roster -v
git commit -m "Expose org roster appoint and assignment HTTP APIs."
```

---

### Task 4: Rules — activation, grant departments, dispatch gates

**Files:**
- Modify: `company/core.py` (`validate_policy` already allows GRANT_OPTIONAL; `_effective_grant` / `_scope` to honor `departments` when present)
- Modify: `company/core.py` — `activate_department_for_project`, tighten `dispatch_project_brief`
- Modify: `tests/test_org_roster.py`, `tests/test_production_slice.py`
- Modify: `company/service.py` — activate + dispatch payload

**Interfaces:**
- `Company.activate_department_for_project(actor, project_id, department_id) -> dict`
- `Company.department_dispatchable(project_id, department_id) -> bool`
- `dispatch_project_brief(..., department_budgets: dict[str,int], ...)` — **breaking**: replace single `budget_cents` with `department_budgets` mapping; update all callers
- When grant has `departments` list, actions on that project also require `department_id` in grant for handoff assign (Task 5); for `execute_mock` keep backward compatible: missing `departments` key means no dept restriction (existing grants keep working)

- [ ] **Step 1: Failing tests**

```python
class OrgActivationDispatchTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Org handoff")
        self.addCleanup(self.c.close)

    def test_dormant_department_dispatch_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.c.dispatch_project_brief(
                "human-ceo", "app",
                brief="Need product",
                department_budgets={"product": 1000},
                acceptance_criteria="PRD draft",
            )
        self.assertIn("dormant", str(ctx.exception).lower())

    def test_activate_then_dispatch_dormant(self):
        self.c.activate_department_for_project("human-ceo", "app", "product")
        self.c.appoint_head("human-ceo", "product", "prod-head")
        out = self.c.dispatch_project_brief(
            "human-ceo", "app",
            brief="Need product",
            department_budgets={"product": 1000},
            acceptance_criteria="PRD draft",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["status"], "queued_for_head")

    def test_initially_active_vacant_head_blocks_inbox_status(self):
        out = self.c.dispatch_project_brief(
            "human-ceo", "app",
            brief="Eng work",
            department_budgets={"engineering": 2000},
            acceptance_criteria="Ship",
        )
        self.assertEqual(out[0]["status"], "blocked_vacant_head")
        self.assertIsNone(out[0].get("head_principal_id"))
```

- [ ] **Step 2: Implement activation + dispatchable helper**

```python
def activate_department_for_project(self, actor, project_id, department_id):
    self._ceo_or_admin_companion(actor)
    if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        raise ValueError("Project not found")
    if not self.db.execute("SELECT 1 FROM departments WHERE id=?", (department_id,)).fetchone():
        raise ValueError("Unknown department")
    with self.tx():
        self.db.execute(
            "INSERT OR REPLACE INTO project_department_activations VALUES(?,?,?,?)",
            (project_id, department_id, actor, now().isoformat()))
        self._event("org.department_activated", {
            "project_id": project_id, "department_id": department_id,
        }, actor_id=actor, project_id=project_id)
    return {"project_id": project_id, "department_id": department_id}

def department_dispatchable(self, project_id, department_id) -> bool:
    dept = self.db.execute(
        "SELECT initially_active FROM departments WHERE id=?", (department_id,)).fetchone()
    if not dept:
        return False
    if dept["initially_active"]:
        return True
    return bool(self.db.execute(
        "SELECT 1 FROM project_department_activations WHERE project_id=? AND department_id=?",
        (project_id, department_id)).fetchone())
```

- [ ] **Step 3: Rewrite `dispatch_project_brief` signature**

```python
def dispatch_project_brief(self, actor, project_id, brief, department_budgets,
                           acceptance_criteria, due_at=None):
    self._ceo_or_admin_companion(actor)
    if not brief or not str(brief).strip():
        raise ValueError("Brief required")
    if not acceptance_criteria or not str(acceptance_criteria).strip():
        raise ValueError("Acceptance criteria required")
    if not isinstance(department_budgets, dict) or not department_budgets:
        raise ValueError("department_budgets mapping required")
    if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        raise ValueError("Project not found")
    known = {r[0] for r in self.db.execute("SELECT id FROM departments")}
    for dept_id, budget in department_budgets.items():
        if dept_id not in known:
            raise ValueError(f"Unknown department {dept_id}")
        money(budget)
        if not self.department_dispatchable(project_id, dept_id):
            raise ValueError(f"Department {dept_id} is dormant for this project; activate first")
    dispatches = []
    with self.tx():
        for dept_id, budget_cents in department_budgets.items():
            dispatch_id = str(uuid.uuid4())
            # ... work_order insert as today ...
            seat = self.db.execute(
                "SELECT * FROM department_seats WHERE department_id=?", (dept_id,)).fetchone()
            if seat and seat["status"] == "active" and seat["principal_id"]:
                status = "queued_for_head"
                head_pid = seat["principal_id"]
                inbox_at = now().isoformat()
            else:
                status = "blocked_vacant_head"
                head_pid = None
                inbox_at = None
            self.db.execute(
                "INSERT INTO project_dispatches VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (dispatch_id, project_id, dept_id, woid, brief.strip(),
                 acceptance_criteria.strip(), budget_cents, due_at, now().isoformat(),
                 status, head_pid, inbox_at))
            self._event("project.dispatched", {
                "dispatch_id": dispatch_id, "department_id": dept_id,
                "work_order_id": woid, "status": status,
            }, actor_id=actor, project_id=project_id)
            dispatches.append({
                "id": dispatch_id, "department_id": dept_id, "work_order_id": woid,
                "status": status, "head_principal_id": head_pid, "budget_cents": budget_cents,
            })
    return dispatches
```

Align INSERT column count with schema. Update `service.py` dispatch route to pass `payload["department_budgets"]`. Update `tests/test_production_slice.py` and `scripts/exercise_production_slice.py`.

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m unittest tests.test_org_roster tests.test_production_slice -v
.venv/bin/python -m unittest discover -s tests
```

- [ ] **Step 5: Commit**

```bash
git commit -m "Gate dispatch on department activation and per-dept budgets."
```

---

### Task 5: Head assign dispatch → queue + inbox read

**Files:**
- Modify: `company/core.py`
- Modify: `company/service.py`
- Test: `tests/test_org_handoff.py`

**Interfaces:**
- `Company.list_head_inbox(actor) -> {"items": [...]}` — dispatches where `head_principal_id=actor` and status in `queued_for_head`, `blocked_vacant_head` (CEO sees all open), plus `blocked` later
- `Company.assign_dispatch(actor, dispatch_id, assignee, action="draft", cost_cents=...) -> dict`
  - Actor is CEO or seated head for that department
  - If not CEO: require `_effective_grant` with `work.assign` in actions (or `draft` temporarily if policy templates lack `work.assign` — **prefer adding `work.assign` to head grant in test policy**, not weakening check)
  - If grant has `departments`, require `department_id in grant["departments"]`
  - Assignee: active `position_assignments` for department **or** grant exists for assignee on project (contractor path: `_effective_grant(assignee)` with project in projects)
  - Status → `assigned`; insert `dispatch_assignments`; call `queue_task(assignee, project_id, action, cost, task_id)`
  - Reject if status is `blocked_vacant_head` unless CEO first appointed head and re-opened (simpler: require status `queued_for_head` only)

- [ ] **Step 1: Failing tests in `tests/test_org_handoff.py`**

```python
class OrgHandoffTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Handoff")
        self.addCleanup(self.c.close)

    def _head_grant(self):
        # propose/approve policy grant for eng-cto with work.assign, projects=["app"], departments=["engineering"]
        ...

    def test_vacant_cannot_assign(self):
        d = self.c.dispatch_project_brief(
            "human-ceo", "app", "x", {"engineering": 100}, "y")[0]
        with self.assertRaises(ValueError):
            self.c.assign_dispatch("human-ceo", d["id"], "dev-1", action="draft", cost_cents=10)

    def test_head_assigns_rostered_specialist(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.c.assign_position("human-ceo", "engineering:Developer", "dev-1")
        self._head_grant()
        # also grant dev-1 draft on app
        d = self.c.dispatch_project_brief(
            "human-ceo", "app", "x", {"engineering": 500}, "y")[0]
        self.assertEqual(d["status"], "queued_for_head")
        result = self.c.assign_dispatch("eng-cto", d["id"], "dev-1", action="draft", cost_cents=25)
        self.assertEqual(result["status"], "assigned")
        q = self.c.db.execute("SELECT * FROM queue WHERE task_id=?", (result["queue_task_id"],)).fetchone()
        self.assertEqual(q["actor"], "dev-1")
        self.assertEqual(q["status"], "queued")

    def test_roster_miss_fails(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self._head_grant()
        d = self.c.dispatch_project_brief(
            "human-ceo", "app", "x", {"engineering": 500}, "y")[0]
        with self.assertRaises(PermissionError):
            self.c.assign_dispatch("eng-cto", d["id"], "not-on-roster", action="draft", cost_cents=10)

    def test_vacate_cancels_queued_descendant(self):
        # appoint, grant, assign to queue, vacate head → former head queued cancelled;
        # also mark open dispatches blocked or cancel assignee queue for that dispatch
        ...
```

- [ ] **Step 2: Implement `assign_dispatch` / `list_head_inbox`**

Core checks (exact):

```python
def assign_dispatch(self, actor, dispatch_id, assignee, *, action, cost_cents):
    money(cost_cents)
    row = self.db.execute(
        "SELECT * FROM project_dispatches WHERE id=?", (dispatch_id,)).fetchone()
    if not row:
        raise ValueError("Dispatch not found")
    if row["status"] != "queued_for_head":
        raise ValueError("Dispatch is not assignable")
    seat = self.db.execute(
        "SELECT * FROM department_seats WHERE department_id=?", (row["department_id"],)).fetchone()
    is_ceo = actor == self.ceo or str(actor).startswith("companion-admin-")
    if not is_ceo:
        if not seat or seat["status"] != "active" or seat["principal_id"] != actor:
            raise PermissionError("Seated head required")
        g = self._effective_grant(actor)
        if not g or "work.assign" not in g["actions"]:
            raise PermissionError("work.assign grant required")
        if row["project_id"] not in g["projects"]:
            raise PermissionError("Project out of grant scope")
        depts = g.get("departments")
        if depts is not None and row["department_id"] not in depts:
            raise PermissionError("Department out of grant scope")
    rostered = self.db.execute(
        """SELECT 1 FROM position_assignments
           WHERE department_id=? AND principal_id=? AND status='active'""",
        (row["department_id"], assignee)).fetchone()
    contractor = False
    ag = self._effective_grant(assignee)
    if ag and row["project_id"] in ag["projects"]:
        contractor = True
    if not rostered and not contractor:
        raise PermissionError("Assignee not on department roster and has no project grant")
    task_id = f"dispatch-assign-{dispatch_id[:8]}-{assignee}"
    with self.tx():
        # queue_task does its own tx in current code — either call outside nested tx
        # or inline queue insert; follow existing queue_task without nested tx conflict
        ...
```

If `queue_task` opens its own `tx()`, call it **outside** an outer transaction, then update dispatch status in a second transaction; or refactor to `_queue_task_unlocked`. Prefer two-step: `queue_task` then update dispatch + `dispatch_assignments` if queue succeeded.

On `vacate_head`: set open `project_dispatches` for that department with `head_principal_id=old` and status `queued_for_head` → `blocked_vacant_head`, clear `head_principal_id`; cancel `queue` rows for assignees on those dispatches via `dispatch_assignments`.

- [ ] **Step 3: API**

```python
@app.get("/api/v1/inbox/head")
def head_inbox(...):
    scoped(ident, "organization.read")
    return company.list_head_inbox(ident["principal_id"])

@app.post("/api/v1/dispatches/{dispatch_id}/assign")
def dispatch_assign(...):
    scoped(ident, "organization.write")  # core still enforces seat+grant
    ...
```

- [ ] **Step 4: Full unittest discover PASS + commit**

```bash
.venv/bin/python -m unittest discover -s tests
git commit -m "Add head inbox and grant-checked dispatch assignment."
```

---

### Task 6: Desk + companion UI + docs + version 0.3.51

**Files:**
- Modify: `company/service.py` (desk HTML/JS — Org section listing seats; project dispatch form uses `department_budgets`; head inbox list + assign)
- Modify: `companion/` pages (Org tab or section; handoff on Projects)
- Modify: `pyproject.toml`, `company/__init__.py`, `companion/package.json` → `0.3.51`
- Modify: `docs/18-handoff.md`, `docs/14-roadmap.md`, `docs/03-data-model.md`, `docs/decisions.md`, `docs/05-organization.md` (mark implemented vs design), `README.md` capability matrix
- Modify: design spec status → implemented when done
- Run: `python3 scripts/check_bundle.py`, `cd companion && npm run build`

- [ ] **Step 1: Desk** — fetch `GET /api/v1/org`; render department id, seat status, principal or “vacant”; no fake activity. Head inbox section: `GET /api/v1/inbox/head`. Dispatch UI: JSON/map of dept→budget instead of single budget.

- [ ] **Step 2: Companion** — same reads; appoint/assign forms for admin; avoid `window.prompt` where a small form fits (aligns with M10-04).

- [ ] **Step 3: Docs + version bump + matrix**

- [ ] **Step 4: Verify**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
python3 scripts/check_bundle.py
```

- [ ] **Step 5: Commit**

```bash
git commit -m "Surface org roster and head handoff in desk and companion (v0.3.51)."
```

---

### Task 7 (trailing): Cross-department work-order fields

**Files:**
- Modify: `company/schema.py`, new Alembic `0015_cross_dept_work_orders.py` (or fold into 0014 if not yet released — prefer **0015** if 0014 already shipped)
- Columns on `work_orders` or new `cross_department_requests`: `requesting_department_id`, `delivering_department_id`, `budget_owner`, `due_at`, `acceptance_criteria`, `escalation_path`, `status`
- Commands: `create_cross_dept_request`, `accept_cross_dept_request` (delivering head)
- Tests: create → delivering inbox → accept; reject side-channel as authority (N/A in code — just no chat API)

Ship only after Tasks 1–6 are green on fs-dev if desired.

---

## Self-review (plan vs spec)

| Spec item | Task |
|---|---|
| Approach B grants-only | Global + Tasks 2–5 |
| `department_seats` / `position_assignments` | Task 1–2 |
| Appoint/vacate/assign APIs | Task 2–3 |
| Activation + dormant reject | Task 4 |
| Per-dept budgets | Task 4 |
| Dispatch statuses + inbox | Task 4–5 |
| Head assign + roster/contractor + queue | Task 5 |
| Vacate blocks queue | Task 2 + 5 |
| Optional grant `departments` | Task 1 GRANT_OPTIONAL + Task 5 |
| UI desk/companion | Task 6 |
| Docs/matrix/handoff | Task 6 |
| Cross-dept WO | Task 7 |
| No invented healthy seats | Tasks 2, 6 |
| Employees link | Deferred: no duplicate authority; optional later mapping — not blocking M1–4 |

No TBD placeholders remain. `work.assign` must appear in test grants; seed policy templates are not auto-updated to grant heads.

---

## Execution note

Optional opt-in demo principal map (`FS_CORP_DEMO_ORG_SEED=1`) is **out of Task 1–6** unless needed for UI demos — do not invent seats in production seed.
