# Work / People / Money Browse–Manage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Browse/Manage structure across Work, People, and Money companion panels (v0.3.66) by extracting Projects/Corporate/Org panels and wrapping Workers with the shared mode switch — without new APIs or invented metrics.

**Architecture:** Small reusable `ModeSwitch` (`browse` | `manage`). Extract large JSX blocks from `App.tsx` into `ProjectsPanel`, `CorporatePanel`, and `OrgPanel`. `WorkersPanel` gains Browse/Manage in place. `FinancePanel` keeps its four sub-tabs; only copy clarifies browse vs write. `App` retains data loading and wires panels like `HomePanel`.

**Tech Stack:** React/Vite companion, existing cosmic-glass CSS, unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-10-work-people-money-browse-manage-design.md` (owner-approved).
- No new APIs; no invented metrics; preserve all capabilities and scope notices.
- Finance: **no** nested Browse/Manage layer.
- Mode is local React state; default **browse**; may reset when leaving a Work sub-tab.
- Version **0.3.66**. Do not commit `local repos/service-department/`.
- Prefer owner-gated commits; if executing this plan under SDD/owner “execute”, commits are authorized.
- Branch tip: start from current `main` (0.3.65 deployed).

## File map

| Path | Role |
|---|---|
| `companion/src/ModeSwitch.tsx` | Reusable browse/manage segmented control |
| `companion/src/ProjectsPanel.tsx` | Projects Browse/Manage (from App ~719–1116) |
| `companion/src/CorporatePanel.tsx` | Corporate Browse/Manage (from App ~1391–1689) |
| `companion/src/OrgPanel.tsx` | People/Org Browse/Manage (from App ~1118–1389) |
| `companion/src/WorkersPanel.tsx` | Wrap list vs create with ModeSwitch |
| `companion/src/FinancePanel.tsx` | Lede/copy only |
| `companion/src/App.tsx` | Import panels; delete moved JSX |
| `companion/src/styles.css` | `.panel-mode` if needed (reuse `.segmented`) |
| `tests/test_work_people_money_browse_manage.py` | Source contracts |
| Docs / versions | 24, 11, ADR, roadmap, handoff, `__version__`, `package.json`, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_work_people_money_browse_manage.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Task 2–7 must satisfy

- [ ] **Step 1: Write the test module**

```python
"""Work/People/Money Browse–Manage structure (v0.3.66)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class WorkPeopleMoneyBrowseManageTests(unittest.TestCase):
    def test_mode_switch_module(self):
        text = (SRC / "ModeSwitch.tsx").read_text()
        self.assertIn("browse", text)
        self.assertIn("manage", text)
        self.assertIn("export function ModeSwitch", text)

    def test_projects_panel_browse_manage(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("Browse", text)
        self.assertIn("Manage", text)
        self.assertIn("Local candidates", text)

    def test_corporate_panel_browse_manage(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("CEO scorecard", text)

    def test_org_panel_browse_manage(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("organization", text.lower())  # props or copy

    def test_workers_panel_uses_mode_switch(self):
        text = (SRC / "WorkersPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)

    def test_finance_has_no_nested_browse_manage(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertNotIn("ModeSwitch", text)
        self.assertIn("Overview", text)
        self.assertIn("Create invoice", text)

    def test_app_wires_extracted_panels(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("ProjectsPanel", text)
        self.assertIn("CorporatePanel", text)
        self.assertIn("OrgPanel", text)
        # Projects JSX must not remain inline as the old section opener alone
        self.assertNotIn('tab === "projects" && (\n        <section>', text)
```

If the exact `assertNotIn` string is too brittle after formatting, replace with: `self.assertLess(text.count("Local candidates"), 1)` in App and `self.assertIn("Local candidates", projects panel)` — i.e. enroll copy lives only in ProjectsPanel.

- [ ] **Step 2: Run — expect FAIL**

```bash
.venv/bin/python -m unittest tests.test_work_people_money_browse_manage -v
```

Expected: FAIL (missing modules).

- [ ] **Step 3: Commit (owner-gated)**

```bash
git add tests/test_work_people_money_browse_manage.py
git commit -m "$(cat <<'EOF'
test(companion): expect Browse/Manage panel structure

EOF
)"
```

---

### Task 2: ModeSwitch component

**Files:**
- Create: `companion/src/ModeSwitch.tsx`
- Modify: `companion/src/styles.css` (optional; prefer existing `.segmented`)

**Interfaces:**
- Consumes: none
- Produces:

```tsx
export type PanelMode = "browse" | "manage";

export type ModeSwitchProps = {
  mode: PanelMode;
  onChange: (mode: PanelMode) => void;
  label?: string; // aria-label, default "Panel mode"
};

export function ModeSwitch({ mode, onChange, label = "Panel mode" }: ModeSwitchProps): JSX.Element;
```

- [ ] **Step 1: Implement ModeSwitch**

```tsx
import type { PanelMode } from "./ModeSwitch"; // or define PanelMode in this file

const OPTIONS: [PanelMode, string][] = [
  ["browse", "Browse"],
  ["manage", "Manage"],
];

export type PanelMode = "browse" | "manage";

export type ModeSwitchProps = {
  mode: PanelMode;
  onChange: (mode: PanelMode) => void;
  label?: string;
};

export function ModeSwitch({ mode, onChange, label = "Panel mode" }: ModeSwitchProps) {
  return (
    <div className="segmented panel-mode" role="tablist" aria-label={label}>
      {OPTIONS.map(([value, text]) => (
        <button
          key={value}
          type="button"
          role="tab"
          aria-selected={mode === value}
          className={mode === value ? "active" : ""}
          onClick={() => onChange(value)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
```

Fix the circular import sketch: define `PanelMode` once in this file only (remove the bogus import line).

- [ ] **Step 2: Run ModeSwitch test only**

```bash
.venv/bin/python -m unittest tests.FAKESECRET_a3b4c5d6e7f8g9h0i1j2 -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add companion/src/ModeSwitch.tsx companion/src/styles.css
git commit -m "$(cat <<'EOF'
feat(companion): add Browse/Manage ModeSwitch

EOF
)"
```

---

### Task 3: WorkersPanel Browse/Manage

**Files:**
- Modify: `companion/src/WorkersPanel.tsx`

**Interfaces:**
- Consumes: `ModeSwitch`, `PanelMode`
- Produces: Workers Browse = host list + row actions; Manage = create form + issued token

- [ ] **Step 1: Add mode state and split UI**

At top of `WorkersPanel` body:

```tsx
const [mode, setMode] = useState<PanelMode>("browse");
```

Render `<ModeSwitch mode={mode} onChange={setMode} label="Workers mode" />` then:

- `mode === "browse"`: existing host list, load error, enable/disable/delete, empty copy
- `mode === "manage"`: create-host form + one-time token card

Do not remove capabilities. Keep `scopeNotice` / `canPause` gating as today.

- [ ] **Step 2: Run**

```bash
.venv/bin/python -m unittest tests.FAKESECRET_g1h2i3j4k5l6m7n8o9p0 -v
cd companion && npm run build
```

Expected: workers test PASS; build OK (other panel tests still FAIL).

- [ ] **Step 3: Commit**

```bash
git add companion/src/WorkersPanel.tsx
git commit -m "$(cat <<'EOF'
feat(companion): Browse/Manage on Workers panel

EOF
)"
```

---

### Task 4: FinancePanel copy (no ModeSwitch)

**Files:**
- Modify: `companion/src/FinancePanel.tsx`

**Interfaces:**
- Consumes: none new
- Produces: clearer lede that Overview/lists are read surfaces; creates stay on sub-tabs

- [ ] **Step 1: Add a short lede under the Finance heading / before SUB_TABS**

Example:

```tsx
<p className="lede">
  Overview and lists are read from persisted finance state. Create invoice, adjustment,
  and period actions stay on their tabs — not a second Browse/Manage layer.
</p>
```

Do **not** import `ModeSwitch`.

- [ ] **Step 2: Run**

```bash
.venv/bin/python -m unittest tests.FAKESECRET_e3f4g5h6i7j8k9l0m1n2 -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add companion/src/FinancePanel.tsx
git commit -m "$(cat <<'EOF'
docs(companion): clarify Finance browse vs create surfaces

EOF
)"
```

---

### Task 5: Extract ProjectsPanel

**Files:**
- Create: `companion/src/ProjectsPanel.tsx`
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: App state/handlers for projects, selectedProject, dispatch, enroll, GitHub, scopes
- Produces: `<ProjectsPanel … />` when `tab === "projects"`

- [ ] **Step 1: Move JSX**

Cut the entire `{tab === "projects" && ( <section>…</section> )}` block (~lines 719–1116) into `ProjectsPanel`.

Panel structure:

```tsx
export function ProjectsPanel(props: ProjectsPanelProps) {
  const [mode, setMode] = useState<PanelMode>("browse");
  // When selectedProject is set, force browse detail (or keep detail visible regardless of mode).
  return (
    <section>
      <ModeSwitch mode={mode} onChange={setMode} label="Projects mode" />
      {selectedProject ? (
        /* existing detail + dispatch UI unchanged */
      ) : mode === "browse" ? (
        /* project list cards only */
      ) : (
        /* local candidates + GitHub assign + enroll form */
      )}
    </section>
  );
}
```

**Browse:** project list + Details button only.

**Manage:** local candidates, GitHub assign, enroll form.
**Detail view:** when `selectedProject` is set, show existing detail UI (dispatch etc.) and a Back control already present — detail is part of Browse flow; ModeSwitch may stay visible or hide while in detail (prefer **keep ModeSwitch**, Back clears selection).

Define `ProjectsPanelProps` with every binding the moved JSX needs (copy from App closures). Prefer passing setters and handlers rather than inventing new API calls.

- [ ] **Step 2: Wire App**

```tsx
{tab === "projects" && (
  <ProjectsPanel
    /* props */
  />
)}
```

Ensure `Local candidates` text no longer appears in `App.tsx`.

- [ ] **Step 3: Run**

```bash
.venv/bin/python -m unittest tests.FAKESECRET_a2b3c4d5e6f7g8h9i0j1 tests.FAKESECRET_u1v2w3x4y5z6a7b8c9d0 -v
cd companion && npm run build
```

Expected: those PASS; build OK.

- [ ] **Step 4: Commit**

```bash
git add companion/src/ProjectsPanel.tsx companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): extract ProjectsPanel with Browse/Manage

EOF
)"
```

---

### Task 6: Extract CorporatePanel

**Files:**
- Create: `companion/src/CorporatePanel.tsx`
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: scorecard, objectives, packs, divisions, promotions, staffing, crossDept, activity, hqRoomCount, handlers
- Produces: `<CorporatePanel … />` for `tab === "corporate"`

- [ ] **Step 1: Move JSX (~1391–1689)**

Split per spec:

**Browse:** scorecard, objectives list + in-row close, packs, divisions list + activate/deactivate, promotions decide, staffing list + decide, cross-dept list + accept, activity list.

**Manage:** create objective form, propose division form, create cross-dept form, floorplan default button, staffing scan button.

Use `ModeSwitch` + `useState<PanelMode>("browse")`.

- [ ] **Step 2: Wire App; run tests + build**

```bash
.venv/bin/python -m unittest tests.FAKESECRET_a1b2c3d4e5f6g7h8i9j0 -v
cd companion && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add companion/src/CorporatePanel.tsx companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): extract CorporatePanel with Browse/Manage

EOF
)"
```

---

### Task 7: Extract OrgPanel (People)

**Files:**
- Create: `companion/src/OrgPanel.tsx`
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: organization, headInbox, worker card state, org write handlers
- Produces: `<OrgPanel … />` for `tab === "organization"`

- [ ] **Step 1: Move JSX (~1118–1389)**

**Browse:** department catalog cards, head inbox list + in-row assign UI.

**Manage:** create dept/head/position forms, reorder, vacate/release, activate, load worker card.

- [ ] **Step 2: Wire App; run full browse-manage suite + build**

```bash
.venv/bin/python -m unittest tests.test_work_people_money_browse_manage -v
cd companion && npm run build
```

Expected: **all** module tests PASS; build OK.

- [ ] **Step 3: Commit**

```bash
git add companion/src/OrgPanel.tsx companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): extract OrgPanel with Browse/Manage

EOF
)"
```

---

### Task 8: Docs + version 0.3.66

**Files:**
- Modify: `company/__init__.py`, `companion/package.json` → `0.3.66`
- Modify: `docs/24-mobile-companion.md`, `docs/11-user-experience.md`, `docs/decisions.md` (ADR), `docs/14-roadmap.md`, `docs/18-handoff.md`, README if version listed
- Modify: spec status → implemented in v0.3.66
- Include untracked design/plan files in the docs commit

- [ ] **Step 1: Bump + docs** describing Browse/Manage on Work/People; Finance unchanged sub-tabs.
- [ ] **Step 2: Full verify**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add company/__init__.py companion/package.json docs/ README.md
git commit -m "$(cat <<'EOF'
docs: Work/People/Money Browse-Manage and release 0.3.66

EOF
)"
```

---

## Spec coverage

| Spec | Task |
|---|---|
| ModeSwitch / Browse·Manage | 2 |
| Workers Browse/Manage | 3 |
| Finance no nested mode | 4 |
| ProjectsPanel | 5 |
| CorporatePanel | 6 |
| OrgPanel | 7 |
| Docs / 0.3.66 | 8 |
| Source contracts | 1 |

## Self-review notes

- Corporate “staffing scan” and “floorplan default” are Manage per spec even though they are buttons, not long forms.
- Project detail stays reachable from Browse list; do not put enroll forms on Browse.
- Avoid inventing scorecard UI changes beyond the move.
