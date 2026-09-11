# Design: Companion Projects split + Browse/Manage polish

Date: 2026-09-11. Status: **implemented in v0.3.68**.

## Goal

Ship **Projects Browse as a responsive split pane** (list | selected project workspace)
and apply **medium shared shell polish** (ModeSwitch, section heads, empty states) across
Corporate, Workers, and Organization — without new APIs, URL sync, or Finance Browse/Manage.

## Owner locks

| Topic | Choice |
|---|---|
| Focus | B — Projects-first master-detail + shared shell |
| Projects layout | B — split pane (list left / detail right; stacked on narrow) |
| Detail vs Manage | C — detail = full project workspace (brief, GitHub, dispatch); Manage = enroll/assign |
| Shared shell depth | B — medium (CSS + empty states + consistent titles; no Corporate/Workers/Org restructure) |
| Delivery | 1 — CSS + `ProjectsPanel` layout in place |
| Visual mock | Owner-approved Projects Browse split mockup |

## Non-goals

- URL-synced project selection (`?project=`).
- Nested Browse/Manage on Finance.
- Deep structural redesign of Corporate / Workers / Org.
- New control-plane APIs or invented metrics.
- Native Expo / desk / welcome changes.
- Extracting shared `PanelChrome` / `ProjectBrowseSplit` components (deferred unless
  `ProjectsPanel` becomes unreadable mid-implementation — prefer in-place first).

## Projects Browse

### Layout

- **Wide:** CSS grid/flex split — project list (narrow) | detail workspace (wide).
- **Narrow (~≤720px or existing companion breakpoint):** list stacked above detail.
- Selecting a list row sets `selectedProject` (existing state); selected row shows active
  styling. Wide split does **not** use “← Back”; include a quiet **Clear selection**
  control in the detail header (or list) that sets `selectedProject` to `null`.
- When no project is selected: detail pane shows honest empty copy (“Select a project”) —
  no placeholder fake projects.

### Detail workspace (Browse)

Holds today’s project detail capabilities, regrouped for hierarchy:

1. Identity — id/title, brief, departments, GitHub ids (read).
2. Dispatch workspace — recommend, templates, department budgets, submit (existing forms).

Capabilities unchanged; presentation only (plus split layout).

### Manage

Unchanged capability set: local enroll, GitHub assign, enroll form. May reuse shared
section-head / empty-state styles. ModeSwitch remains at panel top.

## Shared shell polish (medium)

Apply across **Projects, Corporate, Workers, Org** (and light Finance lede consistency if
trivial):

| Element | Change |
|---|---|
| ModeSwitch | Spacing/alignment with panel title region; keep existing segmented control |
| Section heads | Consistent `.section-head` / muted lede pattern |
| Lists | Tighter row density; selected/active affordance where selection exists |
| Empty states | Short honest copy when lists are empty (no invented rows) |

Finance: **no** Browse/Manage layer; optional lede/spacing only if it shares the same CSS
tokens without special casing.

## Delivery

| Path | Role |
|---|---|
| `companion/src/styles.css` | Split layout, list/empty/section polish |
| `companion/src/ProjectsPanel.tsx` | Browse split markup; keep Manage block |
| `companion/src/{Corporate,Workers,Org}Panel.tsx` | Empty/title polish only as needed |
| `tests/test_*` | Source contracts for split markers / empty copy |
| Docs | UX brief, ADR, roadmap, handoff; version **0.3.68** |

## Failure modes

| Case | Behavior |
|---|---|
| Empty project list | List empty copy; detail stays “Select a project” |
| Detail load failure | Existing error/status pattern; do not invent project fields |
| Missing scopes | Existing scope notices; dispatch/enroll remain gated |
| Narrow viewport | Stacked split; no horizontal overflow |

## Verification

- Source tests: Browse split markers (e.g. `project-browse-split` / list+detail structure);
  Manage still enroll/assign; no Finance ModeSwitch.
- `cd companion && npm run build`
- `.venv/bin/python -m unittest discover -s tests`
- Manual: Projects Browse select/deselect; dispatch still works; Manage enroll; Corporate/
  Workers/Org empty states; Finance tabs unchanged.

## Follow-ups (deferred)

- URL-synced selection.
- Extract reusable split/chrome components.
- Deep Corporate/Workers/Org hierarchy polish.
- Projects list filters/search (not requested).
