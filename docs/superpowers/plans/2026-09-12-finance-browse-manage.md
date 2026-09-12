# Finance Browse/Manage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finance ModeSwitch + hybrid ManageClusters (lists vs forms) with App-owned `mode`/`group` URL sync (v0.3.77).

**Architecture:** Add `finance` to `MODE_CAPABLE_TABS`. Mode-aware group tables (Browse vs Manage ids differ). Controlled `FinancePanel` with ModeSwitch + two ManageClusters. Extend parse/serialize so finance writes `group` in Browse too. Close-period stays Browse in-row.

**Tech Stack:** React companion, existing ModeSwitch/ManageClusters/urlState, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-finance-browse-manage-design.md` (owner-approved).
- Browse groups: `overview` (default), `invoices`, `adjustments`, `periods`.
- Manage groups: `invoice` (default), `adjustment`, `period`.
- Close period remains Browse Periods in-row. No new APIs. `replaceState` only.
- Version **0.3.77**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/finance-browse-manage` from current `main` before Task 1.
- Soften older exact version pins to `0\.3\.\d+`; exact `0.3.77` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `tests/test_finance_browse_manage.py` | Source contracts |
| `companion/src/urlState.ts` | Finance mode-capable + mode-aware groups |
| `companion/src/FinancePanel.tsx` | ModeSwitch + ManageClusters split |
| `companion/src/App.tsx` | Controlled Finance props; mode-change group reset |
| Docs + versions | **0.3.77**, ADR-059 |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_finance_browse_manage.py`

**Interfaces:**
- Consumes: none
- Produces: RED contracts Tasks 2–5 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/finance-browse-manage
```

- [ ] **Step 2: Write the test module**

```python
"""Finance Browse/Manage + URL sync (v0.3.77)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class FinanceBrowseManageTests(unittest.TestCase):
    def test_url_state_finance_mode_capable_and_groups(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn('"finance"', text)
        self.assertIn("MODE_CAPABLE_TABS", text)
        self.assertIn("defaultGroupFor", text)
        self.assertIn('"overview"', text)
        self.assertIn('"invoices"', text)
        self.assertIn('"adjustments"', text)
        self.assertIn('"periods"', text)
        self.assertIn('"invoice"', text)
        self.assertIn('"adjustment"', text)
        self.assertIn('"period"', text)
        # finance writes group in browse — look for finance-specific serialize path
        self.assertRegex(text, r"tab\s*===\s*[\"']finance[\"']")

    def test_finance_panel_mode_switch_and_clusters(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("ManageClusters", text)
        self.assertIn('label="Finance mode"', text)
        self.assertIn('ariaLabel="Finance browse groups"', text)
        self.assertIn('ariaLabel="Finance manage groups"', text)
        for title in ("Overview", "Invoices", "Adjustments", "Periods"):
            self.assertIn(f'label: "{title}"', text)
        for title in ("Invoice", "Adjustment", "Period"):
            # Manage cluster-head labels — use Create invoice style section heads inside
            pass
        self.assertIn('label: "Invoice"', text)
        self.assertIn('label: "Adjustment"', text)
        self.assertIn('label: "Period"', text)
        self.assertNotIn("not a second Browse/Manage layer", text)
        self.assertIn("manageGroup", text)
        self.assertIn("onManageGroupChange", text)
        self.assertIn("onModeChange", text)

    def test_app_wires_finance_controlled_props(self):
        text = (SRC / "App.tsx").read_text()
        # FinancePanel call site must pass mode/group handlers
        idx = text.find("<FinancePanel")
        self.assertGreaterEqual(idx, 0)
        snippet = text[idx : idx + 800]
        self.assertIn("mode={panelMode}", snippet)
        self.assertIn("onModeChange=", snippet)
        self.assertIn("manageGroup={manageGroup}", snippet)
        self.assertIn("onManageGroupChange=", snippet)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.77"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.77"', pkg)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_finance_browse_manage -v`

Expected: FAIL.

- [ ] **Step 4: Commit**

```bash
git add tests/test_finance_browse_manage.py
git commit -m "$(cat <<'EOF'
test(companion): Finance Browse/Manage contracts

EOF
)"
```

---

### Task 2: Extend urlState for finance

**Files:**
- Modify: `companion/src/urlState.ts`

**Interfaces:**
- Produces:

```ts
export function defaultGroupFor(tab: CompanionTab, mode: PanelMode): string | null;
export function allowedGroups(tab: CompanionTab, mode: PanelMode): ReadonlySet<string> | null;
// MODE_CAPABLE_TABS includes "finance"
// parse/serialize use mode-aware groups; finance browse also emits group
```

- [ ] **Step 1: Add finance to MODE_CAPABLE_TABS and mode-aware tables**

```ts
export const MODE_CAPABLE_TABS = new Set<CompanionTab>([
  "projects",
  "organization",
  "corporate",
  "workers",
  "finance",
]);

const MANAGE_GROUPS: Record<string, ReadonlySet<string>> = {
  organization: new Set(["catalog", "seats", "positions", "lookup"]),
  corporate: new Set(["goals", "structure", "coordination", "ops"]),
  projects: new Set(["enroll", "github"]),
  workers: new Set(["hosts", "token"]),
  finance: new Set(["invoice", "adjustment", "period"]),
};

const MANAGE_DEFAULT: Record<string, string> = {
  organization: "catalog",
  corporate: "goals",
  projects: "enroll",
  workers: "hosts",
  finance: "invoice",
};

const FINANCE_BROWSE_GROUPS = new Set([
  "overview",
  "invoices",
  "adjustments",
  "periods",
]);
const FINANCE_BROWSE_DEFAULT = "overview";

export function allowedGroups(
  tab: CompanionTab,
  mode: PanelMode,
): ReadonlySet<string> | null {
  if (tab === "finance") {
    return mode === "manage" ? MANAGE_GROUPS.finance : FINANCE_BROWSE_GROUPS;
  }
  if (mode !== "manage") return null;
  return MANAGE_GROUPS[tab] ?? null;
}

export function defaultGroupFor(
  tab: CompanionTab,
  mode: PanelMode,
): string | null {
  if (tab === "finance") {
    return mode === "manage" ? MANAGE_DEFAULT.finance : FINANCE_BROWSE_DEFAULT;
  }
  if (mode !== "manage") return null;
  return MANAGE_DEFAULT[tab] ?? null;
}

/** @deprecated Prefer defaultGroupFor(tab, "manage") */
export function defaultManageGroup(tab: CompanionTab): string | null {
  return defaultGroupFor(tab, "manage");
}
```

Keep `GROUPS` / `DEFAULT_GROUP` aliases pointing at MANAGE_* if other code imports them, or migrate call sites to `defaultGroupFor`.

- [ ] **Step 2: Update parseCompanionSearch group resolution**

```ts
  const rawGroup = (params.get("group") || "").trim();
  let group: string | null = null;
  if (capable) {
    const allowed = allowedGroups(tab, mode);
    const fallback = defaultGroupFor(tab, mode);
    if (allowed && fallback) {
      // Finance browse+manage; other tabs manage-only (allowed null on browse)
      group = allowed.has(rawGroup) ? rawGroup : fallback;
    }
  }
```

For non-finance browse, `allowedGroups` returns null → `group` stays null (cluster still handles corporate).

- [ ] **Step 3: Update serializeCompanionSearch**

```ts
  if (capable) {
    const allowed = allowedGroups(tab, mode);
    const fallback = defaultGroupFor(tab, mode);
    if (allowed && fallback) {
      const group =
        state.group && allowed.has(state.group) ? state.group : fallback;
      if (group !== fallback) params.set("group", group);
    }
  }
```

Remove the old `mode === "manage"`-only group block (replaced by above). Mode still only written when manage.

- [ ] **Step 4: Fix App call sites** that use `defaultManageGroup(tab)` — pass mode where needed (Task 4 will refine). For build, `defaultManageGroup` wrapper is enough.

- [ ] **Step 5: Verify**

```bash
.venv/bin/python -m unittest \
  tests.test_finance_browse_manage.FinanceBrowseManageTests.test_url_state_finance_mode_capable_and_groups \
  tests.test_mode_cluster_group_url_sync \
  -v
cd companion && npm run build
```

Expected: finance urlState test PASS; mode_cluster tests still PASS; build OK.

- [ ] **Step 6: Commit**

```bash
git add companion/src/urlState.ts companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): finance mode-capable URL group tables

EOF
)"
```

(Include App.tsx only if import/call updates are required for build.)

---

### Task 3: FinancePanel ModeSwitch + ManageClusters

**Files:**
- Modify: `companion/src/FinancePanel.tsx`

**Interfaces:**
- Consumes: controlled props from App (Task 4 may stub temporarily)

```ts
mode: PanelMode;
onModeChange: (mode: PanelMode) => void;
manageGroup: string;
onManageGroupChange: (id: string) => void;
```

- [ ] **Step 1: Add imports and props**; remove internal `subTab` state.

- [ ] **Step 2: Structure JSX**

```tsx
<section>
  <p className="lede">
    Persisted finance totals and lists in Browse; create invoice, adjustment, and
    period actions in Manage.
  </p>
  <ModeSwitch mode={mode} onChange={onModeChange} label="Finance mode" />
  {loadError && <p className="error">…</p>}

  {mode === "browse" && (
    <ManageClusters
      ariaLabel="Finance browse groups"
      activeGroupId={manageGroup}
      onActiveGroupIdChange={onManageGroupChange}
      defaultGroupId="overview"
      groups={[
        { id: "overview", label: "Overview", content: (<>{/* summary card */}</>) },
        { id: "invoices", label: "Invoices", content: (<>{/* list only */}</>) },
        { id: "adjustments", label: "Adjustments", content: (<>{/* list only */}</>) },
        { id: "periods", label: "Periods", content: (<>{/* list + close */}</>) },
      ]}
    />
  )}

  {mode === "manage" && (
    <ManageClusters
      ariaLabel="Finance manage groups"
      activeGroupId={manageGroup}
      onActiveGroupIdChange={onManageGroupChange}
      defaultGroupId="invoice"
      groups={[
        { id: "invoice", label: "Invoice", content: (<>{/* create form or scopeNotice */}</>) },
        { id: "adjustment", label: "Adjustment", content: (<>{/* form or notice */}</>) },
        { id: "period", label: "Period", content: (<>{/* form or notice */}</>) },
      ]}
    />
  )}
</section>
```

Use `section-head` for form titles (Create invoice, etc.) and `panel-empty` for empty lists (replace bare `muted` empty messages where they are empty-list copy).

- [ ] **Step 3: Keep handlers** (`createInvoice`, `postAdjustment`, `setBudgetPeriod`, `closePeriod`, `toggleInvoice`, loads) unchanged in behavior.

- [ ] **Step 4: Stub App props** if needed so build passes (temporary local state until Task 4). Prefer completing Task 4 next.

- [ ] **Step 5: Verify panel contract + build**

```bash
.venv/bin/python -m unittest \
  tests.test_finance_browse_manage.FinanceBrowseManageTests.test_finance_panel_mode_switch_and_clusters \
  -v
cd companion && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add companion/src/FinancePanel.tsx companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): Finance ModeSwitch and ManageClusters split

EOF
)"
```

---

### Task 4: App wires Finance + mode-change group reset

**Files:**
- Modify: `companion/src/App.tsx`

- [ ] **Step 1: Pass controlled props into FinancePanel** (same `panelMode` / `manageGroup` as other panels).

- [ ] **Step 2: Mode-change reset for finance groups**

When `panelMode` changes while `tab === "finance"`, set `manageGroup` to `defaultGroupFor("finance", panelMode)`.

Use a `modeRef` (mirror `tabRef`) so popstate applying mode+group together does not wipe:

```tsx
const modeRef = useRef(panelMode);
useEffect(() => {
  if (modeRef.current === panelMode) return;
  modeRef.current = panelMode;
  if (tab === "finance") {
    setManageGroup(defaultGroupFor("finance", panelMode) ?? "overview");
  } else if (MODE_CAPABLE_TABS.has(tab as CompanionTab) && panelMode === "manage") {
    setManageGroup(defaultGroupFor(tab as CompanionTab, "manage") ?? "catalog");
  }
}, [panelMode, tab]);
```

On popstate, set `modeRef.current = parsed.mode` before `setPanelMode`.

On tab change reset (existing tabRef effect), use `defaultGroupFor(tab, "browse")` for finance and `defaultGroupFor(tab, "manage")` only when appropriate — simplest: always reset to `defaultGroupFor(newTab, "browse")` since tab change also forces browse:

```tsx
setPanelMode("browse");
setCorporateCluster("strategy");
setManageGroup(defaultGroupFor(tab as CompanionTab, "browse")
  ?? defaultGroupFor(tab as CompanionTab, "manage")
  ?? "catalog");
```

For non-finance tabs, browse default is null → fall through to manage default for the stored group until Manage opens (existing behavior OK).

- [ ] **Step 3: Serialize** already includes finance browse groups via Task 2; ensure effect passes `group: manageGroup` whenever finance (browse or manage), not only when manage:

```tsx
group:
  tab === "finance" || panelMode === "manage" ? manageGroup : null,
```

- [ ] **Step 4: Verify**

```bash
.venv/bin/python -m unittest tests.test_finance_browse_manage tests.test_mode_cluster_group_url_sync tests.test_companion_url_sync -v
cd companion && npm run build
```

Expected: App wire test PASS; version may FAIL; build OK.

- [ ] **Step 5: Commit**

```bash
git add companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): wire Finance mode/group into App URL sync

EOF
)"
```

---

### Task 5: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.77`
- Modify: `companion/package.json` → `0.3.77`
- Soften exact pins in `tests/test_mode_cluster_group_url_sync.py` (and any other hard `0.3.76`) to `0\.3\.\d+`
- Modify: `README.md`, `docs/11-user-experience.md`, `docs/14-roadmap.md`, `docs/decisions.md` (ADR-059), `docs/18-handoff.md`
- Spec status → implemented

**Critical:** Explicit paths only. No `git add -A`.

- [ ] **Step 1–2:** Bump versions; soften old exact pins.

- [ ] **Step 3: ADR-059**

| ADR-059 | 2026-09-12 | Finance Browse/Manage with URL sync | Finance ModeSwitch + ManageClusters lists-vs-forms; finance in MODE_CAPABLE_TABS; group in browse+manage; close-period stays Browse; no new APIs. |

- [ ] **Step 4:** UX / roadmap / handoff / README / spec.

- [ ] **Step 5:** Full suite + companion build.

- [ ] **Step 6: Commit**

```bash
git add company/__init__.py companion/package.json \
  tests/test_mode_cluster_group_url_sync.py \
  README.md docs/11-user-experience.md docs/14-roadmap.md \
  docs/decisions.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-finance-browse-manage-design.md
git commit -m "$(cat <<'EOF'
docs: Finance Browse/Manage and release 0.3.77

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| finance MODE_CAPABLE + mode-aware groups | Task 2 |
| Browse/Manage group ids + omit defaults | Task 2 |
| FinancePanel ModeSwitch + ManageClusters | Task 3 |
| Close period Browse in-row | Task 3 |
| App controlled props + resets | Task 4 |
| Contracts + 0.3.77 + ADR-059 | Tasks 1 + 5 |
| Non-goals | Global constraints |

## Plan self-review

- Spec coverage mapped; mode-aware `defaultGroupFor` / `allowedGroups` avoid browse/manage id collision.
- Manage cluster labels **Invoice / Adjustment / Period** match Task 1 contracts (short labels; forms keep Create/Post/Set section-heads inside).
- Explicit `git add` paths; no `git add -A`.
