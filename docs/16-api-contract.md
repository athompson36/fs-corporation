# Proposed API contract — loopback implementation

Base path `/api/v1`. Implemented by `python3 -m company.service` bound to `127.0.0.1`. This is not a trusted remote API. Actor identity comes from a bearer token. Request bodies may not supply owner/CEO identity; a payload `actor` field is ignored.

The "Required authority" column is the scope checked at the route. Some routes apply a
**further** identity check inside `company/core.py`; those are listed under
[Checks beyond the route scope](#checks-beyond-the-route-scope). A caller holding only the
listed scope can still receive 403 from those routes.

| Method and route | Purpose | Required authority |
|---|---|---|
| GET /health | Liveness probe: `{ok, version, db}`. No bearer token | — |
| GET /company | Current company and pause state | company.read |
| GET /dashboard | CEO dashboard: stats, projects, decisions, queues, inbox count | company.read |
| GET /projects | List enrolled projects with summary stats | company.read |
| GET /local-repos | List `local repos/` folder candidates (enrolled flag) | company.read |
| GET /projects/{id} | Project detail, tasks, timeline, dispatches | company.read |
| GET /decisions/inbox | Unified pending policy, consultant, expansion items | company.read |
| GET /owner-inbox | Owner feedback/escalation requests (optional `status` query filter) | company.read |
| POST /owner-inbox | Create owner request (heads need `owner.escalate`) | owner.escalate |
| POST /owner-inbox/{id}/respond | CEO response to open request | company.pause |
| POST /push/subscriptions | Register an HTTPS Web Push endpoint | company.pause |
| POST /push/subscriptions/{id}/revoke | Revoke a push subscription | company.pause |
| GET /push/status | VAPID configuration summary (public key when set) | company.read |
| GET /push/subscriptions | List active CEO push subscriptions | company.read |
| POST /push/notify | Send a test/owner Web Push to active subscriptions | company.pause |
| GET /workers/status | Container worker readiness: Docker/scratch/image, `default_runtime`, `gateway_egress`, `worker_plane` (`same_host_nic` healthy/degraded/unset), optional flat `worker_nic_*` | company.read |
| POST /projects/{id}/dispatch-brief | Dispatch project brief to department heads | project.enroll |
| GET /events/stream | SSE audit events (cursor query param). Each frame carries `{seq, kind, at}` only; fetch bodies from `GET /events` | audit.read |
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
| POST /tasks/{id}/dispatch-worker | Isolated worker dispatch. Payload: `worker_id`, `scratch_root`, `runtime`, `approval` — all optional; `runtime` defaults from `FS_CORP_DEFAULT_WORKER_RUNTIME` and fails closed with 422 when container dispatch is not ready | task.dispatch |
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
| GET /impact-briefs | List impact briefs (no auto-publish) | company.read |
| POST /impact-briefs | Propose a brief from a signal (`signal_id`, `project_id`, `affected_summary`, `recommended_action`, `cost_cents`, `authority`) | intelligence.ingest |
| POST /signals/{id}/correct | Mark linked briefs corrected (`payload.note`) | intelligence.ingest |
| POST /learning/{id}/study | Record HTTPS study evidence for a skill assignment | intelligence.ingest |
| POST /learning/{id}/certify | Independent certification of study evidence (HR or CEO) | artifact.accept |
| POST /expansions | Cost facilities work | facilities.propose |
| POST /expansions/{id}/decision | Approve exact plan | facilities.approve |
| GET /events | Cursor-paginated audit/activity (`limit`, default 50; optional `project_id`) | audit.read |
| GET /activity | Open event-projected HQ activity sessions by default (`status=open|closed`) | company.read |
| GET /events/stream | SSE cursor frames (`seq`, `kind`, `at`, optional projected `room_id`) | audit.read |
| GET /headquarters | Event-projected rooms and departments | company.read |
| GET /headquarters/rooms/{id} | Persisted tasks, staff, deliverables, costs and decisions for one expansion room | company.read |
| POST /projects/{id}/github-enrollment | Enroll upstream/fork repo IDs and branch policy | project.enroll (CEO or admin companion) |
| POST /projects/{id}/github-assign | Paste upstream github.com address; create/reuse `{repo}-corp`; enroll | project.enroll (CEO or admin companion) |
| GET /github/status | GitHub App connectivity + `webhook_secret_configured` (no secrets returned) | company.read |
| POST /github/webhooks | Signed GitHub App webhook ingress (HMAC; no bearer) | webhook secret |
| GET /model/status | Model provider connectivity (no secrets returned) | company.read |
| GET /chatdev/status | ChatDev opt-in readiness: pin, `home_set`, `configured`, `pin_verified`, `control_plane_allowed`, `worker_live_ready`, `worker_image_chatdev`, workflow path; optional `pin_check_skipped` (no secrets) | company.read |
| GET /feeds | List CEO-approved market feed sources | company.read |
| POST /feeds | Approve an HTTPS feed URL (`payload.id`, `payload.url`) | project.enroll (CEO) |
| POST /feeds/{id}/poll | Poll an approved feed and ingest signals | company.pause (CEO) |
| GET /remote-access | VPN/pairing status and `pairing_levels` catalog | company.read |
| POST /remote-access/pairing | Issue one-time pairing QR (`payload.access_level`: `read_only`, `user`, `admin`) | company.pause (owner only) |
| POST /remote-access/redeem | Redeem ticket for scoped companion token (no auth) | — |
| POST /remote-access/revoke/{principal_id} | Revoke a paired companion service principal | company.pause (owner only) |
| GET /slos | SLO catalog and latest sourced observation (or unmeasured) | company.read |
| POST /slos/{id}/observations | Record a sourced, windowed measurement | company.pause |
| POST /consultant-proposals | Submit an evidence-backed proposal | consultant.propose |
| GET /consultant-proposals | List consultant proposals | consultant.read |
| POST /consultant-proposals/{id}/decision | CEO approve/reject | consultant.decide |
| POST /consultant-proposals/{id}/revise | New digest; does not mutate the old proposal | consultant.propose |

HTML CEO desk: `GET /` and its alias `GET /desk` (no auth for the shell page; the API reads it
performs still require a bearer token). The alias exists so the fs-dev Caddy edge can serve the
companion PWA at `/` and the desk at `/desk`.

## Unauthenticated routes

Five routes intentionally skip the bearer check. Every other route requires both a valid token
and a scope.

| Route | Why | How it is protected |
|---|---|---|
| `GET /` and `GET /desk` | HTML shell only, contains no data | All data fetches from the page carry a token |
| `GET /api/v1/health` | Liveness probe for systemd, Caddy, and the native companion | Returns only `ok`, `version`, `db` |
| `POST /api/v1/github/webhooks` | github.com cannot present a bearer token | HMAC `X-Hub-Signature-256` against `GITHUB_WEBHOOK_SECRET`; unsigned or mismatched requests are rejected |
| `POST /api/v1/remote-access/redeem` | The caller has no token yet — redeeming is how it gets one | Single-use hashed ticket with an expiry |

## Rate limiting (HTTP 429)

In-process sliding window (`company/rate_limit.py`), enforced by middleware before the route
handler. Over-limit responses are `429` with body `{"detail": "rate limit exceeded"}` and a
`Retry-After` header (seconds).

| Surface | Key | Default | Override |
|---|---|---|---|
| Authenticated `/api/v1/*` | Resolved bearer principal | 120 requests / 60 s | `FS_CORP_RATE_LIMIT_AUTH`, `FS_CORP_RATE_LIMIT_WINDOW_SEC` |
| `POST /api/v1/github/webhooks`, `POST /api/v1/remote-access/redeem` | Client IP | 60 requests / 60 s | `FS_CORP_RATE_LIMIT_UNAUTH`, same window |
| `GET /`, `GET /desk`, `GET /api/v1/health` | — | **Exempt** — never 429 | — |

Unauthenticated requests that are not webhook/redeem (for example a missing bearer on a
protected route) are not counted; they fail with 401 as usual. Limits are per process and
reset on restart. Tests inject a tighter policy via `create_app(..., rate_limit=...)`.

## Checks beyond the route scope

These routes pass the scope check above and then apply a further identity check in
`company/core.py`. Holding the scope alone is not sufficient.

| Route | Scope | Additional requirement |
|---|---|---|
| `POST /push/subscriptions`, `GET /push/subscriptions` | company.pause / company.read | CEO principal, or an identity of kind `service` (a paired companion). A non-CEO sees only its own subscriptions |
| `POST /push/subscriptions/{id}/revoke` | company.pause | CEO, or the principal that owns the subscription |
| `POST /owner-inbox` | owner.escalate | CEO, or a principal registered in `identities` |
| `POST /feeds`, `POST /feeds/{id}/poll` | project.enroll / company.pause | CEO principal (`_ceo`) |
| `POST /projects/{id}/github-enrollment` | project.enroll | CEO or `companion-admin-*` (`_ceo_or_admin_companion`) |
| `POST /projects/{id}/github-assign` | project.enroll | CEO or `companion-admin-*`; live GitHub App; same-owner `{repo}-corp` |
| `POST /projects/{id}/dispatch-brief` | project.enroll | CEO or `companion-admin-*` |
| `POST /remote-access/pairing`, `POST /remote-access/revoke/{principal_id}` | company.pause | CEO principal (`_ceo`). The route table says "owner only" because the owner *is* the CEO principal by default; the code compares against the CEO id, not an `owner` kind. `paired_devices` on `GET /remote-access` is likewise CEO-only and returns `[]` for others |
| `GET /employees/{id}/training`, `GET /employees/{id}/performance`, `GET /hr/development`, `POST /employees`, `POST /training/schedule`, `POST /employees/{id}/goals`, `POST /employees/{id}/reviews` | organization.read | `_hr_or_ceo`: the CEO, or an actor `people:<title>` where title is `HR Director`, `People Director`, or `Training Specialist`. `GET /employees/{id}` additionally allows the employee reading their own record |

## Status endpoint responses

Status routes return more than their one-line purpose suggests. No secret values appear in any
of them.

- **`GET /workers/status`** — `docker_available`, `scratch_configured`, `scratch_writable`,
  `image`, `image_present`, `container_dispatch_ready`, `default_runtime`, plus two nested
  objects. `worker_plane` is `{mode, ip, present, state, reasons}` where `state` is `healthy`,
  `degraded`, or `unset`; it is advisory and never blocks dispatch. `gateway_egress` is
  `{mode, egress_active, egress_table}` plus `egress_source_ip`, `egress_ready`, and
  `egress_blockers` when relevant, and `worker_nic_ip` / `worker_nic_present` when
  `FS_CORP_WORKER_NIC_IP` is set. Those two duplicate the plane values and are retained for
  compatibility.
- **`GET /chatdev/status`** — `pin`, `home_set`, `configured`, `pin_verified`,
  `control_plane_allowed`, `worker_live_ready`, `workflow` (a path string), and optional
  `pin_check_skipped`. `worker_image_chatdev` is `null` when Docker is unavailable or the image
  inspect fails; otherwise `{image, enabled, pin?}` read from image labels.
- **`GET /github/status`** — `configured`, `live`, `webhook_secret_configured`, and
  `funnel_webhooks` (`{opt_in, path, public_url, cli}`). When live it adds `app_slug`, `app_id`,
  `installation_id`, and `account`; on failure it adds `error`.
- **`GET /model/status`** — top-level `configured` and `live` are the OR across providers,
  alongside separate `openai` and `anthropic` objects, each `{configured, live}` plus optional
  `error`, `base_url`, `models_available`. A top-level `base_url` appears only when OpenAI is
  live.
- **`GET /push/status`** — `{configured: false, live: false}` when VAPID is unset. When
  configured it adds `contact`, `public_key`, and `application_server_key` (URL-safe base64 for
  `PushManager.subscribe`).
- **`GET /remote-access`** — `vpn`, `public_url`, `recommended_url`, `companion_url`,
  `tailnet_ipv4`, `tailscale_cli`, `auth_key_configured`, the `pairing_levels` catalog (each with
  `scopes` and `summary`), and `paired_devices`. `paired_devices` is populated for the CEO and
  an empty list otherwise.
- **`GET /company`** — the `company.status()` fields (`mode`, `policy_version`, counts,
  `simulated_spend_cents`, `billed_cost_cents`, `revenue_cents`, `rooms`, `audit_valid`)
  merged with `paused`. Simulated, billed, and revenue totals are never summed together.
## Command envelope

Each mutation uses an Idempotency-Key header plus a body containing expected resource/policy version and typed payload. Derive requester identity from the session/service token. Approval commands include proposal digest, decision and reason. Reject changed payloads under the same idempotency key.

Return operation ID, resource version, status and event correlation ID. Validation errors should identify the field and a safe explanation. Use 401 for unauthenticated, 403 for unauthorized, 409 for stale/conflicting state, 422 for invalid input and 429 for rate/queue limits. Do not include credentials or raw private content in errors.

**Implementation status:** 401, 403, 409, 422, and 429 are implemented and tested. See
[Rate limiting](#rate-limiting-http-429) for the 429 policy.

## Concurrency

Use optimistic resource versions and transaction-level budget reservation. Long work returns 202 with an operation resource. Event consumers resume using persisted cursors; SSE/WebSocket events must pass the same project ACLs as REST reads. Never use an event stream as the only persistence mechanism. The current loopback service persists in SQLite and emits SSE at `/api/v1/events/stream`. The mobile PWA polls every 15 seconds as a fallback.

## Approval binding

The production binding includes authenticated principal, company/project/repository IDs, action, branch or target SHA, artifact/workflow digest, max spend, current effective grant/policy versions and expiry. The reference core binds a smaller mock payload and is not sufficient for real GitHub/deployment operations.
