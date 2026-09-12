# Projects List-Row + Clear-on-Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix invalid HTML in Projects Browse list rows (`div`→`span` inside buttons) and add Clear selection on the loading detail card (v0.3.72).

**Architecture:** In-place markup in `ProjectsPanel.tsx` plus a one-line CSS `display: block` on `.list-row .muted`. Source contracts lock the strings; docs/ADR/version at the end. No URL sync or shared toolbar component.

**Tech Stack:** React companion, existing CSS, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-projects-list-row-clear-loading-design.md` (owner-approved).
- List-row muted lines must be `<span className="muted">` (not `div`).
- Loading card (`selectedProject && !projectDetail`) gets `detail-toolbar` + Clear selection; empty “Select a project” pane stays without Clear.
- No URL sync, Manage groups, Corporate/Org changes, DetailToolbar extraction, new APIs.
- Version **0.3.72**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/projects-list-row-clear-loading` from current `main` before Task 1.
- Relax hard-pinned `0.3.71` version assertions (e.g. `tests/test_corporate_browse_clusters.py`) to `0\.3\.\d+`; keep exact `0.3.72` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `tests/test_projects_list_row_clear_loading.py` | Source contracts |
| `companion/src/ProjectsPanel.tsx` | span.muted; Clear on loading |
| `companion/src/styles.css` | `.list-row .muted { display: block; }` |
| `company/__init__.py` + `companion/package.json` | **0.3.72** |
| `tests/test_corporate_browse_clusters.py` | Relax version pin |
| Docs | UX, ADR-054, roadmap, handoff, README, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_projects_list_row_clear_loading.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Task 2–3 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/projects-list-row-clear-loading
```

- [ ] **Step 2: Write the test module**

```python
"""Projects list-row span fix + Clear on loading (v0.3.72)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ProjectsListRowClearLoadingTests(unittest.TestCase):
    def test_list_row_uses_span_muted_not_div(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        # Extract the list map button body roughly between list-row and project-browse-detail
        list_part = text.split("project-browse-list", 1)[1].split("project-browse-detail", 1)[0]
        self.assertIn('className="muted"', list_part)
        self.assertIn("<span className=\"muted\">", list_part)
        self.assertNotIn("<div className=\"muted\">", list_part)
        self.assertIn("list-row", list_part)

    def test_loading_card_has_clear_selection_toolbar(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        # Loading branch sits between empty pane and loaded detail
        loading = text.split("selectedProject && !projectDetail", 1)[1].split(
            "selectedProject && projectDetail", 1
        )[0]
        self.assertIn("detail-toolbar", loading)
        self.assertIn("Clear selection", loading)
        self.assertIn("Loading…", loading)
        self.assertIn("setSelectedProject(null)", loading)
        # Empty pane must not gain Clear
        empty = text.split("!selectedProject", 1)[1].split("selectedProject && !projectDetail", 1)[0]
        self.assertIn("Select a project", empty)
        self.assertNotIn("Clear selection", empty)

    def test_list_row_muted_display_block(self):
        css = (SRC / "styles.css").read_text()
        self.assertRegex(
            css,
            r"\.list-row\s+\.muted\s*\{[^}]*display:\s*block",
        )

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.72"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.72"', pkg)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_projects_list_row_clear_loading -v`

Expected: FAIL (div.muted in list; loading lacks Clear/toolbar; CSS missing display:block; version 0.3.71).

- [ ] **Step 4: Commit**

```bash
git add tests/test_projects_list_row_clear_loading.py
git commit -m "$(cat <<'EOF'
test(companion): Projects list-row Clear-on-loading contracts

EOF
)"
```

---

### Task 2: ProjectsPanel markup + CSS

**Files:**
- Modify: `companion/src/ProjectsPanel.tsx`
- Modify: `companion/src/styles.css`

**Interfaces:**
- Consumes: Task 1 string contracts
- Produces: green markup/CSS tests (version may still fail until Task 3)

- [ ] **Step 1: CSS — add `display: block` to `.list-row .muted`**

In `companion/src/styles.css`, change:

```css
.list-row .muted {
  margin-top: 0.2rem;
  font-size: 0.8rem;
}
```

to:

```css
.list-row .muted {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.8rem;
}
```

- [ ] **Step 2: List rows — `div` → `span`**

In the `projects.map` button body of `ProjectsPanel.tsx`, replace both muted lines:

```tsx
                  <strong>{id}</strong>
                  <span className="muted">{String(project.brief)}</span>
                  <span className="muted">
                    Blockers: {(project.blockers as string[])?.join(", ") || "none"}
                  </span>
```

Do not change the button, `aria-pressed`, or `onClick`.

- [ ] **Step 3: Loading card — toolbar + Clear**

Replace:

```tsx
            {selectedProject && !projectDetail && (
              <div className="card">
                <p className="muted">Loading…</p>
              </div>
            )}
```

with:

```tsx
            {selectedProject && !projectDetail && (
              <div className="card">
                <div className="detail-toolbar">
                  <h2>{selectedProject}</h2>
                  <button type="button" onClick={() => setSelectedProject(null)}>
                    Clear selection
                  </button>
                </div>
                <p className="muted">Loading…</p>
              </div>
            )}
```

Leave the empty “Select a project” card and the loaded-detail toolbar unchanged.

- [ ] **Step 4: Verify (expect version still FAIL)**

```bash
.venv/bin/python -m unittest \
  tests.test_projects_list_row_clear_loading.ProjectsListRowClearLoadingTests.test_list_row_uses_span_muted_not_div \
  tests.test_projects_list_row_clear_loading.ProjectsListRowClearLoadingTests.test_loading_card_has_clear_selection_toolbar \
  tests.test_projects_list_row_clear_loading.ProjectsListRowClearLoadingTests.test_list_row_muted_display_block \
  tests.test_projects_split_browse_polish \
  -v
cd companion && npm run build
```

Expected: three named tests PASS; version test still FAIL if run; build OK.

- [ ] **Step 5: Commit**

```bash
git add companion/src/ProjectsPanel.tsx companion/src/styles.css
git commit -m "$(cat <<'EOF'
fix(companion): Projects list-row spans and Clear on loading

EOF
)"
```

---

### Task 3: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.72`
- Modify: `companion/package.json` → `0.3.72`
- Modify: `tests/test_corporate_browse_clusters.py` — relax version pin to `0\.3\.\d+`
- Modify: `README.md` banner if it cites companion version
- Modify: `docs/11-user-experience.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-054
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-12-projects-list-row-clear-loading-design.md` → implemented

**Critical:** Stage **only** the files listed. Do not `git add -A`. Do not stage `.vscode/` or `local repos/`.

- [ ] **Step 1: Bump versions** to **0.3.72** in `company/__init__.py` and `companion/package.json`.

- [ ] **Step 2: Relax Corporate clusters version assertion**

In `tests/test_corporate_browse_clusters.py` replace `test_version_bump_target` body with:

```python
    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

- [ ] **Step 3: ADR-054** in `docs/decisions.md` table + detail:

| ADR-054 | 2026-09-12 | Projects list-row span + Clear on loading | Projects Browse list rows use span.muted inside buttons; loading detail shows Clear selection; no URL sync or API changes. |

Detail: context (invalid div-in-button; Clear only on loaded detail), decision (span + loading toolbar), alternatives (CSS-only; Clear on empty pane; DetailToolbar extract), consequences (0.3.72; URL sync still deferred).

- [ ] **Step 4: UX / roadmap / handoff / README / spec status**

- UX: note list-row spans + Clear while loading.
- Roadmap: mark item done; update status banner and Immediate next (URL sync, Manage groups, …).
- Handoff: local branch state for 0.3.72 (not deployed until finish).
- Spec status → **implemented in v0.3.72**.

- [ ] **Step 5: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all PASS; build OK; package version 0.3.72.

- [ ] **Step 6: Commit (explicit paths only)**

```bash
git add \
  company/__init__.py \
  companion/package.json \
  tests/test_corporate_browse_clusters.py \
  README.md \
  docs/11-user-experience.md \
  docs/14-roadmap.md \
  docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-projects-list-row-clear-loading-design.md
git commit -m "$(cat <<'EOF'
docs: Projects list-row Clear-on-loading and release 0.3.72

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| List-row `span.muted` | Task 2 |
| `.list-row .muted { display: block }` | Task 2 |
| Clear on loading toolbar | Task 2 |
| Empty pane without Clear | Task 2 (preserved) |
| Source contracts + 0.3.72 | Tasks 1 + 3 |
| ADR-054 / docs | Task 3 |
| Non-goals honored | Global constraints |

## Plan self-review

- No TBD placeholders; exact markup in Task 2.
- Version pin migration for Corporate clusters called out.
- Explicit `git add` paths; no `git add -A`.
