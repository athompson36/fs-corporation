# Proposed API contract — loopback implementation

Base path `/api/v1`. Implemented by `python3 -m company.service` bound to `127.0.0.1`. This is not a trusted remote API. Actor identity comes from a bearer token. Request bodies may not supply owner/CEO identity; a payload `actor` field is ignored.

| Method and route | Purpose | Required authority |
|---|---|---|
| GET /company | Current company and pause state | company.read |
| GET /dashboard | CEO dashboard: stats, projects, decisions, queues, inbox count | company.read |
| GET /projects | List enrolled projects with summary stats | company.read |
| GET /projects/{id} | Project detail, tasks, timeline, dispatches | company.read |
| GET /decisions/inbox | Unified pending policy, consultant, expansion items | company.read |
| GET /owner-inbox | Owner feedback/escalation requests | company.read |
| POST /owner-inbox | Create owner request (heads need `owner.escalate`) | owner.escalate |
| POST /owner-inbox/{id}/respond | CEO response to open request | company.pause |
| POST /push/subscriptions | Register an HTTPS Web Push endpoint | company.pause |
| POST /push/subscriptions/{id}/revoke | Revoke a push subscription | company.pause |
| POST /projects/{id}/dispatch-brief | Dispatch project brief to department heads | project.enroll |
| GET /events/stream | SSE audit events (cursor query param) | audit.read |
| POST /company/pause | Stop new dispatch | company.pause |
| POST /company/resume | Resume dispatch | company.resume |
| GET /departments | Organization and effective head assignments | organization.read |
| POST /delegations | Propose bounded responsibility grant | delegation.propose |
| POST /delegations/{id}/revoke | Revoke a grant and dependent scopes | delegation.revoke |
| POST /policy-proposals | Submit versioned diff | policy.propose |
| POST /policy-proposals/{id}/decision | Approve/reject/withdraw exact proposal | policy.approve |
| GET /policy-proposals/{id}/diff | Before/after grant diff | policy.propose |
| POST /policy/rollback | Activate a new version restoring earlier content | policy.approve |
| POST /projects | Enroll a selected project; hardware if `platform` or `domain=hardware` | project.enroll |
| GET /projects/{id}/skills | Platform, skill gaps, learning assignments | company.read |
| POST /projects/{id}/tasks | Queue a scoped task | task.create |
| POST /tasks/{id}/dispatch | Dispatch authorized mock execution in-process | task.dispatch |
| POST /tasks/{id}/dispatch-worker | Dispatch through an isolated worker (`runtime`, `scratch_root`, `worker_id`) | task.dispatch |
| POST /tasks/{id}/quality-inspect | Quality Control pass/fail on the exact artifact | quality.inspect |
| POST /tasks/{id}/accept | Accept exact artifact after a passing QC inspection | artifact.accept |
| GET /hr/development | Learning assignments and acquired skills | organization.read |
| POST /employees | Hire with position, attributes and background; assign pertinent training | organization.read |
| GET /employees/{id} | Employee record | organization.read |
| GET /employees/{id}/training | Documented training file and due skills | organization.read |
| POST /training/schedule | Reassign overdue training for active employees | organization.read |
| POST /employees/{id}/goals | Set a performance goal | organization.read |
| POST /employees/{id}/reviews | Record an independent performance review | organization.read |
| GET /employees/{id}/performance | Score trend and goals | organization.read |
| POST /model-assignments | Propose role/provider assignment | model.assign |
| POST /signals | Record source evidence | intelligence.ingest |
| POST /learning/{id}/study | Record HTTPS study evidence for a skill assignment | intelligence.ingest |
| POST /learning/{id}/certify | Independent certification of study evidence (HR or CEO) | artifact.accept |
| POST /expansions | Cost facilities work | facilities.propose |
| POST /expansions/{id}/decision | Approve exact plan | facilities.approve |
| GET /events | Cursor-paginated audit/activity | audit.read |
| GET /headquarters | Event-projected rooms and departments | company.read |
| POST /consultant-proposals | Submit an evidence-backed proposal | consultant.propose |
| GET /consultant-proposals | List consultant proposals | consultant.read |
| POST /consultant-proposals/{id}/decision | CEO approve/reject | consultant.decide |
| POST /consultant-proposals/{id}/revise | New digest; does not mutate the old proposal | consultant.propose |

HTML CEO desk: `GET /` (no auth for the shell page; API reads still require a bearer token).

## Command envelope

Each mutation uses an Idempotency-Key header plus a body containing expected resource/policy version and typed payload. Derive requester identity from the session/service token. Approval commands include proposal digest, decision and reason. Reject changed payloads under the same idempotency key.

Return operation ID, resource version, status and event correlation ID. Validation errors should identify the field and a safe explanation. Use 401 for unauthenticated, 403 for unauthorized, 409 for stale/conflicting state, 422 for invalid input and 429 for rate/queue limits. Do not include credentials or raw private content in errors.

## Concurrency

Use optimistic resource versions and transaction-level budget reservation. Long work returns 202 with an operation resource. Event consumers resume using persisted cursors; SSE/WebSocket events must pass the same project ACLs as REST reads. Never use an event stream as the only persistence mechanism. The current loopback service persists in SQLite and emits SSE at `/api/v1/events/stream`. The mobile PWA polls every 15 seconds as a fallback.

## Approval binding

The production binding includes authenticated principal, company/project/repository IDs, action, branch or target SHA, artifact/workflow digest, max spend, current effective grant/policy versions and expiry. The reference core binds a smaller mock payload and is not sufficient for real GitHub/deployment operations.
