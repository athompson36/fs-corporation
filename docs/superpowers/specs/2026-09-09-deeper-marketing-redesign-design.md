# Design: Deeper marketing redesign (welcome + campaign furniture)

Date: 2026-09-09. Status: **implemented** in v0.3.64.

## Goal

Deepen marketing presence without inventing operational state: a **bold** public
`/welcome` (self-hosted typography, full-bleed constellation motif, intentional
motion) and a distinctly richer desk **`campaign`** furniture glyph (banner + podium).

Builds on ADR-045 (v0.3.59 welcome + campaign kind). Companion stays at `/`.

## Locks (owner brainstorming)

| Topic | Choice |
|---|---|
| Scope | `/welcome` **and** desk `campaign` furniture (D) |
| Craft depth | Bold — motif + distinctive campaign mark (B) |
| Fonts | Self-hosted woff2 under `/static/fonts/` (A) |
| Approach | Redesign `WELCOME_HTML` + upgrade desk SVG (1) |
| Motif | Constellation / starfield grid as full-bleed background plane |

## Non-goals

- Below-fold sections, stats cards, feature grids, promo overlays
- Photoreal art, invented marketing wing, occupancy, or company metrics on `/welcome`
- Google Fonts / any CDN font load
- Moving companion off `/` or auth-gating the landing
- Alembic / new APIs
- Changing `furnitureKind` mapping beyond existing `market*` → `campaign`

## Architecture

### Static assets

- `ASSETS_DIR` = repo `assets/` mounted at `/static` (existing).
- Add `assets/fonts/*.woff2` (display + text faces; open-licensed).
- Optional `assets/welcome.css` for page-local rules, **or** keep page CSS inline in
  `WELCOME_HTML` — prefer a small `welcome.css` if the HTML constant grows large.
- `@font-face` with `font-display: swap` and system fallbacks.

### `/welcome` (FastAPI HTML)

Keep `GET /welcome` → `WELCOME_HTML` (public, rate-limit exempt, Caddy `handle /welcome`).

First viewport (hero budget — do not expand):

1. Brand **FS-Corporation** as the dominant type signal
2. One headline (persistent AI company / ChatDev)
3. One support sentence (offline starter / owner-operated)
4. CTA group: **Open companion** → `/` · **CEO desk** → `/desk`

Visual:

- Cosmic-glass tokens via `/static/cosmic-glass-tokens.css`
- Full-bleed constellation / starfield motif (inline SVG and/or CSS) as the background
  plane — not an inset card or side panel
- Expressive self-hosted fonts (not Inter/Roboto/Arial/system-only)
- 2–3 intentional motions (e.g. brand rise, motif drift/pulse, CTA fade)
- `@media (prefers-reduced-motion: reduce)` disables those motions
- No cards in the hero; no floating badges/overlays on the motif; no invented ops copy

### Desk `campaign` furniture

- Keep `furnitureKind`: lowered `roomType` containing `market` → `campaign`.
- Replace the current desk + thin board with a clearer geometric mark:
  **low podium + upright banner** (additional SVG rects/paths, still isometric scale).
- Binding remains persisted `room.room_type` / floorplan data only.

### Docs / governance

- Amend ADR-045 consequences: deeper welcome craft + richer campaign glyph; still no
  photoreal / invented wing.
- Roadmap + handoff: marketing redesign shipped; next = owner-directed backlog.
- Version **0.3.64**.

## Failure modes

| Case | Result |
|---|---|
| Font files missing | Readable via swap + system fallbacks |
| `prefers-reduced-motion` | Motions off |
| Unauthenticated `/welcome` | Still public HTML; no company data |
| Non-marketing room types | Unchanged furniture kinds |

## Testing

- `tests/test_welcome.py`: brand, CTAs, tokens CSS, `/static/fonts/` or `@font-face`,
  constellation/motif marker, reduced-motion rule present.
- Font files exist under `assets/fonts/`.
- `tests/test_desk_furniture.py`: `campaign` path includes podium/banner markers
  distinct from generic `desk`.
- Existing Caddy `/welcome` proxy assertion retained.
- Full unittest discover before merge.

## Acceptance

1. `/welcome` is bold, brand-first, self-hosted fonts, constellation motif, same CTAs,
   no invented operational content.
2. Marketing-typed rooms still map to `campaign`; glyph reads as banner + podium.
3. No CDN fonts; reduced-motion respected; no Alembic; companion at `/` unchanged.
4. Docs/ADR-045/handoff/version **0.3.64** updated.

Do not commit `local repos/service-department/`.
