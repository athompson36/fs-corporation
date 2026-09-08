# Design: Marketing layout (welcome + HQ furniture)

Date: 2026-09-08. Status: **implemented** (v0.3.59).

## Goal

Ship Track **C** in one release: a public **welcome** landing page, then a distinct
**marketing** furniture mark on the CEO desk HQ isometric view.

## Locks

| Topic | Choice |
|---|---|
| Scope | C1 then C2 in one release (approach 1) |
| Landing path | `/welcome`; `/` stays companion PWA (B) |
| Hero content | Brand + headline + offline-starter line + CTAs (B) |
| Serving | FastAPI HTML + `/static` tokens + Caddy `handle /welcome` (A) |
| C2 depth | Marketing → `campaign` furniture kind only (A) |

## Non-goals

- Moving companion off `/` or auth-gated landing
- Photoreal HQ art / inventing occupancy or marketing “wing” rooms
- Stats cards, feature grids, or operational inventing on the landing page
- Track B auto-placement
- Companion duplicate of desk furniture (desk-only today)

## C1 — `/welcome`

### Behavior

1. `GET /welcome` returns HTML (constant alongside `DESK_HTML` or equivalent).
2. Page links `href="/static/cosmic-glass-tokens.css"`.
3. First viewport only: brand **FS-Corporation**, one headline (persistent AI company /
   ChatDev), one support sentence (offline starter / owner-operated), CTA group:
   - **Open companion** → `/`
   - **CEO desk** → `/desk`
4. Visual: cosmic-glass tokens; atmospheric full-bleed background from existing palette;
   page-local layout CSS. Subtle motion with `prefers-reduced-motion` respected.
5. Public; add `/welcome` to `EXEMPT_PATHS` with `/`, `/desk`, health.
6. fs-dev Caddy: `handle /welcome { reverse_proxy 127.0.0.1:8000 }` before SPA `handle /*`.

### Tests

- Response 200; body contains brand string, both CTA `href`s, tokens stylesheet link.
- Caddyfile contains `/welcome` handle.

## C2 — Marketing furniture

### Behavior

1. `furnitureKind(roomType)`: if lowered string includes `market`, return `campaign`
   (checked before the generic `desk` fallback).
2. `drawFurniture(..., "campaign", ...)`: distinct geometric SVG (e.g. desk + upright
   display board), still not photoreal.
3. Binding remains `room.room_type` / `source_project` only — no invented staff.

### Tests

- Extend `tests/test_desk_furniture.py`: `DESK_HTML` includes `campaign` and a
  `market` match in `furnitureKind`.

## Authority

- `/welcome`: unauthenticated read-only HTML (no company state mutation).
- Furniture: projection of existing floorplan data only.

## Acceptance

1. `/welcome` is public, token-styled, with CTAs to companion and desk; Caddy proxies it.
2. Marketing-typed rooms use `campaign` furniture in desk SVG helpers.
3. Companion at `/` unchanged; ADR-045; version **0.3.59**; handoff notes C done.

## Out of band

- Branch: `feature/marketing-layout` from `main`.
- No Alembic revision.
