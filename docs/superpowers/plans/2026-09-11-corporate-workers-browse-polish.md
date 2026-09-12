# Corporate + Workers Browse Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Corporate and Workers Browse titles/empties consistent with Projects (v0.3.69) via in-place `section-head` + `panel-empty` markup — no capability or API changes.

**Architecture:** Edit `CorporatePanel.tsx` and `WorkersPanel.tsx` only for UI structure. Source contracts encode required `section-head` wrappers and Workers title placement. Docs/ADR/version bump at the end.

**Tech Stack:** React companion, existing CSS classes, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-corporate-workers-browse-polish-design.md` (owner-approved).
- No Corporate groups/sub-tabs; no Org redesign; no Projects `span` fix; no URL sync.
- No new APIs, Finance ModeSwitch, desk/welcome changes.
- Preserve all in-row actions and Manage forms.
- Version **0.3.69**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch tip: start from current `main` (0.3.68 on fs-dev).

## File map

| Path | Role |
|---|---|
| `tests/test_corporate_workers_browse_polish.py` | Source contracts |
| `companion/src/CorporatePanel.tsx` | Wrap Browse list titles |
| `companion/src/WorkersPanel.tsx` | Move section-head outside card |
| `company/__init__.py` + `companion/package.json` | **0.3.69** |
| Docs | UX, ADR-051, roadmap, handoff, spec status, README |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_corporate_workers_browse_polish.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Tasks 2–3 must satisfy

- [ ] **Step 1: Write the test module**

```python
"""Corporate + Workers Browse consistency (v0.3.69)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _section_head_wraps_h2(text: str, title: str) -> bool:
    """True if an h2 with this title appears inside a section-head div."""
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class CorporateWorkersBrowsePolishTests(unittest.TestCase):
    def test_corporate_browse_section_heads(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in (
            "Objectives",
            "Industry packs",
            "Divisions",
            "Pending promotions",
            "Staffing proposals",
            "Cross-department requests",
            "Open activity",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"Corporate Browse missing section-head for {title!r}",
            )
        self.assertIn("panel-empty", text)
        self.assertIn("CEO scorecard", text)

    def test_workers_section_head_outside_card(self):
        text = (SRC / "WorkersPanel.tsx").read_text()
        self.assertTrue(_section_head_wraps_h2(text, "Worker hosts"))
        # section-head must appear before the Browse list card that contains hosts.map
        head_at = text.find('className="section-head"')
        hosts_card_at = text.find("{hosts.map")
        self.assertGreaterEqual(head_at, 0)
        self.assertGreaterEqual(hosts_card_at, 0)
        self.assertLess(
            head_at,
            hosts_card_at,
            "Worker hosts section-head must precede hosts.map",
        )
        # Title should not be nested inside the first card of browse in the old way:
        # after ModeSwitch browse block, section-head comes before `<div className="card">`
        browse = text.split('mode === "browse"')[1].split('mode === "manage"')[0]
        self.assertRegex(
            browse,
            r'section-head[\s\S]*?<div className="card">',
            "section-head should appear before the Browse card",
        )
        self.assertIn("panel-empty", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.69"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.69"', pkg)
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_corporate_workers_browse_polish -v`

Expected: FAIL (Industry packs etc. still bare `<h2>`; Workers section-head still inside card; version 0.3.68).

- [ ] **Step 3: Commit**

```bash
git add tests/test_corporate_workers_browse_polish.py
git commit -m "$(cat <<'EOF'
test(companion): Corporate/Workers Browse consistency contracts

EOF
)"
```

---

### Task 2: CorporatePanel section-heads

**Files:**
- Modify: `companion/src/CorporatePanel.tsx`

**Interfaces:**
- Consumes: Task 1 title list
- Produces: Corporate Browse titles wrapped

- [ ] **Step 1: Wrap each bare Browse list `<h2>`** in:

```tsx
<div className="section-head">
  <h2>Industry packs</h2>
</div>
```

Apply the same pattern for: Industry packs, Divisions, Pending promotions, Staffing proposals, Cross-department requests, Open activity.

Objectives already wrapped — leave as-is (ensure empty still `panel-empty`).

Optional: wrap CEO scorecard `h2` the same way **inside** its card, or leave scorecard as a special card title — either is fine if “CEO scorecard” text remains and contracts pass (contracts do not require scorecard `section-head`).

Do not move Manage forms. Do not change action handlers.

- [ ] **Step 2: Run Corporate test**

Run: `.venv/bin/python -m unittest tests.FAKESECRET_e3f4g5h6i7j8k9l0m1n2 -v`

(Use real method name: `test_corporate_browse_section_heads`.)

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add companion/src/CorporatePanel.tsx
git commit -m "$(cat <<'EOF'
style(companion): section-head all Corporate Browse lists

EOF
)"
```

---

### Task 3: WorkersPanel title placement

**Files:**
- Modify: `companion/src/WorkersPanel.tsx`

**Interfaces:**
- Consumes: Task 1 Workers placement contract
- Produces: section-head before Browse card

- [ ] **Step 1: Restructure Browse block** from:

```tsx
<div className="card">
  <div className="section-head">
    <h2>Worker hosts</h2>
  </div>
  {hosts.map(...)}
  {!hosts.length && !loadError && <p className="panel-empty">…</p>}
</div>
```

to:

```tsx
<div className="section-head">
  <h2>Worker hosts</h2>
</div>
<div className="card">
  {hosts.map(...)}
  {!hosts.length && !loadError && (
    <p className="panel-empty">No worker hosts registered.</p>
  )}
</div>
```

Keep loadError banner, enable/disable/delete actions, and Manage mode unchanged.

- [ ] **Step 2: Run Workers + prior browse tests + build**

```bash
.venv/bin/python -m unittest \
  tests.test_corporate_workers_browse_polish \
  tests.test_work_people_money_browse_manage \
  tests.test_projects_split_browse_polish \
  -v
cd companion && npm run build
```

Expected: Corporate + Workers placement PASS; version may still FAIL; build OK.

- [ ] **Step 3: Commit**

```bash
git add companion/src/WorkersPanel.tsx
git commit -m "$(cat <<'EOF'
style(companion): lift Workers section-head outside list card

EOF
)"
```

---

### Task 4: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.69`
- Modify: `companion/package.json` → `0.3.69`
- Modify: `README.md` banner if present
- Modify: `docs/11-user-experience.md` (Corporate/Workers section-head consistency)
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-051
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-11-corporate-workers-browse-polish-design.md` → implemented

**Interfaces:**
- Consumes: Tasks 2–3 UI
- Produces: full suite green

- [ ] **Step 1: Bump versions** to **0.3.69** (Python + companion lockstep).

- [ ] **Step 2: ADR-051**

| ADR-051 | 2026-09-11 | Corporate and Workers Browse section consistency | Corporate Browse lists use section-head + panel-empty; Workers title sits outside the list card; no capability or API changes. |

Add short detail subsection.

- [ ] **Step 3: UX / roadmap / handoff / spec status / README**

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all PASS; build OK.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json README.md \
  docs/11-user-experience.md docs/14-roadmap.md docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-11-corporate-workers-browse-polish-design.md
git commit -m "$(cat <<'EOF'
docs: Corporate/Workers Browse polish and release 0.3.69

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Corporate list section-heads + panel-empty | 1–2 |
| Workers title outside card | 1, 3 |
| No groups/Org/Projects span/URL/APIs | Global |
| 0.3.69 docs/ADR | 4 |

Note: Task 2 step mentions a FAKESECRET-style alias only as a reminder — always run `test_corporate_browse_section_heads` by its real name.
