# Deeper Marketing Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bold `/welcome` craft (self-hosted fonts, constellation motif, motion) plus richer desk `campaign` furniture (banner + podium), without inventing ops state or CDN fonts.

**Architecture:** Keep FastAPI `WELCOME_HTML` + `/static` assets. Add OFL woff2 fonts under `assets/fonts/`, `assets/welcome.css`, constellation motif in HTML/CSS. Upgrade `drawFurniture(..., "campaign")` in `DESK_HTML`. Amend ADR-045; version **0.3.64**.

**Tech Stack:** FastAPI HTML, static assets, existing desk SVG helpers, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-09-deeper-marketing-redesign-design.md` (approved).
- Version **0.3.64**; no Alembic; no CDN fonts; companion stays at `/`.
- Hero budget unchanged: brand + one headline + one support + CTAs to `/` and `/desk`.
- No inventing company stats/occupancy/marketing wing.
- Branch: `feature/deeper-marketing-redesign` from `main`.
- Do not commit `local repos/service-department/`.

## File map

| File | Responsibility |
|---|---|
| `assets/fonts/*.woff2` + `LICENSE` note | Self-hosted Syne (display) + Manrope (text) or equivalent OFL pair |
| `assets/welcome.css` | `@font-face`, constellation, hero layout, motion, reduced-motion |
| `company/service.py` | `WELCOME_HTML` redesign; `campaign` SVG upgrade |
| `tests/test_welcome.py` | Fonts, motif, reduced-motion |
| `tests/test_desk_furniture.py` | Podium/banner markers |
| Docs / versions | ADR-045, roadmap, handoff, 0.3.64 |

**Font acquisition:** Download OFL woff2 files (e.g. from [fontsource](https://github.com/fontsource/font-files) or Google Fonts GitHub `ofl/` trees). Prefer **Syne** (700) for brand + **Manrope** (400/600) for body. Commit binary woff2 + a short `assets/fonts/README.md` citing license/source. Do not hotlink CDNs at runtime.

---

### Task 1: Welcome redesign + fonts + campaign furniture

**Files:**
- Create: `assets/fonts/` (woff2 + README)
- Create: `assets/welcome.css`
- Modify: `company/service.py` (`WELCOME_HTML`, `drawFurniture` campaign branch)
- Test: `tests/test_welcome.py`, `tests/test_desk_furniture.py`

- [ ] **Step 1: Failing tests**

Extend `tests/test_welcome.py`:

```python
def test_welcome_deeper_craft(self):
    r = self.client.get("/welcome")
    text = r.text
    self.assertIn("/static/welcome.css", text)
    self.assertIn("/static/fonts/", text)
    self.assertIn("constellation", text.lower())
    self.assertIn("prefers-reduced-motion", text)
    # still public hero contract
    self.assertIn("FS-Corporation", text)
    self.assertIn('href="/"', text)
    self.assertIn('href="/desk"', text)

def test_welcome_font_files_exist(self):
    root = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    woffs = list(root.glob("*.woff2"))
    self.assertGreaterEqual(len(woffs), 2, "need display + text woff2")
```

Extend `tests/test_desk_furniture.py`:

```python
self.assertIn("campaign-podium", DESK_HTML)  # or marker strings used in SVG
self.assertIn("campaign-banner", DESK_HTML)
```

(Use the exact class/`data-*` / comment markers you put in the campaign SVG.)

- [ ] **Step 2: Run — expect fail**

```bash
.venv/bin/python -m unittest tests.test_welcome tests.test_desk_furniture -v
```

- [ ] **Step 3: Add fonts**

Place at least:
- `assets/fonts/syne-latin-700-normal.woff2` (or similar name)
- `assets/fonts/manrope-latin-400-normal.woff2`
- `assets/fonts/manrope-latin-600-normal.woff2` (optional)
- `assets/fonts/README.md` with license (OFL) and upstream attribution

- [ ] **Step 4: `assets/welcome.css`**

Include:
- `@font-face` for display + text → `/static/fonts/...`
- Full-bleed `.constellation` (SVG background or positioned SVG stars)
- Brand as largest type; hero centered; no cards
- Animations: brand rise, constellation drift/pulse, CTA fade
- `@media (prefers-reduced-motion: reduce) { … animation: none; }`

- [ ] **Step 5: Rewrite `WELCOME_HTML`**

- Link `/static/cosmic-glass-tokens.css` and `/static/welcome.css`
- Structure: full-bleed motif element with class/id containing `constellation`, then `.hero` with brand, h1, support, CTAs
- Keep offline-starter support copy
- Minimal inline CSS only if needed for critical layout

- [ ] **Step 6: Upgrade campaign furniture**

In `drawFurniture` `campaign` branch, draw podium + banner and mark them, e.g.:

```javascript
} else if (kind === 'campaign') {
  const podium = ns('rect');
  podium.setAttribute('class', 'campaign-podium');
  // … geometry …
  const banner = ns('rect');
  banner.setAttribute('class', 'campaign-banner');
  // … geometry …
  g.appendChild(podium); g.appendChild(banner);
}
```

Keep `furnitureKind` `market` → `campaign` unchanged.

- [ ] **Step 7: Tests green + commit**

```bash
.venv/bin/python -m unittest tests.test_welcome tests.test_desk_furniture -v
```

```bash
git add assets/fonts assets/welcome.css company/service.py tests/test_welcome.py tests/test_desk_furniture.py
git commit -m "$(cat <<'EOF'
Redesign /welcome craft and enrich campaign furniture.

EOF
)"
```

---

### Task 2: Docs, ADR-045, version 0.3.64

**Files:**
- Modify: `docs/decisions.md` (ADR-045 consequences)
- Modify: `docs/14-roadmap.md`, `docs/18-handoff.md`
- Modify: `docs/superpowers/specs/2026-09-09-deeper-marketing-redesign-design.md` → implemented
- Modify: `company/__init__.py`, `companion/package.json` → `0.3.64`

- [ ] **Step 1: ADR-045**

Append to consequences:

```markdown
In v0.3.64 the welcome page gained self-hosted display/text fonts, a constellation
background motif, and stronger motion (reduced-motion respected). Desk `campaign`
furniture became a podium + banner mark. Photoreal art and invented wings remain out of scope.
```

- [ ] **Step 2: Roadmap + handoff**

Mark deeper marketing redesign done; handoff next = owner-directed (backlog clear / ask).

- [ ] **Step 3: Version + full verify**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
Document deeper marketing redesign and release 0.3.64.

EOF
)"
```

---

## Spec coverage

| Requirement | Task |
|---|---|
| Self-hosted fonts + welcome.css | 1 |
| Constellation motif + motion + reduced-motion | 1 |
| Hero budget / CTAs / no inventing | 1 |
| Campaign podium + banner | 1 |
| ADR / docs / 0.3.64 | 2 |

## Verification (merge gate)

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```
