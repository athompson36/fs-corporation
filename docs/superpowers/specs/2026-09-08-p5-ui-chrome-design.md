# Design: P5 UI chrome (shared tokens + M10-04)

Date: 2026-09-08. Status: **implemented** (v0.3.55).

## Goal

Ship production **P5** as scoped by the owner:

- **Approach 2:** one shared cosmic-glass token stylesheet for desk + companion.
- **M10-04:** backend version in primary chrome; HQ tiles keyboard-accessible.
- **Light polish:** token-driven focus/spacing/radius only — no layout redesign, no marketing page.

Owner locks:

| Topic | Choice |
|---|---|
| Scope | B — M10-04 + light polish |
| Version placement | A — desk rail footer; companion above bottom tabs |
| Implementation | 2 — shared CSS tokens file |
| Tokens path | `assets/cosmic-glass-tokens.css` |

## Non-goals

- Marketing / landing layout.
- Photoreal HQ art or inventing occupancy.
- Tailwind or a JS design-system package.
- Remote worker agent / new APIs beyond static CSS serving.
- Showing invented version strings when health fails.

## Shared tokens

**File:** `assets/cosmic-glass-tokens.css`

Contents (only):

- `:root` color tokens already used by both surfaces (`--midnight`, `--glass`, `--cosmic`, …).
- Shared knobs: `--space-*`, `--radius-*`, `--focus-ring`.
- Shared primitives: `.glass`, `.chip`, `.muted`, `.lede`, and `:focus-visible` using `--focus-ring`.

**Wire-up:**

| Surface | Mechanism |
|---|---|
| Desk | FastAPI serves `assets/` at `/static/…`; `DESK_HTML` `<link rel="stylesheet" href="/static/cosmic-glass-tokens.css">`; inline CSS keeps layout-only rules and drops duplicated `:root` colors. |
| Companion | Import the same file from `companion/src/styles.css` (Vite can resolve `../../assets/cosmic-glass-tokens.css`); remove duplicated `:root` color block. |

No npm publish; single source of truth in-repo.

## Version chrome

- Source of truth: `GET /api/v1/health` → `version` (backend `__version__`).
- **Desk:** element in rail footer (e.g. `#desk-version`); fill on load; format `v{version}`; if health fails, leave empty or show muted `version unavailable` — never invent.
- **Companion:** muted strip above the primary bottom tab bar; same rules.
- When shipping this release, bump companion `package.json` `version` to match backend so package metadata is not stale; **chrome still displays backend health version**.

## HQ keyboard access

For isometric room groups, plan room rects, and worker markers already clickable:

- `tabindex="0"`, `role="button"`, meaningful `aria-label`.
- `keydown` Enter/Space → `preventDefault` + same handler as click.
- Visible focus via shared `--focus-ring` / `:focus-visible` on `[data-room-id]` and `[data-worker-id]`.
- List view remains the existing accessible path; no change to invent occupancy.

## Light polish

Apply only through tokens and small spacing tweaks on existing rail / tabs / cards. Do not restructure the companion shell or desk grid.

## Authority / honesty

- Version is read-only projection of health.
- Furniture/tiles remain projections of persisted headquarters data (P4 furniture unchanged except keyboard attrs).

## Testing

- Tokens file exists and contains `--cosmic` / `--focus-ring`.
- Desk HTML links `/static/cosmic-glass-tokens.css`; TestClient `GET /static/cosmic-glass-tokens.css` → 200.
- Companion CSS imports the shared file (source assertion).
- Desk source assertions: `#desk-version`, `tabindex`, `role="button"`, Enter/Space handler.
- Companion source assertions: version chrome above tabs.
- Full `unittest discover`; companion `npm run build`.

## Acceptance

1. Desk and companion show backend version in primary chrome (not only Diagnostics).
2. HQ plan/iso tiles (and worker markers) are focusable and activate with Enter/Space.
3. One shared tokens file drives colors/focus for both surfaces.
4. No invented operational or version state.
5. ADR-041 documents shared tokens; M10-04 checkboxes closed; handoff points next.

## Follow-on (not P5)

Marketing layout; deeper visual redesign; remote worker agent.
