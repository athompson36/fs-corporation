# Design: Desk corporate write forms session gate (0.3.84)

Date: 2026-09-14. Status: **implemented in v0.3.84**.

## Goal

Extend the Organization `organization.write` fail-closed gate to Corporate-adjacent
desk forms that already POST with that scope: Create objective, Create
cross-department request, Propose division — including dynamic Close/Accept row
actions — matching the Finance/Org init + session pattern.

## Owner locks

| Topic | Choice |
|---|---|
| Cluster | Corporate write forms using `organization.write` |
| Depth | Three static submits + dynamic Close objective / Accept cross-dept |
| Notices | One short notice per `#scorecard`, `#cross-department`, `#corporate-upgrades` (same copy as Org) |
| Helper | Extend `setOrgMutateEnabled` (not a separate corporate helper) |
| Version | **0.3.84** |

## Non-goals

- Promotions, staffing-scan, dispatch, pairing, Finance pause rules.
- Companion behavior beyond version lockstep.
- New APIs, Alembic.

## Problem

After 0.3.83, `#departments` Manage fails closed on `organization.write`, but
objective / cross-dept / division create chips (and Close/Accept row actions)
stay enabled until 403. They share the same API scope and `submitOrgCommand`
(or equivalent write POSTs).

## Behavior

### Markup

1. Add visible notices (no `hidden`), copy identical to Org:
   ```html
   <p class="muted" data-org-write-notice>Mutations require organization.write.</p>
   ```
   Place in `#scorecard` (before Create objective form), `#cross-department`
   (before Create request form), `#corporate-upgrades` (before Propose form).
2. Add `data-org-write-notice` to existing `#org-scope-notice` as well (keep its id).
3. Static submits — stable ids + `disabled`:
   - `desk-org-create-objective-submit` — Create objective
   - `desk-org-create-cross-dept-submit` — Create request
   - `desk-org-propose-division-submit` — Propose

### JS — extend `setOrgMutateEnabled`

1. Keep toggling `#org-scope-notice` / seven department submits.
2. Also toggle the three new submit ids.
3. Toggle **all** `[data-org-write-notice]` via `hidden = !!enabled` (including
   `#org-scope-notice` if it carries the attribute — avoid double-toggling by
   either querying the attribute set only, or keeping the id path and also
   querying other notices with the attribute excluding the id). Simplest:
   query `[data-org-write-notice]` for all notices; keep explicit id list for
   static submits.
4. Toggle all `[data-org-write]` buttons: `disabled = !enabled`.
5. Keep `setOrgMutateEnabled(false)` at init; session path unchanged
   (`organization.write` in `applyFinancePauseFromSession`).

### Dynamic rows

1. In `renderObjectives`, Close buttons get `data-org-write` and start disabled
   when write is off (call `setOrgMutateEnabled` with current enabled state after
   render, or set `btn.disabled` from a module-level `orgWriteEnabled` flag
   updated inside `setOrgMutateEnabled`).
2. In `renderCrossDept`, Accept buttons get `data-org-write` the same way.
3. On Close/Accept fetch `403`: call `setOrgMutateEnabled(false)` (and show error).

Preferred: `let orgWriteEnabled = false;` updated at the top of
`setOrgMutateEnabled(enabled)`; renderers set `btn.disabled = !orgWriteEnabled`
when creating buttons; after each render batch, no extra session fetch needed.

### Out of scope

Promotions Approve/Reject, staffing scan, dispatch, pairing, Finance.

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + helper + renderers + 403 |
| `tests/test_desk_org_corporate_write_gate.py` | Source contracts + version **0.3.84** |
| Soften | Exact `0.3.83` pins → `0\.3\.\d+` where needed |
| Docs | ADR-066, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.84** |

Branch: `feature/desk-org-corporate-write-gate`.

## Verification

- Source contracts: three section notices + `data-org-write-notice` on org notice;
  three new submit ids disabled; `data-org-write` in objective/cross-dept renderers;
  `setOrgMutateEnabled` lists new ids / attribute queries; 403 paths; version **0.3.84**.
- Full `unittest discover`; companion build.
- Manual: cold desk → objective/cross-dept/division chips + notices fail closed;
  owner with write → enable; Close/Accept respect gate.

## Follow-ups (deferred)

- Promotions / staffing / dispatch session gates.
- Rename `applyFinancePauseFromSession` → `applySessionScopes`.
