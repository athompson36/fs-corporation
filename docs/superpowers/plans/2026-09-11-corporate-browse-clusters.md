# Corporate Browse Clusters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Group Corporate Browse into Strategy · Structure · People · Coordination clusters with narrow-viewport sub-tabs, plus light Manage `section-head` titles (v0.3.71).

**Architecture:** In-place `CorporatePanel.tsx` using `matchMedia("(min-width: 720px)")`. Wide layout scrolls all four `cluster-head` groups; narrow layout uses a `.segmented` tablist to show one cluster. Manage titles lift into `section-head` outside cards. Source contracts lock strings; no new APIs.

**Tech Stack:** React companion, existing `.segmented` CSS, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-11-corporate-browse-clusters-design.md` (owner-approved).
- Clusters fixed: Strategy (scorecard + objectives) · Structure (packs + divisions) · People (promotions + staffing) · Coordination (cross-dept + activity).
- Sub-tabs only when viewport width &lt; 720px; labeled scroll when ≥ 720px.
- No URL sync, Manage groups, shared component extraction, desk/welcome, Finance ModeSwitch, or new APIs.
- Version **0.3.71**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/corporate-browse-clusters` from current `main` before Task 1.
- Relax older hard-pinned `0.3.70` version assertions to `0\.3\.\d+` when bumping (exact `0.3.71` only in this release’s contract).

## File map

| Path | Role |
|---|---|
| `tests/test_corporate_browse_clusters.py` | Source contracts |
| `companion/src/CorporatePanel.tsx` | Clusters, matchMedia tabs, Manage section-heads |
| `companion/src/styles.css` | `.cluster-head` styling |
| `company/__init__.py` + `companion/package.json` | **0.3.71** |
| `tests/test_org_browse_manage_polish.py` | Relax version pin to regex |
| Docs | UX, ADR-053, roadmap, handoff, README, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_corporate_browse_clusters.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Task 2–3 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/corporate-browse-clusters
```

- [ ] **Step 2: Write the test module**

```python
"""Corporate Browse clusters + Manage title polish (v0.3.71)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _cluster_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="cluster-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


def _section_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class CorporateBrowseClustersTests(unittest.TestCase):
    def test_browse_cluster_heads_and_narrow_tablist(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in ("Strategy", "Structure", "People", "Coordination"):
            self.assertTrue(
                _cluster_head_wraps_h2(text, title),
                f"CorporatePanel missing cluster-head for {title!r}",
            )
        self.assertIn('aria-label="Corporate clusters"', text)
        self.assertIn('matchMedia("(min-width: 720px)")', text)
        self.assertIn("panel-empty", text)
        self.assertIn("ModeSwitch", text)
        # Existing list titles remain section-heads
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
                f"CorporatePanel missing section-head for {title!r}",
            )

    def test_manage_section_heads(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in (
            "Corporate operations",
            "Create objective",
            "Propose division",
            "Create cross-department request",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"CorporatePanel Manage missing section-head for {title!r}",
            )

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.71"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.71"', pkg)

    def test_cluster_head_css_present(self):
        css = (SRC / "styles.css").read_text()
        self.assertIn(".cluster-head", css)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_corporate_browse_clusters -v`

Expected: FAIL (no cluster-heads / tablist / matchMedia / Manage section-heads / 0.3.71 / `.cluster-head` CSS).

- [ ] **Step 4: Commit**

```bash
git add tests/test_corporate_browse_clusters.py
git commit -m "$(cat <<'EOF'
test(companion): Corporate Browse cluster contracts

EOF
)"
```

---

### Task 2: CorporatePanel clusters + Manage titles + CSS

**Files:**
- Modify: `companion/src/CorporatePanel.tsx`
- Modify: `companion/src/styles.css`

**Interfaces:**
- Consumes: Task 1 string contracts (`cluster-head`, tablist label, `matchMedia("(min-width: 720px)")`, Manage section-heads)
- Produces: green browse/manage/CSS tests (version may still fail until Task 3)

- [ ] **Step 1: Add `.cluster-head` CSS** near `.section-head` in `companion/src/styles.css`:

```css
.cluster-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem;
  margin: 1rem 0 0.35rem;
}

.cluster-head h2 {
  font-size: 0.95rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--muted, #9aa4b2);
  margin: 0;
}

.corporate-cluster-tabs {
  margin: 0 0 0.65rem;
}
```

- [ ] **Step 2: Extend imports and add helpers at top of `CorporatePanel.tsx`**

Replace the React import line with:

```tsx
import {
  useEffect,
  useState,
  type Dispatch,
  type FormEvent,
  type ReactNode,
  type SetStateAction,
} from "react";
```

After the existing type aliases / before `export function CorporatePanel`, add:

```tsx
type CorporateCluster = "strategy" | "structure" | "people" | "coordination";

const CORPORATE_CLUSTERS: { id: CorporateCluster; label: string }[] = [
  { id: "strategy", label: "Strategy" },
  { id: "structure", label: "Structure" },
  { id: "people", label: "People" },
  { id: "coordination", label: "Coordination" },
];

function useWideViewport(minWidthPx = 720): boolean {
  const query = `(min-width: ${minWidthPx}px)`;
  const [wide, setWide] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia(query).matches;
  });
  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setWide(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [query]);
  return wide;
}

function ClusterHead({ title }: { title: string }) {
  return (
    <div className="cluster-head">
      <h2>{title}</h2>
    </div>
  );
}
```

**Contract note:** `useWideViewport` must call `window.matchMedia("(min-width: 720px)")` with that exact string literal so the source test matches. Prefer:

```tsx
function useWideViewport(): boolean {
  const [wide, setWide] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(min-width: 720px)").matches;
  });
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 720px)");
    const onChange = () => setWide(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return wide;
}
```

- [ ] **Step 3: Inside `CorporatePanel`, add state and replace Browse body**

After `const [mode, setMode] = useState<PanelMode>("browse");` add:

```tsx
  const wide = useWideViewport();
  const [cluster, setCluster] = useState<CorporateCluster>("strategy");
```

Replace the entire `{mode === "browse" && ( <> ... </> )}` block so Browse renders:

1. When `!wide`, a segmented tablist:

```tsx
<div className="segmented corporate-cluster-tabs" role="tablist" aria-label="Corporate clusters">
  {CORPORATE_CLUSTERS.map((item) => (
    <button
      key={item.id}
      type="button"
      role="tab"
      aria-selected={cluster === item.id}
      className={cluster === item.id ? "active" : ""}
      onClick={() => setCluster(item.id)}
    >
      {item.label}
    </button>
  ))}
</div>
```

2. Four cluster blocks, each gated by `wide || cluster === "<id>"`, each starting with `<ClusterHead title="..." />` then the existing section markup moved under that cluster:

| Cluster id | Label | Contents (move existing JSX; do not change card/action logic) |
|---|---|---|
| `strategy` | Strategy | CEO scorecard card + Objectives section-head/list/empty |
| `structure` | Structure | Industry packs + Divisions |
| `people` | People | Pending promotions + Staffing proposals |
| `coordination` | Coordination | Cross-department requests + Open activity |

Example skeleton for one cluster (repeat pattern for all four):

```tsx
{(wide || cluster === "strategy") && (
  <div className="corporate-cluster" data-cluster="strategy">
    <ClusterHead title="Strategy" />
    {/* existing scorecard card */}
    {/* existing Objectives section-head + list + panel-empty */}
  </div>
)}
```

Keep CEO scorecard’s internal `<h2>CEO scorecard</h2>` inside the card (no new section-head required for scorecard). Keep every existing list `section-head`, `panel-empty`, button, and `status(...)` call.

- [ ] **Step 4: Manage — lift titles into `section-head`**

For each Manage block currently like:

```tsx
<div className="card">
  <h2>Corporate operations</h2>
  ...
</div>
```

or

```tsx
<form className="card" ...>
  <h2>Create objective</h2>
  ...
</form>
```

Change to:

```tsx
<div className="section-head">
  <h2>Corporate operations</h2>
</div>
<div className="card">
  ...
</div>
```

Apply to: Corporate operations, Create objective, Propose division, Create cross-department request. Do not change fields or handlers.

- [ ] **Step 5: Verify (expect version still FAIL)**

```bash
.venv/bin/python -m unittest \
  tests.test_corporate_browse_clusters.CorporateBrowseClustersTests.test_browse_cluster_heads_and_narrow_tablist \
  tests.test_corporate_browse_clusters.CorporateBrowseClustersTests.test_manage_section_heads \
  tests.test_corporate_browse_clusters.CorporateBrowseClustersTests.test_cluster_head_css_present \
  tests.test_corporate_workers_browse_polish \
  -v
cd companion && npm run build
```

Expected: three named tests PASS; `test_version_bump_target` still FAIL if run; build OK.

- [ ] **Step 6: Commit**

```bash
git add companion/src/CorporatePanel.tsx companion/src/styles.css
git commit -m "$(cat <<'EOF'
feat(companion): Corporate Browse clusters and Manage titles

EOF
)"
```

---

### Task 3: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.71`
- Modify: `companion/package.json` → `0.3.71`
- Modify: `tests/test_org_browse_manage_polish.py` — relax version pin to `0\.3\.\d+`
- Modify: `README.md` banner if it cites companion version
- Modify: `docs/11-user-experience.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-053
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-11-corporate-browse-clusters-design.md` → status implemented

**Critical:** Stage **only** the files listed. Do not `git add -A`. Do not stage `.vscode/` or `local repos/`.

- [ ] **Step 1: Bump versions** to **0.3.71** in `company/__init__.py` and `companion/package.json`.

- [ ] **Step 2: Relax Org polish version assertion**

In `tests/test_org_browse_manage_polish.py` replace `test_version_bump_target` body with:

```python
    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

(If `tests/test_corporate_workers_browse_polish.py` or similar still hard-pins `0.3.70`, apply the same regex pattern.)

- [ ] **Step 3: ADR-053** in `docs/decisions.md` table + detail:

| ADR-053 | 2026-09-11 | Corporate Browse clusters with narrow sub-tabs | Corporate Browse groups Strategy · Structure · People · Coordination; segmented cluster tabs below 720px; Manage section-head titles only; no URL sync or new APIs. |

Detail: context (long ungrouped Browse after ADR-051/052), decision (hybrid viewport), alternatives (always-tabs, CSS-only, extracted ClusterSwitch), consequences (0.3.71; deferred URL sync / Projects nit / Manage groups).

- [ ] **Step 4: UX / roadmap / handoff / README / spec status**

- `docs/11-user-experience.md`: note Companion v0.3.71 Corporate Browse clusters + narrow tabs; Manage section-heads.
- `docs/14-roadmap.md`: mark Corporate Browse clusters (0.3.71) done; update status banner and Immediate next to remaining owner-directed items (Projects list-row nit, URL sync, etc.).
- `docs/18-handoff.md`: local branch state for 0.3.71 (not deployed until finish).
- Spec status → **implemented in v0.3.71**.

- [ ] **Step 5: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all PASS; build OK; package version 0.3.71.

- [ ] **Step 6: Commit (explicit paths only)**

```bash
git add \
  company/__init__.py \
  companion/package.json \
  tests/test_org_browse_manage_polish.py \
  README.md \
  docs/11-user-experience.md \
  docs/14-roadmap.md \
  docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-11-corporate-browse-clusters-design.md
# plus any other pinned-version test files you actually edited
git commit -m "$(cat <<'EOF'
docs: Corporate Browse clusters and release 0.3.71

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Four clusters with fixed membership | Task 2 |
| Wide ≥720 labeled scroll with `cluster-head` | Task 2 |
| Narrow &lt;720 segmented tablist, default Strategy | Task 2 |
| Local cluster state, no URL | Task 2 |
| Keep cluster label in active pane | Task 2 |
| Manage section-heads for four titles | Task 2 |
| `.cluster-head` CSS | Task 2 |
| Source contracts + 0.3.71 | Tasks 1 + 3 |
| ADR-053 / UX / roadmap / handoff | Task 3 |
| Non-goals honored | Global constraints |

## Plan self-review

- No TBD placeholders; exact matchMedia string locked for contracts.
- Version pin migration for Org polish called out.
- Explicit `git add` paths; no `git add -A`.
