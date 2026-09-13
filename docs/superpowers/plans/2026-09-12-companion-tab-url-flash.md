# Companion Tab/Mode URL Flash Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship companion v0.3.81 so tab and Browse/Manage changes never briefly write a non-canonical `mode`/`cluster`/`group` to the address bar.

**Architecture:** Export pure `stateAfterTabChange` / `stateAfterModeChange` from `urlState.ts`. App batches sibling resets inside `selectTab` and `handlePanelModeChange` (same React event → one render → one `replaceState`). Extend the existing tsx harness to assert transition sequences. Remove the redundant tab/mode reset effects.

**Tech Stack:** Companion TypeScript/`urlState`, `npx tsx` harness, Python unittest source contracts, no new package.json dependency.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-companion-tab-url-flash-design.md` (owner-approved).
- Version **0.3.81**. Soften older exact `0.3.80` pins where this release owns the version contract; exact `0.3.81` only in this release’s contract.
- No Vitest; no new permanent companion test-runner dep; use `npx --yes tsx`.
- No desk changes, no Router/`pushState`, no pairing-hash changes, no Alembic, no new APIs.
- Do not rewrite org/corporate permission clamps unless a flash is observed.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/companion-tab-url-flash` from current `main` before Task 1.
- Work in-place on the feature branch (dirty tree may have untracked `local repos/`).

## File map

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | `stateAfterTabChange` / `stateAfterModeChange` |
| `companion/src/App.tsx` | `selectTab`; batch mode handler; drop reset effects; wire call sites |
| `companion/scripts/check-url-state.mts` | Transition sequence assertions |
| `tests/test_companion_tab_url_flash.py` | Source contracts + version **0.3.81** |
| `tests/test_url_state_behavior.py` | Already runs harness (no API change expected) |
| Docs + versions | ADR-063, UX/roadmap/handoff; `__version__` + `package.json` **0.3.81** |

---

### Task 1: RED contracts + transition helpers + harness

**Files:**
- Create: `tests/test_companion_tab_url_flash.py`
- Modify: `companion/src/urlState.ts`
- Modify: `companion/scripts/check-url-state.mts`
- Test: `tests/test_url_state_behavior.py` (existing runner; must stay green)

**Interfaces:**
- Consumes: `CompanionUrlState`, `defaultGroupFor`, `MODE_CAPABLE_TABS`, `serializeCompanionSearch`, `PanelMode`, `CompanionTab`
- Produces:
  - `stateAfterTabChange(prev: CompanionUrlState, nextTab: CompanionTab): CompanionUrlState`
  - `stateAfterModeChange(prev: CompanionUrlState, nextMode: PanelMode): CompanionUrlState`

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/companion-tab-url-flash
```

- [ ] **Step 2: Write failing source-contract module**

```python
"""Companion tab/mode URL flash fix (v0.3.81)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"
APP = SRC / "App.tsx"
URL = SRC / "urlState.ts"
HARNESS = ROOT / "companion" / "scripts" / "check-url-state.mts"


class CompanionTabUrlFlashTests(unittest.TestCase):
    def test_url_state_exports_transition_helpers(self):
        text = URL.read_text()
        self.assertRegex(text, r"export function stateAfterTabChange\(")
        self.assertRegex(text, r"export function stateAfterModeChange\(")

    def test_app_select_tab_batches_resets(self):
        text = APP.read_text()
        self.assertRegex(text, r"function selectTab|const selectTab")
        self.assertIn("stateAfterTabChange", text)
        self.assertIn("stateAfterModeChange", text)
        # User tab clicks must not use raw setTab(
        for needle in (
            'onClick={() => setTab("dashboard")}',
            "onClick={() => setTab(t)}",
            "onClick={() => setTab(lastWorkTab)}",
            "onClick={() => setTab(lastMoreTab)}",
            'onClick={() => setTab("organization")}',
            'onClick={() => setTab("finance")}',
            'onOpenDecisions={() => setTab("decisions")}',
            'onOpenInbox={() => setTab("inbox")}',
        ):
            self.assertNotIn(needle, text, f"raw setTab still used: {needle}")

    def test_no_tab_or_mode_reset_effects(self):
        text = APP.read_text()
        # Former tab-change effect pattern: tabRef.current === tab early return then setPanelMode("browse")
        self.assertNotRegex(
            text,
            r"if \(tabRef\.current === tab\) return;\s*tabRef\.current = tab;\s*setPanelMode\(\"browse\"\)",
            re.S,
        )
        self.assertNotRegex(
            text,
            r"if \(modeRef\.current === panelMode\) return;\s*modeRef\.current = panelMode;",
            re.S,
        )

    def test_harness_covers_tab_mode_transitions(self):
        text = HARNESS.read_text()
        self.assertIn("stateAfterTabChange", text)
        self.assertIn("stateAfterModeChange", text)
        self.assertIn("org-manage-to-finance", text)
        self.assertIn("finance-manage-to-dashboard", text)
        self.assertIn("corporate-people-to-org", text)
        self.assertIn("finance-periods-to-manage", text)
        self.assertIn("finance-adjustment-to-browse", text)

    def test_version_0_3_81(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.81"', init)
        self.assertIn('"version": "0.3.81"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run contracts — expect RED**

```bash
.venv/bin/python -m unittest tests.test_companion_tab_url_flash -v
```

Expected: FAIL (helpers / selectTab / version missing).

- [ ] **Step 4: Implement helpers in `urlState.ts`**

Append (after `defaultManageGroup`):

```ts
/** Canonical App URL state after a user tab change (always browse + strategy + default group). */
export function stateAfterTabChange(
  prev: CompanionUrlState,
  nextTab: CompanionTab,
): CompanionUrlState {
  const project = nextTab === "projects" ? prev.project : null;
  const mode: PanelMode = "browse";
  const cluster: CorporateClusterId = "strategy";
  const group =
    defaultGroupFor(nextTab, "browse") ?? defaultGroupFor(nextTab, "manage");
  return { tab: nextTab, project, mode, cluster, group };
}

/** Canonical App URL state after a Browse/Manage mode change on the current tab. */
export function stateAfterModeChange(
  prev: CompanionUrlState,
  nextMode: PanelMode,
): CompanionUrlState {
  const capable = MODE_CAPABLE_TABS.has(prev.tab);
  let mode: PanelMode = nextMode === "manage" ? "manage" : "browse";
  if (!capable) mode = "browse";

  let group = prev.group;
  if (prev.tab === "finance") {
    group = defaultGroupFor("finance", mode);
  } else if (capable && mode === "manage") {
    group = defaultGroupFor(prev.tab, "manage");
  }

  let cluster = prev.cluster;
  if (prev.tab !== "corporate" || mode !== "browse") {
    cluster = "strategy";
  }

  return {
    tab: prev.tab,
    project: prev.project,
    mode,
    cluster,
    group,
  };
}
```

- [ ] **Step 5: Extend harness with transition cases**

In `companion/scripts/check-url-state.mts`, import the new helpers and after the existing `cases` loop (keep those passing), add:

```ts
import {
  parseCompanionSearch,
  serializeCompanionSearch,
  stateAfterTabChange,
  stateAfterModeChange,
  type CompanionUrlState,
} from "../src/urlState.ts";

function assertTransition(
  id: string,
  startSearch: string,
  apply: (s: CompanionUrlState) => CompanionUrlState,
  expectSerialize: string,
) {
  const start = parseCompanionSearch(startSearch);
  const next = apply(start);
  const serialized = serializeCompanionSearch(next);
  eq(serialized, expectSerialize, id);
  // Single-step transition: applying helper once must equal end state (no mid-flight URL).
  const again = serializeCompanionSearch(apply(start));
  eq(again, expectSerialize, `${id} idempotent apply`);
  console.log(`ok - ${id}`);
}

const transitions: Array<{
  id: string;
  start: string;
  apply: (s: CompanionUrlState) => CompanionUrlState;
  expect: string;
}> = [
  {
    id: "org-manage-to-finance",
    start: "?tab=organization&mode=manage",
    apply: (s) => stateAfterTabChange(s, "finance"),
    expect: "?tab=finance",
  },
  {
    id: "finance-manage-to-dashboard",
    start: "?tab=finance&mode=manage",
    apply: (s) => stateAfterTabChange(s, "dashboard"),
    expect: "?tab=dashboard",
  },
  {
    id: "corporate-people-to-org",
    start: "?tab=corporate&cluster=people",
    apply: (s) => stateAfterTabChange(s, "organization"),
    expect: "?tab=organization",
  },
  {
    id: "finance-periods-to-manage",
    start: "?tab=finance&group=periods",
    apply: (s) => stateAfterModeChange(s, "manage"),
    expect: "?tab=finance&mode=manage",
  },
  {
    id: "finance-adjustment-to-browse",
    start: "?tab=finance&mode=manage&group=adjustment",
    apply: (s) => stateAfterModeChange(s, "browse"),
    expect: "?tab=finance",
  },
];

for (const t of transitions) {
  try {
    assertTransition(t.id, t.start, t.apply, t.expect);
  } catch (e) {
    failed += 1;
    console.error(`not ok - ${t.id}:`, e instanceof Error ? e.message : e);
  }
}
```

Ensure `failed` is declared before both loops (move `let failed = 0` above the first loop if needed) and the final exit check runs after transitions.

- [ ] **Step 6: Run harness + Task 1 contracts**

```bash
npx --yes tsx companion/scripts/check-url-state.mts
.venv/bin/python -m unittest tests.test_url_state_behavior tests.test_companion_tab_url_flash -v
```

Expected: harness PASS; `test_url_state_exports_transition_helpers` and harness marker tests PASS; App/version tests still FAIL.

- [ ] **Step 7: Commit** (if authorized)

```bash
git add \
  companion/src/urlState.ts \
  companion/scripts/check-url-state.mts \
  tests/test_companion_tab_url_flash.py \
  docs/superpowers/specs/2026-09-12-companion-tab-url-flash-design.md \
  docs/superpowers/plans/2026-09-12-companion-tab-url-flash.md
git commit -m "$(cat <<'EOF'
feat(companion): add tab/mode URL transition helpers and harness

EOF
)"
```

Include the design + plan only if they are still uncommitted on the branch.

---

### Task 2: Wire App batched navigation

**Files:**
- Modify: `companion/src/App.tsx`
- Test: `tests/test_companion_tab_url_flash.py`

**Interfaces:**
- Consumes: `stateAfterTabChange`, `stateAfterModeChange` from `./urlState`
- Produces: `selectTab`; updated `handlePanelModeChange`; no tab/mode reset effects

- [ ] **Step 1: Extend imports in `App.tsx`**

Add `stateAfterTabChange` and `stateAfterModeChange` to the existing `./urlState` import list.

- [ ] **Step 2: Add `selectTab` and update mode handler**

Place near `handlePanelModeChange` (after refs exist). Use helpers so App and harness share rules:

```tsx
  const selectTab = useCallback((next: Tab) => {
    const canonical = stateAfterTabChange(
      {
        tab: tab as CompanionTab,
        project: selectedProject,
        mode: panelMode,
        cluster: corporateCluster,
        group: manageGroup,
      },
      next as CompanionTab,
    );
    tabRef.current = canonical.tab;
    modeRef.current = canonical.mode;
    setTab(canonical.tab);
    setPanelMode(canonical.mode);
    setCorporateCluster(canonical.cluster);
    setManageGroup(canonical.group ?? "catalog");
    if (canonical.project === null) setSelectedProject(null);
    else setSelectedProject(canonical.project);
  }, [tab, selectedProject, panelMode, corporateCluster, manageGroup]);

  const handlePanelModeChange = useCallback(
    (mode: PanelMode) => {
      if (tab === "corporate" && !canManageOrg && mode === "manage") {
        setPanelMode("browse");
        modeRef.current = "browse";
        return;
      }
      const canonical = stateAfterModeChange(
        {
          tab: tab as CompanionTab,
          project: selectedProject,
          mode: panelMode,
          cluster: corporateCluster,
          group: manageGroup,
        },
        mode,
      );
      modeRef.current = canonical.mode;
      setPanelMode(canonical.mode);
      setCorporateCluster(canonical.cluster);
      setManageGroup(canonical.group ?? "catalog");
    },
    [tab, canManageOrg, selectedProject, panelMode, corporateCluster, manageGroup],
  );
```

Replace the existing `handlePanelModeChange` body with the above (keep the function name).

- [ ] **Step 3: Remove tab and mode reset effects**

Delete these two `useEffect` blocks entirely (the ones that sync `tabRef`/`modeRef` and call `setPanelMode("browse")` / `setManageGroup` on tab/mode change). Keep:

- URL `replaceState` effect
- org/corporate permission clamps
- project clear effect (or rely on `selectTab` clearing project — if `selectTab` always clears when `canonical.project === null`, the leave-projects effect is redundant for user nav but still useful if something else sets tab; **keep** the `if (tab !== "projects" && selectedProject !== null) setSelectedProject(null)` effect for safety)
- popstate (must still set `tabRef` / `modeRef` before state)

- [ ] **Step 4: Wire all user `setTab` call sites to `selectTab`**

Replace:

| Before | After |
|---|---|
| `onClick={() => setTab(t)}` (Work + More loops) | `onClick={() => selectTab(t)}` |
| `onOpenDecisions={() => setTab("decisions")}` | `onOpenDecisions={() => selectTab("decisions")}` |
| `onOpenInbox={() => setTab("inbox")}` | `onOpenInbox={() => selectTab("inbox")}` |
| `onClick={() => setTab("dashboard")}` | `onClick={() => selectTab("dashboard")}` |
| `onClick={() => setTab(lastWorkTab)}` | `onClick={() => selectTab(lastWorkTab)}` |
| `onClick={() => setTab("organization")}` | `onClick={() => selectTab("organization")}` |
| `onClick={() => setTab("finance")}` | `onClick={() => selectTab("finance")}` |
| `onClick={() => setTab(lastMoreTab)}` | `onClick={() => selectTab(lastMoreTab)}` |

Leave `setTab(parsed.tab)` inside `popstate` unchanged.

- [ ] **Step 5: Run Task 2 contracts + build**

```bash
.venv/bin/python -m unittest tests.test_companion_tab_url_flash tests.test_url_state_behavior -v
cd companion && npm run build
```

Expected: App contract tests PASS; `test_version_0_3_81` still FAIL; build OK.

- [ ] **Step 6: Commit** (if authorized)

```bash
git add companion/src/App.tsx
git commit -m "$(cat <<'EOF'
fix(companion): batch tab/mode URL state to stop one-frame flash

EOF
)"
```

---

### Task 3: Version 0.3.81 + docs

**Files:**
- Modify: `company/__init__.py`
- Modify: `companion/package.json`
- Modify: `docs/decisions.md` (ADR-063 + index row)
- Modify: `docs/11-user-experience.md` (one sentence on batched tab/mode URL writes)
- Modify: `docs/14-roadmap.md` (v0.3.81 status + checkbox + immediate next)
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-12-companion-tab-url-flash-design.md` (status → implemented)
- Soften: any exact `0.3.80` version pin that this release supersedes for companion lockstep (e.g. if a companion-oriented test pins `0.3.80`, use `0\.3\.\d+`; leave desk-only `test_desk_finance_polish` exact pin **or** soften to soft regex if the suite expects lockstep — prefer soft regex `0\.3\.\d+` in desk polish version asserts only if they fail; otherwise leave desk test asserting historical ship note — **do not** change desk polish behavior tests; if `test_version` in desk polish fails after bump, change that one assert to soft `0\.3\.\d+` matching companion finance polish pattern)

**Interfaces:**
- Consumes: Tasks 1–2 complete
- Produces: shipped docs + version **0.3.81**

- [ ] **Step 1: Bump versions**

`company/__init__.py`:

```python
__version__ = "0.3.81"
```

`companion/package.json`: `"version": "0.3.81"`.

If `tests/test_desk_finance_polish.py` asserts exact `0.3.80`, soften to:

```python
self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

- [ ] **Step 2: ADR-063**

Add index row and detail in `docs/decisions.md`:

- **Decision:** Batch companion tab/mode sibling resets in `selectTab` / `handlePanelModeChange` using `stateAfterTabChange` / `stateAfterModeChange`; remove lagging reset effects; extend tsx harness for transition sequences; no Router.
- **Consequences:** v0.3.81; desk init-time Finance disable and clamp timing remain follow-ups.

- [ ] **Step 3: UX / roadmap / handoff / spec status**

- UX: note that tab and mode changes write canonical search in one batched update (no one-frame manage flash).
- Roadmap: checkbox for companion tab/mode URL flash **0.3.81**; update status blurb; next = desk init-time Finance disable or owner-directed.
- Handoff: version **0.3.81**, branch tip placeholder until merge; verification commands; next tasks.
- Spec status line → **implemented in v0.3.81**.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build OK; package version 0.3.81.

- [ ] **Step 5: Commit** (if authorized)

```bash
git add company/__init__.py companion/package.json docs/decisions.md \
  docs/11-user-experience.md docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-companion-tab-url-flash-design.md \
  tests/test_companion_tab_url_flash.py tests/test_desk_finance_polish.py
git commit -m "$(cat <<'EOF'
docs: ship companion tab URL flash fix as 0.3.81

EOF
)"
```

Only stage paths that actually changed.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Batch tab resets via `selectTab` | 2 |
| Batch mode group reset via `handlePanelModeChange` | 2 |
| Dumb URL `replaceState` effect kept | 2 (unchanged writer) |
| Remove tab/mode reset effects | 2 |
| popstate does not use `selectTab` | 2 |
| Pure helpers in `urlState.ts` | 1 |
| Harness transition cases 1–5 | 1 |
| Python source contracts + version | 1 + 3 |
| Permission clamps left alone | 2 |
| Version 0.3.81 + ADR/docs | 3 |

## Plan self-review

- No TBD/placeholder steps; helper and App snippets are concrete.
- Harness ids match source-contract needles.
- `stateAfterTabChange` / `stateAfterModeChange` names consistent across tasks.
- Desk non-goal preserved; clamp rewrite out of scope.
