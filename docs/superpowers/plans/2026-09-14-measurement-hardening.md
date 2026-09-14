# Measurement Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.89 closing three 0.3.87 measurement nits: same-tx baseline/after with replay writes, `json_extract` list filter, denied-scope GET test.

**Architecture:** Move `ensure_measurement` calls inside existing authorize/complete `tx()` blocks; replace LIKE with `json_extract` in `list_measurements`; add 403 API test; bump versions and ADR-071.

**Tech Stack:** Python/SQLite company core, FastAPI tests, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-measurement-hardening-design.md` (owner-approved).
- Version **0.3.89**. Soften exact `0.3.88` pins to `0\.3\.\d+` where needed.
- Alembic: **none**.
- No new metrics, UI, scopes, or Stripe work.
- Auth stays `consultant.read` OR `company.read` for measurement GETs.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/measurement-hardening` from current `main` before Task 1.
- Work **in-place** on the feature branch.

## File map

| Path | Role |
|---|---|
| `company/core.py` | Co-commit `ensure_measurement` inside authorize/complete tx |
| `company/measurements.py` | `json_extract` list filter |
| `tests/test_work_order_measurements.py` | List filter + optional co-commit/rollback |
| `tests/test_desk_consultant_measurements.py` | Denied-scope 403 |
| Docs + versions | ADR-071, README, VERIFICATION, handoff, roadmap; **0.3.89** |

---

### Task 1: Co-commit + json_extract + denied-scope tests

**Files:**
- Modify: `company/core.py` (`record_work_order_authorized`, `complete_work_order_outcome`)
- Modify: `company/measurements.py` (`list_measurements`)
- Modify: `tests/test_work_order_measurements.py`
- Modify: `tests/test_desk_consultant_measurements.py`

**Interfaces:**
- Consumes: existing `ensure_measurement(company, actor, work_order_id, phase)`
- Produces: same public APIs; measurement rows co-committed with new replay inserts

- [ ] **Step 1: Create branch**

```bash
cd /Users/andrew/Documents/FS-Tech/fs-corporation
git checkout main
git pull --ff-only
git checkout -b feature/measurement-hardening
```

- [ ] **Step 2: Write failing tests**

Append to `tests/test_work_order_measurements.py`:

```python
class ListFilterTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_json_extract_not_like_false_positive(self):
        with self.c.tx():
            self.c.db.execute(
                "INSERT INTO work_orders VALUES(?,?,?,?,?,?,?)",
                ("wo-noise", "t1", 1, "digest", 0,
                 '{"note":"source:consultant elsewhere","source":"engineering"}',
                 "authorized"),
            )
        desk = ConsultantDesk(self.c)
        pid = desk.submit("consultant", PROPOSAL)
        desk.decide("human-ceo", pid, "approved", "ok")
        oid = desk.to_work_order("human-ceo", pid)
        ids = {row["work_order_id"] for row in self.c.list_work_order_measurements()}
        self.assertIn(oid, ids)
        self.assertNotIn("wo-noise", ids)


class CoCommitTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_failed_measurement_rolls_back_new_replay(self):
        import company.measurements as m
        real = m.ensure_measurement

        def boom(company, actor, work_order_id, phase):
            raise RuntimeError("force rollback")

        with self.c.tx():
            self.c.db.execute(
                "INSERT INTO work_orders VALUES(?,?,?,?,?,?,?)",
                ("wo-co", "t-co", 1, "d-co", 100,
                 '{"source":"consultant","proposal_id":"p"}', "authorized"),
            )
        m.ensure_measurement = boom
        try:
            with self.assertRaises(RuntimeError):
                self.c.record_work_order_authorized("human-ceo", "wo-co", "d-co")
        finally:
            m.ensure_measurement = real
        replay = self.c.db.execute(
            "SELECT 1 FROM work_order_replays WHERE work_order_id='wo-co'").fetchone()
        # GREEN after fix: replay rolled back with measurement
        self.assertIsNone(replay)
```

On RED (before fix), this co-commit assertion **fails** because the replay row is already committed.

Add to `tests/test_desk_consultant_measurements.py`:

```python
    def test_measurements_denied_without_read_scopes(self):
        c, _ = owner_client()
        self.addCleanup(c.close)
        c.register_identity("noscope", "service", "noscope-token", ["audit.read"])
        client = TestClient(create_app(c))
        r = client.get(
            "/api/v1/work-orders/measurements",
            headers={"Authorization": "Bearer noscope-token"},
        )
        self.assertEqual(r.status_code, 403, r.text)
```

(If `audit.read` is not a registered scope name in this codebase, use any scope that is **not** `consultant.read` / `company.read` — match patterns in `tests/test_api.py`.)

- [ ] **Step 3: Run — expect FAIL**

```bash
.venv/bin/python -m unittest \
  tests.test_work_order_measurements.ListFilterTests \
  tests.test_work_order_measurements.CoCommitTests \
  tests.test_desk_consultant_measurements.WorkOrderMeasurementsApiTests.test_measurements_denied_without_read_scopes \
  -v
```

Expected: co-commit assert fails (replay still present); list filter may pass or fail depending on LIKE false positive; denied-scope may fail if test missing.

- [ ] **Step 4: Implement**

In `company/core.py` `record_work_order_authorized` — move `ensure_measurement` **inside** the `with self.tx():` block that inserts the new authorized replay. Keep the post-tx call only for the **existing** authorized branch (idempotent baseline), or call ensure_measurement after the if/else for existing path only:

```python
        if existing:
            row = ...
            from company.measurements import ensure_measurement
            ensure_measurement(self, actor, work_order_id, "baseline")
        else:
            rid = str(uuid.uuid4())
            ...
            with self.tx():
                self.db.execute(...INSERT replay...)
                self._event(...)
                from company.measurements import ensure_measurement
                ensure_measurement(self, actor, work_order_id, "baseline")
            row = ...
        return row
```

In `complete_work_order_outcome`:

```python
        with self.tx():
            self.db.execute(...INSERT completed replay...)
            self._event(...)
            from company.measurements import ensure_measurement
            ensure_measurement(self, actor, work_order_id, "after")
```

In `company/measurements.py` `list_measurements` SQL WHERE clause:

```sql
WHERE json_extract(wo.payload, '$.source') = 'consultant'
```

- [ ] **Step 5: Run — expect PASS**

```bash
.venv/bin/python -m unittest tests.test_work_order_measurements tests.test_desk_consultant_measurements -v
```

Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add company/core.py company/measurements.py \
  tests/test_work_order_measurements.py tests/test_desk_consultant_measurements.py
git commit -m "$(cat <<'EOF'
fix(consultant): harden work-order measurement tx and list filter

EOF
)"
```

---

### Task 2: Version 0.3.89 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `docs/decisions.md` (ADR-071), `README.md`, `VERIFICATION.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`
- Modify: this design status → **implemented in v0.3.89**; note on 0.3.87 design that nits closed in 0.3.89
- Commit plan if untracked: `docs/superpowers/plans/2026-09-14-measurement-hardening.md`

**Interfaces:** none new.

- [ ] **Step 1: Bump versions to `0.3.89`**

- [ ] **Step 2: ADR-071** — co-commit, json_extract, denied-scope test; no Alembic.

- [ ] **Step 3: README / VERIFICATION / handoff / roadmap**

Handoff tip pin to **ship commit SHA** (not thrash HEAD).

- [ ] **Step 4: Full suite + companion build**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json docs/decisions.md README.md \
  VERIFICATION.md docs/18-handoff.md docs/14-roadmap.md \
  docs/superpowers/specs/2026-09-14-measurement-hardening-design.md \
  docs/superpowers/specs/2026-09-14-consultant-work-order-measurements-design.md \
  docs/superpowers/plans/2026-09-14-measurement-hardening.md
git commit -m "$(cat <<'EOF'
docs: ship measurement hardening as 0.3.89

EOF
)"
```

---

## Spec coverage

| Spec item | Task |
|---|---|
| Co-commit baseline/after | 1 |
| json_extract filter | 1 |
| Denied-scope GET | 1 |
| Version 0.3.89 + ADR-071 + docs | 2 |

## Plan self-review

- No TBD placeholders in final steps (Step 2 placeholder removed via Step 2b).
- Co-commit test proves RED→GREEN against separate-tx bug.
- Auth scopes unchanged.
