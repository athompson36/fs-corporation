# Design: Desk Organization session mutate gate (0.3.83)

Date: 2026-09-14. Status: **approved for planning** (owner locks below).

## Goal

Fail-close Organization Manage forms on the CEO desk until
`/api/v1/session` confirms `organization.write`, matching the Finance
init/session pattern from 0.3.80–0.3.82.

## Owner locks

| Topic | Choice |
|---|---|
| Cluster | Desk forms sharing one known scope |
| Scope | `organization.write` |
| Forms | Organization Manage in `#departments` only (seven submit chips) |
| Depth | Markup `disabled` + visible notice + init disable + session enable + 403 backup |
| Session | One shared `GET /api/v1/session` applying Finance (`company.pause`) and Org (`organization.write`) |
| Version | **0.3.83** |

## Non-goals

- Gating objectives, cross-department, division proposals, staffing-scan, dispatch, or pairing.
- Companion OrgPanel behavior beyond version lockstep.
- New APIs, Alembic, ModeSwitch.
- Changing Finance pause rules beyond sharing the session fetch.

## Problem

Org Manage submit chips stay enabled until `submitOrgCommand` gets a 403.
Finance already fail-closes from first paint via session scopes; Org should match.

## Behavior

### Markup (`#departments`)

1. Add visible notice (no `hidden`):
   ```html
   <p id="org-scope-notice" class="muted">Mutations require organization.write.</p>
   ```
   Place after the section intro muted paragraph (before `#org-list` or before the first Manage form — prefer immediately before the first Manage form so catalog list stays above the notice).
2. Ensure each Manage submit has a stable id and ships `disabled`:
   - `desk-org-create-dept-submit` — Create department
   - `desk-org-appoint-head-submit` — Appoint head
   - `desk-org-vacate-head-submit` — Vacate head
   - `desk-org-assign-position-submit` — Assign position
   - `desk-org-release-assignment-submit` — Release assignment
   - `desk-org-create-position-submit` — Create position
   - `desk-org-reorder-submit` — Reorder

### JS

1. `setOrgMutateEnabled(enabled)` — toggle `#org-scope-notice.hidden` and the seven submit `disabled` flags (mirror `setFinanceMutateEnabled`).
2. After the helper is defined: `setOrgMutateEnabled(false)`.
3. Refactor session apply so a single `GET /api/v1/session` (existing call site before `loadFinance` / during `load`) sets:
   - Finance via `company.pause`
   - Org via `organization.write`
   On non-OK or catch: both fail closed (`setFinanceMutateEnabled(false)` and `setOrgMutateEnabled(false)`).
4. Prefer renaming `applyFinancePauseFromSession` to something shared (e.g. `applySessionScopes`) **or** keep the name and have it also apply org — either is fine if call sites and contracts stay clear.
5. `submitOrgCommand`: on `res.status === 403`, call `setOrgMutateEnabled(false)` (and still show error text). Do not invent a success path that re-enables without session.

### Out of scope forms

Even if they call `submitOrgCommand` today, do **not** gate in this slice:

- Cross-department create, division proposals, objective create
- Staffing scan button
- Dynamic head-inbox / promotion / staffing in-row actions

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + helpers + shared session + 403 |
| `tests/test_desk_org_session_gate.py` | Source contracts + version **0.3.83** |
| Soften | Exact `0.3.82` pins → `0\.3\.\d+` where they fail |
| Docs | ADR-065, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.83** |

Branch: `feature/desk-org-session-gate`.

## Verification

- Source contracts: org notice visible; seven ids with `disabled`; init `setOrgMutateEnabled(false)`; session applies `organization.write`; Finance session/`company.pause` still present; `submitOrgCommand` 403 disables org; no new APIs.
- Full `unittest discover`; `cd companion && npm run build`.
- Manual: cold desk → org submits disabled + notice; owner token with write → enable; token without `organization.write` → stay disabled.

## Follow-ups (deferred)

- Gate other desk sections that use `submitOrgCommand` or related scopes.
- Broader shared desk session-cache for all mutate UIs.
