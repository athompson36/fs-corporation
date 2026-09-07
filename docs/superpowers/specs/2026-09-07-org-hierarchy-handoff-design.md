# Design: Org hierarchy, rules, and project handoff

Date: 2026-09-07. Status: **approved design** (not yet implemented).

## Goal

Unify three gaps into one grant-backed system, implemented in ordered milestones:

1. **Org roster** — departments ↔ head principals ↔ specialists (routing/staffing facts).
2. **Rules** — compiled hard checks (activation, seats, roster, grant scopes) on assign/approve/dispatch.
3. **Handoff** — dispatch → head inbox → head assigns → execution queue, without inventing operational state.

## Spine (Approach B)

**Grants and delegations remain the only permission source.** Org edges and titles never authorize alone. Execution-plane workers (containers/subprocesses) stay infrastructure, not org-chart employees.

Authority chain: human owner → CEO (`human-ceo`) → grants → delegations (depth ≤ 2) → specialists. Fail closed for unknown scope, vacant head, dormant department, missing roster membership, stale approval, or revoked grant.

## Current reality (baseline)

- Departments are seeded from `config/departments.json`; `head_title` is a label, not a principal.
- `dispatch_project_brief` writes `project_dispatches` + `work_orders` but does not fill a head inbox, assign specialists, or create grants.
- No supervisor org-chart tables; documentation (`docs/04-governance.md`, `docs/05-organization.md`) describes richer head queues and cross-dept work orders than code enforces.
- Existing `employees` / training tables remain for hire/training; they do not grant authority.

## Authority model

| Fact | Authorizes? |
|---|---|
| Department catalog title | No |
| `department_seats` / `reports_to` | No (routing and display only) |
| Active grant/delegation with matching action + project + department scopes | Yes |
| CEO / owner | Yes, within existing CEO/admin-companion rules |

Natural-language org rules stay **proposals** until compiled into grant fields and code checks. Ambiguous rules are not activated.

**Non-goals:** deriving permission from reporting lines; auto-grants on dispatch; auto model runs on dispatch; treating container workers as employees.

## Org roster (data)

Catalog remains seed truth: `config/departments.json` → `departments` + `positions`.

### Proposed tables

**`department_seats`**

- One active head seat per department (enforced).
- Columns (proposed): `id`, `department_id`, `principal_id` (nullable when vacant), `title`, `status` (`active` | `vacant` | `dormant`), `appointed_by`, `appointed_at`, `vacated_at`.

**`position_assignments`**

- Specialist bound to a catalog position.
- Columns (proposed): `id`, `position_id`, `department_id`, `principal_id`, `status` (`active` | `released`), `reports_to_seat_id` (optional, informational), `assigned_by`, `assigned_at`, `released_at`.

**Link to `employees`:** when an employee acts as a principal, link via principal/employee mapping or shared id convention; do not duplicate permission in employee rows.

### Lifecycle

- **Appoint / vacate head:** CEO or grant with `org.appoint_head`. Emits events. Does **not** imply a grant unless the same transactional command explicitly creates one.
- **Assign / release specialist:** CEO or grant with `org.assign_position`.
- **Vacant head:** department may appear in catalog; head assign/approve fails closed.
- **Dormant department:** no continuous model cost; dispatch rejected unless CEO **activates** the department for that project first.
- Optional demo seed mapping title→principal only when owner opts in — never invent seats as healthy in status/diagnostics.

## Project handoff pipeline

```
CEO dispatch brief
  → project_dispatches + work_order (authorized)
  → head inbox item for seated head (or blocked_vacant_head)
  → head assigns specialist (grant + roster checked)
  → assignment record + optional queue row (execution plane)
  → evidence / QC / accept (existing paths)
```

### Dispatch status (proposed)

| Status | Meaning |
|---|---|
| `queued_for_head` | Dispatch written; head seat active; awaiting head |
| `blocked_vacant_head` | Dispatch written; head vacant; not assignable |
| `assigned` | Specialist assigned; work order linked |
| `in_progress` | Execution started / queue claimed |
| `blocked` | Waiting on dependency, approval, or budget |
| `ready_for_qc` / `accepted` / `rejected` | Tie into existing QC / accept |

### Dispatch rules (tighten `dispatch_project_brief`)

- Actor: CEO / admin-companion (unchanged).
- Reject unknown departments.
- Reject **dormant** departments unless activated for the project.
- Require **per-department budgets** in the payload (or explicit split) to avoid Finance double-counting later.
- When head seat is `active`, create head-inbox row bound to `dispatch_id`, `department_id`, head `principal_id`.
- When vacant, status `blocked_vacant_head` + event; no invented assignee.

### Head assign (new command)

- Actor is seated head for that department **or** CEO; **and** grant covers assign/approve for project+department.
- Assignee must be on `position_assignments` for that department **or** hold an explicit contractor grant for the project — fail closed otherwise.
- Writes assignment; may enqueue `queue` for execution plane; still runs policy/budget checks.
- Does not skip QC or acceptance.

### Cross-department work orders

Schema fields reserved for requesting department, delivering department, budget owner, due date, acceptance criteria, escalation path. Create/accept can trail milestone 1–4 if needed; Marketing→Art style requests must not use side-channel chat as authority.

## Rules (compiled checks)

Hard checks in application code / action gateway:

1. **Department activation** — dispatch and continuous work only if active for company or activated on the project.
2. **Seat occupancy** — head assign/approve requires active seat for actor (CEO may appoint/vacate and emergency-reassign).
3. **Roster membership** — assign target on department roster or explicit contractor grant.
4. **Grant intersection** — child ⊆ parent; project + department scopes required for handoff work.
5. **Approval rights** — head approves subordinate work only with `approval_rights` for that action class.
6. **Budget** — per-dispatch / per-assignment reservation; no silent shared pool across departments.
7. **Dormant cost** — vacant/dormant seats do not enqueue model work; inbox may still show blocked.
8. **Revocation** — vacate seat or revoke head grant blocks/cancels descendant queued assignments (same spirit as `revoke_delegation`).

### Default compiled action sets (seed templates — not auto-granted)

| Role | Example actions |
|---|---|
| Head | `work.assign`, `work.approve` (dept), `owner.escalate`, dept/project read |
| Specialist | `task.execute` / invoke within project+dept; no redelegate unless grant says so |
| CEO | existing + `org.appoint_head`, `org.assign_position`, `org.activate_department` |

Rule amendments: heads propose diffs via existing policy proposal flow; CEO approves a specific version; activation increments policy version and revalidates queued work.

## API (proposed)

| Method | Purpose | Auth note |
|---|---|---|
| `GET /api/v1/org` | Departments, seats, assignments, activation | `organization.read`; honest vacant/dormant |
| `POST /api/v1/org/heads` | Appoint / vacate | `org.appoint_head` or CEO |
| `POST /api/v1/org/assignments` | Assign / release specialist | `org.assign_position` or CEO |
| `POST /api/v1/projects/{id}/activate-department` | Activate dormant dept for project | CEO / scoped grant |
| `POST .../dispatch` (existing) | Tightened brief dispatch | CEO / admin-companion |
| Head inbox read | List `queued_for_head` / blocked for actor | authenticated principal |
| `POST /api/v1/dispatches/{id}/assign` | Head assigns specialist | seat + grant |

Actor identity remains outside model inputs (bearer → principal). Idempotency keys on appoint/assign/dispatch commands.

## UI (desk + companion)

- **Org view:** catalog + seat status + roster; vacant is vacant.
- **Project handoff:** dispatches with status; Assign when head or CEO.
- HQ / building remains an **event projection** — no invented busy workers from vacant seats.
- Diagnostics must not invent healthy org state.

## Implementation milestones

1. **Roster + seed** — migrations, appoint/vacate/assign APIs, unit tests; optional opt-in demo principal map.
2. **Rules wiring** — activation, seat, roster, grant checks on assign/approve/dispatch.
3. **Handoff** — dispatch status + head inbox + assign → queue.
4. **UI** — desk + companion org/inbox; update capability matrix, roadmap, decisions, handoff.
5. **Cross-dept WO** — schema fields + create/accept (may trail).

## Testing (acceptance)

- Vacant head cannot assign; dormant dept dispatch rejected without activation.
- Roster miss fails; grant without project/department scope fails.
- Revoke / vacate blocks descendant queue work.
- Appoint/assign/dispatch idempotent under same key.
- Events emitted for seat, assignment, dispatch status, assign.
- Existing deny/stale/pause/overspend tests still pass.
- No invented healthy seats in org or diagnostics reads.

## Limitations

- Live model execution inside worker containers remains opt-in and fail-closed.
- This design does not configure live credentials or change ChatDev pin.
- Cross-department automation beyond reserved schema may follow after core handoff works.

## Doc touchpoints on implement

Update `docs/05-organization.md` / `docs/04-governance.md` only to mark what is **implemented** vs still design; `docs/03-data-model.md`, `docs/14-roadmap.md`, `docs/18-handoff.md`, `docs/decisions.md`, README capability matrix.
