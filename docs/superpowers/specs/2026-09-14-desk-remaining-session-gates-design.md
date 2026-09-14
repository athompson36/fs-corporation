# Design: Desk remaining session gates + docs honesty (0.3.85)

Date: 2026-09-14. Status: **implemented in v0.3.85**.

## Program context (not implemented in this ship)

Owner chose audit completion option **C** (code-local slices 1–4), finance depth **B**,
consultant depth **B**, shipping cadence **C** (two ships):

| Ship | Version (planned) | Contents |
|---|---|---|
| **1 (this spec)** | **0.3.85** | Desk remaining session gates + README/VERIFICATION honesty |
| **2 (later)** | TBD | Finance ledger+UI (invoices/refunds/pricing) + Consultant measured before/after |

Skipped from the audit: ops verification, live adapters, deferred room art / Expo parity.

## Goal

Fail-close remaining CEO-desk mutators from first paint using `/api/v1/session` scopes,
matching Finance/Org/corporate write gates (0.3.82–0.3.84), and refresh README +
`VERIFICATION.md` so documentation matches shipped code.

## Owner locks

| Topic | Choice |
|---|---|
| Approach | Extend existing helpers (not generic `data-requires-scope`) |
| Org cluster | Division Activate; promotion Approve/Reject; staffing scan + decisions |
| Org scope | `organization.write` via `setOrgMutateEnabled` / `data-org-write` |
| Dispatch cluster | Dispatch submit + Recommend |
| Dispatch scope | `project.enroll` via new `setDispatchEnrollEnabled` |
| Docs | README capability header/matrix + VERIFICATION current for this ship |
| Version | **0.3.85** |

## Non-goals

- Finance invoices/refunds, billed pricing env UX, period rollover (Ship 2).
- Consultant measured before/after metrics (Ship 2).
- Companion panel behavior beyond version lockstep.
- New APIs, Alembic, ModeSwitch.
- Changing server-side authorization checks (scopes already enforced).
- Ops second-host / phone smoke; live doc-fetch / ChatDev; furnished art; Expo parity.

## Problem

After 0.3.84, many Org writes fail closed from first paint, but:

- Division **Activate** chips stay enabled until 403.
- Promotion Approve/Reject stay enabled until 403.
- Staffing scan + staffing Approve/Reject stay enabled until 403.
- Dispatch submit/recommend use **`project.enroll`**, not `organization.write`, and lack a
  session gate (only dormancy can disable submit).
- README still headlines ~v0.3.80; `VERIFICATION.md` tops out ~0.3.61 while code/fs-dev
  are at 0.3.84+.

## Behavior

### Organization.write cluster

#### Markup (`#people` / corporate-upgrades adjacency)

1. Ensure a visible People/staffing notice (no `hidden` initially) using the same copy:
   `Mutations require organization.write.` Prefer `data-org-write-notice` so
   `setOrgMutateEnabled` already toggles it. If `#people` lacks one, add it near
   pending promotions / staffing scan (before scan button is fine).
2. `#staffing-scan-btn` ships with `disabled` (keep id or add a stable id listed in the
   helper — prefer keeping `staffing-scan-btn` and including it in the id list).

#### Dynamic row actions

When rendering:

- `renderPromotions` — Approve / Reject
- `renderStaffingProposals` — Approve / Reject
- `renderDivisions` — **Activate (CEO)** for `status === 'proposed'`

Each button must:

1. `setAttribute('data-org-write', '')`
2. `disabled = !orgWriteEnabled`
3. On `res.status === 403`, call `setOrgMutateEnabled(false)` (then alert/status as today)

#### Staffing scan

- Click handler: if button disabled or `!orgWriteEnabled`, do not POST (optional status:
  `organization.write required`).
- On 403: `setOrgMutateEnabled(false)`.

#### Helper extension

`setOrgMutateEnabled` already toggles `[data-org-write]` and static corporate ids. Add
`staffing-scan-btn` to the static id list (or equivalent). No separate org helper.

### project.enroll cluster (dispatch)

#### Markup (`#projects` / `#dispatch-form`)

1. Visible notice (no `hidden` initially):
   ```html
   <p id="dispatch-scope-notice" class="muted">Mutations require project.enroll.</p>
   ```
   Place near the Dispatch actions row (before or after the action chips).
2. `#dispatch-submit-btn` and `#dispatch-recommend-btn` ship `disabled`.

#### JS

1. `let dispatchEnrollEnabled = false;`
2. `setDispatchEnrollEnabled(enabled)` — set flag; toggle `#dispatch-scope-notice.hidden`;
   set recommend `disabled = !enabled`; call existing dormancy-aware submit updater so
   submit is disabled if **either** enroll missing **or** a checked department is
   non-dispatchable.
3. Immediately after defining the helper: `setDispatchEnrollEnabled(false)`.
4. Session apply (shared `GET /api/v1/session` used for Finance/Org): also
   `setDispatchEnrollEnabled(scopes.indexOf('project.enroll') !== -1)`.
   On non-OK or catch: `setDispatchEnrollEnabled(false)` alongside existing Finance/Org
   fail-closed.
5. Prefer renaming `applyFinancePauseFromSession` → `applySessionScopes` **or** keep the
   name and extend it (same as 0.3.83 guidance); either is fine if call sites stay clear.
6. Dispatch form submit and recommend click: on `res.status === 403`,
   `setDispatchEnrollEnabled(false)`.
7. When dormancy logic sets submit disabled, do not clear enroll notice incorrectly —
   notice reflects enroll only; dormancy message stays in `#dispatch-status`.

### Documentation honesty (same version)

1. **README** — update deliverable status / capability matrix header from stale ~0.3.80
   language to **0.3.85**, summarizing desk session gates through Org write + project
   enroll dispatch (keep entries honest: mock vs live opt-in unchanged).
2. **VERIFICATION.md** — add a current-ship section for **0.3.85** (test count at ship
   time, desk gate contracts, companion version lockstep). Retain older historical notes;
   do not invent fs-dev claims beyond what is verified at ship time.
3. **ADR-067** — desk remaining session gates (org write dynamic + project enroll).
4. **docs/18-handoff.md**, roadmap/UX touch as needed for the ship.

### Tests

New module (name flexible), e.g. `tests/test_desk_remaining_session_gates.py`:

- People/staffing `data-org-write-notice` (or equivalent) + staffing scan ships `disabled`.
- `renderPromotions` / `renderStaffingProposals` / `renderDivisions` chunks include
  `data-org-write`, `orgWriteEnabled`, and 403 → `setOrgMutateEnabled(false)`.
- Dispatch notice contains `project.enroll`; submit + recommend ship `disabled`.
- `setDispatchEnrollEnabled` present; init `setDispatchEnrollEnabled(false)`.
- Session apply references `project.enroll` and still `organization.write`.
- Version pin: `company/__init__.py` and `companion/package.json` → **0.3.85**.
- Soften prior exact `0.3.84` version assertions to `0\.3\.\d+` where they would fail.

Existing Finance/Org/corporate gate tests must remain green.

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + helpers + session + 403 |
| `tests/test_desk_remaining_session_gates.py` | Source contracts + version **0.3.85** |
| Soften | Exact `0.3.84` pins → flexible where needed |
| Docs | README, VERIFICATION, ADR-067, handoff/roadmap/UX |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.85** |

## Acceptance

1. Without `organization.write`, Activate / promo / staffing / scan are disabled from first
   paint (and after list re-render).
2. Without `project.enroll`, Dispatch and Recommend are disabled from first paint; dormancy
   still blocks submit when enroll is present.
3. Session success enables the correct clusters; 403 fail-closes the matching helper.
4. README and VERIFICATION no longer claim a version older than this ship as “current”.
5. Unit tests for the new contracts pass; full suite green before merge.

## Spec self-review

- No placeholders or TBD behavior for Ship 1 controls.
- Dispatch correctly uses `project.enroll` (not conflated with Org write).
- Ship 2 called out only as context; not specified here.
- Matches prior desk gate patterns (markup disabled + notice + init + session + 403).
