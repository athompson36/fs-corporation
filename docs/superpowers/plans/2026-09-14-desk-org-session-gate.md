# Desk Organization Session Mutate Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship desk v0.3.83 so Organization Manage forms fail closed until `/api/v1/session` confirms `organization.write`, sharing one session fetch with Finance.

**Architecture:** In-place `DESK_HTML`: `#org-scope-notice` + seven disabled submit ids; `setOrgMutateEnabled`; rename/extend session apply to set Finance + Org from one response; `submitOrgCommand` 403 → org disable.

**Tech Stack:** Desk HTML/JS in `company/service.py`, Python unittest source contracts, companion version lockstep only.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-desk-org-session-gate-design.md` (owner-approved).
- Version **0.3.83**. Soften exact `0.3.82` pins (e.g. `tests/test_desk_finance_init_disable.py`) to `0\.3\.\d+`; exact `0.3.83` only in this release’s contract.
- Gate **only** the seven `#departments` Manage submits. Do not gate objectives/cross-dept/divisions/staffing-scan.
- One shared session fetch for Finance + Org. No second `/api/v1/session` round-trip.
- No new APIs, Alembic, companion behavior beyond lockstep.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-org-session-gate` from current `main` before Task 1.
- Work in-place on the feature branch.

## File map

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML org gate + shared session |
| `tests/test_desk_org_session_gate.py` | Source contracts + version **0.3.83** |
| `tests/test_desk_finance_init_disable.py` | Soften exact `0.3.82` version pin |
| Docs + versions | ADR-065, UX/roadmap/handoff; **0.3.83** |

---

### Task 1: RED contracts + DESK_HTML org gate

**Files:**
- Create: `tests/test_desk_org_session_gate.py`
- Modify: `company/service.py` (`DESK_HTML` only)
- Test: existing finance init/polish contracts must stay green

**Interfaces:**
- Consumes: existing `setFinanceMutateEnabled`, `/api/v1/session`, `submitOrgCommand`
- Produces: `setOrgMutateEnabled`; shared session apply; seven button ids; RED version until Task 2

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-org-session-gate
```

- [ ] **Step 2: Write failing source-contract module**

```python
"""Desk Organization session mutate gate (v0.3.83)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]

ORG_SUBMIT_IDS = (
    "desk-org-create-dept-submit",
    "desk-org-appoint-head-submit",
    "desk-org-vacate-head-submit",
    "desk-org-assign-position-submit",
    "desk-org-release-assignment-submit",
    "desk-org-create-position-submit",
    "desk-org-reorder-submit",
)


def _departments_section(html: str) -> str:
    start = html.find('id="departments"')
    assert start != -1
    end = html.find("</section>", start)
    assert end != -1
    return html[start:end]


class DeskOrgSessionGateTests(unittest.TestCase):
    def test_org_scope_notice_visible(self):
        self.assertRegex(
            DESK_HTML,
            r'<p id="org-scope-notice" class="muted">Mutations require organization\.write\.</p>',
        )
        self.assertNotRegex(DESK_HTML, r'<p id="org-scope-notice"[^>]*\bhidden\b')

    def test_org_submit_controls_disabled_in_markup(self):
        section = _departments_section(DESK_HTML)
        for control_id in ORG_SUBMIT_IDS:
            self.assertRegex(
                section,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_org_mutate_enabled_and_init(self):
        self.assertRegex(DESK_HTML, r"function setOrgMutateEnabled\s*\(")
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        after = DESK_HTML[idx : idx + 1500]
        self.assertRegex(
            after,
            r"(?s)function setOrgMutateEnabled\s*\(enabled\)\s*\{.*?\}\s*setOrgMutateEnabled\(false\);",
        )
        for control_id in ORG_SUBMIT_IDS:
            self.assertIn(control_id, after)

    def test_shared_session_applies_org_and_finance(self):
        # Single session fetch applies both scopes
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertIn("organization.write", DESK_HTML)
        self.assertIn("company.pause", DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r"setOrgMutateEnabled\s*\(\s*scopes\.indexOf\(['\"]organization\.write['\"]\)",
        )
        self.assertRegex(
            DESK_HTML,
            r"setFinanceMutateEnabled\s*\(\s*scopes\.indexOf\(['\"]company\.pause['\"]\)",
        )
        # Prefer one await of shared apply (rename OK)
        self.assertRegex(
            DESK_HTML,
            r"await\s+(?:applySessionScopes|applyFinancePauseFromSession)\s*\(",
        )
        # Fail-closed paths for org on session error
        self.assertGreaterEqual(DESK_HTML.count("setOrgMutateEnabled(false)"), 2)

    def test_submit_org_command_403_disables(self):
        idx = DESK_HTML.find("async function submitOrgCommand")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 800]
        self.assertIn("403", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_version_0_3_83(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.83"', init)
        self.assertIn('"version": "0.3.83"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run contracts — expect RED**

```bash
.venv/bin/python -m unittest tests.test_desk_org_session_gate -v
```

Expected: FAIL.

- [ ] **Step 4: Markup — notice + seven disabled submits**

In `#departments` section of `DESK_HTML`:

1. Insert before the first Manage form (`create-department-form`):

```html
<p id="org-scope-notice" class="muted">Mutations require organization.write.</p>
```

2. Replace the seven submit buttons with id + `disabled` (keep labels):

| Form | Button markup |
|---|---|
| create-department | `<button type="submit" class="chip" id="desk-org-create-dept-submit" disabled>Create department</button>` |
| appoint-head | `id="desk-org-appoint-head-submit"` |
| vacate-head | `id="desk-org-vacate-head-submit"` |
| assign-position | `id="desk-org-assign-position-submit"` |
| release-assignment | `id="desk-org-release-assignment-submit"` |
| create-position | `id="desk-org-create-position-submit"` |
| reorder | `id="desk-org-reorder-submit"` |

- [ ] **Step 5: `setOrgMutateEnabled` + init**

Near `setFinanceMutateEnabled`, add:

```javascript
function setOrgMutateEnabled(enabled) {
  const notice = document.getElementById('org-scope-notice');
  if (notice) notice.hidden = !!enabled;
  [
    'desk-org-create-dept-submit',
    'desk-org-appoint-head-submit',
    'desk-org-vacate-head-submit',
    'desk-org-assign-position-submit',
    'desk-org-release-assignment-submit',
    'desk-org-create-position-submit',
    'desk-org-reorder-submit',
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  });
}
setOrgMutateEnabled(false);
```

- [ ] **Step 6: Shared session apply**

Replace `applyFinancePauseFromSession` body to also set org (rename to `applySessionScopes` preferred; if renaming, update the `await` in `load()`):

```javascript
async function applySessionScopes() {
  try {
    const res = await fetch('/api/v1/session', {headers});
    if (!res.ok) {
      setFinanceMutateEnabled(false);
      setOrgMutateEnabled(false);
      return;
    }
    const body = await res.json();
    const scopes = Array.isArray(body.scopes) ? body.scopes : [];
    setFinanceMutateEnabled(scopes.indexOf('company.pause') !== -1);
    setOrgMutateEnabled(scopes.indexOf('organization.write') !== -1);
  } catch (e) {
    setFinanceMutateEnabled(false);
    setOrgMutateEnabled(false);
  }
}
```

Update `load()` to `await applySessionScopes();` (and remove the old function name if renamed). Soften finance polish/init tests that require the exact string `applyFinancePauseFromSession` if they fail — prefer updating those asserts to accept `applySessionScopes` **or** keep the old name as an alias:

```javascript
async function applyFinancePauseFromSession() { return applySessionScopes(); }
```

Simplest for green finance contracts: **keep the function name** `applyFinancePauseFromSession` and extend its body to also call `setOrgMutateEnabled(...)`. Do that unless renaming is cleaner and you update finance tests in the same commit.

**Preferred for this task:** keep name `applyFinancePauseFromSession`, extend body (no finance test churn).

- [ ] **Step 7: `submitOrgCommand` 403**

```javascript
async function submitOrgCommand(form, path, payload, success) {
  const status = form.querySelector('span');
  const res = await fetch(path, {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-org-' + Date.now()},
    body: JSON.stringify({payload})
  });
  if (res.status === 403) {
    setOrgMutateEnabled(false);
  }
  status.textContent = res.ok ? ' ' + success : ' ' + await res.text();
  if (res.ok) { form.reset(); load(); }
}
```

Note: read `res.text()` only once — if you need text after status check, clone or buffer:

```javascript
  const text = await res.text();
  if (res.status === 403) setOrgMutateEnabled(false);
  status.textContent = res.ok ? ' ' + success : ' ' + text;
  if (res.ok) { form.reset(); load(); }
```

- [ ] **Step 8: Re-run Task 1 contracts + finance suite slice**

```bash
.venv/bin/python -m unittest \
  tests.test_desk_org_session_gate \
  tests.test_desk_finance_init_disable \
  tests.test_desk_finance_polish -v
```

Expected: org markup/session/403 PASS; `test_version_0_3_83` FAIL; finance tests PASS.

- [ ] **Step 9: Commit** (if authorized)

```bash
git add \
  company/service.py \
  tests/test_desk_org_session_gate.py \
  docs/superpowers/specs/2026-09-14-desk-org-session-gate-design.md \
  docs/superpowers/plans/2026-09-14-desk-org-session-gate.md
git commit -m "$(cat <<'EOF'
feat(desk): gate Organization Manage on session organization.write

EOF
)"
```

---

### Task 2: Version 0.3.83 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `tests/test_desk_finance_init_disable.py` (soften `0.3.82`)
- Modify: `docs/decisions.md` (ADR-065)
- Modify: `docs/11-user-experience.md`, `docs/14-roadmap.md`, `docs/18-handoff.md`
- Modify: spec status → implemented

**Interfaces:**
- Consumes: Task 1 complete
- Produces: shipped **0.3.83**

- [ ] **Step 1: Bump versions**

`__version__ = "0.3.83"`; companion `"version": "0.3.83"`.

Soften `test_desk_finance_init_disable.test_version_0_3_82` to regex `0\.3\.\d+`.

- [ ] **Step 2: ADR-065**

Decision: Desk Organization Manage fail-closes via session `organization.write` (markup + init + shared session with Finance + 403); seven `#departments` submits only.

- [ ] **Step 3: UX / roadmap / handoff / spec**

- UX: Org Manage forms fail closed until session confirms write.
- Roadmap: checkbox **0.3.83**; next = owner-directed.
- Handoff: version **0.3.83**, branch tip; no deploy claim until merge.
- Spec → **implemented in v0.3.83**.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 5: Commit** (if authorized)

```bash
git add company/__init__.py companion/package.json \
  tests/test_desk_org_session_gate.py tests/test_desk_finance_init_disable.py \
  docs/decisions.md docs/11-user-experience.md docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-14-desk-org-session-gate-design.md
git commit -m "$(cat <<'EOF'
docs: ship desk Organization session gate as 0.3.83

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Org notice + seven disabled submits | 1 |
| `setOrgMutateEnabled` + init | 1 |
| Shared session Finance + Org | 1 |
| `submitOrgCommand` 403 | 1 |
| Out-of-scope forms untouched | 1 |
| Version 0.3.83 + ADR/docs | 2 |

## Plan self-review

- Prefer keeping `applyFinancePauseFromSession` name to avoid finance contract churn.
- `submitOrgCommand` must not double-consume response body.
- Seven ids match spec exactly.
