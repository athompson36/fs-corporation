# Companion URL Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deep-link the companion with `?tab=` and `?project=` via `replaceState` (v0.3.73) so refresh/bookmark restores tab and Projects selection.

**Architecture:** Pure parse/serialize helpers in `companion/src/urlState.ts`; `App.tsx` boots from search, writes with `history.replaceState`, clears unknown projects, clears selection when leaving Projects, re-parses on `popstate`. Pairing `#fs-pair=` unchanged. No React Router.

**Tech Stack:** React companion, TypeScript, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-companion-url-sync-design.md` (owner-approved).
- Params: `tab` (valid `Tab` or default `dashboard`); `project` only when `tab=projects` and selection set.
- History: `replaceState` only. Unknown project → clear selection, keep tab, no toast.
- Leaving Projects clears `selectedProject`. Do not strip `#fs-pair=` before redeem.
- No Browse/Manage in URL, no Corporate cluster in URL, no new APIs.
- Version **0.3.73**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/companion-url-sync` from current `main` before Task 1.
- Relax hard-pinned `0.3.72` version assertions to `0\.3\.\d+`; keep exact `0.3.73` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | Pure parse/serialize + Tab allowlist |
| `companion/src/App.tsx` | Boot, replaceState, unknown clear, leave-Projects clear, popstate |
| `tests/test_companion_url_sync.py` | Source contracts |
| `company/__init__.py` + `companion/package.json` | **0.3.73** |
| `tests/test_projects_list_row_clear_loading.py` | Relax version pin |
| Docs | UX, ADR-055, roadmap, handoff, README, spec status |

---

### Task 1: Failing source contracts

**Files:**
- Create: `tests/test_companion_url_sync.py`

**Interfaces:**
- Consumes: none
- Produces: RED tests Tasks 2–3 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/companion-url-sync
```

- [ ] **Step 2: Write the test module**

```python
"""Companion URL sync tab+project deep links (v0.3.73)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class CompanionUrlSyncTests(unittest.TestCase):
    def test_url_state_module_exports(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn("export type CompanionTab", text)
        self.assertIn("export function parseCompanionSearch", text)
        self.assertIn("export function serializeCompanionSearch", text)
        self.assertIn('"dashboard"', text)
        self.assertIn('"projects"', text)
        self.assertIn('"finance"', text)
        self.assertIn('"settings"', text)
        # project forces projects tab when present
        self.assertRegex(text, r"project[\s\S]{0,80}projects")

    def test_app_wires_url_sync(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn('from "./urlState"', text)
        self.assertIn("parseCompanionSearch", text)
        self.assertIn("serializeCompanionSearch", text)
        self.assertIn("history.replaceState", text)
        self.assertIn("popstate", text)
        self.assertIn("pairingTicketFromHash", text)
        self.assertIn("clearPairingHash", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.73"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.73"', pkg)
```

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_companion_url_sync -v`

Expected: FAIL (no `urlState.ts`; App not wired; version 0.3.72).

- [ ] **Step 4: Commit**

```bash
git add tests/test_companion_url_sync.py
git commit -m "$(cat <<'EOF'
test(companion): URL sync tab+project contracts

EOF
)"
```

---

### Task 2: urlState helpers + App wiring

**Files:**
- Create: `companion/src/urlState.ts`
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: Task 1 contracts
- Produces: green module/App tests (version may still fail until Task 3)
- Produces API:

```ts
export type CompanionTab =
  | "dashboard" | "projects" | "organization" | "corporate" | "workers"
  | "decisions" | "inbox" | "diagnostics" | "finance" | "settings";

export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
};

export function parseCompanionSearch(search: string): CompanionUrlState;
export function serializeCompanionSearch(state: CompanionUrlState): string; // returns "" or "?tab=…&project=…"
```

- [ ] **Step 1: Create `companion/src/urlState.ts`**

```ts
export type CompanionTab =
  | "dashboard"
  | "projects"
  | "organization"
  | "corporate"
  | "workers"
  | "decisions"
  | "inbox"
  | "diagnostics"
  | "finance"
  | "settings";

const VALID_TABS = new Set<CompanionTab>([
  "dashboard",
  "projects",
  "organization",
  "corporate",
  "workers",
  "decisions",
  "inbox",
  "diagnostics",
  "finance",
  "settings",
]);

export type CompanionUrlState = {
  tab: CompanionTab;
  project: string | null;
};

function isCompanionTab(value: string): value is CompanionTab {
  return VALID_TABS.has(value as CompanionTab);
}

/** Parse `window.location.search` (with or without leading `?`). */
export function parseCompanionSearch(search: string): CompanionUrlState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );
  const rawTab = (params.get("tab") || "").trim();
  const rawProject = (params.get("project") || "").trim();
  const project = rawProject || null;
  let tab: CompanionTab = isCompanionTab(rawTab) ? rawTab : "dashboard";
  if (project) tab = "projects";
  return { tab, project };
}

/** Build search string including leading `?`, or `""` if only default dashboard with no project. */
export function serializeCompanionSearch(state: CompanionUrlState): string {
  const params = new URLSearchParams();
  const tab = state.tab;
  const project =
    tab === "projects" && state.project ? state.project : null;
  params.set("tab", tab);
  if (project) params.set("project", project);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
```

Note: always writing `tab` (including `dashboard`) keeps deep links explicit; empty string only if somehow no params — with always-set `tab`, result is always `?tab=…`.

- [ ] **Step 2: Wire `App.tsx`**

1. Import:

```ts
import {
  parseCompanionSearch,
  serializeCompanionSearch,
  type CompanionTab,
} from "./urlState";
```

2. Align `Tab` with `CompanionTab` — either `type Tab = CompanionTab` or assert they match. Prefer:

```ts
type Tab = CompanionTab;
```

and remove the duplicate union if identical.

3. Initial state from URL (module-level once):

```ts
const initialUrl =
  typeof window !== "undefined"
    ? parseCompanionSearch(window.location.search)
    : { tab: "dashboard" as CompanionTab, project: null };
```

Then:

```ts
const [tab, setTab] = useState<Tab>(initialUrl.tab);
const [selectedProject, setSelectedProject] = useState<string | null>(initialUrl.project);
```

4. **replaceState effect** (after state declarations):

```ts
useEffect(() => {
  if (typeof window === "undefined") return;
  const next = serializeCompanionSearch({
    tab,
    project: tab === "projects" ? selectedProject : null,
  });
  const url = window.location.pathname + next + window.location.hash;
  const current = window.location.pathname + window.location.search + window.location.hash;
  if (url !== current) {
    window.history.replaceState(null, "", url);
  }
}, [tab, selectedProject]);
```

Preserve hash so `#fs-pair=` survives until `clearPairingHash` runs. When writing, if hash starts with `#fs-pair=`, still preserve it (pairing redeem path).

5. **Leave Projects clears selection:**

```ts
useEffect(() => {
  if (tab !== "projects" && selectedProject !== null) {
    setSelectedProject(null);
  }
}, [tab, selectedProject]);
```

6. **Unknown project clear** (after projects load):

```ts
useEffect(() => {
  if (!selectedProject || !projects.length) return;
  const known = projects.some((p) => String(p.id) === selectedProject);
  if (!known) setSelectedProject(null);
}, [projects, selectedProject]);
```

7. **popstate:**

```ts
useEffect(() => {
  function onPopState() {
    const parsed = parseCompanionSearch(window.location.search);
    setTab(parsed.tab);
    setSelectedProject(parsed.project);
  }
  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}, []);
```

Do not change `pairingTicketFromHash` / `clearPairingHash` behavior.

- [ ] **Step 3: Verify (expect version still FAIL)**

```bash
.venv/bin/python -m unittest \
  tests.test_companion_url_sync.CompanionUrlSyncTests.test_url_state_module_exports \
  tests.test_companion_url_sync.CompanionUrlSyncTests.test_app_wires_url_sync \
  -v
cd companion && npm run build
```

Expected: two tests PASS; version FAIL if run; build OK.

- [ ] **Step 4: Commit**

```bash
git add companion/src/urlState.ts companion/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(companion): sync tab and project selection to URL

EOF
)"
```

---

### Task 3: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.73`
- Modify: `companion/package.json` → `0.3.73`
- Modify: `tests/test_projects_list_row_clear_loading.py` — relax version pin to `0\.3\.\d+`
- Modify: `README.md` banner if needed
- Modify: `docs/11-user-experience.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/decisions.md` — ADR-055
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-12-companion-url-sync-design.md` → implemented

**Critical:** Stage **only** listed files. Do not `git add -A`. Do not stage `.vscode/` or `local repos/`.

- [ ] **Step 1: Bump versions** to **0.3.73**.

- [ ] **Step 2: Relax Projects list-row version assertion** to regex `0\.3\.\d+`.

- [ ] **Step 3: ADR-055**

| ADR-055 | 2026-09-12 | Companion URL sync for tab and project | Query `tab`/`project` with replaceState; unknown project clears silently; pairing hash unchanged; no Router. |

Detail: context (selection was React-only), decision (helpers + App wiring), alternatives (Router, hash routing, pushState), consequences (0.3.73; Manage/cluster URL deferred).

- [ ] **Step 4: UX / roadmap / handoff / README / spec status**

- UX: deep links `?tab=` / `?project=`; Clear/leave Projects drops project; bad id clears.
- Roadmap: mark URL sync done; Immediate next → Manage visual groups or other.
- Handoff: branch-local 0.3.73 until finish.
- Spec → **implemented in v0.3.73**.

- [ ] **Step 5: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all PASS; build OK; version 0.3.73.

- [ ] **Step 6: Commit (explicit paths only)**

```bash
git add \
  company/__init__.py \
  companion/package.json \
  tests/test_projects_list_row_clear_loading.py \
  README.md \
  docs/11-user-experience.md \
  docs/14-roadmap.md \
  docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-companion-url-sync-design.md
git commit -m "$(cat <<'EOF'
docs: companion URL sync and release 0.3.73

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| parse/serialize helpers | Task 2 |
| Boot from search; project forces projects | Task 2 |
| replaceState writes | Task 2 |
| Leave Projects clears selection | Task 2 |
| Unknown project clear | Task 2 |
| popstate re-parse | Task 2 |
| Pairing hash preserved | Task 2 (unchanged helpers) |
| Contracts + 0.3.73 | Tasks 1 + 3 |
| ADR-055 / docs | Task 3 |

## Plan self-review

- No TBD; exact helper code and App wiring steps.
- Version pin migration for 0.3.72 contracts called out.
- Explicit `git add` paths; no `git add -A`.
