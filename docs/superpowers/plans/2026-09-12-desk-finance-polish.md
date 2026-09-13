# Desk Finance Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desk Finance polish v0.3.80 — upfront `company.pause` gate via `/api/v1/session`, restore openRoom simulated spend, scope the dump ban to `#budget` only.

**Architecture:** In-place DESK_HTML JS: `applyFinancePauseFromSession()` fetches session scopes and calls existing `setFinanceMutateEnabled`. Soften `test_no_budget_json_dump` to extract the `#budget` section. Restore the openRoom costs line. Keep 403 fail-closed backup.

**Tech Stack:** Desk HTML/JS in `company/service.py`, existing `/api/v1/session`, Python unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-desk-finance-polish-design.md` (owner-approved).
- Version **0.3.80**. Soften older exact `0.3.79` pins; exact `0.3.80` only in this release’s contract.
- No new APIs, companion behavior changes (version lockstep only), no desk ModeSwitch.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-finance-polish` from current `main` before Task 1.

## File map

| Path | Role |
|---|---|
| `tests/test_desk_finance_polish.py` | New contracts for session gate + openRoom + version **0.3.80** |
| `tests/test_desk_finance_surface.py` | Soften `#budget`-scoped dump ban |
| `company/service.py` | Session pause gate + openRoom restore |
| Docs + versions | ADR-062, **0.3.80** |

---

### Task 1: Failing contracts + scoped dump ban (RED)

**Files:**
- Create: `tests/test_desk_finance_polish.py`
- Modify: `tests/test_desk_finance_surface.py` (`test_no_budget_json_dump` only — make it section-scoped so openRoom restore can land later without fighting this module)

**Interfaces:**
- Consumes: none
- Produces: RED polish contracts; GREEN scoped dump ban (section extract works even before openRoom restore)

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-finance-polish
```

- [ ] **Step 2: Soften `test_no_budget_json_dump`**

Replace the body of `test_no_budget_json_dump` in `tests/test_desk_finance_surface.py` with:

```python
    def test_no_budget_json_dump(self):
        html = DESK_HTML
        start = html.find('id="budget"')
        self.assertGreater(start, -1)
        # section opens at nearest preceding <section
        sec_start = html.rfind("<section", 0, start)
        self.assertGreater(sec_start, -1)
        sec_end = html.find("</section>", start)
        self.assertGreater(sec_end, -1)
        budget = html[sec_start : sec_end + len("</section>")]
        self.assertNotIn("budget-json", budget)
        self.assertNotIn("simulated_spend_cents", budget)
```

Keep `test_version_lockstep_soft` as soft regex (already soft from 0.3.79).

- [ ] **Step 3: Write polish contracts**

```python
"""Desk Finance polish — pause gate + openRoom (v0.3.80)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskFinancePolishTests(unittest.TestCase):
    def test_session_pause_gate_markers(self):
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertIn("applyFinancePauseFromSession", DESK_HTML)
        self.assertIn("company.pause", DESK_HTML)
        self.assertRegex(DESK_HTML, r"await\s+applyFinancePauseFromSession\s*\(")
        self.assertEqual(DESK_HTML.count("setFinanceMutateEnabled(true)"), 0)

    def test_open_room_restores_simulated_spend(self):
        self.assertIn("async function openRoom", DESK_HTML)
        idx = DESK_HTML.find("async function openRoom")
        chunk = DESK_HTML[idx : idx + 1200]
        self.assertIn("simulated_spend_cents", chunk)
        self.assertIn("reserved_cents", chunk)

    def test_version_0_3_80(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.80"', init)
        self.assertIn('"version": "0.3.80"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run RED**

```bash
.venv/bin/python -m unittest tests.test_desk_finance_surface.DeskFinanceSurfaceTests.test_no_budget_json_dump \
  tests.test_desk_finance_polish -v
```

Expected: scoped dump test PASS; polish tests FAIL (no session helper / no openRoom literal / version 0.3.79).

- [ ] **Step 5: Commit**

```bash
git add tests/test_desk_finance_polish.py tests/test_desk_finance_surface.py
git commit -m "$(cat <<'EOF'
test: desk Finance polish contracts (0.3.80)

EOF
)"
```

---

### Task 2: Session pause gate + openRoom restore

**Files:**
- Modify: `company/service.py` (DESK_HTML JS)

**Interfaces:**
- Consumes: existing `setFinanceMutateEnabled`, `loadFinance`, `headers`
- Produces: `applyFinancePauseFromSession`; openRoom spend line

- [ ] **Step 1: Add `applyFinancePauseFromSession` near finance helpers**

```javascript
async function applyFinancePauseFromSession() {
  try {
    const res = await fetch('/api/v1/session', {headers});
    if (!res.ok) {
      setFinanceMutateEnabled(false);
      return;
    }
    const body = await res.json();
    const scopes = Array.isArray(body.scopes) ? body.scopes : [];
    setFinanceMutateEnabled(scopes.indexOf('company.pause') !== -1);
  } catch (e) {
    setFinanceMutateEnabled(false);
  }
}
```

(Use `indexOf` for older desk JS style consistency with the file; or `.includes` if already used nearby.)

- [ ] **Step 2: Call from `load()`**

Near `await loadFinance();` inside `async function load()`, add:

```javascript
  await applyFinancePauseFromSession();
  await loadFinance();
```

Order: session gate first so forms are disabled before finance lists paint if needed.

- [ ] **Step 3: Remove unconditional enable**

Delete the line:

```javascript
setFinanceMutateEnabled(true);
```

that currently sits after the finance form listeners (near adjustment-amount disabled wiring). Keep the adjustment-kind disabled wiring.

If other `setFinanceMutateEnabled(true)` calls exist only as “re-enable after success”, remove those too — session/403 own enablement. Search DESK_HTML for all occurrences; after this task, count must be 0 for `(true)`.

- [ ] **Step 4: Restore openRoom costs line**

Replace:

```javascript
    'Reserved: ' + detail.costs.reserved_cents + '¢',
```

with:

```javascript
    'Simulated spend: ' + detail.costs.simulated_spend_cents + '¢ reserved '
      + detail.costs.reserved_cents + '¢',
```

- [ ] **Step 5: Run polish + surface tests**

```bash
.venv/bin/python -m unittest tests.test_desk_finance_polish tests.test_desk_finance_surface -v
```

Expected: all PASS except `test_version_0_3_80` (still 0.3.79).

- [ ] **Step 6: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): session pause gate and restore openRoom spend

EOF
)"
```

---

### Task 3: Version 0.3.80 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `tests/test_companion_finance_url_polish.py` (soften exact `0.3.79`)
- Modify: docs (UX, ADR-062, roadmap, handoff, design spec status, README)

**Interfaces:**
- Consumes: Task 2 complete
- Produces: green version test + docs

- [ ] **Step 1: Bump versions to 0.3.80**

- [ ] **Step 2: Soften companion polish exact pin**

In `tests/test_companion_finance_url_polish.py` version test, use soft `0\.3\.\d+` regex (rename method if helpful).

- [ ] **Step 3: Docs**

- ADR-062 index: `Desk Finance polish | Session pause gate via /api/v1/session; openRoom simulated spend; #budget-scoped dump ban; no new APIs.`
- ADR-062 detail (ADR-061 style).
- UX: desk Finance mutations gated by session scopes; HQ room detail shows simulated + reserved again.
- Roadmap / handoff / README / mark design spec implemented.
- Handoff: feature-branch pending merge until ship.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json \
  tests/test_companion_finance_url_polish.py tests/test_desk_finance_polish.py \
  docs/11-user-experience.md docs/decisions.md docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-desk-finance-polish-design.md README.md
git commit -m "$(cat <<'EOF'
docs: Desk Finance polish and release 0.3.80

EOF
)"
```

---

## Plan self-review

1. Spec coverage: Fix 1 → Task 2; Fix 2 → Tasks 1+2; version/docs → Task 3.
2. No placeholders.
3. Helper name `applyFinancePauseFromSession` consistent across tests and implementation.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-12-desk-finance-polish.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute in this session with checkpoints  

Which approach?
