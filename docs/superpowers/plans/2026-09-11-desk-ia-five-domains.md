# Desk IA Five Domains Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regroup the CEO desk left rail and reorder `/desk` sections to match companion domains Home · Work · People · Money · More (v0.3.67) without new APIs or ID renames.

**Architecture:** In-place edit of `DESK_HTML` in `company/service.py`: nested always-expanded rail groups, CSS for group labels/indent, and a single long-page section reorder. Hybrid Home keeps metrics + Decisions + Consultant + HQ high; Scorecard moves under Work; More holds Intelligence · Diagnostics · Activity · Pairing.

**Tech Stack:** FastAPI-served desk HTML/CSS/JS string, existing cosmic-glass tokens + brand fonts, Python `unittest` source/HTML contracts.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-desk-ia-five-domains-design.md` (owner-approved).
- Keep all existing section `id`s (including `#desk`, `#departments`, `#people`, `#pairing`).
- No domain panes / show-hide; no Browse/Manage on desk; no companion/`welcome` nav changes.
- No new APIs, invented metrics, or Alembic.
- Version **0.3.67**. Do not commit `local repos/service-department/`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch tip: start from current `main` (0.3.66).
- Existing `test_desk_nav_anchors_resolve_to_sections` must stay green: every `href="#…"` in `DESK_HTML` must have a matching `id`.

## File map

| Path | Role |
|---|---|
| `tests/test_desk_ia_five_domains.py` | Source/HTML contracts for rail groups + section order |
| `company/service.py` | `DESK_HTML` nav CSS, rail markup, section reorder |
| `company/__init__.py` | `__version__ = "0.3.67"` |
| `docs/11-user-experience.md` | Desk sidebar = five domains |
| `docs/14-roadmap.md` | Mark desk IA done; next polish |
| `docs/decisions.md` | ADR-049 row + short detail |
| `docs/18-handoff.md` | 0.3.67 status / next |
| `docs/superpowers/specs/2026-09-11-desk-ia-five-domains-design.md` | Status → implemented |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_desk_ia_five_domains.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Tasks 2–3 must satisfy

- [ ] **Step 1: Write the test module**

```python
"""Desk IA aligned to five companion domains (v0.3.67)."""
from __future__ import annotations

import re
import unittest

from company.service import DESK_HTML


def _id_positions(html: str) -> dict[str, int]:
    return {m.group(1): m.start() for m in re.finditer(r'\bid="([^"]+)"', html)}


class DeskIaFiveDomainsTests(unittest.TestCase):
    def test_rail_has_five_domain_groups(self):
        self.assertIn('class="rail-group"', DESK_HTML)
        for label in ("Home", "Work", "People", "Money", "More"):
            self.assertIn(f'class="rail-group-label">{label}</span>', DESK_HTML)

    def test_rail_nested_anchors(self):
        # Home
        for anchor in ("desk", "decisions", "consultant", "hq", "status"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # Work
        for anchor in (
            "scorecard",
            "projects",
            "cross-department",
            "corporate-upgrades",
            "people",
        ):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # People
        for anchor in ("departments", "head-inbox"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # Money / More
        for anchor in ("budget", "intelligence", "diagnostics", "activity", "pairing"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)

    def test_section_order_matches_domain_map(self):
        pos = _id_positions(DESK_HTML)
        # Home lead (hybrid)
        home = ["desk", "decisions", "consultant", "hq", "status"]
        for earlier, later in zip(home, home[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # Work after Home status
        work = [
            "scorecard",
            "projects",
            "cross-department",
            "corporate-upgrades",
            "people",
        ]
        self.assertLess(pos["status"], pos["scorecard"])
        for earlier, later in zip(work, work[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # People after Work people section
        self.assertLess(pos["people"], pos["departments"])
        self.assertLess(pos["departments"], pos["head-inbox"])
        # Money then More
        self.assertLess(pos["head-inbox"], pos["budget"])
        more = ["intelligence", "diagnostics", "activity", "pairing"]
        self.assertLess(pos["budget"], pos["intelligence"])
        for earlier, later in zip(more, more[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # Scorecard is not before Decisions (moved out of old top placement)
        self.assertGreater(pos["scorecard"], pos["decisions"])

    def test_hq_adjacent_detail_panels(self):
        pos = _id_positions(DESK_HTML)
        self.assertLess(pos["hq"], pos["room-detail"])
        self.assertLess(pos["hq"], pos["worker-card"])
        # Details still before Work scorecard
        self.assertLess(pos["room-detail"], pos["scorecard"])
        self.assertLess(pos["worker-card"], pos["scorecard"])

    def test_version_bump_target(self):
        init = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "company"
            / "__init__.py"
        ).read_text()
        self.assertIn('__version__ = "0.3.67"', init)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_desk_ia_five_domains -v`

Expected: FAIL (missing `rail-group` / wrong section order / version still 0.3.66).

- [ ] **Step 3: Commit**

```bash
git add tests/test_desk_ia_five_domains.py
git commit -m "$(cat <<'EOF'
test(desk): add five-domain IA source contracts

EOF
)"
```

---

### Task 2: Rail CSS + grouped nav

**Files:**
- Modify: `company/service.py` (`DESK_HTML` `<style>` and `<nav>`)

**Interfaces:**
- Consumes: Task 1 label/anchor expectations
- Produces: Grouped always-expanded rail; all `href="#…"` still resolve (incl. `#pairing`, `#head-inbox`)

- [ ] **Step 1: Add nested-rail CSS** inside the existing `<style>` block (near `.rail a` rules):

```css
.rail-group { display: flex; flex-direction: column; gap: 0.15rem; margin: 0 0 0.55rem; }
.rail-group-label {
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  padding: 0.15rem 0.65rem 0.2rem;
}
.rail-group a { padding-left: 0.9rem; font-size: 0.88rem; }
@media (max-width: 840px) {
  .rail-group { flex-direction: row; flex-wrap: wrap; align-items: center; gap: 0.2rem; margin: 0 0 0.35rem; }
  .rail-group-label { width: 100%; padding-bottom: 0; }
}
```

- [ ] **Step 2: Replace the flat `<nav aria-label="Primary">…</nav>` with:**

```html
<nav aria-label="Primary">
<div class="rail-group">
<span class="rail-group-label">Home</span>
<a href="#desk">CEO desk</a>
<a href="#decisions">Decisions</a>
<a href="#consultant">Consultant</a>
<a href="#hq">Headquarters</a>
<a href="#status">Status</a>
</div>
<div class="rail-group">
<span class="rail-group-label">Work</span>
<a href="#scorecard">Scorecard</a>
<a href="#projects">Projects</a>
<a href="#cross-department">Cross-department</a>
<a href="#corporate-upgrades">Corporate upgrades</a>
<a href="#people">People &amp; staffing</a>
</div>
<div class="rail-group">
<span class="rail-group-label">People</span>
<a href="#departments">Organization</a>
<a href="#head-inbox">Head inbox</a>
</div>
<div class="rail-group">
<span class="rail-group-label">Money</span>
<a href="#budget">Budget</a>
</div>
<div class="rail-group">
<span class="rail-group-label">More</span>
<a href="#intelligence">Intelligence</a>
<a href="#diagnostics">Diagnostics</a>
<a href="#activity">Activity</a>
<a href="#pairing">Phone pairing</a>
</div>
</nav>
```

Do **not** put Decisions/Consultant under More. Do **not** rename any `id`s.

- [ ] **Step 3: Run anchor integrity + partial new tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_companion_api.CompanionApiTests.test_desk_nav_anchors_resolve_to_sections \
  tests.test_desk_ia_five_domains.DeskIaFiveDomainsTests.test_rail_has_five_domain_groups \
  tests.test_desk_ia_five_domains.DeskIaFiveDomainsTests.test_rail_nested_anchors \
  -v
```

Expected: those three PASS. `test_section_order_*` / version may still FAIL.

- [ ] **Step 4: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): group rail under Home Work People Money More

EOF
)"
```

---

### Task 3: Reorder main column sections

**Files:**
- Modify: `company/service.py` (`DESK_HTML` `<main class="workspace">` body)

**Interfaces:**
- Consumes: approved section order from spec
- Produces: HTML id order matching Task 1 `test_section_order_matches_domain_map`

- [ ] **Step 1: Reorder blocks** inside `<main class="workspace">` to this sequence (move whole sections; do not rewrite form innards):

1. Keep `<header>…</header>` + `.metrics` ( `#desk` on the `h1` ).
2. **Home Needs-you:** move `#decisions` and `#consultant` **above** the HQ grid (full-width glass sections).
3. **HQ block:** keep `.desk-grid` with `#hq` on the left and `#room-detail` + `#worker-card` on the right (same structure as today, but Decisions/Consultant are no longer inside the right column).
4. `#status` immediately after the HQ grid.
5. **Work:** `#scorecard`, then `#projects` (including local-repo list), `#cross-department`, `#corporate-upgrades`, `#people`.
6. **People:** `#departments`, then `#head-inbox`.
7. **Money:** `#budget`.
8. **More:** `#intelligence`, `#diagnostics`, `#activity`, `#pairing`.

Concrete structural sketch for the Home/HQ region after reorder:

```html
<header>…<h1 id="desk">…</h1>…</header>
<div class="metrics">…</div>
<section class="glass" id="decisions">…</section>
<section class="glass" id="consultant">…</section>
<div class="desk-grid">
  <section class="glass" id="hq">…</section>
  <div>
    <section class="glass" id="room-detail" hidden>…</section>
    <section class="glass" id="worker-card" hidden>…</section>
  </div>
</div>
<section class="glass" id="status">…</section>
<section class="glass" id="scorecard">…</section>
<section class="glass" id="projects">…</section>
<!-- cross-department, corporate-upgrades, people, departments, head-inbox,
     budget, intelligence, diagnostics, activity, pairing — in that order -->
```

Preserve every `id="…"`, form `id`, and script hook. Audit only if a script assumes Decisions is a sibling inside `.desk-grid` (today’s JS uses `getElementById` — should be fine).

- [ ] **Step 2: Run Task 1 order tests + desk smoke tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_desk_ia_five_domains -v
.venv/bin/python -m unittest \
  tests.test_companion_api.CompanionApiTests.test_desk_nav_anchors_resolve_to_sections \
  tests.test_desk_furniture \
  tests.test_activity_projection \
  tests.test_floorplans \
  -v
```

Expected: all PASS except possibly `test_version_bump_target` until Task 4.

- [ ] **Step 3: Commit**

```bash
git add company/service.py
git commit -m "$(cat <<'EOF'
feat(desk): reorder sections to five-domain page map

EOF
)"
```

---

### Task 4: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py`
- Modify: `docs/11-user-experience.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md`
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-11-desk-ia-five-domains-design.md` (status → implemented)

**Interfaces:**
- Consumes: shipped HTML behavior from Tasks 2–3
- Produces: ADR-049; version 0.3.67; handoff next = companion Browse/Manage polish

- [ ] **Step 1: Bump version**

In `company/__init__.py`:

```python
__version__ = "0.3.67"
```

- [ ] **Step 2: UX + roadmap**

In `docs/11-user-experience.md`, update the desk navigation sentence so the CEO desk sidebar is described as five domain groups (**Home · Work · People · Money · More**) with nested anchors matching companion, hybrid Home (metrics + decisions/consultant + HQ), and Scorecard under Work.

In `docs/14-roadmap.md`:
- Set local status line to **v0.3.67**.
- Add a checked M6/M10-style bullet: desk IA aligned to five companion domains (0.3.67).
- Update the closing “Next” paragraph: next = deep visual polish inside companion Browse/Manage (or deploy 0.3.67).

- [ ] **Step 3: ADR-049**

Append to the decisions table:

| ADR-049 | 2026-09-11 | Desk IA matches companion five domains | Desk rail grouped Home · Work · People · Money · More; page sections reordered; hybrid Home keeps HQ high; Scorecard under Work; no ID renames or domain panes. |

Add a short detail subsection mirroring other ADRs.

- [ ] **Step 4: Spec status + handoff**

Spec status → **implemented in v0.3.67**.

`docs/18-handoff.md`: version **0.3.67**; note desk IA shipped; verification commands; next = companion Browse/Manage visual polish (owner-directed) or fs-dev deploy.

- [ ] **Step 5: Full verification**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all tests PASS (including `test_version_bump_target`).

Manual smoke (local or fs-dev after deploy): `GET /desk` — walk each nested rail link; confirm Decisions/Consultant above HQ; Scorecard after Status; Pairing last; pairing/dispatch/org forms still work.

- [ ] **Step 6: Commit**

```bash
git add company/__init__.py docs/11-user-experience.md docs/14-roadmap.md \
  docs/decisions.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-11-desk-ia-five-domains-design.md
git commit -m "$(cat <<'EOF'
docs: desk five-domain IA and release 0.3.67

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Grouped rail Home·Work·People·Money·More | 2 |
| Nested anchors + always expanded | 2 |
| Hybrid Home order + HQ high | 3 |
| Scorecard under Work | 3 |
| Strict More leftovers | 2–3 |
| Keep ids / no panes / no APIs | Global + 2–3 |
| Source contract + unittest | 1, 5 |
| Docs / ADR / 0.3.67 | 4 |

No placeholders remaining. Pairing + head-inbox anchors are added (were missing from the old flat rail) so `test_desk_nav_anchors_resolve_to_sections` stays valid.
