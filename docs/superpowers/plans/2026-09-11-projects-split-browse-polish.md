# Projects Split Browse Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Projects Browse as a responsive list|detail split with a full project workspace in the detail pane, plus medium shared shell polish on Corporate/Workers/Org (v0.3.68).

**Architecture:** In-place `ProjectsPanel` Browse restructure (list always visible; detail pane for selection/empty/workspace). Shared CSS for split, denser lists, empty states, ModeSwitch spacing. Manage and all APIs unchanged. Widen `.app` on mid+ viewports so the split is usable.

**Tech Stack:** React/Vite companion, existing cosmic-glass CSS, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-projects-split-browse-polish-design.md` (owner-approved).
- No new APIs; no invented metrics; no URL-synced `?project=`.
- Finance: **no** Browse/Manage ModeSwitch.
- Detail = full project workspace (brief/GitHub/dispatch); Manage = enroll/assign only.
- Wide split: Clear selection (not ← Back). Narrow: stacked list above detail.
- Version **0.3.68**. Do not commit `local repos/service-department/` or unrelated `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch tip: start from current `main` (0.3.67 on fs-dev).
- Preserve existing `tests/test_work_people_money_browse_manage.py` assertions (Browse/Manage/ModeSwitch markers).

## File map

| Path | Role |
|---|---|
| `tests/test_projects_split_browse_polish.py` | Source contracts for split + polish markers |
| `companion/src/styles.css` | Split layout, list rows, empty states, wider `.app` |
| `companion/src/ProjectsPanel.tsx` | Browse split markup; Clear selection; empty detail |
| `companion/src/CorporatePanel.tsx` | Empty/title polish only as needed |
| `companion/src/WorkersPanel.tsx` | Empty/title polish only as needed |
| `companion/src/OrgPanel.tsx` | Empty/title polish only as needed |
| `company/__init__.py` + `companion/package.json` | **0.3.68** lockstep |
| Docs | UX, ADR-050, roadmap, handoff, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_projects_split_browse_polish.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Tasks 2–4 must satisfy

- [ ] **Step 1: Write the test module**

```python
"""Projects Browse split + shell polish (v0.3.68)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ProjectsSplitBrowsePolishTests(unittest.TestCase):
    def test_projects_browse_split_markers(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("project-browse-split", text)
        self.assertIn("project-browse-list", text)
        self.assertIn("project-browse-detail", text)
        self.assertIn("Select a project", text)
        self.assertIn("Clear selection", text)
        self.assertNotIn("← Back", text)
        self.assertIn("Local candidates", text)  # Manage preserved
        self.assertIn("Assign GitHub", text)

    def test_styles_have_split_and_empty(self):
        css = (SRC / "styles.css").read_text()
        self.assertIn(".project-browse-split", css)
        self.assertIn(".panel-empty", css)
        self.assertIn(".list-row", css)

    def test_sibling_panels_have_empty_or_section_polish(self):
        for name in ("CorporatePanel.tsx", "WorkersPanel.tsx", "OrgPanel.tsx"):
            text = (SRC / name).read_text()
            self.assertTrue(
                "panel-empty" in text or "section-head" in text,
                f"{name} should use panel-empty or section-head",
            )

    def test_finance_still_has_no_mode_switch(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertNotIn("ModeSwitch", text)
        self.assertNotIn("panel-mode", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.68"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.68"', pkg)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_projects_split_browse_polish -v`

Expected: FAIL (missing split class names / Clear selection / version still 0.3.67).

- [ ] **Step 3: Commit**

```bash
git add tests/test_projects_split_browse_polish.py
git commit -m "$(cat <<'EOF'
test(companion): add Projects split browse polish contracts

EOF
)"
```

---

### Task 2: Shared CSS (split + shell)

**Files:**
- Modify: `companion/src/styles.css`

**Interfaces:**
- Consumes: class names from Task 1
- Produces: styles Task 3–4 markup will use

- [ ] **Step 1: Widen app on mid+ viewports** so a split is usable (phone-first `32rem` remains default):

```css
@media (min-width: 720px) {
  .app {
    max-width: 52rem;
  }
}
```

- [ ] **Step 2: Add split / list / empty / ModeSwitch polish** near other layout rules:

```css
.panel-mode {
  margin: 0 0 0.65rem;
}

.project-browse-split {
  display: grid;
  gap: 0.65rem;
  align-items: start;
}

@media (min-width: 720px) {
  .project-browse-split {
    grid-template-columns: minmax(10rem, 0.85fr) minmax(0, 1.35fr);
  }
}

.project-browse-list,
.project-browse-detail {
  min-width: 0;
}

.list-row {
  display: block;
  width: 100%;
  text-align: left;
  background: var(--glass);
  border: 1px solid var(--glass-border);
  border-radius: 0.75rem;
  padding: 0.55rem 0.65rem;
  margin: 0 0 0.4rem;
  color: inherit;
  cursor: pointer;
}

.list-row.active {
  border-color: var(--cosmic);
  background: rgba(59, 130, 246, 0.16);
}

.list-row .muted {
  margin-top: 0.2rem;
  font-size: 0.8rem;
}

.panel-empty {
  color: var(--muted);
  margin: 0.35rem 0;
  font-size: 0.9rem;
}

.detail-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
```

- [ ] **Step 3: Run CSS-related test**

Run: `.venv/bin/python -m unittest tests.FAKESECRET_g1h2i3j4k5l6m7n8o9p0 -v`

Expected: PASS. Other Task 1 tests may still FAIL.

- [ ] **Step 4: Commit**

```bash
git add companion/src/styles.css
git commit -m "$(cat <<'EOF'
style(companion): Projects browse split and list polish tokens

EOF
)"
```

---

### Task 3: ProjectsPanel Browse split

**Files:**
- Modify: `companion/src/ProjectsPanel.tsx`

**Interfaces:**
- Consumes: CSS classes from Task 2; existing props/state
- Produces: Browse always shows list+detail; Manage unchanged

- [ ] **Step 1: Restructure Browse mode**

Today Browse is either (a) full-page detail when `selectedProject` is set, or (b) a list of cards with a Details button. Replace that with:

When `mode === "browse"`:

```tsx
<div className="project-browse-split">
  <div className="project-browse-list">
    <div className="section-head">
      <h2>Projects</h2>
    </div>
    {!projects.length && (
      <p className="panel-empty">No projects enrolled yet.</p>
    )}
    {projects.map((project) => {
      const id = String(project.id);
      const active = selectedProject === id;
      return (
        <button
          key={id}
          type="button"
          className={active ? "list-row active" : "list-row"}
          aria-pressed={active}
          onClick={() => setSelectedProject(id)}
        >
          <strong>{id}</strong>
          <div className="muted">{String(project.brief)}</div>
          <div className="muted">
            Blockers: {(project.blockers as string[])?.join(", ") || "none"}
          </div>
        </button>
      );
    })}
  </div>
  <div className="project-browse-detail">
    {!selectedProject && (
      <div className="card">
        <p className="panel-empty">Select a project</p>
      </div>
    )}
    {selectedProject && !projectDetail && (
      <div className="card">
        <p className="muted">Loading…</p>
      </div>
    )}
    {selectedProject && projectDetail && (
      <div className="card">
        <div className="detail-toolbar">
          <h2>{selectedProject}</h2>
          <button type="button" onClick={() => setSelectedProject(null)}>
            Clear selection
          </button>
        </div>
        {/* Move the existing detail body here: brief, departments, GitHub,
            dispatch form — same handlers as today. Remove ← Back. */}
      </div>
    )}
  </div>
</div>
```

Implementation notes:

- Keep `ModeSwitch` above the split.
- Do **not** show the old full-page detail branch that replaces the list.
- Manage branch (`mode === "manage"`) stays as today’s enroll/GitHub/enroll-form cards; optionally wrap titles with `section-head` and ensure empty local-candidates use `panel-empty`.
- Preserve all dispatch/enroll `runAction` logic and field wiring — cut/paste JSX only.
- Remove every `← Back` string.

- [ ] **Step 2: Run focused tests + build**

```bash
.venv/bin/python -m unittest \
  tests.test_projects_split_browse_polish.ProjectsSplitBrowsePolishTests.test_projects_browse_split_markers \
  tests.test_work_people_money_browse_manage \
  -v
cd companion && npm run build
```

Expected: split markers PASS; existing Browse/Manage tests PASS; build OK. Version/sibling tests may still FAIL until Tasks 4–5.

- [ ] **Step 3: Commit**

```bash
git add companion/src/ProjectsPanel.tsx
git commit -m "$(cat <<'EOF'
feat(companion): Projects Browse list|detail split workspace

EOF
)"
```

---

### Task 4: Medium polish on Corporate / Workers / Org

**Files:**
- Modify: `companion/src/CorporatePanel.tsx`
- Modify: `companion/src/WorkersPanel.tsx`
- Modify: `companion/src/OrgPanel.tsx`

**Interfaces:**
- Consumes: `.panel-empty` / `.section-head` from Task 2
- Produces: Task 1 sibling polish test green

- [ ] **Step 1: Apply light polish only** (no Browse/Manage capability moves):

For each panel:

1. Ensure ModeSwitch is followed by consistent spacing (class `panel-mode` already on ModeSwitch root).
2. Where a list can be empty, use `<p className="panel-empty">…</p>` with honest copy (reuse existing wording if present; switch class from bare `muted` only when it is an empty-list message).
3. Add or keep a `section-head` around the primary list title if missing.

Do **not** restructure Corporate scorecard/forms hierarchy. Do **not** touch Finance ModeSwitch.

Minimum to satisfy the test: each of the three files contains `panel-empty` **or** `section-head` (prefer both where natural).

- [ ] **Step 2: Run sibling test**

Run: `.venv/bin/python -m unittest tests.FAKESECRET_q1r2s3t4u5v6w7x8y9z0 -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add companion/src/CorporatePanel.tsx companion/src/WorkersPanel.tsx companion/src/OrgPanel.tsx
git commit -m "$(cat <<'EOF'
style(companion): empty and section polish on Work/People panels

EOF
)"
```

---

### Task 5: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `__version__ = "0.3.68"`
- Modify: `companion/package.json` → `"version": "0.3.68"`
- Modify: `docs/11-user-experience.md` (Projects Browse split; Clear selection)
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-050
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-11-projects-split-browse-polish-design.md` → implemented
- Modify: `README.md` version banner if it still says 0.3.67

**Interfaces:**
- Consumes: shipped UI from Tasks 2–4
- Produces: full suite green including version lockstep

- [ ] **Step 1: Bump versions** to **0.3.68** in Python + companion package.json.

- [ ] **Step 2: ADR-050 table row + short detail**

| ADR-050 | 2026-09-11 | Companion Projects Browse split workspace | Projects Browse uses list\|detail split; detail holds dispatch workspace; Manage remains enroll/assign; medium empty/section polish on sibling panels; no URL sync or Finance ModeSwitch. |

- [ ] **Step 3: UX / roadmap / handoff / spec status**

Describe Projects Browse split and Clear selection; note medium polish. Next = owner-directed (further Corporate polish, URL sync, or other).

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests PASS; build OK.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json README.md \
  docs/11-user-experience.md docs/14-roadmap.md docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-11-projects-split-browse-polish-design.md
git commit -m "$(cat <<'EOF'
docs: Projects split browse polish and release 0.3.68

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Responsive split list\|detail | 2–3 |
| Detail = full workspace; Manage = enroll/assign | 3 |
| Clear selection; empty “Select a project” | 3 |
| Medium shell polish siblings | 2, 4 |
| No Finance ModeSwitch / no URL sync / no new APIs | Global + 1, 5 |
| Source tests + build + 0.3.68 docs | 1, 5 |

No placeholders. App max-width widen at 720px is required so the approved split is usable outside a phone column.
