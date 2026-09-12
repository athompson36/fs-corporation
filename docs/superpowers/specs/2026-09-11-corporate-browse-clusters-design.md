# Design: Corporate Browse clusters + narrow sub-tabs

Date: 2026-09-11. Status: **implemented in v0.3.71**.

## Goal

Group Corporate Browse into labeled clusters and, on narrow viewports only, switch
among those clusters with a segmented control — plus light Manage `section-head`
titles — without new APIs, URL sync, or Manage regrouping.

## Owner locks

| Topic | Choice |
|---|---|
| Track | Corporate Browse groups/sub-tabs |
| Pattern | Hybrid — labeled scroll groups + sub-tabs when needed |
| Clusters | Strategy · Structure · People · Coordination |
| Sub-tab trigger | Viewport — sub-tabs when width &lt; 720px; labeled scroll when ≥ 720px |
| Manage | Light titles only (`section-head` outside cards); no Manage clusters |
| Delivery | In-place `CorporatePanel` + existing `.segmented` / 720px breakpoint |

## Non-goals

- URL-synced cluster or project selection.
- Manage visual groups / sub-tabs.
- Shared `PanelSection` / `ClusterSwitch` extraction.
- Finance ModeSwitch, desk/welcome changes.
- New APIs, Alembic, invented scorecard UI, capability changes.
- Projects list-row HTML nit (deferred).

## Browse clusters

| Cluster | Sections (unchanged content) |
|---|---|
| Strategy | CEO scorecard, Objectives |
| Structure | Industry packs, Divisions |
| People | Pending promotions, Staffing proposals |
| Coordination | Cross-department requests, Open activity |

### Wide (≥720px)

- Single scroll showing all four clusters.
- Each cluster has a `div.cluster-head` with an `h2` label above its existing
  per-list `section-head`s (distinct class so contracts can tell cluster labels
  from list titles).
- No segmented cluster control.

### Narrow (&lt;720px)

- `.segmented` control with `role="tablist"` and labels Strategy · Structure ·
  People · Coordination.
- Shows **one** cluster at a time; default **Strategy**.
- Selection is local React state only (no URL). Remember last cluster while the
  viewport stays narrow; remount may reset to Strategy.
- Keep the cluster label inside the active pane (same pattern as wide).
- `matchMedia("(min-width: 720px)")` with subscribe/cleanup; crossing the
  breakpoint switches layout immediately.

Cards, `panel-empty` copy, in-row decide/accept/close/activate actions, and
scope notices stay as today.

## Manage

Move each Manage title into a `section-head` **above** its card/form (Org pattern):

- Corporate operations
- Create objective
- Propose division
- Create cross-department request

Do not reorder forms or change fields/`runAction` handlers.

## Delivery

| Path | Role |
|---|---|
| `companion/src/CorporatePanel.tsx` | Cluster markup, narrow tablist, Manage section-heads |
| `companion/src/styles.css` | Minimal cluster-head styling if needed (reuse tokens) |
| `tests/test_corporate_browse_clusters.py` | Source contracts |
| Docs | UX brief, ADR-053, roadmap, handoff; version **0.3.71** |

## Verification

- Source tests assert: four cluster labels present; narrow-path tablist strings;
  Manage titles inside `section-head`; version **0.3.71**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: wide = four labeled groups in one scroll; narrow = cluster tabs; Manage
  titles outside cards; in-row actions still work.

## Follow-ups (deferred)

- Projects list-row `div`→`span` / Clear-on-loading polish.
- URL-synced `?project=` (and optional cluster query).
- Shared panel chrome extraction.
- Corporate Manage grouping.
