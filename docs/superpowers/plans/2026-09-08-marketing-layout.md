# Marketing Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship public `/welcome` landing (C1) and desk HQ `campaign` furniture for marketing rooms (C2) as v0.3.59.

**Architecture:** FastAPI serves `WELCOME_HTML` like `DESK_HTML`, with shared cosmic-glass tokens via `/static`. Caddy proxies `/welcome` before the companion SPA. Desk SVG `furnitureKind` / `drawFurniture` gain a `campaign` kind when `room_type` includes `market`.

**Tech Stack:** FastAPI HTMLResponse, existing StaticFiles, Caddyfile, unittest, desk inline JS in `DESK_HTML`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-marketing-layout-design.md`
- Version **0.3.59**; ADR-045; no Alembic (HEAD stays `0028_remote_worker_jobs`)
- `/` stays companion; `/welcome` is public landing only
- Hero: brand + one headline + offline-starter line + CTAs to `/` and `/desk` — no stats cards
- Preserve cosmic-glass tokens; no inventing HQ occupancy
- Branch: `feature/marketing-layout` from `main`
- Do not commit `local repos/service-department/`

## File map

| File | Responsibility |
|---|---|
| `company/service.py` | `WELCOME_HTML`, `GET /welcome`; desk `furnitureKind` / `drawFurniture` |
| `company/rate_limit.py` | Exempt `/welcome` |
| `deploy/fs-dev/Caddyfile` | `handle /welcome` → API |
| `tests/test_welcome.py` | New welcome route tests |
| `tests/test_desk_furniture.py` | Assert `campaign` + marketing match |
| Docs / version files | ADR-045, handoff, roadmap, API note, 0.3.59 bump |

---

### Task 1: Welcome page route + rate-limit exempt

**Files:**
- Modify: `company/service.py` (add `WELCOME_HTML`, route next to `/desk`)
- Modify: `company/rate_limit.py` (`EXEMPT_PATHS`)
- Create: `tests/test_welcome.py`

**Interfaces:**
- Produces: `WELCOME_HTML: str`; `GET /welcome` → 200 HTML
- CTA hrefs exactly `/` and `/desk`; stylesheet `/static/cosmic-glass-tokens.css`
- Brand text includes `FS-Corporation`

- [ ] **Step 1: Write failing tests**

```python
"""Public /welcome landing page."""
import unittest
from tests.test_api import owner_client


class WelcomeTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_welcome_is_public_html(self):
        # no Authorization header
        r = self.client.get("/welcome")
        self.assertEqual(r.status_code, 200)
        text = r.text
        self.assertIn("FS-Corporation", text)
        self.assertIn('href="/"', text)
        self.assertIn('href="/desk"', text)
        self.assertIn("/static/cosmic-glass-tokens.css", text)
        self.assertIn("offline", text.lower())  # support line mentions offline starter

    def test_welcome_exempt_from_auth(self):
        from company.rate_limit import EXEMPT_PATHS
        self.assertIn("/welcome", EXEMPT_PATHS)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_welcome -v`  
Expected: 404 and/or missing `/welcome` in EXEMPT_PATHS

- [ ] **Step 3: Implement**

Add near `DESK_HTML`:

```python
WELCOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>FS-Corporation</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="/static/cosmic-glass-tokens.css"/>
<style>
/* page-local hero only — use token vars; respect prefers-reduced-motion */
body {
  margin: 0; min-height: 100vh; color: var(--soft);
  font-family: "Segoe UI", system-ui, sans-serif;
  background:
    radial-gradient(1000px 500px at 80% 0%, rgba(59,130,246,0.25), transparent 55%),
    radial-gradient(800px 400px at 10% 100%, rgba(52,211,153,0.12), transparent 50%),
    var(--midnight);
  display: grid; place-items: center;
}
.hero { text-align: center; padding: 2rem 1.25rem; max-width: 36rem; }
.brand {
  font-size: clamp(2.4rem, 8vw, 3.6rem); font-weight: 700;
  letter-spacing: 0.06em; margin: 0 0 0.75rem;
  animation: rise 0.7s ease-out;
}
h1 { font-size: clamp(1.15rem, 3vw, 1.45rem); font-weight: 600; margin: 0 0 0.75rem; }
.support { color: var(--muted); margin: 0 0 1.5rem; line-height: 1.45; }
.ctas { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.ctas a {
  color: var(--soft); text-decoration: none;
  border: 1px solid var(--glass-border); background: var(--glass);
  border-radius: var(--radius-glass); padding: 0.65rem 1.1rem;
  animation: rise 0.9s ease-out;
}
.ctas a.primary { border-color: var(--cosmic); background: rgba(59,130,246,0.22); }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  .brand, .ctas a { animation: none; }
}
</style>
</head>
<body data-theme="cosmic-glass">
<main class="hero">
  <p class="brand">FS-Corporation</p>
  <h1>A persistent AI company built on ChatDev</h1>
  <p class="support">Offline starter — owner-operated, fail-closed integrations until you configure them.</p>
  <div class="ctas">
    <a class="primary" href="/">Open companion</a>
    <a href="/desk">CEO desk</a>
  </div>
</main>
</body>
</html>
"""
```

Wire route (mirror desk):

```python
@app.get("/welcome", response_class=HTMLResponse)
def welcome():
    return WELCOME_HTML
```

Update `EXEMPT_PATHS`:

```python
EXEMPT_PATHS = frozenset({"/", "/desk", "/welcome", "/api/v1/health"})
```

Export `WELCOME_HTML` if tests import it (optional).

- [ ] **Step 4: Run tests — PASS**

Run: `.venv/bin/python -m unittest tests.test_welcome -v`

- [ ] **Step 5: Commit** when appropriate

```bash
git add company/service.py company/rate_limit.py tests/test_welcome.py
git commit -m "$(cat <<'EOF'
Add public /welcome landing with cosmic-glass hero.

EOF
)"
```

---

### Task 2: Caddy `/welcome` proxy

**Files:**
- Modify: `deploy/fs-dev/Caddyfile`
- Modify: `tests/test_welcome.py` (or small file assert)

- [ ] **Step 1: Failing test**

```python
from pathlib import Path

class WelcomeCaddyTests(unittest.TestCase):
    def test_caddyfile_proxies_welcome(self):
        text = (Path(__file__).resolve().parents[1] / "deploy/fs-dev/Caddyfile").read_text()
        self.assertIn("handle /welcome", text)
        self.assertIn("reverse_proxy 127.0.0.1:8000", text)
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Insert in `(lan_site)` after `/desk` handle:**

```
	handle /welcome {
		reverse_proxy 127.0.0.1:8000
	}
```

Must appear **before** `handle /*` SPA catch-all.

- [ ] **Step 4: PASS + commit**

---

### Task 3: Marketing `campaign` furniture

**Files:**
- Modify: `company/service.py` (`furnitureKind`, `drawFurniture` inside `DESK_HTML`)
- Modify: `tests/test_desk_furniture.py`

- [ ] **Step 1: Extend failing assertions**

```python
        self.assertIn("campaign", DESK_HTML)
        self.assertIn("market", DESK_HTML)  # match in furnitureKind
```

- [ ] **Step 2: Run — FAIL** (missing campaign)

- [ ] **Step 3: Update JS in DESK_HTML**

```javascript
function furnitureKind(roomType) {
  const t = String(roomType || '').toLowerCase();
  if (t.includes('engine') || t.includes('hardware') || t.includes('dev')) return 'workstation';
  if (t.includes('executive') || t.includes('ceo') || t.includes('board')) return 'conference';
  if (t.includes('ops') || t.includes('infra') || t.includes('server')) return 'rack';
  if (t.includes('market')) return 'campaign';
  return 'desk';
}
function drawFurniture(g, kind, ix, iy) {
  // ... existing branches ...
  } else if (kind === 'campaign') {
    const desk = ns('rect');
    desk.setAttribute('x', ix - 5); desk.setAttribute('y', iy + 7);
    desk.setAttribute('width', '10'); desk.setAttribute('height', '3');
    desk.setAttribute('fill', '#78716c');
    const board = ns('rect');
    board.setAttribute('x', ix + 2); board.setAttribute('y', iy + 1);
    board.setAttribute('width', '3'); board.setAttribute('height', '7');
    board.setAttribute('fill', '#38bdf8');
    g.appendChild(desk); g.appendChild(board);
  } else {
    // existing desk fallback
```

- [ ] **Step 4: PASS**

Run: `.venv/bin/python -m unittest tests.test_desk_furniture tests.test_welcome -v`

- [ ] **Step 5: Commit**

---

### Task 4: Docs, ADR-045, version 0.3.59

**Files:**
- `company/__init__.py`, `companion/package.json`, `README.md`, `VERIFICATION.md` → **0.3.59**
- `docs/decisions.md` — ADR-045 table + detail
- `docs/16-api-contract.md` — note `GET /welcome`
- `docs/18-handoff.md`, `docs/14-roadmap.md`
- Spec status → implemented
- Commit design/plan if not already on branch

ADR-045 summary:
> Public `/welcome` landing (FastAPI + cosmic-glass); desk HQ maps marketing rooms to `campaign` furniture; companion remains at `/`.

- [ ] **Step 1: Apply doc/version edits**

- [ ] **Step 2: Full suite**

Run: `.venv/bin/python -m unittest discover -s tests`  
Expected: all PASS

- [ ] **Step 3: Companion build** (version bump): `cd companion && npm run build`

- [ ] **Step 4: Commit** when owner asks; merge/push/deploy only on request

---

## Spec coverage

| Spec item | Task |
|---|---|
| `/welcome` HTML + tokens + CTAs + offline line | 1 |
| Rate-limit exempt | 1 |
| Caddy handle | 2 |
| `campaign` furniture + market match | 3 |
| ADR-045 / 0.3.59 / docs | 4 |
| No Alembic; `/` unchanged | all |

## Self-review

- No placeholders; CTA paths locked to `/` and `/desk`
- Furniture kind string locked: `campaign`; match: `market`
- Version locked: `0.3.59`; ADR: `045`
