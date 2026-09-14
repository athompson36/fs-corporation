# Desk Remaining Session Gates + Docs Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship desk v0.3.85 fail-closing division Activate, promotions, staffing scan/decisions (`organization.write`) and dispatch submit/recommend (`project.enroll`), and refresh README + VERIFICATION to the current ship.

**Architecture:** Extend `setOrgMutateEnabled` for People/division dynamic chips + staffing scan; add `setDispatchEnrollEnabled` composed with existing dormancy `updateDispatchSubmitGate`; extend shared session apply; docs + version lockstep only.

**Tech Stack:** Desk HTML/JS in `company/service.py`, Python unittest, companion `package.json` lockstep, markdown docs.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-desk-remaining-session-gates-design.md` (owner-approved).
- Version **0.3.85**. Soften exact `0.3.84` pins to `0\.3\.\d+`; exact `0.3.85` only in this release’s contract.
- Org cluster uses existing `setOrgMutateEnabled` / `data-org-write` / `data-org-write-notice` — no second org helper.
- Dispatch uses **`project.enroll`** via new `setDispatchEnrollEnabled` — do not gate dispatch on `organization.write`.
- Compose submit disable: `!dispatchEnrollEnabled` OR dormancy blocked.
- No new APIs, Alembic, companion feature work beyond version lockstep.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/desk-remaining-session-gates` from current `main` before Task 1.
- Work in-place on the feature branch (dirty tree has huge untracked `local repos/`).

## File map

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + helpers + session + 403 |
| `tests/test_desk_remaining_session_gates.py` | Source contracts + version **0.3.85** |
| `tests/test_desk_org_corporate_write_gate.py` | Soften exact `0.3.84` pin |
| `company/__init__.py`, `companion/package.json` | **0.3.85** |
| `README.md`, `VERIFICATION.md`, `docs/decisions.md`, `docs/18-handoff.md`, roadmap/UX if needed | Docs honesty + ADR-067 |

---

### Task 1: RED contracts + DESK_HTML remaining gates

**Files:**
- Create: `tests/test_desk_remaining_session_gates.py`
- Modify: `company/service.py` (`DESK_HTML` only)
- Soften later in Task 2: `tests/test_desk_org_corporate_write_gate.py` version pin

**Interfaces:**
- Consumes: `orgWriteEnabled`, `setOrgMutateEnabled`, `updateDispatchSubmitGate`, `applyFinancePauseFromSession` (extend or rename)
- Produces: People/org dynamic gates; `dispatchEnrollEnabled` / `setDispatchEnrollEnabled`; session applies `project.enroll`

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/desk-remaining-session-gates
```

- [ ] **Step 2: Write failing source-contract module**

Create `tests/test_desk_remaining_session_gates.py`:

```python
"""Desk remaining session gates + docs ship (v0.3.85)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskRemainingSessionGatesTests(unittest.TestCase):
    def test_people_notice_and_staffing_scan_disabled(self):
        start = DESK_HTML.find('id="people"')
        self.assertGreater(start, -1)
        end = DESK_HTML.find("</section>", start)
        chunk = DESK_HTML[start:end]
        self.assertIn("data-org-write-notice", chunk)
        self.assertIn("Mutations require organization.write.", chunk)
        self.assertRegex(
            DESK_HTML,
            r'id="staffing-scan-btn"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="staffing-scan-btn"',
        )

    def test_set_org_includes_staffing_scan(self):
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 2500]
        self.assertIn("staffing-scan-btn", after)

    def test_dynamic_org_write_markers(self):
        for fn_name in (
            "function renderPromotions",
            "function renderStaffingProposals",
            "function renderDivisions",
        ):
            idx = DESK_HTML.find(fn_name)
            self.assertGreater(idx, -1, fn_name)
            chunk = DESK_HTML[idx : idx + 2200]
            self.assertIn("data-org-write", chunk, fn_name)
            self.assertIn("orgWriteEnabled", chunk, fn_name)
            self.assertIn("403", chunk, fn_name)
            self.assertIn("setOrgMutateEnabled(false)", chunk, fn_name)

    def test_staffing_scan_403_and_guard(self):
        idx = DESK_HTML.find("staffing-scan-btn').addEventListener")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 900]
        self.assertIn("orgWriteEnabled", chunk)
        self.assertIn("403", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_dispatch_enroll_markup(self):
        self.assertIn('id="dispatch-scope-notice"', DESK_HTML)
        self.assertIn("Mutations require project.enroll.", DESK_HTML)
        for control_id in ("dispatch-submit-btn", "dispatch-recommend-btn"):
            self.assertRegex(
                DESK_HTML,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_dispatch_enroll_helper(self):
        self.assertIn("function setDispatchEnrollEnabled", DESK_HTML)
        self.assertIn("dispatchEnrollEnabled", DESK_HTML)
        self.assertIn("setDispatchEnrollEnabled(false)", DESK_HTML)
        idx = DESK_HTML.find("function updateDispatchSubmitGate")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 800]
        self.assertIn("dispatchEnrollEnabled", chunk)

    def test_session_applies_project_enroll(self):
        # Shared session apply (name may still be applyFinancePauseFromSession)
        self.assertIn("project.enroll", DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r"setDispatchEnrollEnabled\(scopes\.indexOf\('project\.enroll'\)",
        )
        fail_idx = DESK_HTML.find("async function applyFinancePauseFromSession")
        if fail_idx < 0:
            fail_idx = DESK_HTML.find("async function applySessionScopes")
        self.assertGreater(fail_idx, -1)
        chunk = DESK_HTML[fail_idx : fail_idx + 900]
        self.assertIn("setDispatchEnrollEnabled(false)", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_dispatch_403_fail_closed(self):
        for marker in (
            "dispatch-form').addEventListener('submit'",
            "dispatch-recommend-btn').addEventListener",
        ):
            idx = DESK_HTML.find(marker)
            self.assertGreater(idx, -1, marker)
            chunk = DESK_HTML[idx : idx + 1200]
            self.assertIn("403", chunk, marker)
            self.assertIn("setDispatchEnrollEnabled(false)", chunk, marker)

    def test_version_0_3_85(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.85"', init)
        self.assertIn('"version": "0.3.85"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify RED**

```bash
.venv/bin/python -m unittest tests.test_desk_remaining_session_gates -v
```

Expected: FAIL on missing People notice / helpers / version (not import errors).

- [ ] **Step 4: Markup — People notice + staffing scan disabled**

In `DESK_HTML`, `#people` section, after `<h2>People</h2>...` and before pending promotions (or immediately before the scan row), add:

```html
<p class="muted" data-org-write-notice>Mutations require organization.write.</p>
```

Change the staffing scan button to ship disabled:

```html
<button type="button" class="chip" id="staffing-scan-btn" disabled>Scan staffing gaps</button>
```

- [ ] **Step 5: Markup — dispatch notice + disabled chips**

Inside `#dispatch-form`, before the actions row (or immediately after the h3), add:

```html
<p id="dispatch-scope-notice" class="muted">Mutations require project.enroll.</p>
```

Ensure both action chips ship `disabled`:

```html
<button type="button" class="chip" id="dispatch-recommend-btn" disabled>Recommend for this project</button>
<button type="submit" class="chip" id="dispatch-submit-btn" disabled>Dispatch</button>
```

- [ ] **Step 6: Extend `setOrgMutateEnabled` static id list**

Add `'staffing-scan-btn'` to the id array inside `setOrgMutateEnabled` (alongside the corporate submit ids).

- [ ] **Step 7: Dynamic `data-org-write` + 403 on promotions, staffing, Activate**

Mirror Accept cross-dept. For each Approve/Reject in `renderPromotions` and `renderStaffingProposals`, and Activate in `renderDivisions`:

```javascript
button.setAttribute('data-org-write', '');
button.disabled = !orgWriteEnabled;
// inside click after fetch:
if (res.status === 403) setOrgMutateEnabled(false);
```

- [ ] **Step 8: Staffing scan guard + 403**

Replace the staffing-scan click handler body start with:

```javascript
document.getElementById('staffing-scan-btn').addEventListener('click', async () => {
  const status = document.getElementById('staffing-scan-status');
  if (!orgWriteEnabled) {
    status.textContent = ' organization.write required.';
    return;
  }
  const res = await fetch('/api/v1/staffing-proposals/scan', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-staffing-scan-' + Date.now()},
    body: JSON.stringify({payload: {}})
  });
  if (res.status === 403) setOrgMutateEnabled(false);
  status.textContent = res.ok ? ' Scan complete.' : ' ' + await res.text();
  if (res.ok) load();
});
```

- [ ] **Step 9: Add `setDispatchEnrollEnabled` and compose submit gate**

Near `setOrgMutateEnabled(false);`, add:

```javascript
let dispatchEnrollEnabled = false;
function setDispatchEnrollEnabled(enabled) {
  dispatchEnrollEnabled = !!enabled;
  const notice = document.getElementById('dispatch-scope-notice');
  if (notice) notice.hidden = !!enabled;
  const recommend = document.getElementById('dispatch-recommend-btn');
  if (recommend) recommend.disabled = !enabled;
  updateDispatchSubmitGate();
}
setDispatchEnrollEnabled(false);
```

**Note:** `updateDispatchSubmitGate` is defined later in DESK_HTML. Either (a) place `setDispatchEnrollEnabled` **after** `updateDispatchSubmitGate` is defined, or (b) keep the function declaration hoisted pattern — in DESK_HTML scripts, `function updateDispatchSubmitGate` is hoisted within the script, but `let dispatchEnrollEnabled` must be declared before first use. Prefer defining `setDispatchEnrollEnabled` immediately **after** `updateDispatchSubmitGate`, and call `setDispatchEnrollEnabled(false)` once there. If init must run before session, ensure first paint has markup `disabled` on both chips (Step 5) so late init is safe.

Replace `updateDispatchSubmitGate` body to compose enroll:

```javascript
function updateDispatchSubmitGate() {
  const status = document.getElementById('dispatch-status');
  const submit = document.getElementById('dispatch-submit-btn');
  let blocked = false;
  document.querySelectorAll('#dispatch-dept-list .dispatch-dept-row').forEach(row => {
    const check = row.querySelector('input[type="checkbox"]');
    if (check && check.checked && check.dataset.dispatchable === 'false') blocked = true;
  });
  submit.disabled = blocked || !dispatchEnrollEnabled;
  if (blocked) status.textContent = 'Activate dormant departments before dispatch.';
}
```

Declare `let dispatchEnrollEnabled = false;` near other lets (before `updateDispatchSubmitGate`) so the gate can read it.

- [ ] **Step 10: Session apply `project.enroll`**

In `applyFinancePauseFromSession` (keep name or rename to `applySessionScopes` and update all call sites — either OK):

```javascript
async function applyFinancePauseFromSession() {
  try {
    const res = await fetch('/api/v1/session', {headers});
    if (!res.ok) {
      setFinanceMutateEnabled(false);
      setOrgMutateEnabled(false);
      setDispatchEnrollEnabled(false);
      return;
    }
    const body = await res.json();
    const scopes = Array.isArray(body.scopes) ? body.scopes : [];
    setFinanceMutateEnabled(scopes.indexOf('company.pause') !== -1);
    setOrgMutateEnabled(scopes.indexOf('organization.write') !== -1);
    setDispatchEnrollEnabled(scopes.indexOf('project.enroll') !== -1);
  } catch (e) {
    setFinanceMutateEnabled(false);
    setOrgMutateEnabled(false);
    setDispatchEnrollEnabled(false);
  }
}
```

If `setDispatchEnrollEnabled` is defined later in the file than this function, that is fine for a `function` declaration; if it is a `const setDispatchEnrollEnabled = ...` arrow, define the helper earlier or use `function setDispatchEnrollEnabled`. Prefer `function setDispatchEnrollEnabled` for hoist safety.

- [ ] **Step 11: Dispatch / recommend 403 fail-closed**

In `#dispatch-form` submit handler and `#dispatch-recommend-btn` click handler, after fetch:

```javascript
if (res.status === 403) setDispatchEnrollEnabled(false);
```

Also guard recommend/submit early if `!dispatchEnrollEnabled` (optional but recommended):

```javascript
if (!dispatchEnrollEnabled) {
  status.textContent = 'project.enroll required.';
  return;
}
```

- [ ] **Step 12: Run gate tests (expect version still RED)**

```bash
.venv/bin/python -m unittest tests.test_desk_remaining_session_gates tests.test_desk_org_corporate_write_gate tests.test_desk_org_session_gate tests.test_desk_finance_init_disable -v
```

Expected: remaining-gates tests pass except `test_version_0_3_85`; corporate write may still pass on 0.3.84 until Task 2 softens.

- [ ] **Step 13: Commit**

```bash
git add tests/test_desk_remaining_session_gates.py company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): fail-close remaining Org and dispatch session gates

Gate Activate/promotions/staffing on organization.write and dispatch
actions on project.enroll from first paint, matching prior Finance/Org gates.
EOF
)"
```

---

### Task 2: Version 0.3.85 + docs honesty

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `tests/test_desk_org_corporate_write_gate.py` (soften 0.3.84)
- Modify: `README.md`, `VERIFICATION.md`, `docs/decisions.md`, `docs/18-handoff.md`
- Optionally: `docs/14-roadmap.md`, `docs/11-user-experience.md` one-line notes
- Mark: `docs/superpowers/specs/2026-09-14-desk-remaining-session-gates-design.md` status implemented

**Interfaces:**
- Consumes: Task 1 behavior
- Produces: ship **0.3.85** with honest docs

- [ ] **Step 1: Bump versions**

`company/__init__.py`:

```python
__version__ = "0.3.85"
```

`companion/package.json`: `"version": "0.3.85"`

- [ ] **Step 2: Soften prior exact pin**

In `tests/test_desk_org_corporate_write_gate.py`, replace `test_version_0_3_84` with:

```python
    def test_version_lockstep(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

Update the module docstring to drop the hard “v0.3.84 only” implication if needed.

- [ ] **Step 3: ADR-067**

In `docs/decisions.md` index table, add:

```markdown
| ADR-067 | 2026-09-14 | Desk remaining session gates | People/Activate/promotions/staffing use organization.write; dispatch submit/recommend use project.enroll via setDispatchEnrollEnabled; README/VERIFICATION honesty. |
```

Append detail section:

```markdown
### ADR-067 detail

**Context.** After ADR-066, division Activate, promotion decisions, staffing scan/decisions,
and project dispatch chips still stayed enabled until 403. Dispatch APIs require
`project.enroll`, not `organization.write`. README and VERIFICATION lagged the live
version.

**Decision.** Extend `setOrgMutateEnabled` for People/division dynamic chips and staffing
scan; add `setDispatchEnrollEnabled` composed with dormancy submit gating; session apply
sets Finance (`company.pause`), Org (`organization.write`), and Dispatch (`project.enroll`);
refresh README + VERIFICATION for v0.3.85.

**Alternatives considered.** Generic `data-requires-scope` helper (rejected — YAGNI).
Gating dispatch on `organization.write` (rejected — wrong scope). Docs-only ship
(rejected — leaves UX fail-open).

**Consequences.** Desk v0.3.85 fail-closes remaining audit desk-gate gaps from first paint.
Ship 2 (finance ledger UI + consultant measured before/after) remains separate.
```

Also update ADR-066 consequences line that says promotions/staffing remain follow-ups — add a note they are superseded by ADR-067 (do not rewrite ADR-066 history; append “Superseded for remaining gates by ADR-067” only if the file’s convention allows forward references).

- [ ] **Step 4: README deliverable status**

Prepend to the long **Deliverable status:** sentence (keep history):

```text
v0.3.85 with Desk remaining session gates (Activate/promotions/staffing organization.write; dispatch submit/recommend project.enroll; README/VERIFICATION honesty; no new APIs),
```

Do not claim live billing or consultant measured metrics are done.

- [ ] **Step 5: VERIFICATION.md current-ship section**

At the top (after title), add a short **0.3.85** block:

```markdown
Updated 2026-09-14 for **0.3.85** (desk remaining session gates: Org write on
Activate/promotions/staffing; `project.enroll` on dispatch submit/recommend; docs honesty).
Prior headline 0.3.61 retained below as historical host evidence.

## Verified in this workspace (0.3.85)

- Unit tests: run `.venv/bin/python -m unittest discover -s tests` at ship; record count.
- Desk contracts: `tests/test_desk_remaining_session_gates.py` plus prior Finance/Org/corporate gate modules.
- Companion version lockstep **0.3.85**; `cd companion && npm run build` when shipping.
- No Alembic revision in 0.3.85.
```

Keep older sections; update “Not tested” only if a bullet is now false — do **not** remove “Real provider invoices / refunds” (still Ship 2).

- [ ] **Step 6: Handoff + spec status**

Rewrite `docs/18-handoff.md` for **0.3.85** tip (fill after commit). Mark design spec status **implemented in v0.3.85**.

Next handoff line: Ship 2 finance B + consultant B (brainstorm/plan separately).

- [ ] **Step 7: Run full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build OK.

- [ ] **Step 8: Commit**

```bash
git add company/__init__.py companion/package.json \
  tests/test_desk_remaining_session_gates.py \
  tests/test_desk_org_corporate_write_gate.py \
  README.md VERIFICATION.md docs/decisions.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-14-desk-remaining-session-gates-design.md \
  docs/14-roadmap.md docs/11-user-experience.md
git commit -m "$(cat <<'EOF'
docs: ship desk remaining session gates as 0.3.85

Lockstep versions and refresh README/VERIFICATION/ADR-067 for Org write
and project.enroll desk fail-closed gates.
EOF
)"
```

Only add files that actually changed.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| People notice + staffing scan disabled | Task 1 |
| Dynamic Activate / promo / staffing `data-org-write` + 403 | Task 1 |
| Staffing scan guard + 403 | Task 1 |
| Dispatch notice + disabled chips | Task 1 |
| `setDispatchEnrollEnabled` + dormancy compose | Task 1 |
| Session `project.enroll` | Task 1 |
| Dispatch/recommend 403 | Task 1 |
| README + VERIFICATION + ADR-067 + handoff | Task 2 |
| Version 0.3.85 + soften 0.3.84 | Task 2 |
| No Ship 2 finance/consultant | Explicit non-goal |

Placeholder scan: none. Naming: `setDispatchEnrollEnabled` / `dispatchEnrollEnabled` / `project.enroll` consistent across tasks.
