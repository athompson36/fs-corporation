# Desk Corporate Write Forms Session Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship desk v0.3.84 extending `organization.write` fail-closed gating to Create objective, Create cross-dept request, Propose division, plus Close/Accept row actions.

**Architecture:** Extend `setOrgMutateEnabled` with three new submit ids, `[data-org-write-notice]` notices, `orgWriteEnabled` flag, and `[data-org-write]` on dynamic Close/Accept. Session path unchanged.

**Tech Stack:** Desk HTML/JS in `company/service.py`, Python unittest, companion version lockstep only.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-desk-org-corporate-write-gate-design.md` (owner-approved).
- Version **0.3.84**. Soften exact `0.3.83` pins to `0\.3\.\d+`; exact `0.3.84` only in this release’s contract.
- Extend `setOrgMutateEnabled` — do not invent a separate corporate helper.
- Per-section notices in scorecard / cross-department / corporate-upgrades; tag `#org-scope-notice` with `data-org-write-notice`.
- Do not gate promotions, staffing-scan, dispatch, pairing.
- No new APIs, Alembic, companion behavior beyond lockstep.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-org-corporate-write-gate` from current `main` before Task 1.
- Work in-place on the feature branch.

## File map

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML extensions |
| `tests/test_desk_org_corporate_write_gate.py` | Source contracts + version **0.3.84** |
| `tests/test_desk_org_session_gate.py` | Soften exact `0.3.83` pin |
| Docs + versions | ADR-066, UX/roadmap/handoff; **0.3.84** |

---

### Task 1: RED contracts + DESK_HTML corporate write gate

**Files:**
- Create: `tests/test_desk_org_corporate_write_gate.py`
- Modify: `company/service.py` (`DESK_HTML`)
- Test: `tests/test_desk_org_session_gate.py` must stay green (except version pin if soft later)

**Interfaces:**
- Consumes: `setOrgMutateEnabled`, `orgWriteEnabled` (new), `renderObjectives`, `renderCrossDept`
- Produces: extended gate; RED version until Task 2

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-org-corporate-write-gate
```

- [ ] **Step 2: Write failing source-contract module**

```python
"""Desk corporate write forms session gate (v0.3.84)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]

CORP_SUBMIT_IDS = (
    "desk-org-create-objective-submit",
    "desk-org-create-cross-dept-submit",
    "desk-org-propose-division-submit",
)


class DeskOrgCorporateWriteGateTests(unittest.TestCase):
    def test_section_notices_present(self):
        self.assertGreaterEqual(DESK_HTML.count('data-org-write-notice'), 4)
        self.assertIn('id="org-scope-notice"', DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r'id="org-scope-notice"[^>]*data-org-write-notice|data-org-write-notice[^>]*id="org-scope-notice"',
        )
        for section_id in ("scorecard", "cross-department", "corporate-upgrades"):
            start = DESK_HTML.find(f'id="{section_id}"')
            self.assertGreater(start, -1, section_id)
            end = DESK_HTML.find("</section>", start)
            chunk = DESK_HTML[start:end]
            self.assertIn("data-org-write-notice", chunk)
            self.assertIn("Mutations require organization.write.", chunk)

    def test_corporate_submits_disabled(self):
        for control_id in CORP_SUBMIT_IDS:
            self.assertRegex(
                DESK_HTML,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_org_mutate_extended(self):
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 2000]
        self.assertIn("orgWriteEnabled", after)
        self.assertIn("data-org-write-notice", after)
        self.assertIn("data-org-write", after)
        for control_id in CORP_SUBMIT_IDS:
            self.assertIn(control_id, after)

    def test_dynamic_row_markers(self):
        # Close / Accept use data-org-write
        obj_idx = DESK_HTML.find("function renderObjectives")
        self.assertGreater(obj_idx, -1)
        obj_chunk = DESK_HTML[obj_idx : obj_idx + 1200]
        self.assertIn("data-org-write", obj_chunk)
        self.assertIn("orgWriteEnabled", obj_chunk)
        xd_idx = DESK_HTML.find("function renderCrossDept")
        self.assertGreater(xd_idx, -1)
        xd_chunk = DESK_HTML[xd_idx : xd_idx + 1500]
        self.assertIn("data-org-write", xd_chunk)
        self.assertIn("orgWriteEnabled", xd_chunk)
        # 403 fail-closed on Accept/Close
        self.assertRegex(obj_chunk, r"403[\s\S]{0,200}setOrgMutateEnabled\(false\)")
        self.assertRegex(xd_chunk, r"403[\s\S]{0,200}setOrgMutateEnabled\(false\)")

    def test_version_0_3_84(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.84"', init)
        self.assertIn('"version": "0.3.84"', pkg)


if __name__ == "__main__":
    unittest.main()
```

If the 403 regex is too brittle because text is read before status check, assert separately that both renderer click handlers contain `setOrgMutateEnabled(false)` and `403`.

- [ ] **Step 3: Run — expect RED**

```bash
.venv/bin/python -m unittest tests.test_desk_org_corporate_write_gate -v
```

- [ ] **Step 4: Markup**

1. On `#org-scope-notice`, add `data-org-write-notice` (keep id and copy).
2. In `#scorecard` before Create objective form:

```html
<p class="muted" data-org-write-notice>Mutations require organization.write.</p>
```

3. Same notice in `#cross-department` before Create request form; `#corporate-upgrades` before Propose form.
4. Update submit buttons:

```html
<button type="submit" class="chip" id="desk-org-create-objective-submit" disabled>Create objective</button>
<button type="submit" class="chip" id="desk-org-create-cross-dept-submit" disabled>Create request</button>
<button type="submit" class="chip" id="desk-org-propose-division-submit" disabled>Propose</button>
```

- [ ] **Step 5: Extend `setOrgMutateEnabled`**

Replace the function body with:

```javascript
let orgWriteEnabled = false;
function setOrgMutateEnabled(enabled) {
  orgWriteEnabled = !!enabled;
  document.querySelectorAll('[data-org-write-notice]').forEach(notice => {
    notice.hidden = !!enabled;
  });
  [
    'desk-org-create-dept-submit',
    'desk-org-appoint-head-submit',
    'desk-org-vacate-head-submit',
    'desk-org-assign-position-submit',
    'desk-org-release-assignment-submit',
    'desk-org-create-position-submit',
    'desk-org-reorder-submit',
    'desk-org-create-objective-submit',
    'desk-org-create-cross-dept-submit',
    'desk-org-propose-division-submit',
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  });
  document.querySelectorAll('[data-org-write]').forEach(btn => {
    btn.disabled = !enabled;
  });
}
setOrgMutateEnabled(false);
```

Remove the old `getElementById('org-scope-notice')` path — attribute query covers it. Keep the existing init call (do not double-call if already present once).

- [ ] **Step 6: Dynamic Close / Accept**

In `renderObjectives` when creating Close button:

```javascript
      button.setAttribute('data-org-write', '');
      button.disabled = !orgWriteEnabled;
      button.addEventListener('click', async () => {
        const res = await fetch(...);
        const text = await res.text();
        if (res.status === 403) setOrgMutateEnabled(false);
        if (!res.ok) { alert(text); return; }
        load();
      });
```

In `renderCrossDept` Accept button: same `data-org-write`, `disabled = !orgWriteEnabled`, and 403 → `setOrgMutateEnabled(false)` with single `text()` consume.

- [ ] **Step 7: Re-run**

```bash
.venv/bin/python -m unittest \
  tests.test_desk_org_corporate_write_gate \
  tests.test_desk_org_session_gate -v
```

Expected: corporate contracts PASS except version; org session gate still PASS (may need soft version later).

- [ ] **Step 8: Commit** (if authorized)

```bash
git add company/service.py tests/test_desk_org_corporate_write_gate.py \
  docs/superpowers/specs/2026-09-14-desk-org-corporate-write-gate-design.md \
  docs/superpowers/plans/2026-09-14-desk-org-corporate-write-gate.md
git commit -m "$(cat <<'EOF'
feat(desk): gate corporate write forms on organization.write

EOF
)"
```

---

### Task 2: Version 0.3.84 + docs

**Files:**
- `company/__init__.py`, `companion/package.json`
- Soften `tests/test_desk_org_session_gate.py` version asserts
- ADR-066, UX, roadmap, handoff, spec status

- [ ] **Step 1: Bump to 0.3.84**; soften `0.3.83` pin in org session gate test.

- [ ] **Step 2: ADR-066** — extend org write gate to scorecard/cross-dept/corporate-upgrades static + dynamic Close/Accept.

- [ ] **Step 3: UX / roadmap / handoff / spec implemented**.

- [ ] **Step 4:**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 5: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs: ship desk corporate write gate as 0.3.84

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Per-section notices + org notice attribute | 1 |
| Three new disabled submits | 1 |
| Extended `setOrgMutateEnabled` + `orgWriteEnabled` | 1 |
| Close/Accept `data-org-write` + 403 | 1 |
| Version 0.3.84 + docs | 2 |

## Plan self-review

- Notice toggle via `[data-org-write-notice]` only (no double-hide on `#org-scope-notice`).
- Response body consumed once on Close/Accept.
- Promotions/staffing left ungated.
