# Manage Visual Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hybrid Manage visual groups on Org, Corporate, Projects, and Workers via shared `useWideViewport` + `ManageClusters` (v0.3.74).

**Architecture:** Extract shared viewport hook and Manage cluster chrome. Each Manage panel passes group configs with existing form JSX as children. Corporate Browse keeps its cluster markup but imports the shared hook. No URL sync for Manage groups; no form/handler changes.

**Tech Stack:** React companion, existing `.cluster-head` / `.segmented` CSS, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-manage-visual-groups-design.md` (owner-approved).
- Hybrid: wide ≥720px labeled scroll; narrow &lt;720px group tabs; exact `matchMedia("(min-width: 720px)")`.
- Memberships fixed in the spec (Org Catalog/Seats/Positions/Lookup; Corporate Goals/Structure/Coordination/Ops; Projects Enroll/GitHub; Workers Hosts/Token).
- No URL sync for Manage groups; no Browse regrouping; no new APIs.
- Version **0.3.74**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/manage-visual-groups` from current `main` before Task 1.
- Relax hard-pinned `0.3.73` version assertions to `0\.3\.\d+`; keep exact `0.3.74` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `tests/test_manage_visual_groups.py` | Source contracts |
| `companion/src/useWideViewport.ts` | Shared hook |
| `companion/src/ManageClusters.tsx` | Shared Manage chrome |
| `companion/src/CorporatePanel.tsx` | Browse uses shared hook; Manage groups |
| `companion/src/OrgPanel.tsx` | Manage groups |
| `companion/src/ProjectsPanel.tsx` | Manage groups |
| `companion/src/WorkersPanel.tsx` | Manage groups + section-heads |
| `companion/src/styles.css` | `.manage-cluster-tabs` if needed |
| Docs + versions | **0.3.74**, ADR-056 |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_manage_visual_groups.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Tasks 2–4 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/manage-visual-groups
```

- [ ] **Step 2: Write the test module**

```python
"""Manage visual groups hybrid chrome (v0.3.74)."""
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


class ManageVisualGroupsTests(unittest.TestCase):
    def test_shared_modules_exist(self):
        hook = (SRC / "useWideViewport.ts").read_text()
        self.assertIn('matchMedia("(min-width: 720px)")', hook)
        self.assertIn("export function useWideViewport", hook)
        chrome = (SRC / "ManageClusters.tsx").read_text()
        self.assertIn("export function ManageClusters", chrome)
        self.assertIn("manage-cluster-tabs", chrome)
        self.assertIn('role="tablist"', chrome)
        self.assertIn("useWideViewport", chrome)
        self.assertRegex(
            chrome,
            r'className="cluster-head"[\s\S]{0,80}<h2>\{group\.label\}</h2>',
        )

    def test_org_manage_group_labels(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        self.assertIn("ManageClusters", text)
        self.assertIn('ariaLabel="Organization manage groups"', text)
        for title in ("Catalog", "Seats", "Positions", "Lookup"):
            self.assertIn(f'label: "{title}"', text)

    def test_corporate_manage_group_labels(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        self.assertIn("ManageClusters", text)
        self.assertIn('ariaLabel="Corporate manage groups"', text)
        for title in ("Goals", "Structure", "Coordination", "Ops"):
            self.assertIn(f'label: "{title}"', text)
        self.assertIn('from "./useWideViewport"', text)
        self.assertNotRegex(text, r"function useWideViewport\s*\(")

    def test_projects_and_workers_manage_groups(self):
        projects = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("ManageClusters", projects)
        self.assertIn('ariaLabel="Projects manage groups"', projects)
        for title in ("Enroll", "GitHub"):
            self.assertIn(f'label: "{title}"', projects)
        workers = (SRC / "WorkersPanel.tsx").read_text()
        self.assertIn("ManageClusters", workers)
        self.assertIn('ariaLabel="Workers manage groups"', workers)
        for title in ("Hosts", "Token"):
            self.assertIn(f'label: "{title}"', workers)
        self.assertTrue(_section_head_wraps_h2(workers, "Create worker host"))
        self.assertTrue(_section_head_wraps_h2(workers, "Worker host token"))
        self.assertIn("No token issued yet.", workers)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.74"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.74"', pkg)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_manage_visual_groups -v`

Expected: FAIL (missing modules / ManageClusters / labels / 0.3.74).

- [ ] **Step 4: Commit**

```bash
git add tests/test_manage_visual_groups.py
git commit -m "$(cat <<'EOF'
test(companion): Manage visual groups contracts

EOF
)"
```

---

### Task 2: Shared hook + ManageClusters + Corporate Browse migrate

**Files:**
- Create: `companion/src/useWideViewport.ts`
- Create: `companion/src/ManageClusters.tsx`
- Modify: `companion/src/CorporatePanel.tsx` (Browse hook only in this task — Manage wiring is Task 3)
- Modify: `companion/src/styles.css` (add `.manage-cluster-tabs { margin: 0 0 0.65rem; }` mirroring `.corporate-cluster-tabs`)

**Interfaces:**
- Produces:

```ts
// useWideViewport.ts
export function useWideViewport(): boolean;

// ManageClusters.tsx
export type ManageClusterGroup = {
  id: string;
  label: string;
  content: React.ReactNode;
};

export type ManageClustersProps = {
  ariaLabel: string;
  groups: ManageClusterGroup[];
  defaultGroupId?: string;
};

export function ManageClusters(props: ManageClustersProps): JSX.Element;
```

- [ ] **Step 1: Create `useWideViewport.ts`** — move the exact CorporatePanel implementation (literal `matchMedia("(min-width: 720px)")`).

- [ ] **Step 2: Create `ManageClusters.tsx`**

```tsx
import { useState, type ReactNode } from "react";
import { useWideViewport } from "./useWideViewport";

export type ManageClusterGroup = {
  id: string;
  label: string;
  content: ReactNode;
};

export type ManageClustersProps = {
  ariaLabel: string;
  groups: ManageClusterGroup[];
  defaultGroupId?: string;
};

export function ManageClusters({ ariaLabel, groups, defaultGroupId }: ManageClustersProps) {
  const wide = useWideViewport();
  const initial = defaultGroupId && groups.some((g) => g.id === defaultGroupId)
    ? defaultGroupId
    : groups[0]?.id ?? "";
  const [active, setActive] = useState(initial);

  return (
    <>
      {!wide && (
        <div className="segmented manage-cluster-tabs" role="tablist" aria-label={ariaLabel}>
          {groups.map((group) => (
            <button
              key={group.id}
              type="button"
              role="tab"
              aria-selected={active === group.id}
              className={active === group.id ? "active" : ""}
              onClick={() => setActive(group.id)}
            >
              {group.label}
            </button>
          ))}
        </div>
      )}
      {groups.map((group) =>
        (wide || active === group.id) ? (
          <div key={group.id} className="manage-cluster" data-cluster={group.id}>
            <div className="cluster-head">
              <h2>{group.label}</h2>
            </div>
            {group.content}
          </div>
        ) : null,
      )}
    </>
  );
}
```

- [ ] **Step 3: Corporate Browse** — delete local `useWideViewport`; `import { useWideViewport } from "./useWideViewport";`. Leave Browse cluster JSX unchanged. Do **not** wrap Manage yet.

- [ ] **Step 4: CSS** — add `.manage-cluster-tabs { margin: 0 0 0.65rem; }`.

- [ ] **Step 5: Verify shared tests**

```bash
.venv/bin/python -m unittest \
  tests.test_manage_visual_groups.ManageVisualGroupsTests.test_shared_modules_exist \
  -v
cd companion && npm run build
```

Expected: shared test PASS (or FAIL only on panel tests if run together); build OK.

- [ ] **Step 6: Commit**

```bash
git add companion/src/useWideViewport.ts companion/src/ManageClusters.tsx \
  companion/src/CorporatePanel.tsx companion/src/styles.css
git commit -m "$(cat <<'EOF'
feat(companion): extract ManageClusters and useWideViewport

EOF
)"
```

---

### Task 3: Wire Manage groups on all four panels

**Files:**
- Modify: `companion/src/OrgPanel.tsx`
- Modify: `companion/src/CorporatePanel.tsx`
- Modify: `companion/src/ProjectsPanel.tsx`
- Modify: `companion/src/WorkersPanel.tsx`

**Interfaces:**
- Consumes: `ManageClusters` from Task 2
- Produces: green panel label contracts

- [ ] **Step 1: OrgPanel Manage** — Inside `mode === "manage"`, wrap forms in:

```tsx
<ManageClusters
  ariaLabel="Organization manage groups"
  defaultGroupId="catalog"
  groups={[
    { id: "catalog", label: "Catalog", content: (<>{/* create dept, reorder, activate */}</>) },
    { id: "seats", label: "Seats", content: (<>{/* appoint, vacate, assign, release */}</>) },
    { id: "positions", label: "Positions", content: (<>{/* create position */}</>) },
    { id: "lookup", label: "Lookup", content: (<>{/* worker card */}</>) },
  ]}
/>
```

Keep `canManage` gating: Catalog/Seats/Positions only when `canManage`; Lookup always. Prefer two `ManageClusters` or pass empty content — cleaner: always show Lookup; nest `canManage` groups only when true:

```tsx
{canManage && (
  <ManageClusters ariaLabel="Organization manage groups" defaultGroupId="catalog" groups={[...catalog seats positions]} />
)}
{/* Lookup always */}
<ManageClusters ariaLabel="Organization manage lookup" defaultGroupId="lookup" groups={[lookup only]} />
```

**Spec wants one chrome with four groups.** When `!canManage`, still render ManageClusters with only Lookup (single group — tabs hide when one group or still show Lookup alone). Implementation: build `groups` array conditionally:

```tsx
const groups = [];
if (canManage) { groups.push(catalog, seats, positions); }
groups.push(lookup);
<ManageClusters ariaLabel="Organization manage groups" defaultGroupId={canManage ? "catalog" : "lookup"} groups={groups} />
```

- [ ] **Step 2: CorporatePanel Manage** — Wrap the four Manage blocks:

```tsx
groups={[
  { id: "goals", label: "Goals", content: /* Create objective */ },
  { id: "structure", label: "Structure", content: /* Propose division */ },
  { id: "coordination", label: "Coordination", content: /* cross-dept */ },
  { id: "ops", label: "Ops", content: /* Corporate operations */ },
]}
ariaLabel="Corporate manage groups"
defaultGroupId="goals"
```

- [ ] **Step 3: ProjectsPanel Manage** — Enroll + GitHub groups; `ariaLabel="Projects manage groups"`; `defaultGroupId="enroll"`.

- [ ] **Step 4: WorkersPanel Manage** — Hosts + Token; section-head for Create worker host and Worker host token; Token empty: `<p className="panel-empty">No token issued yet.</p>` when `!issuedToken`; `ariaLabel="Workers manage groups"`; `defaultGroupId="hosts"`.

- [ ] **Step 5: Verify**

```bash
.venv/bin/python -m unittest \
  tests.test_manage_visual_groups.ManageVisualGroupsTests.test_org_manage_group_labels \
  tests.test_manage_visual_groups.ManageVisualGroupsTests.test_corporate_manage_group_labels \
  tests.test_manage_visual_groups.ManageVisualGroupsTests.test_projects_and_workers_manage_groups \
  tests.test_corporate_browse_clusters \
  -v
cd companion && npm run build
```

Expected: panel tests PASS; corporate browse still OK; version may FAIL.

- [ ] **Step 6: Commit**

```bash
git add companion/src/OrgPanel.tsx companion/src/CorporatePanel.tsx \
  companion/src/ProjectsPanel.tsx companion/src/WorkersPanel.tsx
git commit -m "$(cat <<'EOF'
feat(companion): wire Manage visual groups on Work/People panels

EOF
)"
```

---

### Task 4: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.74`
- Modify: `companion/package.json` → `0.3.74`
- Modify: `tests/test_companion_url_sync.py` — relax version pin to `0\.3\.\d+`
- Modify: `README.md`, `docs/11-user-experience.md`, `docs/14-roadmap.md`, `docs/decisions.md` (ADR-056), `docs/18-handoff.md`
- Modify: spec status → implemented

**Critical:** Explicit paths only. No `git add -A`.

- [ ] **Step 1–2:** Bump versions; relax URL sync version pin.

- [ ] **Step 3: ADR-056**

| ADR-056 | 2026-09-12 | Manage visual groups with shared hybrid chrome | Org/Corporate/Projects/Workers Manage use ManageClusters + shared useWideViewport; no URL sync or API changes. |

- [ ] **Step 4:** UX / roadmap / handoff / README / spec.

- [ ] **Step 5:** Full suite + companion build.

- [ ] **Step 6:** Commit with message `docs: Manage visual groups and release 0.3.74`.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Shared useWideViewport + ManageClusters | Task 2 |
| Corporate Browse uses shared hook | Task 2 |
| Org/Corporate/Projects/Workers memberships | Task 3 |
| Workers section-heads + token empty | Task 3 |
| Contracts + 0.3.74 + ADR-056 | Tasks 1 + 4 |
| Non-goals | Global constraints |

## Plan self-review

- Panel contracts assert `label: "…"` literals; ManageClusters owns `cluster-head` + `{group.label}`.
- Explicit `git add` paths; no `git add -A`.
- Four Manage memberships match the approved spec.
