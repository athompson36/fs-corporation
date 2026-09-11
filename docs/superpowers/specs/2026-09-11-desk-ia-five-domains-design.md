# Design: Desk IA aligned to five companion domains

Date: 2026-09-11. Status: **implemented in v0.3.67**.

## Goal

Align the CEO desk (`/desk`) information architecture with the companion’s five domains —
**Home · Work · People · Money · More** — by regrouping the left rail and reordering the
long-page sections. No new APIs, no invented metrics, no domain show/hide panes.

## Owner locks

| Topic | Choice |
|---|---|
| Track | Desk IA (not Browse/Manage visual polish) |
| Depth | Nav + section order (single long scroll) |
| Home | Hybrid — metrics + Decisions/Consultant first; HQ stays high; Scorecard under Work |
| Leftovers map | Strict companion-style map (Intelligence / Diagnostics / Activity / Pairing → More) |
| Rail chrome | Grouped rail with nested anchors (always expanded) |
| Delivery | In-place HTML/CSS in `company/service.py` |

## Non-goals

- Domain panes / show-hide sections (companion-tab behavior on desk).
- Browse/Manage modes on desk.
- HQ interaction redesign or new floorplan UX.
- Renaming section `id`s (preserve bookmarks and existing tests).
- Extracting desk markup into a separate template file.
- Companion or `/welcome` nav changes.
- New control-plane APIs or invented summary metrics.
- Alembic / schema changes.

## Information architecture

### Rail (nested under five domain labels)

| Domain | Nested anchors (existing `id`s) |
|---|---|
| **Home** | `#desk` (CEO desk), `#decisions`, `#consultant`, `#hq`, `#status` |
| **Work** | `#scorecard`, `#projects`, `#cross-department`, `#corporate-upgrades`, `#people` |
| **People** | `#departments` (Organization), `#head-inbox` |
| **Money** | `#budget` |
| **More** | `#intelligence`, `#diagnostics`, `#activity`, `#pairing` |

Domain labels are **non-linking** group headings (e.g. `<p class="rail-group">` or
`<span>`). Nested items are normal `href="#…"` anchors. Groups stay **always expanded**
(no `<details>` collapse, no filter mode).

**Decisions / Consultant** appear once in the Home page block and once in the Home rail.
They are **not** duplicated under More (More rail = Intelligence · Diagnostics · Activity ·
Pairing only).

### Main column order (top → bottom)

1. **Home lead:** header + metrics (`#desk`) → Decisions → Consultant → Headquarters
   (`#hq`) → Status. Keep `#room-detail` and `#worker-card` adjacent to HQ (hidden until
   selected; do not invent a new placement).
2. **Work:** Scorecard → Projects → Cross-department → Corporate upgrades → People /
   staffing / promotions (`#people`).
3. **People:** Organization (`#departments`) → Head inbox.
4. **Money:** Budget.
5. **More:** Intelligence → Diagnostics → Activity → Phone pairing.

Local-repo list and other Project-adjacent blocks stay inside or immediately under
`#projects` as today.

## Delivery

| Surface | Change |
|---|---|
| `company/service.py` desk HTML | Regroup `<nav>` into five domains; reorder `<section>` blocks |
| Desk CSS (inline in same file) | Nested rail indent + group label styles; reuse cosmic-glass / brand fonts |
| Desk JS | No behavioral change required if `id`s and form handlers stay intact; fix only if
  reorder breaks a DOM query that assumed sibling order (audit `getElementById` / query
  paths — prefer id-based) |
| Tests | Source contract: domain labels present; key section `id` order matches Home→Work→
  People→Money→More |
| Docs | `docs/11-user-experience.md`, ADR, roadmap/capability if listed, `docs/18-handoff.md` |
| Version | **0.3.67** |

## Failure / edge cases

| Case | Behavior |
|---|---|
| Deep link `#projects` etc. | Still scrolls to the same `id` after reorder |
| Narrow viewport | Existing rail wrap rules; nested groups remain readable |
| Missing live data | Unchanged empty/unavailable copy; no placeholder inventions |

## Verification

- New (or extended) unit test on `GET /desk` HTML for rail domain labels and section-order
  markers.
- Existing desk feature tests that assert substring presence of section ids/forms remain
  green (ids unchanged).
- `.venv/bin/python -m unittest discover -s tests`
- Manual: open `/desk`, walk each nested rail link, confirm scroll targets and forms still
  work (dispatch, org, pairing, diagnostics).

## Follow-ups (deferred)

- Deep visual polish inside companion Browse/Manage panels.
- Optional desk domain panes / less long-scroll.
- Shared Decision/Inbox card extraction (companion follow-up from 0.3.65).
