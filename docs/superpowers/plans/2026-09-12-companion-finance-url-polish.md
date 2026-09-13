# Companion Finance URL Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship companion polish v0.3.79 — remove dead Close-period focus, mode-aware cold-load/popstate group fallback, and a minimal tsx behavioral harness for `urlState` parse/serialize.

**Architecture:** Keep `urlState.ts` as the source of truth. Add `companion/scripts/check-url-state.mts` that imports parse/serialize and asserts a fixed case table. Python unittest shells out via `npx --yes tsx`. Fix `FinancePanel.closePeriod` and `App` init/popstate fallbacks to use `defaultGroupFor(tab, mode)`.

**Tech Stack:** Companion TypeScript/`urlState`, `npx tsx`, Python unittest, no new package.json dependency.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-companion-finance-url-polish-design.md` (owner-approved).
- Version **0.3.79**. Soften older exact `0.3.78` pins to `0\.3\.\d+`; exact `0.3.79` only in this release’s contract.
- No Vitest; no new permanent companion test-runner dep; use `npx --yes tsx`.
- No desk polish, no new APIs, no ModeSwitch redesign, no Alembic.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/companion-finance-url-polish` from current `main` before Task 1.

## File map

| Path | Role |
|---|---|
| `tests/test_companion_finance_url_polish.py` | Source contracts + version **0.3.79** |
| `tests/test_url_state_behavior.py` | Subprocess harness runner |
| `companion/scripts/check-url-state.mts` | Behavioral parse/serialize assertions |
| `companion/src/FinancePanel.tsx` | Remove dead focus / redundant group change |
| `companion/src/App.tsx` | Cold-load + popstate `defaultGroupFor` |
| Docs + versions | ADR-061, **0.3.79** |

---

### Task 1: Failing source + behavior contracts

**Files:**
- Create: `tests/test_companion_finance_url_polish.py`
- Create: `tests/test_url_state_behavior.py` (runner only; harness file comes in Task 2)

**Interfaces:**
- Consumes: none
- Produces: RED contracts Tasks 2–5 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/companion-finance-url-polish
```

- [ ] **Step 2: Write source-contract module**

```python
"""Companion finance URL polish (v0.3.79)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class CompanionFinanceUrlPolishTests(unittest.TestCase):
    def test_finance_close_period_no_dead_focus(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        # closePeriod must not focus Manage period input or force group=periods
        close_idx = text.find("async function closePeriod")
        self.assertGreater(close_idx, -1)
        # slice until next top-level async function or export end — use next "async function"
        rest = text[close_idx:]
        next_fn = rest.find("\n  async function ", 10)
        next_fn2 = rest.find("\n  function ", 10)
        ends = [i for i in (next_fn, next_fn2) if i > 0]
        chunk = rest[: min(ends)] if ends else rest[:800]
        self.assertNotIn("periodStartRef.current?.focus", chunk)
        self.assertNotIn('onManageGroupChange("periods")', chunk)
        self.assertIn("period_end", chunk)

    def test_app_cold_load_and_popstate_use_default_group_for(self):
        text = (SRC / "App.tsx").read_text()
        self.assertRegex(
            text,
            r"initialUrl\.group\s*\?\?\s*defaultGroupFor\(\s*initialUrl\.tab\s*,\s*initialUrl\.mode\s*\)",
        )
        self.assertRegex(
            text,
            r"parsed\.group\s*\?\?\s*defaultGroupFor\(\s*parsed\.tab\s*,\s*parsed\.mode\s*\)",
        )
        # Must not keep manage-biased cold-load fallback as the primary path
        self.assertNotRegex(
            text,
            r"initialUrl\.group\s*\?\?\s*defaultManageGroup\(\s*initialUrl\.tab\s*\)",
        )
        self.assertNotRegex(
            text,
            r"parsed\.group\s*\?\?\s*defaultManageGroup\(\s*parsed\.tab\s*\)",
        )

    def test_version_0_3_79(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.79"', init)
        self.assertIn('"version": "0.3.79"', pkg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Write behavior runner (expects harness to exist)**

```python
"""Behavioral urlState parse/serialize via tsx harness (v0.3.79)."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "companion" / "scripts" / "check-url-state.mts"


class UrlStateBehaviorTests(unittest.TestCase):
    def test_check_url_state_harness(self):
        self.assertTrue(HARNESS.is_file(), f"missing harness {HARNESS}")
        npx = shutil.which("npx")
        self.assertIsNotNone(npx, "npx not found — install Node.js to run companion URL harness")
        result = subprocess.run(
            [npx, "--yes", "tsx", str(HARNESS)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            self.fail(
                "urlState harness failed\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run tests to verify RED**

```bash
.venv/bin/python -m unittest tests.test_companion_finance_url_polish tests.test_url_state_behavior -v
```

Expected: FAIL — missing harness and/or still has dead focus / `defaultManageGroup` / version 0.3.78.

- [ ] **Step 5: Commit**

```bash
git add tests/test_companion_finance_url_polish.py tests/test_url_state_behavior.py
git commit -m "$(cat <<'EOF'
test: companion finance URL polish contracts (0.3.79)

EOF
)"
```

---

### Task 2: URL harness script (GREEN behavior tests)

**Files:**
- Create: `companion/scripts/check-url-state.mts`

**Interfaces:**
- Consumes: `parseCompanionSearch`, `serializeCompanionSearch` from `companion/src/urlState.ts`
- Produces: exit 0 harness Task 1’s behavior test expects

- [ ] **Step 1: Write the harness**

Create `companion/scripts/check-url-state.mts`:

```typescript
import {
  parseCompanionSearch,
  serializeCompanionSearch,
  type CompanionUrlState,
} from "../src/urlState.ts";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

function eq(actual: string, expected: string, label: string) {
  assert(actual === expected, `${label}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
}

function roundTrip(search: string, label: string) {
  const parsed = parseCompanionSearch(search);
  const serialized = serializeCompanionSearch(parsed);
  const again = serializeCompanionSearch(parseCompanionSearch(serialized));
  eq(again, serialized, `${label} stable serialize`);
  return { parsed, serialized };
}

const cases: Array<{
  name: string;
  input: string;
  expectSerialize: string;
  check?: (s: CompanionUrlState) => void;
}> = [
  {
    name: "finance browse defaults",
    input: "?tab=finance",
    expectSerialize: "?tab=finance",
    check: (s) => {
      assert(s.mode === "browse", "mode browse");
      assert(s.group === "overview", "group overview");
    },
  },
  {
    name: "finance browse periods",
    input: "?tab=finance&group=periods",
    expectSerialize: "?tab=finance&group=periods",
    check: (s) => assert(s.group === "periods", "group periods"),
  },
  {
    name: "finance manage default omits group",
    input: "?tab=finance&mode=manage",
    expectSerialize: "?tab=finance&mode=manage",
    check: (s) => {
      assert(s.mode === "manage", "mode manage");
      assert(s.group === "invoice", "group invoice");
    },
  },
  {
    name: "finance manage adjustment",
    input: "?tab=finance&mode=manage&group=adjustment",
    expectSerialize: "?tab=finance&mode=manage&group=adjustment",
    check: (s) => assert(s.group === "adjustment", "group adjustment"),
  },
  {
    name: "invalid finance browse group → overview",
    input: "?tab=finance&group=not-a-group",
    expectSerialize: "?tab=finance",
    check: (s) => assert(s.group === "overview", "coerced overview"),
  },
  {
    name: "projects manage default omits group",
    input: "?tab=projects&mode=manage",
    expectSerialize: "?tab=projects&mode=manage",
    check: (s) => assert(s.group === "enroll", "group enroll"),
  },
];

let failed = 0;
for (const c of cases) {
  try {
    const { parsed, serialized } = roundTrip(c.input, c.name);
    eq(serialized, c.expectSerialize, c.name);
    c.check?.(parsed);
    console.log(`ok - ${c.name}`);
  } catch (e) {
    failed += 1;
    console.error(`not ok - ${c.name}:`, e instanceof Error ? e.message : e);
  }
}

if (failed) {
  console.error(`${failed} case(s) failed`);
  process.exit(1);
}
console.log("all urlState cases passed");
```

- [ ] **Step 2: Run harness directly**

```bash
npx --yes tsx companion/scripts/check-url-state.mts
```

Expected: exit 0, “all urlState cases passed”.

- [ ] **Step 3: Run behavior unittest**

```bash
.venv/bin/python -m unittest tests.test_url_state_behavior -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add companion/scripts/check-url-state.mts
git commit -m "$(cat <<'EOF'
test(companion): add urlState behavioral tsx harness

EOF
)"
```

---

### Task 3: Fix Close-period dead focus

**Files:**
- Modify: `companion/src/FinancePanel.tsx`

**Interfaces:**
- Consumes: Task 1 `test_finance_close_period_no_dead_focus`
- Produces: Close-period keeps prefill only

- [ ] **Step 1: Edit `closePeriod`**

Replace the success body so it no longer changes group or focuses. Keep prefill + reload:

```typescript
  async function closePeriod(period: Record<string, unknown>) {
    if (!window.confirm("Close this budget period? Snapshot will be frozen.")) return;
    await runAction(
      `finance-close-${String(period.id)}`,
      "Period closed.",
      async () => {
        await api.closeFinanceBudgetPeriod(String(period.id));
        setPeriodStart(toDatetimeLocalValue(String(period.period_end)));
        await loadAll();
      },
    );
  }
```

- [ ] **Step 2: Remove unused `periodStartRef` if nothing else references it**

Search `FinancePanel.tsx` for `periodStartRef`. If only the declaration and the removed focus remain:

1. Delete `const periodStartRef = useRef<HTMLInputElement>(null);`
2. On the Manage period start input, remove `ref={periodStartRef}` (keep `id="finance-period-start"`).
3. If `useRef` is then unused in imports, drop it from the React import list.

- [ ] **Step 3: Run focused source test**

```bash
.venv/bin/python -m unittest \
  tests.test_companion_finance_url_polish.CompanionFinanceUrlPolishTests.test_finance_close_period_no_dead_focus \
  -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add companion/src/FinancePanel.tsx
git commit -m "$(cat <<'EOF'
fix(companion): drop dead Close-period focus after Browse close

EOF
)"
```

---

### Task 4: Cold-load / popstate `defaultGroupFor`

**Files:**
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: Task 1 `test_app_cold_load_and_popstate_use_default_group_for`
- Produces: mode-aware group fallback

- [ ] **Step 1: Fix initial state**

Replace:

```typescript
  const [manageGroup, setManageGroup] = useState<string>(
    initialUrl.group ?? defaultManageGroup(initialUrl.tab) ?? "catalog",
  );
```

with:

```typescript
  const [manageGroup, setManageGroup] = useState<string>(
    initialUrl.group
      ?? defaultGroupFor(initialUrl.tab, initialUrl.mode)
      ?? "catalog",
  );
```

- [ ] **Step 2: Fix popstate handler**

Replace:

```typescript
      setManageGroup(parsed.group ?? defaultManageGroup(parsed.tab) ?? "catalog");
```

with:

```typescript
      setManageGroup(
        parsed.group ?? defaultGroupFor(parsed.tab, parsed.mode) ?? "catalog",
      );
```

- [ ] **Step 3: Clean imports if `defaultManageGroup` unused**

If `defaultManageGroup` is no longer referenced in `App.tsx`, remove it from the `urlState` import. Keep `defaultGroupFor`.

- [ ] **Step 4: Run focused source test + build**

```bash
.venv/bin/python -m unittest \
  tests.test_companion_finance_url_polish.CompanionFinanceUrlPolishTests.test_app_cold_load_and_popstate_use_default_group_for \
  -v
cd companion && npm run build
```

Expected: test PASS; build OK (version may still be 0.3.78 until Task 5).

- [ ] **Step 5: Commit**

```bash
git add companion/src/App.tsx
git commit -m "$(cat <<'EOF'
fix(companion): mode-aware group fallback on cold load and popstate

EOF
)"
```

---

### Task 5: Version 0.3.79 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `tests/test_desk_finance_surface.py` (soften exact `0.3.78` if present)
- Modify: `docs/11-user-experience.md`, `docs/decisions.md` (ADR-061), `docs/14-roadmap.md`, `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-12-companion-finance-url-polish-design.md` (status → implemented)
- Modify: `README.md` deliverable status line

**Interfaces:**
- Consumes: Tasks 2–4 complete
- Produces: green `test_version_0_3_79` + docs

- [ ] **Step 1: Bump versions**

```python
__version__ = "0.3.79"
```

```json
"version": "0.3.79",
```

- [ ] **Step 2: Soften prior desk exact pin**

In `tests/test_desk_finance_surface.py` `test_version_0_3_78`, replace exact asserts with:

```python
self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
```

Rename method to `test_version_lockstep_soft` (or keep name but soften body — prefer rename for clarity).

- [ ] **Step 3: Docs**

- UX: note Close-period no longer focuses Manage; cold-load uses mode-aware group defaults; behavioral urlState harness.
- ADR-061 index:

```markdown
| ADR-061 | 2026-09-12 | Companion finance URL polish | Drop dead Close-period focus; cold-load/popstate use defaultGroupFor; tsx urlState harness; no new APIs. |
```

Add ADR-061 detail (context/decision/alternatives/consequences) in ADR-060 style.

- Roadmap: checked polish item 0.3.79; Immediate next → desk polish nits or owner-directed.
- Handoff: feature-branch pending merge style until ship.
- Spec status → `implemented in v0.3.79`.
- README: lead with v0.3.79 polish.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all OK; harness invoked from discover.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json \
  tests/test_desk_finance_surface.py tests/test_companion_finance_url_polish.py \
  docs/11-user-experience.md docs/decisions.md docs/14-roadmap.md docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-companion-finance-url-polish-design.md README.md
git commit -m "$(cat <<'EOF'
docs: companion finance URL polish and release 0.3.79

EOF
)"
```

(Only add paths that changed.)

---

## Plan self-review

1. **Spec coverage:** Fix 1 → Task 3; Fix 2 → Task 4; harness cases 1–7 → Task 2; version/docs → Task 5; RED contracts → Task 1.
2. **Placeholders:** none.
3. **Consistency:** `defaultGroupFor(tab, mode)` naming matches `urlState.ts`; harness imports match exports; serialize expectations match omit-defaults rules in ADR-058/059.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-12-companion-finance-url-polish.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute in this session with checkpoints  

Which approach?
