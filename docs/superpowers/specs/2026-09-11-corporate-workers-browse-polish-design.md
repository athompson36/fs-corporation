# Design: Corporate + Workers Browse consistency

Date: 2026-09-11. Status: **implemented in v0.3.69**.

## Goal

Finish the medium shell polish for **Corporate** and **Workers** so every Browse list
uses consistent `section-head` titles and honest `panel-empty` empty states, and Workers
matches Projects/Corporate title placement — without regrouping Corporate, touching Org
deeply, or changing capabilities/APIs.

## Owner locks

| Topic | Choice |
|---|---|
| Track | A — Corporate/Workers hierarchy polish |
| Width | B — Corporate + Workers (not Org restructure) |
| Depth | A — consistency pass (no Browse groups or sub-tabs) |
| Delivery | 1 — in-place class/markup polish |

## Non-goals

- Corporate Browse groups or sub-tabs.
- Org panel hierarchy redesign.
- Projects list-row `div`→`span` HTML fix (deferred nit).
- URL-synced project selection.
- New APIs, invented metrics, Finance ModeSwitch, desk/welcome changes.
- Shared `PanelSection` component extraction.

## Corporate

**Browse** (keep single long scroll):

| Section | Treatment |
|---|---|
| CEO scorecard | Keep card; optional `section-head` only if it improves consistency without changing content |
| Objectives | Already has `section-head`; ensure empty uses `panel-empty` |
| Industry packs | Add `section-head` + `panel-empty` when empty |
| Divisions | Add `section-head` + `panel-empty` when empty |
| Pending promotions | Add `section-head` + `panel-empty` when empty |
| Staffing proposals | Add `section-head` + `panel-empty` when empty |
| Cross-department requests | Add `section-head` + `panel-empty` when empty |
| Open activity | Add `section-head` + `panel-empty` when empty |

**Manage:** unchanged forms and capabilities; may keep existing titles.

Preserve all in-row decide/accept/scan actions and scope notices.

## Workers

- Move **Worker hosts** `section-head` **outside** the list card (same pattern as Projects list title / Corporate Objectives).
- Browse: list rows, enable/disable/delete, empty `panel-empty` copy unchanged in meaning.
- Manage: create host + token UI unchanged.

## Delivery

| Path | Role |
|---|---|
| `companion/src/CorporatePanel.tsx` | section-head + panel-empty on Browse lists |
| `companion/src/WorkersPanel.tsx` | title outside card; empty class consistency |
| `tests/test_corporate_workers_browse_polish.py` | Source contracts |
| Docs | UX brief, ADR-051, roadmap, handoff; version **0.3.69** |

## Verification

- Source tests assert each Corporate Browse list title appears inside `section-head` (or
  immediately after a `section-head` wrapper containing that `h2` text), and Workers
  “Worker hosts” `section-head` precedes the hosts card.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: Corporate Browse empty and non-empty lists; Workers Browse title placement;
  Manage still works on both.

## Follow-ups (deferred)

- Corporate Browse visual groups / sub-tabs.
- Org hierarchy polish.
- Projects list-row HTML validity (`span`).
- URL-synced project selection.
