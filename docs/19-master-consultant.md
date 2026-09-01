# Master Consultant — independent company improvement

## Mandate

The Master Consultant advises the CEO about defects and inefficiencies in both the company software and its operating structure. It sits outside department reporting lines and can assess cross-department problems without owning their execution. It has an explicit, configurable model assignment; a stronger reviewer or a bounded multi-model review can be used for consequential recommendations.

Its scope includes the company control code, approved project code, architecture, tests, queues, delegation rules, handoffs, model choices, costs, unused roles, duplicated work and growth proposals. Access is read-only and scoped: company-wide advisory responsibility does not automatically expose every project's private data or secrets.

## What it looks for

| Area | Examples | Evidence required |
|---|---|---|
| Code correctness | Logic bugs, fragile state transitions, error handling | Reproduction or failing test and exact source revision |
| Execution efficiency | Repeated calls, excess retries, unbounded loops | Measured traces, sample sizes and cost baseline |
| Organizational design | Duplicate roles, unclear accountability, unnecessary handoffs | Work histories, delays and responsibility mapping |
| Governance | Conflicting rules, excessive escalations, missing scope | Policy versions and specific denied/delayed work |
| Model assignments | Expensive models on simple tasks, weak review quality | Role benchmark quality/cost comparisons |
| Growth and staffing | Idle departments, expansion without workload | Utilization and capacity evidence |

Separate confirmed defects, measured inefficiencies, heuristic concerns and speculative improvements. A rule match is a reason to investigate, not proof of a bug. A lack of findings is not a clean bill of health.

## Proposal and CEO workflow

Observe approved data → reproduce or measure → create a ranked improvement proposal → CEO reviews evidence, cost and risk → approve/reject/request revision → responsible head prepares a scoped work order → implement on an approved branch → independent validation → CEO/delegated acceptance → compare before/after outcome.

Each proposal includes finding, affected code/policy/roles, exact revision and evidence, recommendation, alternatives, expected benefit, implementation cost, risks, validation and rollback. Prioritize by impact, evidence strength, urgency and effort. Limit proposal volume and deduplicate recurring observations. The CEO can dismiss a known tradeoff rather than repeatedly receive the same advice.

Approval of an idea is not blanket permission to edit code, change policies, dismiss staff, increase budgets or deploy. Those effects still require their ordinary action scopes. If the proposal changes after approval, resubmit it with a new digest. Revalidate stale evidence before implementation.

The consultant must not approve or independently verify its own fixes. It can evaluate outcomes, but acceptance comes from a distinct authorized reviewer. Findings about its own configuration or performance should receive an independent review.

## Review triggers (future runtime configuration)

Manual CEO request, after accepted projects, after repeated task failures, after material policy/model changes, and a configurable periodic organizational review. Each review has read scopes, allowed diagnostics, cost ceiling and timeout. These are proposed in-app triggers; no scheduled job is created by the starter.

Avoid constant self-reorganization. Recommend small measurable changes, establish a baseline, run a bounded trial and keep or revert based on results. Organizational changes should not be driven by building size or token usage alone.

## Implemented in version 0.2.0

`python3 -m company.consultant --root .` performs a read-only local heuristic scan of company Python files and selected department/model metadata. It flags syntax errors, bare exception handlers, mutable default arguments and active departments without an enabled default routing candidate. It does not execute scanned code or edit files. It does not review arbitrary user repositories, fetch evidence, benchmark performance or invoke AI.

`ConsultantDesk` persists exact proposal bodies and deduplicates identical author/body submissions. The local CEO can approve or reject a pending proposal with a reason; the author cannot approve their own. Decisions emit audit events and survive restart. Approval does not create tasks or execute fixes. `python3 -m examples.consultant_proposal` demonstrates the full local proposal/decision flow with an explicitly synthetic observation.

The loopback service authenticates consultant principals with `consultant.read` / `consultant.propose` and requires `consultant.decide` for CEO decisions. `revise` creates a new digest. `to_work_order` records an authorized work order without dispatching. Production container isolation, live AI analysis and scheduled triggers remain roadmap work.
