# Organization and operating rhythm

The company blueprint includes Executive, Product, Engineering, Quality Control, Art/Design, Media/Audio, Marketing, Sales/Partnerships, Finance, Legal/Compliance, Human Resources, IT/Security, Facilities/Procurement and Customer Success. The canonical department catalog, initial activation flags, heads, specialist positions and measures are in `config/departments.json`. Prompts exist for each department in `prompts/departments/`. Human Resources retains catalog id `people`.

## Implemented organization handoff

The reference core persists one head seat per catalog department plus active specialist
assignments. `GET /api/v1/org` exposes the catalog, honest `active` / `vacant` / `dormant`
seat state, and roster. The desk and companion render those records without turning vacant
seats into activity. CEO/admin companions can explicitly activate a dormant department for
a project. Dispatch requires an explicit budget for each department; occupied heads receive
persisted inbox items and can assign rostered or project-granted specialists through the
grant-checked queue path.

Corporate HQ Phase 7 adds persisted industry-pack templates and approval-gated divisions.
The Master Consultant, CEO, or a currently seated department head may propose a minimal or
full division. Only the CEO/admin companion may activate it. Activation atomically creates
missing departments and positions, links the division roster, seeds pack skills and company
learning assignments, and creates a division-tagged floorplan. Deactivation fails closed while
any linked department has an open dispatch or cross-department request.

Corporate HQ Phase 8 adds CEO/admin-authored objectives and a CEO scorecard derived only
from persisted acceptance events, QC inspections, dispatches, reservations/ledger entries,
billed costs, and revenue. Objectives express direction but do not alter measured metrics;
the Desk explicitly labels the scorecard as operational measurement, not simulation.

## Department head responsibilities

Maintain the department queue, translate CEO objectives into deliverables, estimate resources, assign capable workers, review evidence, coordinate dependencies, report outcomes and propose process/staffing changes. Heads own results within their mandate; they do not invent project goals or create permissions by consensus.

Cross-department requests are persisted separately from execution work orders with explicit
requesting and delivering departments, subject/brief, budget owner, due date, acceptance
criteria, escalation path and integer-cent budget. A seated requesting head may create one;
the current seated delivering head may list and accept it. CEO/admin companions may create,
list and accept as an explicit override. Unknown departments, dormant delivery without
project activation, and vacant-head acceptance fail closed. A shared specialist may belong
to one position with several project assignments; permissions remain task-specific.

Quality Control inspects product artifacts before acceptance. Human Resources oversees employee development and training, including hire records, documented training files, performance goals and reviews. See [21-quality-hr.md](21-quality-hr.md) and [22-employee-development.md](22-employee-development.md).

## Start small, preserve the full blueprint

Initial active departments: Executive, Engineering, Quality Control, Art, Marketing, Finance, Facilities and Human Resources. Product responsibilities may be fulfilled by approved temporary roles until dedicated staffing is justified. Activate other departments when a project actually requires them. A dormant department retains records but incurs no continuous model cost.

## Staffing lifecycle

Identify gap → propose role and measured workload → evaluate model/tool candidates → approve assignment and budget → run trial tasks → review quality/cost → activate or revise. Store role version and model assignment separately. A model change must pass the role's regression fixtures before promotion. HR certifies training evidence; Quality Control inspects product output.

## Operating rhythm (configurable, not scheduled by this bundle)

Daily: exception-driven queue and blocked-work review. Weekly: portfolio priorities, budget and evidence review. After each accepted project: retrospective, reusable artifacts and growth assessment. Monthly: model/provider benchmark and delegation expiry review. Use summaries and event triggers rather than meetings involving every agent.

## Practical measures

Prefer accepted artifacts, time to acceptance, defect escapes, revision burden, budget adherence and customer outcomes. Do not reward message count, apparent busyness, agent count or building size. Qualification of a lead or trend should not be labeled revenue. Finance maintains separate actual, estimated and simulated accounts.
