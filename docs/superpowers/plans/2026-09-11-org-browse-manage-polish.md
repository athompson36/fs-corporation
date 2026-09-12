# Org Browse + Manage Title Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consistent `section-head` titles to Org Browse (Departments) and all Manage forms in `OrgPanel` (v0.3.70) without changing capabilities or APIs.

**Architecture:** In-place markup in `OrgPanel.tsx` only. Source contracts lock title strings inside `section-head`. Docs/ADR/version at the end.

**Tech Stack:** React companion, existing CSS, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-org-browse-manage-polish-design.md` (owner-approved).
- No Manage groups; no Corporate/Projects/URL changes; no new APIs.
- Preserve Head inbox assign flow and all Manage handlers.
- Version **0.3.70**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch tip: start from current `main` (0.3.69 on fs-dev). Also commit any pending tip-only handoff fix if still unstaged (`docs/18-handoff.md` tip → `b0aba4b`) only as part of Task 3 docs if still dirty — do not mix unrelated `.vscode` changes.

## File map

| Path | Role |
|---|---|
| `tests/test_org_browse_manage_polish.py` | Source contracts |
| `companion/src/OrgPanel.tsx` | section-head markup |
| `company/__init__.py` + `companion/package.json` | **0.3.70** |
| Docs | UX, ADR-052, roadmap, handoff, README, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_org_browse_manage_polish.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Task 2 must satisfy

- [ ] **Step 1: Write the test module**

```python
"""Org Browse + Manage title consistency (v0.3.70)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _section_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class OrgBrowseManagePolishTests(unittest.TestCase):
    def test_org_browse_and_manage_section_heads(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        for title in (
            "Departments",
            "Head inbox",
            "Create department",
            "Appoint department head",
            "Vacate department head",
            "Assign position",
            "Release assignment",
            "Create position",
            "Reorder departments",
            "Activate dormant department for project",
            "Worker card",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"OrgPanel missing section-head for {title!r}",
            )
        self.assertIn("panel-empty", text)
        self.assertIn("ModeSwitch", text)
        self.assertIn("assign-dispatch", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.70"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.70"', pkg)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_org_browse_manage_polish -v`

Expected: FAIL (no Departments section-head; Manage titles bare; version 0.3.69).

- [ ] **Step 3: Commit**

```bash
git add tests/test_org_browse_manage_polish.py
git commit -m "$(cat <<'EOF'
test(companion): Org Browse/Manage section-head contracts

EOF
)"
```

---

### Task 2: OrgPanel section-heads

**Files:**
- Modify: `companion/src/OrgPanel.tsx`

**Interfaces:**
- Consumes: Task 1 title list
- Produces: all titles wrapped

- [ ] **Step 1: Browse — add Departments head**

Before `organization.map(...)`:

```tsx
<div className="section-head">
  <h2>Departments</h2>
</div>
```

Keep existing Head inbox `section-head` and both `panel-empty` messages.

- [ ] **Step 2: Manage — lift each form `h2` into `section-head` above the form card**

For each Manage form currently structured like:

```tsx
<form className="card" ...>
  <h2>Create department</h2>
  ...
</form>
```

Change to:

```tsx
<div className="section-head">
  <h2>Create department</h2>
</div>
<form className="card" ...>
  ...
</form>
```

Apply to all Manage titles listed in Task 1 (including Worker card block if it uses a card + h2).

Do not change form fields, `onSubmit`, or `runAction` keys. Fix indentation only if needed for readability.

- [ ] **Step 3: Verify**

```bash
.venv/bin/python -m unittest \
  tests.test_org_browse_manage_polish.OrgBrowseManagePolishTests.test_org_browse_and_manage_section_heads \
  tests.test_work_people_money_browse_manage \
  tests.test_corporate_workers_browse_polish \
  -v
cd companion && npm run build
```

Expected: section-head test PASS; version may FAIL; build OK.

- [ ] **Step 4: Commit**

```bash
git add companion/src/OrgPanel.tsx
git commit -m "$(cat <<'EOF'
style(companion): Org Browse/Manage section-head titles

EOF
)"
```

---

### Task 3: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.70`
- Modify: `companion/package.json` → `0.3.70`
- Modify: `README.md` banner if needed
- Modify: `docs/11-user-experience.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-052
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-11-org-browse-manage-polish-design.md` → implemented
- If still needed: relax any hard-pinned `0.3.69` version assertions in older polish tests to `0\.3\.\d+` (keep exact `0.3.70` only in this task’s contract).

**Critical:** Stage **only** the files listed for this release. Do not `git add -A`. Do not stage `.vscode/` or `local repos/`.

- [ ] **Step 1: Bump versions** to **0.3.70**.

- [ ] **Step 2: ADR-052**

| ADR-052 | 2026-09-11 | Org Browse and Manage section-head consistency | Organization catalog and Manage forms use section-head titles matching Corporate/Workers; no capability or API changes. |

- [ ] **Step 3: UX / roadmap / handoff / README / spec status**

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all PASS; build OK.

- [ ] **Step 5: Commit (explicit paths only)**

```bash
git add company/__init__.py companion/package.json README.md \
  docs/11-user-experience.md docs/14-roadmap.md docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-11-org-browse-manage-polish-design.md \
  tests/test_corporate_workers_browse_polish.py \
  tests/test_projects_split_browse_polish.py
# Only include older test pin files if you actually changed them.
git status
git commit -m "$(cat <<'EOF'
docs: Org Browse/Manage polish and release 0.3.70

EOF
)"
```

Before committing, confirm `git status` shows **no** deletions of this release’s feature files.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Departments section-head | 1–2 |
| Manage form section-heads | 1–2 |
| Head inbox / assign preserved | 1–2 |
| 0.3.70 docs/ADR | 3 |
| Explicit staging hygiene | 3 |
