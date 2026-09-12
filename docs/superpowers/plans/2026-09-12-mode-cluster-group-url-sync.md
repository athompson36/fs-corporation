# Mode/Cluster/Group URL Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deep-link Browse/Manage (`mode`), Corporate Browse clusters (`cluster`), and Manage visual groups (`group`) via App-owned state and extended `urlState` helpers (v0.3.76).

**Architecture:** Extend `CompanionUrlState` in `urlState.ts` with parse/serialize rules that omit defaults. App lifts `panelMode` / `corporateCluster` / `manageGroup`, one `replaceState` effect. Panels and `ManageClusters` become controlled. No pushState; pairing hash unchanged.

**Tech Stack:** React companion, existing `urlState.ts`, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-mode-cluster-group-url-sync-design.md` (owner-approved).
- Params: `mode=browse|manage` (omit browse), `cluster=` (omit strategy), `group=` (omit tab default).
- History: `replaceState` only. No React Router. No Finance ModeSwitch. No new APIs.
- Mode-capable tabs: `projects`, `organization`, `corporate`, `workers` only.
- Version **0.3.76**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/mode-cluster-group-url-sync` from current `main` before Task 1.
- Soft-pin older exact version contracts to `0\.3\.\d+` when they break; exact `0.3.76` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | Parse/serialize mode/cluster/group |
| `tests/test_mode_cluster_group_url_sync.py` | Source contracts |
| `companion/src/ManageClusters.tsx` | Controlled active group |
| `companion/src/{Org,Corporate,Projects,Workers}Panel.tsx` | Controlled props |
| `companion/src/App.tsx` | Own state; wire panels; replaceState |
| Docs + versions | **0.3.76**, ADR-058 |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_mode_cluster_group_url_sync.py`

**Interfaces:**
- Consumes: none
- Produces: RED contracts Tasks 2–5 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/mode-cluster-group-url-sync
```

- [ ] **Step 2: Write the test module**

```python
"""Mode/cluster/group companion URL sync (v0.3.76)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ModeClusterGroupUrlSyncTests(unittest.TestCase):
    def test_url_state_exports_mode_cluster_group(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn("mode", text)
        self.assertIn("cluster", text)
        self.assertIn("group", text)
        self.assertIn("PanelMode", text)
        self.assertIn('"browse"', text)
        self.assertIn('"manage"', text)
        self.assertIn('"strategy"', text)
        self.assertIn('"catalog"', text)
        self.assertIn('"goals"', text)
        self.assertIn('"enroll"', text)
        self.assertIn('"hosts"', text)
        self.assertIn("MODE_CAPABLE_TABS", text)
        self.assertIn("defaultManageGroup", text)
        self.assertIn("serializeCompanionSearch", text)
        self.assertIn("parseCompanionSearch", text)

    def test_manage_clusters_supports_controlled_active(self):
        text = (SRC / "ManageClusters.tsx").read_text()
        self.assertIn("activeGroupId", text)
        self.assertIn("onActiveGroupIdChange", text)

    def test_panels_accept_controlled_mode_props(self):
        for name, extras in (
            ("OrgPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
            ("CorporatePanel.tsx", ("mode", "onModeChange", "cluster", "onClusterChange", "manageGroup", "onManageGroupChange")),
            ("ProjectsPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
            ("WorkersPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
        ):
            text = (SRC / name).read_text()
            for marker in extras:
                self.assertIn(marker, text, f"{name} missing {marker}")

    def test_app_wires_mode_cluster_group(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("panelMode", text)
        self.assertIn("corporateCluster", text)
        self.assertIn("manageGroup", text)
        self.assertIn("onModeChange", text)
        self.assertIn("onClusterChange", text)
        self.assertIn("onManageGroupChange", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.76"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.76"', pkg)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_mode_cluster_group_url_sync -v`

Expected: FAIL (missing markers / 0.3.76).

- [ ] **Step 4: Commit**

```bash
git add tests/test_mode_cluster_group_url_sync.py
git commit -m "$(cat <<'EOF'
test(companion): mode/cluster/group URL sync contracts

EOF
)"
```

---

### Task 2: Extend urlState.ts

**Files:**
- Modify: `companion/src/urlState.ts`

**Interfaces:**
- Produces:

```ts
export type PanelMode = "browse" | "manage";
export type CorporateClusterId = "strategy" | "structure" | "people" | "coordination";
export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
  mode: PanelMode;           // always resolved; default browse
  cluster: CorporateClusterId; // always resolved; default strategy
  group: string | null;      // manage group id or null when browse / N/A
};
export const MODE_CAPABLE_TABS: ReadonlySet<CompanionTab>;
export function defaultManageGroup(tab: CompanionTab): string | null;
export function parseCompanionSearch(search: string): CompanionUrlState;
export function serializeCompanionSearch(state: CompanionUrlState): string;
```

- [ ] **Step 1: Expand types and tables**

Replace/extend `urlState.ts` so it includes (exact behavior):

```ts
import type { PanelMode } from "./ModeSwitch";
// Prefer re-export PanelMode from ModeSwitch OR define here and keep ModeSwitch as source —
// BINDING: define PanelMode in ModeSwitch.tsx (existing) and import it in urlState to avoid drift.

export type CorporateClusterId = "strategy" | "structure" | "people" | "coordination";

export const MODE_CAPABLE_TABS = new Set<CompanionTab>([
  "projects",
  "organization",
  "corporate",
  "workers",
]);

const CLUSTERS = new Set<CorporateClusterId>([
  "strategy",
  "structure",
  "people",
  "coordination",
]);

const GROUPS: Record<string, ReadonlySet<string>> = {
  organization: new Set(["catalog", "seats", "positions", "lookup"]),
  corporate: new Set(["goals", "structure", "coordination", "ops"]),
  projects: new Set(["enroll", "github"]),
  workers: new Set(["hosts", "token"]),
};

const DEFAULT_GROUP: Record<string, string> = {
  organization: "catalog",
  corporate: "goals",
  projects: "enroll",
  workers: "hosts",
};

export function defaultManageGroup(tab: CompanionTab): string | null {
  return DEFAULT_GROUP[tab] ?? null;
}

export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
  mode: PanelMode;
  cluster: CorporateClusterId;
  group: string | null;
};
```

- [ ] **Step 2: parseCompanionSearch**

```ts
export function parseCompanionSearch(search: string): CompanionUrlState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );
  const rawTab = (params.get("tab") || "").trim();
  const rawProject = (params.get("project") || "").trim();
  const project = rawProject || null;
  let tab: CompanionTab = isCompanionTab(rawTab) ? rawTab : "dashboard";
  if (project) tab = "projects";

  const capable = MODE_CAPABLE_TABS.has(tab);
  const rawMode = (params.get("mode") || "").trim();
  let mode: PanelMode = rawMode === "manage" ? "manage" : "browse";
  if (!capable) mode = "browse";

  const rawCluster = (params.get("cluster") || "").trim();
  let cluster: CorporateClusterId = CLUSTERS.has(rawCluster as CorporateClusterId)
    ? (rawCluster as CorporateClusterId)
    : "strategy";
  if (tab !== "corporate" || mode !== "browse") cluster = "strategy";

  const rawGroup = (params.get("group") || "").trim();
  let group: string | null = null;
  if (capable && mode === "manage") {
    const allowed = GROUPS[tab];
    const fallback = DEFAULT_GROUP[tab];
    group = allowed?.has(rawGroup) ? rawGroup : fallback;
  }

  return { tab, project, mode, cluster, group };
}
```

- [ ] **Step 3: serializeCompanionSearch**

```ts
export function serializeCompanionSearch(state: CompanionUrlState): string {
  const params = new URLSearchParams();
  const tab = state.tab;
  const project = tab === "projects" && state.project ? state.project : null;
  params.set("tab", tab);
  if (project) params.set("project", project);

  const capable = MODE_CAPABLE_TABS.has(tab);
  const mode: PanelMode = capable && state.mode === "manage" ? "manage" : "browse";
  if (capable && mode === "manage") params.set("mode", "manage");

  if (tab === "corporate" && mode === "browse") {
    const cluster = CLUSTERS.has(state.cluster) ? state.cluster : "strategy";
    if (cluster !== "strategy") params.set("cluster", cluster);
  }

  if (capable && mode === "manage") {
    const fallback = DEFAULT_GROUP[tab];
    const allowed = GROUPS[tab];
    const group =
      state.group && allowed?.has(state.group) ? state.group : fallback;
    if (group && group !== fallback) params.set("group", group);
  }

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
```

- [ ] **Step 4: Verify urlState contracts**

```bash
.venv/bin/python -m unittest \
  tests.test_mode_cluster_group_url_sync.ModeClusterGroupUrlSyncTests.test_url_state_exports_mode_cluster_group \
  -v
cd companion && npm run build
```

Expected: urlState test PASS (or FAIL only if ModeSwitch import path wrong); build OK.

- [ ] **Step 5: Commit**

```bash
git add companion/src/urlState.ts
git commit -m "$(cat <<'EOF'
feat(companion): parse/serialize mode cluster group URL state

EOF
)"
```

**Note:** Existing `tests/test_companion_url_sync.py` may still pass if it only checks export names. If soft/exact version pins fail later, Task 5 fixes them. If `CompanionUrlState` shape breaks App compile until Task 4, keep App compiling by temporarily spreading defaults in App call sites in Task 4 only — Task 2 may leave App temporarily type-broken until Task 4; prefer Task 2+4 same session or add temporary defaults in App serialize call in Task 2:

```ts
serializeCompanionSearch({
  tab,
  project: tab === "projects" ? selectedProject : null,
  mode: "browse",
  cluster: "strategy",
  group: null,
})
```

Do that minimal App touch in Task 2 **only if** needed for `npm run build` (explicit `git add companion/src/App.tsx` then). Prefer keeping Task 2 urlState-only and accepting build fail until Task 4 if tsc fails — but plan requires build OK in Step 4: **include the minimal serialize call-site patch in Task 2**.

---

### Task 3: Controlled ManageClusters + panels

**Files:**
- Modify: `companion/src/ManageClusters.tsx`
- Modify: `companion/src/OrgPanel.tsx`
- Modify: `companion/src/CorporatePanel.tsx`
- Modify: `companion/src/ProjectsPanel.tsx`
- Modify: `companion/src/WorkersPanel.tsx`

**Interfaces:**
- Consumes: App will pass props in Task 4
- Produces: controlled prop APIs

- [ ] **Step 1: ManageClusters controlled API**

```tsx
export type ManageClustersProps = {
  ariaLabel: string;
  groups: ManageClusterGroup[];
  defaultGroupId?: string;
  activeGroupId?: string;
  onActiveGroupIdChange?: (id: string) => void;
};

export function ManageClusters({
  ariaLabel,
  groups,
  defaultGroupId,
  activeGroupId,
  onActiveGroupIdChange,
}: ManageClustersProps) {
  const wide = useWideViewport();
  const initial =
    defaultGroupId && groups.some((g) => g.id === defaultGroupId)
      ? defaultGroupId
      : groups[0]?.id ?? "";
  const [uncontrolled, setUncontrolled] = useState(initial);
  const controlled = activeGroupId !== undefined;
  const active = controlled ? activeGroupId : uncontrolled;
  const setActive = (id: string) => {
    if (!controlled) setUncontrolled(id);
    onActiveGroupIdChange?.(id);
  };
  // ... render using active / setActive (same JSX as today)
}
```

- [ ] **Step 2: Panels — controlled mode (and cluster/group)**

For each panel, extend props:

```tsx
// Org / Projects / Workers
mode: PanelMode;
onModeChange: (mode: PanelMode) => void;
manageGroup: string;
onManageGroupChange: (id: string) => void;

// Corporate also:
cluster: CorporateClusterId;
onClusterChange: (id: CorporateClusterId) => void;
```

Remove internal `useState` for mode (all four). Corporate: remove internal cluster state; use props. Wire ModeSwitch to `onModeChange`. Pass ManageClusters:

```tsx
<ManageClusters
  activeGroupId={manageGroup}
  onActiveGroupIdChange={onManageGroupChange}
  defaultGroupId={...} // keep as hint for uncontrolled fallback; when controlled, activeGroupId wins
  ...
/>
```

Workers token force: when `setIssuedToken(...)` succeeds, also call `onManageGroupChange("token")`. Remove remount `key={issuedToken ? ...}` if controlled active id is enough; keep key only if needed for form reset — prefer no key remount when controlled.

- [ ] **Step 3: Verify panel contracts (App may still fail until Task 4)**

```bash
.venv/bin/python -m unittest \
  tests.test_mode_cluster_group_url_sync.ModeClusterGroupUrlSyncTests.test_manage_clusters_supports_controlled_active \
  tests.test_mode_cluster_group_url_sync.ModeClusterGroupUrlSyncTests.test_panels_accept_controlled_mode_props \
  -v
```

If `npm run build` fails on App missing props, that is expected until Task 4 — still run the unittest above. Optionally stub App props in Task 3 to keep build green; **prefer completing Task 4 immediately after**.

- [ ] **Step 4: Commit**

```bash
git add companion/src/ManageClusters.tsx companion/src/OrgPanel.tsx \
  companion/src/CorporatePanel.tsx companion/src/ProjectsPanel.tsx \
  companion/src/WorkersPanel.tsx
git commit -m "$(cat <<'EOF'
feat(companion): controlled mode cluster group panel props

EOF
)"
```

---

### Task 4: App owns state and wires panels

**Files:**
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: `parseCompanionSearch` / `serializeCompanionSearch` expanded state; panel controlled props

- [ ] **Step 1: State from initialUrl**

```tsx
const [panelMode, setPanelMode] = useState<PanelMode>(initialUrl.mode);
const [corporateCluster, setCorporateCluster] = useState<CorporateClusterId>(
  initialUrl.cluster,
);
const [manageGroup, setManageGroup] = useState<string>(
  initialUrl.group ?? defaultManageGroup(initialUrl.tab) ?? "catalog",
);
```

Import `PanelMode` from `ModeSwitch`, `CorporateClusterId` / `defaultManageGroup` / `MODE_CAPABLE_TABS` from `urlState`.

- [ ] **Step 2: replaceState effect deps**

```tsx
useEffect(() => {
  if (typeof window === "undefined") return;
  const next = serializeCompanionSearch({
    tab,
    project: tab === "projects" ? selectedProject : null,
    mode: panelMode,
    cluster: corporateCluster,
    group: panelMode === "manage" ? manageGroup : null,
  });
  // ... replaceState as today
}, [tab, selectedProject, panelMode, corporateCluster, manageGroup]);
```

- [ ] **Step 3: Reset when leaving capable tabs**

```tsx
useEffect(() => {
  if (!MODE_CAPABLE_TABS.has(tab as CompanionTab)) {
    if (panelMode !== "browse") setPanelMode("browse");
    return;
  }
}, [tab, panelMode]);
```

When `tab` changes among capable tabs, reset `manageGroup` to `defaultManageGroup(tab)` unless parsing from popstate just applied — simpler approach: on `tab` change, set `manageGroup` to `defaultManageGroup(tab) ?? "catalog"` and `panelMode` to `"browse"` and `corporateCluster` to `"strategy"` **except** when the change came from URL parse. Practical pattern used in this codebase: popstate sets all fields together; user tab clicks call `setTab` and a dedicated effect resets panel locals:

```tsx
useEffect(() => {
  // When tab changes, drop panel URL locals to defaults for the new tab.
  setPanelMode("browse");
  setCorporateCluster("strategy");
  setManageGroup(defaultManageGroup(tab as CompanionTab) ?? "catalog");
}, [tab]);
```

**Conflict:** this would wipe mode on every tab set including boot. Use a ref skip for initial mount, **or** only reset when `tab` changes after mount:

```tsx
const tabRef = useRef(tab);
useEffect(() => {
  if (tabRef.current === tab) return;
  tabRef.current = tab;
  setPanelMode("browse");
  setCorporateCluster("strategy");
  setManageGroup(defaultManageGroup(tab as CompanionTab) ?? "catalog");
}, [tab]);
```

popstate handler must update `tabRef.current` when applying parsed tab so it does not double-reset, **or** set mode/cluster/group in the same popstate callback after setTab:

```tsx
function onPopState() {
  const parsed = parseCompanionSearch(window.location.search);
  tabRef.current = parsed.tab;
  setTab(parsed.tab);
  setSelectedProject(parsed.project);
  setPanelMode(parsed.mode);
  setCorporateCluster(parsed.cluster);
  setManageGroup(parsed.group ?? defaultManageGroup(parsed.tab) ?? "catalog");
}
```

- [ ] **Step 4: Pass props into panels**

```tsx
<ProjectsPanel
  mode={panelMode}
  onModeChange={setPanelMode}
  manageGroup={manageGroup}
  onManageGroupChange={setManageGroup}
  ...
/>
// OrgPanel same
<CorporatePanel
  mode={panelMode}
  onModeChange={setPanelMode}
  cluster={corporateCluster}
  onClusterChange={setCorporateCluster}
  manageGroup={manageGroup}
  onManageGroupChange={setManageGroup}
  ...
/>
// WorkersPanel same + onManageGroupChange for token
```

- [ ] **Step 5: Verify**

```bash
.venv/bin/python -m unittest tests.test_mode_cluster_group_url_sync -v
.venv/bin/python -m unittest tests.test_companion_url_sync -v
cd companion && npm run build
```

Expected: mode/cluster/group tests PASS except exact version; companion_url_sync soft pins OK; build OK.

- [ ] **Step 6: Commit**

```bash
git add companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): App-owned mode cluster group URL sync

EOF
)"
```

---

### Task 5: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.76`
- Modify: `companion/package.json` → `0.3.76`
- Modify: `tests/test_companion_url_sync.py` — change exact `0.3.75` pin to soft `0\.3\.\d+` **or** update exact test to `0.3.76` (prefer: exact pin lives only in `test_mode_cluster_group_url_sync.py`; soften `test_version_bump_target_exact` in companion_url_sync to soft regex)
- Modify: `README.md`, `docs/11-user-experience.md`, `docs/14-roadmap.md`, `docs/decisions.md` (ADR-058), `docs/18-handoff.md`
- Modify: design spec status → implemented

**Critical:** Explicit paths only. No `git add -A`.

- [ ] **Step 1–2:** Bump versions; soften old exact pins.

- [ ] **Step 3: ADR-058**

| ADR-058 | 2026-09-12 | Mode/cluster/group companion URL sync | App-owned `mode`/`cluster`/`group` with replaceState; omit defaults; panels controlled; pairing unchanged. |

- [ ] **Step 4:** UX / roadmap / handoff / README / spec.

- [ ] **Step 5:** Full suite + companion build.

- [ ] **Step 6: Commit**

```bash
git add company/__init__.py companion/package.json \
  tests/test_companion_url_sync.py \
  README.md docs/11-user-experience.md docs/14-roadmap.md \
  docs/decisions.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-mode-cluster-group-url-sync-design.md
git commit -m "$(cat <<'EOF'
docs: mode/cluster/group URL sync and release 0.3.76

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| urlState mode/cluster/group parse+serialize | Task 2 |
| Omit browse/strategy/default group | Task 2 |
| Controlled ManageClusters | Task 3 |
| Four panels controlled | Task 3 |
| App state + replaceState + popstate | Task 4 |
| Workers token → group token | Task 3 |
| Contracts + 0.3.76 + ADR-058 | Tasks 1 + 5 |
| Non-goals | Global constraints |

## Plan self-review

- Spec coverage mapped; Org `!canManage` default `lookup` left as panel/App refinement in Task 4 (when passing manageGroup, if `!canManage` and groups only lookup, App may still hold `catalog` until Manage opens — acceptable if Org clamps via allowed groups on change; implementers: when `canManage` is false, prefer `setManageGroup("lookup")` if mode is manage).
- No TBD placeholders; explicit commit paths.
- Task 2 includes minimal App serialize patch if required for build.
