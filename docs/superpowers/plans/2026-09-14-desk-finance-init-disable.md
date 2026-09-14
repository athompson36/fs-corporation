# Desk Finance Init-Time Mutate Disable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship desk v0.3.82 so Finance mutate controls are disabled (and the pause notice visible) from first paint until `/api/v1/session` enables them.

**Architecture:** In-place `DESK_HTML` in `company/service.py`: static controls ship `disabled`; `#finance-scope-notice` ships without `hidden`; call `setFinanceMutateEnabled(false)` once after the helper is defined. Keep `applyFinancePauseFromSession` and 403 backup unchanged.

**Tech Stack:** Desk HTML/JS in `company/service.py`, Python unittest source contracts, companion version lockstep only.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-desk-finance-init-disable-design.md` (owner-approved).
- Version **0.3.82**. Soften exact `0.3.81` pins (e.g. `tests/test_companion_tab_url_flash.py`) to `0\.3\.\d+`; exact `0.3.82` only in this release’s contract.
- No new APIs, Alembic, companion behavior beyond lockstep, no ModeSwitch.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-finance-init-disable` from current `main` before Task 1.
- Work in-place on the feature branch (dirty tree may have untracked `local repos/`).

## File map

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + init `setFinanceMutateEnabled(false)` |
| `tests/test_desk_finance_init_disable.py` | Source contracts + version **0.3.82** |
| `tests/test_companion_tab_url_flash.py` | Soften exact `0.3.81` version pin |
| Docs + versions | ADR-064, UX/roadmap/handoff; `__version__` + `package.json` **0.3.82** |

---

### Task 1: RED contracts + DESK_HTML init disable

**Files:**
- Create: `tests/test_desk_finance_init_disable.py`
- Modify: `company/service.py` (`DESK_HTML` only)
- Test: `tests/test_desk_finance_polish.py` (must stay green — still asserts no `setFinanceMutateEnabled(true)`)

**Interfaces:**
- Consumes: existing `setFinanceMutateEnabled`, `applyFinancePauseFromSession`
- Produces: fail-closed markup + init call; RED version test until Task 2

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-finance-init-disable
```

- [ ] **Step 2: Write failing source-contract module**

```python
"""Desk Finance init-time mutate disable (v0.3.82)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


def _budget_section(html: str) -> str:
    start = html.find('id="budget"')
    assert start != -1
    end = html.find("</section>", start)
    assert end != -1
    return html[start:end]


class DeskFinanceInitDisableTests(unittest.TestCase):
    def test_scope_notice_visible_in_markup(self):
        # Must not be hidden at first paint
        self.assertRegex(
            DESK_HTML,
            r'<p id="finance-scope-notice" class="muted">Mutations require company\.pause\.</p>',
        )
        self.assertNotRegex(
            DESK_HTML,
            r'<p id="finance-scope-notice"[^>]*\bhidden\b',
        )

    def test_static_mutate_controls_disabled_in_markup(self):
        section = _budget_section(DESK_HTML)
        for control_id in (
            "desk-finance-invoice-submit",
            "desk-finance-adjustment-submit",
            "desk-finance-period-submit",
            "desk-finance-invoice-month",
            "desk-finance-period-30d",
        ):
            self.assertRegex(
                section,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_init_calls_set_finance_mutate_enabled_false(self):
        # After setFinanceMutateEnabled is defined, an init call must disable
        idx = DESK_HTML.find("function setFinanceMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 1200]
        # Closing brace of function then init call — allow whitespace/newlines
        self.assertRegex(
            after,
            r"function setFinanceMutateEnabled\(enabled\) \{.*?\}\s*setFinanceMutateEnabled\(false\);",
            re.S,
        )

    def test_session_and_403_paths_preserved(self):
        self.assertIn("applyFinancePauseFromSession", DESK_HTML)
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertRegex(DESK_HTML, r"await\s+applyFinancePauseFromSession\s*\(")
        self.assertEqual(DESK_HTML.count("setFinanceMutateEnabled(true)"), 0)
        # 403 backup still disables
        self.assertIn("setFinanceMutateEnabled(false)", DESK_HTML)

    def test_version_0_3_82(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.82"', init)
        self.assertIn('"version": "0.3.82"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run contracts — expect RED**

```bash
.venv/bin/python -m unittest tests.test_desk_finance_init_disable -v
```

Expected: FAIL (notice still `hidden`, controls lack `disabled`, no init call, version still 0.3.81).

- [ ] **Step 4: Markup — notice + disabled controls**

In `company/service.py` `DESK_HTML`:

Replace:

```html
<p id="finance-scope-notice" class="muted" hidden>Mutations require company.pause.</p>
```

with:

```html
<p id="finance-scope-notice" class="muted">Mutations require company.pause.</p>
```

Add `disabled` to the five buttons (attribute order may be `disabled` before or after `id` — either is fine if the regex matches). Example shapes:

```html
<button type="button" class="chip" id="desk-finance-invoice-month" disabled>This calendar month</button>
<button type="submit" class="chip" id="desk-finance-invoice-submit" disabled>Create invoice</button>
```

```html
<button type="submit" class="chip" id="desk-finance-adjustment-submit" disabled>Post adjustment</button>
```

```html
<button type="button" class="chip" id="desk-finance-period-30d" disabled>Next 30 days</button>
<button type="submit" class="chip" id="desk-finance-period-submit" disabled>Set period</button>
```

- [ ] **Step 5: Init call after helper**

Immediately after the closing `}` of `function setFinanceMutateEnabled(enabled) { ... }`, add:

```javascript
setFinanceMutateEnabled(false);
```

Do **not** add `setFinanceMutateEnabled(true)` anywhere. Keep `applyFinancePauseFromSession` and the 403 path that calls `setFinanceMutateEnabled(false)`.

- [ ] **Step 6: Re-run Task 1 contracts**

```bash
.venv/bin/python -m unittest tests.test_desk_finance_init_disable tests.test_desk_finance_polish -v
```

Expected: markup/init/session tests PASS; `test_version_0_3_82` still FAIL.

- [ ] **Step 7: Commit** (if authorized)

```bash
git add \
  company/service.py \
  tests/test_desk_finance_init_disable.py \
  docs/superpowers/specs/2026-09-14-desk-finance-init-disable-design.md \
  docs/superpowers/plans/2026-09-14-desk-finance-init-disable.md
git commit -m "$(cat <<'EOF'
fix(desk): disable Finance mutate controls until session

EOF
)"
```

Include design + plan only if still uncommitted.

---

### Task 2: Version 0.3.82 + docs

**Files:**
- Modify: `company/__init__.py`
- Modify: `companion/package.json`
- Modify: `tests/test_companion_tab_url_flash.py` (soften exact `0.3.81`)
- Modify: `docs/decisions.md` (ADR-064 + index row)
- Modify: `docs/11-user-experience.md` (one sentence: Finance forms fail-closed until session)
- Modify: `docs/14-roadmap.md` (v0.3.82 status + checkbox + immediate next)
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-14-desk-finance-init-disable-design.md` (status → implemented)

**Interfaces:**
- Consumes: Task 1 complete
- Produces: shipped docs + version **0.3.82**

- [ ] **Step 1: Bump versions**

`company/__init__.py`:

```python
__version__ = "0.3.82"
```

`companion/package.json`: `"version": "0.3.82"`.

In `tests/test_companion_tab_url_flash.py` `test_version_0_3_81`, soften to:

```python
self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

(Keep the method name or rename to `test_version_lockstep` — either OK.)

- [ ] **Step 2: ADR-064**

Add index row and detail in `docs/decisions.md`:

- **Decision:** Desk Finance mutate controls ship `disabled` with visible `#finance-scope-notice`; call `setFinanceMutateEnabled(false)` at init; session/403 paths unchanged.
- **Consequences:** v0.3.82; broader desk session use remains follow-up.

- [ ] **Step 3: UX / roadmap / handoff / spec status**

- UX: note Finance forms fail closed from first paint until session scopes apply.
- Roadmap: checkbox for desk Finance init-time disable **0.3.82**; update status blurb; next = owner-directed.
- Handoff: version **0.3.82**, branch tip until merge; verification commands; next tasks.
- Spec status → **implemented in v0.3.82**.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build OK; package version 0.3.82.

- [ ] **Step 5: Commit** (if authorized)

```bash
git add company/__init__.py companion/package.json \
  tests/test_desk_finance_init_disable.py tests/test_companion_tab_url_flash.py \
  docs/decisions.md docs/11-user-experience.md docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-14-desk-finance-init-disable-design.md
git commit -m "$(cat <<'EOF'
docs: ship desk Finance init-time disable as 0.3.82

EOF
)"
```

Only stage paths that actually changed.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Notice visible (no `hidden`) | 1 |
| Five static controls `disabled` in markup | 1 |
| Init `setFinanceMutateEnabled(false)` | 1 |
| Session / 403 unchanged | 1 |
| Version 0.3.82 + ADR/docs | 2 |
| Soften 0.3.81 pin | 2 |

## Plan self-review

- No TBD steps; markup ids and regexes are concrete.
- Init-call regex requires the call immediately after the helper body (matches spec “after helper defined”).
- Polish test `count(...(true)) == 0` remains compatible.
