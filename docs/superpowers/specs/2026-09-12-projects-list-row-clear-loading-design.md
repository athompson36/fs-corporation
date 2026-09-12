# Design: Projects list-row HTML + Clear-on-loading

Date: 2026-09-12. Status: **approved for implementation** (target **v0.3.72**).

## Goal

Fix invalid HTML in Projects Browse list rows (`div` inside `button`) and let the
owner clear selection while project detail is still loading — without URL sync,
Manage changes, or new APIs.

## Owner locks

| Topic | Choice |
|---|---|
| Track | Projects list-row HTML nit + Clear-on-loading |
| Width | List-row `span` fix **plus** Clear on the loading card |
| Delivery | In-place `ProjectsPanel` markup (+ minimal CSS) |

## Non-goals

- URL-synced `?project=` selection.
- Clear on the empty “Select a project” pane.
- Manage visual groups / Corporate / Org changes.
- Shared `DetailToolbar` extraction.
- New APIs, Alembic, desk/welcome, Finance ModeSwitch.

## Browse list rows

In `companion/src/ProjectsPanel.tsx`, each project list button keeps:

- `<button type="button" className="list-row …">`
- `<strong>{id}</strong>`

Change brief and blockers lines from:

```tsx
<div className="muted">…</div>
```

to:

```tsx
<span className="muted">…</span>
```

Ensure `.list-row .muted` remains block-stacked (`display: block` in
`companion/src/styles.css` if not already).

## Loading detail

When `selectedProject && !projectDetail`, replace the bare Loading card with:

- `detail-toolbar` containing `<h2>{selectedProject}</h2>` and a **Clear
  selection** button that calls `setSelectedProject(null)` (same control as
  loaded detail).
- A muted “Loading…” line under the toolbar.

Empty state (`!selectedProject`) stays a card with `panel-empty` “Select a
project” and **no** Clear control. Loaded detail toolbar/behavior unchanged
aside from any incidental consistency.

## Delivery

| Path | Role |
|---|---|
| `companion/src/ProjectsPanel.tsx` | `span.muted`; Clear on loading card |
| `companion/src/styles.css` | `.list-row .muted { display: block; }` if needed |
| `tests/test_projects_list_row_clear_loading.py` | Source contracts |
| Docs | UX brief, ADR-054, roadmap, handoff; version **0.3.72** |

## Verification

- Source tests assert: no `<div className="muted">` inside list-row buttons;
  loading branch includes `Clear selection` and `detail-toolbar`; version
  **0.3.72**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: list rows; Clear while Loading…; empty pane unchanged.

## Follow-ups (deferred)

- URL-synced project selection.
- Manage visual groups.
- Shared detail toolbar component.
