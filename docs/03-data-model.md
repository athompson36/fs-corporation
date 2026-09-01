# Domain model and events

## Planned authoritative entities

| Entity | Key information | Invariant |
|---|---|---|
| Company | ID, owner, CEO mode, currency, paused state | Root owner cannot be replaced by an agent |
| Department | Mission, head position, measures, budget | Organization is persistent, not a workflow run |
| Position | Department, responsibilities, required capabilities | Position independent of assigned model |
| Assignment | Position, model profile/version, effective time | Historical runs retain original assignment |
| PolicyVersion | Immutable body, parent version, approver, rationale | Atomic activation; no silent mutation |
| Delegation | Grantor/grantee, parent, scope, expiry, limits | Child authority never exceeds parent |
| Project | Upstream/fork IDs, branch policy, brief, classification | Enrollment requires explicit scope |
| Task | Owner, dependencies, state, inputs, output hashes | State transition validated and idempotent |
| WorkOrder | Task, policy/model versions, max cost, workflow digest | Immutable execution envelope |
| Approval | Decision type, exact payload hash, approver, expiry | Single use; valid current authority |
| BudgetAccount | Scope, period, limit, reserved and actual amounts | Atomic check and reservation |
| Artifact | Hash, storage URI, producer, version, license/data class | Acceptance binds exact bytes or commit |
| Evidence | Check type, outcome, source, timestamps, target hash | Cannot apply to a changed target |
| Signal | Canonical source, source/observed time, fingerprint | Deduped and explicitly untrusted |
| Expansion | Source milestone, plan, budget, contractor, inspection | Completion cannot be counted twice |
| Event | Sequence, actor, correlation ID, payload, timestamp | Persist with state transaction |

## Reference tables

`company/schema.py` and Alembic revisions `0001_initial`, `0002_hardware_skills`, `0003_quality_control` and `0004_employee_development` create settings, policies, proposals, approvals, tasks, ledger, completions, signals, expansions, events (with envelope columns that do not change the audit hash), consultant_proposals, identities, departments, positions, projects, delegations, model profiles/assignments, work orders, queue, outbox, reservations, artifacts, GitHub enrollment/effects, impact briefs, budget periods, memories, command idempotency, benchmark results, consultant review cooldowns, skills, acquired_skills, project_capabilities, learning_assignments, qc_inspections, employees, training_records, performance_goals and performance_reviews. JSON configurations remain seed templates via `seed_catalog` / `seed_models` / `seed_hardware_skills` / `seed_development_skills`.

The ledger currently records synthetic integer costs immediately within a mock action. It is cumulative for the database lifetime and is not a monthly budget. Policy changes never reset that total. Production reservations, billed reconciliation, refunds and period rollover are M3/M7 work.

## Proposed state machines

Task: proposed → scoped → approved → queued → running → awaiting_review → accepted. Side paths: needs_changes, blocked, failed, cancelled. A resumed/retried task rechecks effective authority and records a new attempt, while preserving its logical idempotency key for external effects.

Policy: draft → proposed → approved → active → superseded. Rejection and withdrawal preserve the proposal. Rollback creates a new approved version restoring earlier content; it never deletes intervening history.

Expansion: proposed → costed → approved → provisioning → inspection → built. A failed inspection blocks capability activation. Pure animation progress is not operational completion.

Reference implementation uses a subset: produced/accepted tasks and proposed/approved/built expansions.

## Event envelope (target)

```json
{
  "event_id": "uuid",
  "event_type": "project.accepted",
  "schema_version": 1,
  "company_id": "company-id",
  "project_id": "project-id",
  "actor_id": "authenticated-principal",
  "policy_version": 4,
  "correlation_id": "command-id",
  "occurred_at": "2026-09-01T12:00:00Z",
  "payload": {"artifact_hash": "sha256", "evidence_ids": ["evidence-id"]}
}
```

Events include policy.proposed, policy.approved, delegation.revoked, task.queued, task.started, artifact.created, review.completed, project.accepted, budget.reserved, cost.reconciled, signal.ingested, expansion.proposed, room.built, project.hardware_enrolled, skill.learning_assigned, skill.studied, skill.acquired, quality.inspected, employee.hired, performance.goal_set and performance.reviewed. Consumers deduplicate by event ID and resume from persisted cursors.

The reference audit chain detects in-place edits without recomputing hashes. It does not prevent privileged rewriting or detect truncation without a separately stored checkpoint. Production needs externally anchored checkpoints or protected append-only storage.

## Consultant proposal records (0.2.0)

`ConsultantDesk` additively creates `consultant_proposals` with immutable proposal body/digest ID, author, pending/approved/rejected status, approver and rationale. Decisions emit consultant.proposal_submitted/approved/rejected events. Approval itself does not mutate policy or dispatch work. Revision requests, exact current-source revalidation and implementation linkage are future service features.
