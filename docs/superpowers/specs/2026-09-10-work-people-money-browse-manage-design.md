# Design: Work / People / Money Browse–Manage structure

Date: 2026-09-10. Status: **implemented in v0.3.66**.

## Goal

Finish the companion cascade after the Home CEO spine: bring **Work**, **People**, and
**Money** to a clear Browse / Manage structure without inventing metrics, changing APIs,
or redesigning desk/`welcome`.

## Owner locks

| Topic | Choice |
|---|---|
| Track | A — deep layout polish inside Work / People / Money |
| Depth | A — structure first (hierarchy + extract panels) |
| Width | A — all three domains in one release |
| List vs forms | A — Browse / Manage switcher |
| Delivery | 1 — shared shell + extract panels |

## Non-goals

- New control-plane APIs or invented summary metrics.
- Desk sidebar / five-domain desk IA.
- Heavy project master-detail beyond today’s Details flow.
- Nested Browse/Manage inside Finance’s existing Overview · Invoices · Adjustments · Periods switcher.
- Native Expo shell changes.
- Welcome hero or brand-font redo (already 0.3.65).

## Pattern

Each structured panel (except Finance) exposes a local segmented control:

- **Browse** (default) — lists and in-row actions (open, decide, accept, enable/disable, …).
- **Manage** — create / enroll / assign / configure forms.

Mode is **local React state** per panel. Switching Work’s Projects · Corporate · Workers
sub-tab (or leaving People) may reset to Browse; no URL routing required.

Missing-scope notices stay on the surface that owns the control.

## Browse / Manage map

| Panel | Browse | Manage |
|---|---|---|
| Projects | Project list + Details (dispatch, budgets) | Local enroll, GitHub assign, enroll form |
| Corporate | Scorecard, objectives, packs, divisions, promotions, staffing, cross-dept, activity (read + in-row decisions) | Create objective, propose division, create cross-dept request, floorplan default, staffing scan |
| Workers | Host list + enable/disable/delete | Create host + one-time token |
| People (Org) | Catalog/roster, head inbox + in-row assign | Dept/head/position CRUD, reorder, vacate/release, activate, worker card load |
| Money | Existing Finance sub-tabs unchanged; list/overview remain the browse surface | Create flows remain on their Finance sub-tabs (no second mode layer) |

All current capabilities remain available — only regrouped.

## Components

| File | Role |
|---|---|
| `companion/src/ModeSwitch.tsx` (or equivalent) | Reusable browse/manage segmented control |
| `companion/src/ProjectsPanel.tsx` | Extracted from `App.tsx` |
| `companion/src/CorporatePanel.tsx` | Extracted from `App.tsx` |
| `companion/src/OrgPanel.tsx` | People / organization extracted from `App.tsx` |
| `companion/src/WorkersPanel.tsx` | Add Browse/Manage around existing UI |
| `companion/src/FinancePanel.tsx` | Lede/copy clarity only |
| `companion/src/App.tsx` | Data load, scopes, Work segmented, wire panels |
| `companion/src/styles.css` | Minimal panel-mode / section-head reuse |

Props follow `HomePanel` / `FinancePanel`: pass `api`, scopes helpers, `runAction`, `status`,
`scopeNotice`, and the data slices each panel needs — do not move `refresh()` ownership
out of `App` in this release unless a panel clearly owns a private fetch (Workers/Finance
already do).

## Failure modes

| Case | Behavior |
|---|---|
| Empty lists | Honest empty copy; no placeholder rows |
| Missing scopes | Inline notice; no silent domain hide |
| Offline | Existing companion offline banner |

## Verification

- Source tests: panels exist; Browse/Manage (or mode) markers; Finance has no nested Browse/Manage.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: each Work sub-tab Browse/Manage; People; Money sub-tabs; scope gating intact.

## Docs / release

- Update `docs/24-mobile-companion.md`, `docs/11-user-experience.md` (brief), ADR, roadmap, handoff.
- Version **0.3.66**. No Alembic.

## Follow-ups (deferred)

- Deep visual polish / master-detail project UX.
- Desk IA alignment to five companion domains.
- Extract Decision/Inbox card shared components (noted in 0.3.65 review).
