# Design: Manage visual groups (hybrid) across Work/People Manage

Date: 2026-09-12. Status: **implemented in v0.3.74**.

## Goal

Group Manage forms on Organization, Corporate, Projects, and Workers behind shared
hybrid cluster chrome (labeled scroll on wide viewports; segmented group tabs on
narrow) — without URL sync, new APIs, or changing form handlers.

## Owner locks

| Topic | Choice |
|---|---|
| Width | All Manage panels that lack groups (Org, Corporate, Projects, Workers) |
| Pattern | Hybrid — labeled scroll ≥720px; group sub-tabs &lt;720px |
| Implementation | Extract shared `useWideViewport` + `ManageClusters` chrome |
| Delivery | One release wiring all four panels |

## Non-goals

- URL sync for Manage group selection.
- Regrouping Corporate **Browse** clusters (Strategy · Structure · People ·
  Coordination stay; only share `useWideViewport`).
- Finance ModeSwitch / nested modes.
- New APIs, Alembic, desk/welcome.
- Empty-list unknown-project URL edge nit.

## Shared chrome

| Path | Role |
|---|---|
| `companion/src/useWideViewport.ts` | `matchMedia("(min-width: 720px)")` hook (exact string for contracts) |
| `companion/src/ManageClusters.tsx` | Tablist + cluster-head wrappers |

`ManageClusters` props (conceptual):

- `ariaLabel: string` — e.g. `"Organization manage groups"`
- `groups: { id: string; label: string; content: ReactNode }[]`
- `defaultGroupId?: string` — default first group

Behavior:

- **Wide (≥720px):** render every group with a `div.cluster-head` + `h2` label
  above its content; no segmented control.
- **Narrow (&lt;720px):** `.segmented` `role="tablist"` with group labels; show one
  group; keep `cluster-head` inside the active pane; local React state only.
- Reuse existing `.cluster-head` / `.segmented` CSS; add a generic class such as
  `manage-cluster-tabs` (Corporate Browse may keep `corporate-cluster-tabs` or
  migrate to the shared class).

Corporate **Browse** switches from its private `useWideViewport` to the shared
hook; Browse cluster markup stays in `CorporatePanel`.

## Group membership

### Organization Manage

| Group | Forms |
|---|---|
| Catalog | Create department, Reorder departments, Activate dormant department for project |
| Seats | Appoint department head, Vacate department head, Assign position, Release assignment |
| Positions | Create position |
| Lookup | Worker card |

Default narrow tab: **Catalog**.

### Corporate Manage

| Group | Forms |
|---|---|
| Goals | Create objective |
| Structure | Propose division |
| Coordination | Create cross-department request |
| Ops | Corporate operations |

Default narrow tab: **Goals**.

### Projects Manage

| Group | Forms / blocks |
|---|---|
| Enroll | Local candidates |
| GitHub | Assign GitHub by address |

Default narrow tab: **Enroll**.

### Workers Manage

| Group | Forms / blocks |
|---|---|
| Hosts | Create worker host |
| Token | One-time worker host token card |

When no token is issued, Token group shows an honest empty (`panel-empty`) such as
“No token issued yet.” Lift any remaining bare Manage `<h2>` into `section-head`
(Create worker host / Worker host token). Default narrow tab: **Hosts**.

## Capabilities

Preserve all fields, `runAction` keys, scope notices, and Browse modes. Do not
reorder forms within a group except as required to nest under cluster wrappers.

## Delivery

| Path | Role |
|---|---|
| `companion/src/useWideViewport.ts` | Shared hook |
| `companion/src/ManageClusters.tsx` | Shared chrome |
| `companion/src/OrgPanel.tsx` | Manage groups |
| `companion/src/CorporatePanel.tsx` | Manage groups + Browse uses shared hook |
| `companion/src/ProjectsPanel.tsx` | Manage groups |
| `companion/src/WorkersPanel.tsx` | Manage groups + section-head titles |
| `companion/src/styles.css` | Minimal shared tab class if needed |
| `tests/test_manage_visual_groups.py` | Source contracts |
| Docs | UX, ADR-056, roadmap, handoff; version **0.3.74** |

## Verification

- Source tests: shared module markers; each panel’s Manage group labels as
  `cluster-head` titles; narrow tablist aria-labels; Workers section-heads;
  `matchMedia("(min-width: 720px)")` in shared hook; version **0.3.74**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: wide/narrow Manage on Org/Corporate/Projects/Workers; Corporate Browse
  clusters unchanged in behavior; form submits still work.

## Follow-ups (deferred)

- URL sync for Manage groups.
- Empty-list unknown-project URL edge.
- Behavioral tests for `ManageClusters` / `useWideViewport`.
