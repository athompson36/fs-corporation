# Dispatch Options + Recommend Autofill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dispatch parameter-key API and mock→live recommend/autofill on desk and companion so owners can fill brief, criteria, and department budgets from valid values without inventing operational state.

**Architecture:** New focused module `company/dispatch_recommend.py` owns templates, budget math, mock heuristics, live JSON parse/validate, and options assembly. `Company` exposes thin wrappers; FastAPI adds `GET …/dispatch-options` and `POST …/dispatch-recommend`. Desk HTML/JS and companion React call those endpoints, autofill editable fields, then still submit via existing `dispatch-brief`.

**Tech Stack:** Python 3.12+, FastAPI, SQLite/`Company`, unittest, companion React/TypeScript, CEO desk static HTML/JS.

## Global Constraints

- Recommendations never call `dispatch_project_brief`, never activate departments, never invent HQ/revenue state.
- Auth for both new routes: `project.enroll` (owner or paired admin), same as dispatch-brief.
- Mock recommend always works offline; live uses existing `invoke_model` + `MODEL_PROVIDER_API_KEY` / `ANTHROPIC_API_KEY`; on live failure return HTTP 200 mock with `notes`.
- Budgets are integer USD cents via `money()`; clamp to `[0, max_cents]`.
- Spec: `docs/superpowers/specs/2026-09-07-dispatch-recommend-autofill-design.md`.
- Prefer small focused modules; do not dump heuristics into `company/core.py`.

## File map

| File | Responsibility |
|---|---|
| Create `company/dispatch_recommend.py` | Templates, presets, options builder, mock recommend, live parse/validate |
| Modify `company/core.py` | `remaining_dispatch_budget_cents()`, `dispatch_options()`, `recommend_dispatch()` wrappers |
| Modify `company/service.py` | Two FastAPI routes + desk UI/JS for options/recommend |
| Modify `companion/src/api/client.ts` | `dispatchOptions()`, `dispatchRecommend()` |
| Modify `companion/src/App.tsx` | Dispatch form: templates, dept checkboxes, chips, Recommend, Valid values |
| Modify `companion/src/styles.css` | Minimal chip/badge styles if missing |
| Create `tests/test_dispatch_recommend.py` | Options + recommend + live fallback tests |
| Modify `tests/test_companion_api.py` | Desk/companion source assertions |
| Modify `docs/16-api-contract.md`, `docs/24-mobile-companion.md`, `docs/18-handoff.md`, `docs/decisions.md` | Contract + ADR-035 + handoff |

---

### Task 1: Core helpers — options + mock recommend

**Files:**
- Create: `company/dispatch_recommend.py`
- Modify: `company/core.py` (add methods near `dispatch_project_brief` ~4628)
- Test: `tests/test_dispatch_recommend.py`

**Interfaces:**
- Produces:
  - `BUDGET_PRESETS_CENTS = (100, 300, 500, 1000, 5000)`
  - `BRIEF_TEMPLATES` / `CRITERIA_TEMPLATES` lists of `{id, label, body}`
  - `build_dispatch_options(company, project_id) -> dict`
  - `mock_recommend(company, project_id) -> dict` with keys `source, live_attempted, brief, acceptance_criteria, departments, notes`
  - `validate_suggestion(raw, catalog_ids, max_cents) -> dict`
  - `Company.remaining_dispatch_budget_cents() -> int`
  - `Company.dispatch_options(project_id) -> dict`
  - `Company.recommend_dispatch(actor, project_id, use_live=True) -> dict` (Task 2 adds live; Task 1 can stub live as always-mock)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dispatch_recommend.py
import unittest
from pathlib import Path
from company.core import Company
from tests.test_core import install, policy


class DispatchOptionsTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "mobile-app", "Mobile companion pilot with API tests")

    def test_options_lists_catalog_and_templates(self):
        opts = self.c.dispatch_options("mobile-app")
        self.assertEqual(opts["project_id"], "mobile-app")
        ids = {d["id"] for d in opts["departments"]}
        self.assertIn("engineering", ids)
        self.assertIn("art", ids)
        art = next(d for d in opts["departments"] if d["id"] == "art")
        self.assertFalse(art["dispatchable"])
        self.assertEqual(art["status"], "dormant")
        fields = opts["fields"]
        self.assertGreaterEqual(len(fields["brief"]["templates"]), 2)
        self.assertEqual(fields["department_budgets"]["presets_cents"], [100, 300, 500, 1000, 5000])
        self.assertGreaterEqual(fields["department_budgets"]["max_cents"], 0)

    def test_mock_recommend_keyword_split(self):
        out = self.c.recommend_dispatch("human-ceo", "mobile-app", use_live=False)
        self.assertEqual(out["source"], "mock")
        ids = {d["id"] for d in out["departments"] if d["recommended"]}
        self.assertIn("engineering", ids)
        self.assertIn("product", ids)
        self.assertIn("quality", ids)  # brief contains "tests"
        max_c = self.c.dispatch_options("mobile-app")["fields"]["department_budgets"]["max_cents"]
        for d in out["departments"]:
            self.assertGreaterEqual(d["budget_cents"], 0)
            self.assertLessEqual(d["budget_cents"], max_c)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_dispatch_recommend -v`  
Expected: FAIL (`dispatch_options` / `recommend_dispatch` missing)

- [ ] **Step 3: Implement module + Company wrappers**

In `company/dispatch_recommend.py`:

```python
"""Dispatch parameter key + mock/live recommendation (advisory only)."""
from __future__ import annotations
import json
import re
from company.core import money

BUDGET_PRESETS_CENTS = (100, 300, 500, 1000, 5000)

BRIEF_TEMPLATES = [
    {"id": "ship-feature", "label": "Ship feature with tests",
     "body": "Deliver the next scoped feature for this project with automated coverage."},
    {"id": "bugfix", "label": "Bugfix with repro",
     "body": "Reproduce, fix, and verify the reported defect; include regression coverage."},
    {"id": "ops-hardening", "label": "Ops hardening",
     "body": "Harden deploy, monitoring, or recovery for this project without expanding product scope."},
]

CRITERIA_TEMPLATES = [
    {"id": "tests-qc", "label": "Tests + QC gate",
     "body": "Automated tests green; QC inspect passes; acceptance recorded."},
    {"id": "docs-only", "label": "Docs evidence",
     "body": "Documented change with linked evidence artifact."},
]

def remaining_budget_cents(company) -> int:
    policy = company.policy()
    company_budget = money(policy["company_budget_cents"])
    spent = company.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
    reserved = company.db.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE status='reserved'"
    ).fetchone()[0]
    return max(0, company_budget - int(spent) - int(reserved))

def build_dispatch_options(company, project_id: str) -> dict:
    row = company.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise ValueError("Project not found")
    max_cents = remaining_budget_cents(company)
    departments = []
    for dept in company.list_org()["departments"]:
        dispatchable = company.department_dispatchable(project_id, dept["id"])
        seat = dept.get("seat") or {}
        seat_status = seat.get("status") or "vacant"
        status = "active" if dispatchable else "dormant"
        departments.append({
            "id": dept["id"],
            "name": dept["name"],
            "status": status,
            "dispatchable": dispatchable,
            "seat_status": seat_status,
            "principal_id": seat.get("principal_id"),
        })
    return {
        "project_id": project_id,
        "brief_default": row["brief"],
        "fields": {
            "brief": {"kind": "text_with_templates", "required": True, "templates": list(BRIEF_TEMPLATES)},
            "acceptance_criteria": {
                "kind": "text_with_templates", "required": True, "templates": list(CRITERIA_TEMPLATES),
            },
            "department_budgets": {
                "kind": "cents_map", "required": True, "min_cents": 0, "max_cents": max_cents,
                "presets_cents": list(BUDGET_PRESETS_CENTS), "unit": "USD_cents",
                "max_basis": "company_budget_cents minus simulated spend and open reservations",
            },
            "due_at": {"kind": "datetime_optional", "required": False, "format": "ISO-8601"},
        },
        "departments": departments,
    }

def _keyword_departments(brief: str) -> list[str]:
    text = (brief or "").lower()
    chosen: list[str] = []
    def add(dept):
        if dept not in chosen:
            chosen.append(dept)
    if re.search(r"\b(code|app|api|repo|bug|fix)\b", text):
        add("engineering"); add("product")
    if re.search(r"\b(test|tests|qc|quality|acceptance)\b", text):
        add("quality")
    if re.search(r"\b(design|art|ui|brand)\b", text):
        add("art")
    if re.search(r"\b(launch|marketing|campaign)\b", text):
        add("marketing")
    if not chosen:
        add("engineering")
    return chosen

def _split_budgets(dept_ids: list[str], max_cents: int) -> dict[str, int]:
    if not dept_ids or max_cents <= 0:
        return {d: 0 for d in dept_ids}
    # Prefer documented example split when possible; otherwise equal presets.
    preferred = {"engineering": 300, "product": 200, "quality": 100, "art": 100, "marketing": 100}
    out = {}
    remaining = max_cents
    for d in dept_ids:
        want = preferred.get(d, 100)
        pick = 0
        for p in sorted(BUDGET_PRESETS_CENTS, reverse=True):
            if p <= want and p <= remaining:
                pick = p
                break
        if pick == 0 and remaining > 0:
            pick = min(remaining, BUDGET_PRESETS_CENTS[0])
        out[d] = pick
        remaining -= pick
    return out

def mock_recommend(company, project_id: str) -> dict:
    opts = build_dispatch_options(company, project_id)
    max_cents = opts["fields"]["department_budgets"]["max_cents"]
    brief_default = opts["brief_default"]
    dept_ids = _keyword_departments(brief_default)
    # Keep only catalog ids
    catalog = {d["id"] for d in opts["departments"]}
    dept_ids = [d for d in dept_ids if d in catalog]
    budgets = _split_budgets(dept_ids, max_cents)
    return {
        "source": "mock",
        "live_attempted": False,
        "brief": f"Ship {project_id}: {brief_default}",
        "acceptance_criteria": (
            f"{CRITERIA_TEMPLATES[0]['body']} Recorded for {project_id}."
        ),
        "departments": [
            {"id": d, "budget_cents": budgets[d], "recommended": True} for d in dept_ids
        ],
        "notes": [],
    }

def validate_suggestion(raw: dict, catalog_ids: set[str], max_cents: int) -> dict:
    brief = str(raw.get("brief") or "").strip()
    criteria = str(raw.get("acceptance_criteria") or "").strip()
    if not brief or not criteria:
        raise ValueError("brief and acceptance_criteria required")
    departments = []
    for item in raw.get("departments") or []:
        dept_id = str(item.get("id") or "").strip()
        if dept_id not in catalog_ids:
            continue
        amount = money(int(item.get("budget_cents") or 0))
        amount = max(0, min(amount, max_cents))
        departments.append({
            "id": dept_id,
            "budget_cents": amount,
            "recommended": bool(item.get("recommended", True)),
        })
    if not departments:
        raise ValueError("no valid departments")
    return {
        "brief": brief,
        "acceptance_criteria": criteria,
        "departments": departments,
    }
```

In `company/core.py` add:

```python
def remaining_dispatch_budget_cents(self):
    from company.dispatch_recommend import remaining_budget_cents
    return remaining_budget_cents(self)

def dispatch_options(self, project_id):
    from company.dispatch_recommend import build_dispatch_options
    return build_dispatch_options(self, project_id)

def recommend_dispatch(self, actor, project_id, use_live=True):
    self._ceo_or_admin_companion(actor)
    from company.dispatch_recommend import mock_recommend
    # Live path added in Task 2; Task 1 always returns mock.
    _ = use_live
    return mock_recommend(self, project_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_dispatch_recommend -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add company/dispatch_recommend.py company/core.py tests/test_dispatch_recommend.py
git commit -m "Add dispatch options catalog and mock recommend helpers."
```

---

### Task 2: Live recommend path + API routes

**Files:**
- Modify: `company/dispatch_recommend.py`
- Modify: `company/core.py` (`recommend_dispatch`)
- Modify: `company/service.py` (routes next to `dispatch_brief` ~1894)
- Modify: `tests/test_dispatch_recommend.py`

**Interfaces:**
- Consumes: Task 1 helpers; `Company.invoke_model`; `company.model_provider.status_summary`
- Produces: `recommend_dispatch(..., use_live)` with `source` `mock|live`; FastAPI:
  - `GET /api/v1/projects/{project_id}/dispatch-options`
  - `POST /api/v1/projects/{project_id}/dispatch-recommend`

- [ ] **Step 1: Write failing live-fallback + HTTP tests**

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from company.service import create_app
from tests.test_api import owner_client


class DispatchRecommendLiveTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "dash", "Dashboard API")

    def test_options_and_recommend_http(self):
        h = {"Authorization": "Bearer owner-token"}
        opts = self.client.get("/api/v1/projects/dash/dispatch-options", headers=h)
        self.assertEqual(opts.status_code, 200, opts.text)
        rec = self.client.post(
            "/api/v1/projects/dash/dispatch-recommend",
            json={"payload": {"use_live": False}},
            headers={**h, "Idempotency-Key": "rec-1"},
        )
        self.assertEqual(rec.status_code, 200, rec.text)
        body = rec.json()["result"] if "result" in rec.json() else rec.json()
        self.assertEqual(body["source"], "mock")

    def test_live_bad_json_falls_back_to_mock(self):
        with patch.object(self.c, "invoke_model", return_value={"text": "not-json", "provider": "openai"}):
            with patch("company.model_provider.status_summary", return_value={"live": True, "configured": True}):
                out = self.c.recommend_dispatch("human-ceo", "dash", use_live=True)
        self.assertEqual(out["source"], "mock")
        self.assertTrue(out["live_attempted"])
        self.assertIn("live_unusable", out["notes"])
```

Adjust assertions to match how `run()` wraps results in this codebase (`{"result": ...}` vs bare body).

- [ ] **Step 2: Run tests — expect FAIL** (routes / live notes missing)

- [ ] **Step 3: Implement live path**

In `dispatch_recommend.py` add `live_recommend(company, project_id) -> dict | None` that:

1. Calls `status_summary(probe=False)`; if not live/configured, return `None`.
2. Builds prompt asking for JSON only: `{"brief","acceptance_criteria","departments":[{"id","budget_cents"}]}`.
3. Picks profile id: prefer enabled profile with provider in `LIVE_PROVIDERS` from seeded models; if none, return `None`.
4. `company.invoke_model(profile_id, prompt, registry)` where registry is loaded like other call sites (seed `config/models.example.json` profiles dict).
5. Parse `result["text"]` as JSON (strip markdown fences if present); `validate_suggestion`; on any error return `None`.

In `Company.recommend_dispatch`:

```python
def recommend_dispatch(self, actor, project_id, use_live=True):
    self._ceo_or_admin_companion(actor)
    from company.dispatch_recommend import mock_recommend, live_recommend
    base = mock_recommend(self, project_id)
    if not use_live:
        return base
    live = live_recommend(self, project_id)
    if live is None:
        base = dict(base)
        base["live_attempted"] = True
        if "live_unavailable" not in base["notes"] and "live_unusable" not in base["notes"]:
            # live_recommend sets notes via raising path — prefer explicit:
            base["notes"] = list(base.get("notes") or []) + ["live_unavailable"]
        return base
    live["source"] = "live"
    live["live_attempted"] = True
    live["notes"] = []
    return live
```

Refine so `live_recommend` returns `("ok", payload)` / `("unusable",)` / `("unavailable",)` to set exact notes.

In `company/service.py` after `dispatch_brief`:

```python
@app.get("/api/v1/projects/{project_id}/dispatch-options")
def dispatch_options(project_id: str, authorization: str | None = Header(default=None)):
    ident = principal(authorization)
    scoped(ident, "project.enroll")
    try:
        return company.dispatch_options(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/v1/projects/{project_id}/dispatch-recommend")
def dispatch_recommend(
        project_id: str, body: Command,
        authorization: str | None = Header(default=None),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    ident = principal(authorization)
    scoped(ident, "project.enroll")
    payload = envelope(ident, body)
    use_live = payload.get("use_live", True)
    if payload.keys() - {"use_live"}:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(payload.keys() - {'use_live'})}")
    return run(
        ident, idempotency_key, payload | {"project_id": project_id},
        lambda: (company.recommend_dispatch(ident["principal_id"], project_id, use_live=bool(use_live)), 200),
    )
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `.venv/bin/python -m unittest tests.test_dispatch_recommend -v`

- [ ] **Step 5: Commit**

```bash
git add company/dispatch_recommend.py company/core.py company/service.py tests/test_dispatch_recommend.py
git commit -m "Expose dispatch-options and dispatch-recommend APIs with live fallback."
```

---

### Task 3: Desk UI — options, recommend, chips, valid values

**Files:**
- Modify: `company/service.py` (`DESK_HTML` dispatch form ~177–183 and JS ~390–420)
- Test: extend `tests/test_dispatch_recommend.py` or `tests/test_companion_api.py` with source assertions

**Interfaces:**
- Consumes: `GET …/dispatch-options`, `POST …/dispatch-recommend`
- Produces: desk controls `#dispatch-recommend-btn`, `#dispatch-brief-template`, `#dispatch-criteria-template`, `#dispatch-dept-list`, `#dispatch-valid-values`

- [ ] **Step 1: Write failing source assertions**

```python
def test_desk_wires_dispatch_recommend_controls(self):
    desk = (Path(__file__).resolve().parents[1] / "company" / "service.py").read_text()
    for needle in (
        'id="dispatch-recommend-btn"',
        "/dispatch-options",
        "/dispatch-recommend",
        'id="dispatch-brief-template"',
        'id="dispatch-valid-values"',
        "presets_cents",
    ):
        self.assertIn(needle, desk)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Update desk markup + JS**

Replace the budget textarea-only UX with:

- Template selects for brief/criteria (populate from options).
- `#dispatch-dept-list` rendered from options departments (checkbox + status badge + budget select/chips).
- Keep a hidden or secondary textarea sync for `department_budgets` map built from checked rows (or build JSON in submit handler).
- Button Recommend → POST recommend → fill fields; show source + notes in `#dispatch-status`.
- Collapsible `<details id="dispatch-valid-values">` listing templates, presets, max, department statuses.
- On dormant check: status text “Activate first” and disable submit while any checked dept has `dispatchable: false`.

Minimal submit change: build `department_budgets` from checked rows instead of only `parseDepartmentBudgets` textarea (may retain textarea as advanced fallback synced from chips).

- [ ] **Step 4: Run source assertion + full related tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add company/service.py tests/test_dispatch_recommend.py
git commit -m "Wire desk dispatch form to options catalog and recommend autofill."
```

---

### Task 4: Companion client + dispatch form UX

**Files:**
- Modify: `companion/src/api/client.ts`
- Modify: `companion/src/App.tsx` (project detail dispatch form)
- Modify: `companion/src/styles.css` (chips / badges if needed)
- Modify: `tests/test_companion_api.py`

**Interfaces:**
- Produces:
  - `ApiClient.dispatchOptions(projectId)`
  - `ApiClient.dispatchRecommend(projectId, useLive?: boolean)`
  - UI: template selects, dept checkboxes with status, budget chips, Recommend button, Valid values disclosure

- [ ] **Step 1: Failing source assertions**

```python
def test_companion_wires_dispatch_recommend(self):
    root = Path(__file__).resolve().parents[1] / "companion" / "src"
    client = (root / "api" / "client.ts").read_text()
    app = (root / "App.tsx").read_text()
    self.assertIn("/dispatch-options", client)
    self.assertIn("/dispatch-recommend", client)
    self.assertIn("dispatchRecommend", client)
    self.assertIn("Recommend for this project", app)
    self.assertIn("dispatch-brief-template", app)
    self.assertIn("Valid values", app)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement client methods**

```typescript
dispatchOptions(projectId: string) {
  return this.get<DispatchOptions>(`/api/v1/projects/${projectId}/dispatch-options`);
}

dispatchRecommend(projectId: string, useLive = true) {
  return this.post(
    `/api/v1/projects/${projectId}/dispatch-recommend`,
    { use_live: useLive },
    `dispatch-rec-${projectId}`,
  );
}
```

Add TypeScript types matching the options/recommend JSON from the spec.

- [ ] **Step 4: Rebuild dispatch form in App.tsx**

On `selectedProject` + project detail:

1. `useEffect` load `dispatchOptions(selectedProject)`.
2. State: selected template ids, brief, criteria, `Record<deptId, {checked, budget}>`, recommendSource.
3. Recommend button → `runAction("dispatch-recommend", …)` → autofill.
4. Budget chips from `presets_cents` filtered to `<= max_cents`; custom number input clamped.
5. Dormant checked → show Activate control (reuse existing activate fields/API) and block submit.
6. Submit builds `departmentBudgets` from checked rows and calls existing `dispatchBrief`.
7. `<details>` Valid values panel summarizing options payload.

Keep touch styles (44px / 16px). Add `.chip` / `.badge-dormant` only if needed.

- [ ] **Step 5: `cd companion && npm run build` and unittest assertions — PASS**

- [ ] **Step 6: Commit**

```bash
git add companion/src/api/client.ts companion/src/App.tsx companion/src/styles.css tests/test_companion_api.py
git commit -m "Add companion dispatch recommend autofill and parameter key UI."
```

---

### Task 5: Docs + ADR + verification

**Files:**
- Modify: `docs/16-api-contract.md`
- Modify: `docs/24-mobile-companion.md`
- Modify: `docs/18-handoff.md`
- Modify: `docs/decisions.md` (ADR-035)
- Modify: `docs/superpowers/specs/2026-09-07-dispatch-recommend-autofill-design.md` (status → implemented when done)

- [ ] **Step 1: Document routes** in `16-api-contract.md`:

| Method | Path | Scope |
|---|---|---|
| GET | `/projects/{id}/dispatch-options` | `project.enroll` |
| POST | `/projects/{id}/dispatch-recommend` | `project.enroll` |

- [ ] **Step 2: ADR-035** — advisory recommend/autofill; mock→live; never auto-dispatch; parameter key from server.

- [ ] **Step 3: Update handoff + mobile companion feature table** for Recommend / Valid values.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build succeeds.

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "Document dispatch options/recommend API and record ADR-035."
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| `GET dispatch-options` parameter key | 1, 2 |
| Templates + presets + max_cents | 1 |
| Full catalog statuses / dispatchable | 1 |
| Mock keyword recommend | 1 |
| Live invoke + validate + fallback notes | 2 |
| Desk autofill + Valid values | 3 |
| Companion autofill + Valid values | 4 |
| Never auto-dispatch | 1–4 (UI still uses dispatch-brief) |
| Docs / ADR | 5 |
| Tests listed in spec | 1, 2, 3, 4 |

## Plan self-review

- No TBD/placeholder steps; concrete code and commands included.
- Types/`source`/`notes` consistent across tasks.
- Live path does not depend on mock provider string output for success (mock heuristics are separate from `invoke_model("mock-text")`).
