# Design: Org Browse + Manage title consistency

Date: 2026-09-11. Status: **implemented in v0.3.70**.

## Goal

Bring **Organization** (`OrgPanel`) to the same Browse/Manage title consistency as
Corporate and Workers: every Browse list and Manage form uses `section-head` + honest
`panel-empty` where lists are empty — without regrouping Manage, changing APIs, or
touching other domains.

## Owner locks

| Topic | Choice |
|---|---|
| Track | A — Org polish |
| Depth | B — Browse + Manage titles |
| Delivery | 1 — in-place `OrgPanel` polish |

## Non-goals

- Manage visual groups (Catalog · Seats · Positions).
- Corporate Browse groups/sub-tabs.
- Projects list-row `div`→`span` fix.
- URL-synced project selection.
- New APIs, Finance ModeSwitch, desk/welcome changes.
- Shared `PanelSection` component extraction.

## Browse

| Section | Treatment |
|---|---|
| Departments (organization catalog) | Add `section-head` with title **Departments** above the department cards; keep existing `panel-empty` when empty |
| Head inbox | Already has `section-head` + `panel-empty`; leave behavior (including inline assign) unchanged |

## Manage

Wrap each form title in `section-head` **outside / above** the form card (same pattern as
Workers title outside list card):

- Create department
- Appoint department head
- Vacate department head
- Assign position
- Release assignment
- Create position
- Reorder departments
- Activate dormant department for project
- Worker card

Preserve all fields, `runAction` handlers, and scope notices. Do not reorder forms.

## Delivery

| Path | Role |
|---|---|
| `companion/src/OrgPanel.tsx` | section-head markup only |
| `tests/test_org_browse_manage_polish.py` | Source contracts |
| Docs | UX brief, ADR-052, roadmap, handoff; version **0.3.70** |

## Verification

- Source tests: `Departments` and each Manage title appear inside `section-head`; Head inbox
  still present; ModeSwitch / assign-dispatch markers preserved.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: People → Organization Browse/Manage titles and empty states; assign still works.

## Follow-ups (deferred)

- Manage grouping labels.
- Corporate Browse groups.
- Projects HTML list-row nit / URL sync.
