# Companion Shell + CEO Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship companion primary nav Home · Work · People · Money · More, a Needs-you Home queue with inline actions, and unified Syne/Manrope brand chrome on companion + light desk/welcome font alignment (v0.3.65).

**Architecture:** Keep fine-grained `tab` state (projects, corporate, workers, …). Primary bar uses the existing More pattern: group buttons restore `lastWorkTab` / `lastMoreTab`. Extract `HomePanel` for the queue + status strip. Share brand fonts via `assets/brand-fonts.css` served at `/static` and imported by the companion.

**Tech Stack:** React/Vite companion, FastAPI desk/`welcome` static assets, cosmic-glass tokens, unittest source assertions, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-10-companion-shell-ceo-spine-design.md` (owner-approved).
- No new APIs; no invented metrics/queues; scope-gated writes unchanged.
- Escalate/create stays on More → Inbox only; Home responds to open inbox items.
- Do not redesign `/welcome` hero or desk sidebar IA.
- Version **0.3.65**. Do not commit `local repos/service-department/`.
- Prefer owner-requested commits; if executing autonomously, pause before each commit step unless the owner already authorized commits for this plan.

## File map

| Path | Role |
|---|---|
| `assets/cosmic-glass-tokens.css` | Add `--font-display`, `--font-body`, optional `--wash` |
| `assets/brand-fonts.css` | Shared `@font-face` for Syne/Manrope (`/static/fonts/…`) |
| `assets/welcome.css` | Drop duplicate `@font-face` if moved; keep landing layout |
| `company/service.py` | Desk + welcome `<link>` to `brand-fonts.css`; desk `font-family` |
| `companion/src/styles.css` | Import brand fonts; display/body families; ops wash; tab polish |
| `companion/src/HomePanel.tsx` | Needs-you queue + status + pause/resume/refresh |
| `companion/src/App.tsx` | Primary groups, Work/More segmented, wire HomePanel |
| `tests/test_companion_api.py` | Update nav assertion for new PRIMARY shape |
| `tests/test_companion_shell_ceo_spine.py` | Source + static assertions for fonts/Home/Needs you |
| Docs / versions | ADR, 11, 24, roadmap, handoff, `__version__`, `package.json`, spec status |

---

### Task 1: Failing nav + brand tests

**Files:**
- Modify: `tests/test_companion_api.py` (`test_companion_nav_is_five_tabs_with_more_switcher`)
- Create: `tests/test_companion_shell_ceo_spine.py`

**Interfaces:**
- Consumes: none (source/static assertions only)
- Produces: failing tests that Task 2–3 must satisfy

- [ ] **Step 1: Rewrite the companion nav source test**

Replace `test_companion_nav_is_five_tabs_with_more_switcher` body so it expects **four** primary entries plus a More button pattern:

```python
def test_companion_nav_is_five_tabs_with_more_switcher(self):
    app_source = (
        Path(__file__).resolve().parents[1] / "companion" / "src" / "App.tsx"
    ).read_text()
    self.assertIn("const PRIMARY_TABS", app_source)
    self.assertIn("const WORK_TABS", app_source)
    self.assertIn("const MORE_TABS", app_source)
    primary = re.search(r"const PRIMARY_TABS[^=]*= \[(.*?)\];", app_source, re.S).group(1)
    self.assertEqual(len(re.findall(r'\["', primary)), 4)
    self.assertIn('["dashboard", "Home"]', primary)
    self.assertIn('["work", "Work"]', primary)
    self.assertIn('["people", "People"]', primary)
    self.assertIn('["money", "Money"]', primary)
    self.assertNotIn('["workers", "Workers"]', primary)
    self.assertIn('["projects", "Projects"]', app_source)  # inside WORK_TABS
    self.assertIn('tab === "finance"', app_source)
    self.assertNotIn('["finance", "Finance"]', re.search(r"const MORE_TABS[^=]*= \[(.*?)\];", app_source, re.S).group(1))
    self.assertIn("setTab(lastWorkTab)", app_source)
    self.assertIn("setTab(lastMoreTab)", app_source)
    self.assertIn("HomePanel", app_source)
    self.assertIn("Needs you", app_source)
```

Note: `PRIMARY_TABS` uses sentinel keys `work` / `people` / `money` only for the bar labels; clicking them must call `setTab(lastWorkTab)` / `organization` / `finance` respectively (see Task 3). The test asserts the constant table shape and `setTab(lastWorkTab)`.

- [ ] **Step 2: Add shell/spine static + source tests**

Create `tests/test_companion_shell_ceo_spine.py`:

```python
"""Companion shell + CEO spine (v0.3.65) — source and static contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompanionShellCeoSpineTests(unittest.TestCase):
    def test_brand_fonts_css_exists_and_faces(self):
        css = (ROOT / "assets" / "brand-fonts.css").read_text()
        self.assertIn('font-family: "Syne"', css)
        self.assertIn('font-family: "Manrope"', css)
        self.assertIn("/static/fonts/syne-latin-700-normal.woff2", css)
        self.assertIn("/static/fonts/manrope-latin-400-normal.woff2", css)
        self.assertIn("/static/fonts/manrope-latin-600-normal.woff2", css)

    def test_tokens_declare_font_vars(self):
        tokens = (ROOT / "assets" / "cosmic-glass-tokens.css").read_text()
        self.assertIn("--font-display", tokens)
        self.assertIn("--font-body", tokens)

    def test_companion_imports_brand_fonts(self):
        css = (ROOT / "companion" / "src" / "styles.css").read_text()
        self.assertIn("brand-fonts.css", css)
        self.assertIn("var(--font-display)", css)
        self.assertIn("var(--font-body)", css)

    def test_desk_and_welcome_link_brand_fonts(self):
        from company.service import DESK_HTML, WELCOME_HTML

        self.assertIn("/static/brand-fonts.css", DESK_HTML)
        self.assertIn("/static/brand-fonts.css", WELCOME_HTML)
        self.assertIn("var(--font-display)", DESK_HTML)
        # welcome may use Manrope via CSS file; brand link is required

    def test_static_brand_fonts_route(self):
        from tests.test_api import owner_client

        c, client = owner_client()
        self.addCleanup(c.close)
        r = client.get("/static/brand-fonts.css")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Syne", r.text)

    def test_home_panel_module_exists(self):
        path = ROOT / "companion" / "src" / "HomePanel.tsx"
        self.assertTrue(path.is_file())
        text = path.read_text()
        self.assertIn("Needs you", text)
        self.assertIn("View all", text)
```

Adjust `create_app` kwargs to match whatever `tests/test_p5_ui_chrome.py` already uses if signatures differ — copy that file’s client setup exactly.

- [ ] **Step 3: Run tests — expect FAIL**

Run:

```bash
.venv/bin/python -m unittest tests.test_companion_api.ControlPlaneAPITests.test_companion_nav_is_five_tabs_with_more_switcher tests.test_companion_shell_ceo_spine -v
```

Expected: FAIL (missing `WORK_TABS` / `brand-fonts.css` / `HomePanel.tsx`, old PRIMARY still has Workers).

- [ ] **Step 4: Commit (owner-gated)**

```bash
git add tests/test_companion_api.py tests/test_companion_shell_ceo_spine.py
git commit -m "$(cat <<'EOF'
test(companion): expect Home/Work/People/Money shell contracts

EOF
)"
```

---

### Task 2: Shared brand fonts + token polish

**Files:**
- Create: `assets/brand-fonts.css`
- Modify: `assets/cosmic-glass-tokens.css`
- Modify: `assets/welcome.css` (remove duplicate `@font-face` blocks that move into brand-fonts)
- Modify: `company/service.py` (`DESK_HTML` head + body font; `WELCOME_HTML` link)
- Modify: `companion/src/styles.css`
- Modify: `assets/fonts/README.md` (note shared ops use)

**Interfaces:**
- Consumes: existing woff2 under `assets/fonts/`
- Produces: `/static/brand-fonts.css`; CSS vars `--font-display` / `--font-body`

- [ ] **Step 1: Add font vars to tokens**

In `assets/cosmic-glass-tokens.css` `:root`, add:

```css
  --font-display: "Syne", system-ui, sans-serif;
  --font-body: "Manrope", system-ui, sans-serif;
  --wash: radial-gradient(900px 480px at 20% -20%, #12203a 0%, var(--midnight) 55%);
```

- [ ] **Step 2: Create `assets/brand-fonts.css`**

Move the three `@font-face` blocks from `assets/welcome.css` unchanged into `assets/brand-fonts.css`. Keep `font-display: swap` and `/static/fonts/…` URLs.

- [ ] **Step 3: Wire welcome + desk**

- `welcome.css`: delete the three `@font-face` blocks; keep `font-family: "Manrope", …` on body (or switch to `var(--font-body)`).
- `WELCOME_HTML`: after cosmic-glass tokens link, add  
  `<link rel="stylesheet" href="/static/brand-fonts.css"/>`  
  (preload links to woff2 may remain).
- `DESK_HTML`: after cosmic-glass tokens link, add brand-fonts link; change  
  `body { font-family: system-ui, sans-serif; …}` →  
  `body { font-family: var(--font-body); …}` and  
  `.brand, h1 { font-family: var(--font-display); }` (or equivalent minimal heading rule).

- [ ] **Step 4: Companion styles**

At top of `companion/src/styles.css`:

```css
@import "../../assets/cosmic-glass-tokens.css";
@import "../../assets/brand-fonts.css";

:root {
  font-family: var(--font-body);
  background: var(--wash);
  color: var(--soft);
  line-height: 1.4;
}

h1, h2, .brand-title {
  font-family: var(--font-display);
}
```

Keep existing touch/safe-area/tab rules. Optional: `.app::before` quiet constellation wash using low-opacity radial gradients only (no fake stars inventing HQ state). Respect existing `prefers-reduced-motion` block.

- [ ] **Step 5: Run brand subset of new tests**

```bash
.venv/bin/python -m unittest \
  tests.FAKESECRET_u1v2w3x4y5z6a7b8c9d0 \
  tests.FAKESECRET_c3d4e5f6g7h8i9j0k1l2 \
  tests.FAKESECRET_e4f5g6h7i8j9k0l1m2n3 \
  tests.FAKESECRET_a3b4c5d6e7f8g9h0i1j2 \
  tests.FAKESECRET_c3d4e5f6g7h8i9j0k1l2 \
  -v
```

Expected: those five PASS. `test_home_panel_module_exists` still FAIL until Task 3.

- [ ] **Step 6: Commit (owner-gated)**

```bash
git add assets/brand-fonts.css assets/cosmic-glass-tokens.css assets/welcome.css assets/fonts/README.md company/service.py companion/src/styles.css
git commit -m "$(cat <<'EOF'
feat(ui): share Syne/Manrope brand fonts across surfaces

EOF
)"
```

---

### Task 3: HomePanel + App nav regroup

**Files:**
- Create: `companion/src/HomePanel.tsx`
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Consumes: existing `DecisionItem`, `OwnerRequest`, `canApprove`, `canRespondInbox`, `canPause`/`canResume`, `api.pause`/`api.resume`, `status()` renderer, `decide`, `respond`, `ownerResponseDrafts` setters from App
- Produces: `<HomePanel … />` used when `tab === "dashboard"`

- [ ] **Step 1: Define tab constants in App.tsx**

Replace PRIMARY/MORE definitions with:

```tsx
/** Primary bar labels. `work`/`people`/`money` are group sentinels for the bar only. */
const PRIMARY_TABS: [string, string][] = [
  ["dashboard", "Home"],
  ["work", "Work"],
  ["people", "People"],
  ["money", "Money"],
];

const WORK_TABS: [Tab, string][] = [
  ["projects", "Projects"],
  ["corporate", "Corporate"],
  ["workers", "Workers"],
];

const MORE_TABS: [Tab, string][] = [
  ["decisions", "Decisions"],
  ["inbox", "Inbox"],
  ["diagnostics", "Diagnostics"],
  ["settings", "Settings"],
];
```

Keep `Tab` union including `"dashboard" | "projects" | … | "finance" | …` (do **not** add `"work"|"people"|"money"` to `Tab` unless you also handle them as real panels — prefer sentinels only in PRIMARY_TABS typing as `string` or a separate `PrimaryKey` type).

Add state:

```tsx
const [lastWorkTab, setLastWorkTab] = useState<Tab>("projects");
```

In the effect that tracks More tabs, also:

```tsx
if (WORK_TABS.some(([t]) => t === tab)) setLastWorkTab(tab);
```

- [ ] **Step 2: Create `HomePanel.tsx`**

```tsx
import type { FormEvent } from "react";
import type { DecisionItem, OwnerRequest } from "./api/client";
import { canApprove, canPause, canRespondInbox, canResume } from "./scopes";

type StatusFn = (key: string) => React.ReactNode;
type ScopeNoticeFn = (action: string, scope: string) => React.ReactNode;

export type HomePanelProps = {
  scopes: string[] | undefined;
  decisions: DecisionItem[];
  inbox: OwnerRequest[];
  company: Record<string, unknown>;
  dashboard: Record<string, unknown> | null;
  ownerResponseDrafts: Record<string, string>;
  setOwnerResponseDrafts: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  onDecide: (item: DecisionItem, decision: "approved" | "rejected") => void;
  onRespond: (req: OwnerRequest) => void;
  onPause: () => void;
  onResume: () => void;
  onRefresh: () => void;
  onOpenDecisions: () => void;
  onOpenInbox: () => void;
  status: StatusFn;
  scopeNotice: ScopeNoticeFn;
  accessBadge: string | null;
};

export function HomePanel(props: HomePanelProps) {
  const {
    scopes, decisions, inbox, company, dashboard,
    ownerResponseDrafts, setOwnerResponseDrafts,
    onDecide, onRespond, onPause, onResume, onRefresh,
    onOpenDecisions, onOpenInbox, status, scopeNotice, accessBadge,
  } = props;

  return (
    <section className="home-panel">
      <h1 className="brand-title">
        FS-Corporation{" "}
        {accessBadge && <span className="tag tag-proposal">{accessBadge}</span>}
      </h1>
      <p className="lede">Needs-you queue from persisted decisions and inbox — nothing invented.</p>

      <div className="card">
        <div className="section-head">
          <h2>Needs you</h2>
          <div className="chip-row">
            <button type="button" className="chip" onClick={onOpenDecisions}>View all decisions</button>
            <button type="button" className="chip" onClick={onOpenInbox}>View all inbox</button>
          </div>
        </div>

        {decisions.map((item) => (
          <div key={`d-${item.kind}-${item.id}`} className="card nested-card">
            <div className={item.kind === "consultant" ? "tag tag-proposal" : "tag tag-warning"}>{item.kind}</div>
            <strong>{item.title}</strong>
            <p className="muted">{item.summary}</p>
            {canApprove(scopes) && (item.kind === "policy" || item.kind === "consultant") && (
              <div className="actions">
                <button className="approve" type="button" onClick={() => onDecide(item, "approved")}>Approve</button>
                <button className="danger" type="button" onClick={() => onDecide(item, "rejected")}>Reject</button>
              </div>
            )}
            {status(`decision-${item.id}`)}
          </div>
        ))}

        {inbox.map((req) => (
          <div key={`i-${req.id}`} className="card nested-card">
            <div className="muted">{req.kind} · {req.department_id}</div>
            <strong>{req.subject}</strong>
            <p>{req.body}</p>
            {canRespondInbox(scopes) && (
              <form
                onSubmit={(event: FormEvent) => {
                  event.preventDefault();
                  onRespond(req);
                }}
              >
                <label htmlFor={`home-owner-response-${req.id}`}>Response</label>
                <textarea
                  id={`home-owner-response-${req.id}`}
                  required
                  value={ownerResponseDrafts[req.id] || ""}
                  onChange={(e) => setOwnerResponseDrafts((prev) => ({
                    ...prev,
                    [req.id]: e.target.value,
                  }))}
                />
                <div className="actions">
                  <button className="primary" type="submit">Respond</button>
                </div>
              </form>
            )}
            {status(`respond-${req.id}`)}
          </div>
        ))}

        {!decisions.length && !inbox.length && (
          <p className="muted">Nothing needs you right now.</p>
        )}
        {decisions.length > 0 && !canApprove(scopes) && scopeNotice("decide proposals", "policy.approve")}
      </div>

      <div className="card">
        <h2>Status</h2>
        <div>Policy v{String(company.policy_version ?? "?")}</div>
        <div>Paused: {String(company.paused ?? false)}</div>
        <div>Simulated spend: {String(company.simulated_spend_cents ?? 0)}¢</div>
        <div>Reserved: {String(company.reserved_cents ?? 0)}¢</div>
        <div>Open owner inbox: {String(dashboard?.owner_inbox_open ?? inbox.length)}</div>
        <div>Pending decisions: {String(decisions.length)}</div>
        <div className="actions">
          {canResume(scopes) && (
            <button className="primary" type="button" onClick={onResume}>Resume</button>
          )}
          {canPause(scopes) && (
            <button className="danger" type="button" onClick={onPause}>Pause</button>
          )}
          <button type="button" onClick={onRefresh}>Refresh</button>
        </div>
      </div>
    </section>
  );
}
```

Match **exact** field names already used on the dashboard card in `App.tsx` for spend/reserved (copy from the current dashboard block — do not invent new keys). If current dashboard uses different property paths, use those verbatim.

- [ ] **Step 3: Wire App shell**

1. Import `HomePanel`.
2. Replace `tab === "dashboard"` block with `<HomePanel … />` (pass decide/respond/pause/resume/refresh and `setTab("decisions")` / `setTab("inbox")` for View all).
3. Move the page-level `<h1>FS-Corporation…` out of the global chrome when on Home (HomePanel owns the title); keep a compact title on other tabs **or** keep one global h1 and drop duplicate inside HomePanel — pick **one** title only.
4. Render Work segmented control when `WORK_TABS.some(([t]) => t === tab)` (same markup pattern as More).
5. Primary nav:

```tsx
<nav className="tabs" aria-label="Primary">
  <button type="button" className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>
    Home
    {moreCount > 0 && <span className="tab-badge">{moreCount}</span>}
  </button>
  <button
    type="button"
    className={WORK_TABS.some(([t]) => t === tab) ? "active" : ""}
    onClick={() => setTab(lastWorkTab)}
  >
    Work
  </button>
  <button
    type="button"
    className={tab === "organization" ? "active" : ""}
    onClick={() => setTab("organization")}
  >
    People
  </button>
  <button
    type="button"
    className={tab === "finance" ? "active" : ""}
    onClick={() => setTab("finance")}
  >
    Money
  </button>
  <button
    type="button"
    className={MORE_TABS.some(([t]) => t === tab) ? "active" : ""}
    onClick={() => setTab(lastMoreTab)}
  >
    More
  </button>
</nav>
```

You may keep mapping `PRIMARY_TABS` for labels but the click handlers above are required so `setTab(lastWorkTab)` appears in source for the test.

6. Remove Finance from MORE_TABS (Money tab owns it). Keep Decisions/Inbox in More as overflow.
7. Ensure `tab === "finance"` still renders `FinancePanel`.

- [ ] **Step 4: CSS for Home nested cards (minimal)**

In `styles.css`:

```css
.section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.nested-card {
  margin: 0.5rem 0;
  box-shadow: none;
}
```

- [ ] **Step 5: Run shell tests + companion build**

```bash
.venv/bin/python -m unittest tests.test_companion_shell_ceo_spine tests.test_companion_api.ControlPlaneAPITests.test_companion_nav_is_five_tabs_with_more_switcher -v
cd companion && npm run build
```

Expected: PASS / build OK.

- [ ] **Step 6: Commit (owner-gated)**

```bash
git add companion/src/HomePanel.tsx companion/src/App.tsx companion/src/styles.css
git commit -m "$(cat <<'EOF'
feat(companion): Home Needs-you queue and domain primary tabs

EOF
)"
```

---

### Task 4: Docs, ADR, version 0.3.65

**Files:**
- Modify: `company/__init__.py` → `0.3.65`
- Modify: `companion/package.json` → `0.3.65`
- Modify: `docs/24-mobile-companion.md` (tab model section)
- Modify: `docs/11-user-experience.md` (companion shell paragraph)
- Modify: `docs/decisions.md` (new ADR)
- Modify: `docs/14-roadmap.md` (checkbox + note)
- Modify: `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-10-companion-shell-ceo-spine-design.md` status → implemented in v0.3.65
- Modify: capability matrix / README only if version is listed there

**Interfaces:**
- Consumes: shipped behavior from Tasks 2–3
- Produces: documented 0.3.65

- [ ] **Step 1: Bump versions**

`company/__init__.py`:

```python
__version__ = "0.3.65"
```

`companion/package.json` `"version": "0.3.65"`.

- [ ] **Step 2: Docs**

- `docs/24-mobile-companion.md`: replace “six tabs — Home, Projects, Org, Corporate, Workers, More” with Home · Work · People · Money · More and the domain mapping from the spec.
- `docs/11-user-experience.md`: companion bottom bar = five domain tabs; Home is Needs-you queue.
- ADR in `docs/decisions.md`: Companion shell + CEO spine; unified brand fonts; approach 1 delivery.
- Roadmap: mark item done at 0.3.65.
- Handoff: version 0.3.65; next = deep polish inside Work/People/Money or desk IA.
- Spec status line → **implemented** in v0.3.65.

- [ ] **Step 3: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests PASS; companion build OK.

- [ ] **Step 4: Commit (owner-gated)**

```bash
git add company/__init__.py companion/package.json docs/
git commit -m "$(cat <<'EOF'
docs: companion shell CEO spine and release 0.3.65

EOF
)"
```

---

## Spec coverage

| Spec requirement | Task |
|---|---|
| Primary Home · Work · People · Money · More | 1, 3 |
| Domain map (Work/People/Money/More contents) | 3 |
| Home Needs-you queue + inline actions | 3 |
| Escalate only on More → Inbox | 3 (HomePanel omits escalate form) |
| Unified Syne/Manrope + tokens | 2 |
| Desk/welcome font alignment only | 2 |
| No API / no invented metrics | 3 (reuse lists/fields) |
| Docs + 0.3.65 | 4 |
| Verification build + unittest | 3–4 |

## Placeholder / consistency self-review

- No TBD steps; PRIMARY sentinel keys documented; spend field paths must be copied from live dashboard JSX.
- `MORE_TABS` no longer includes Finance; Money → `finance` tab.
- Nav test expects four PRIMARY entries + `setTab(lastWorkTab)` + `HomePanel` + `Needs you`.
