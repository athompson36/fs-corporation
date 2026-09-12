# Architecture decision log

| ID | Date | Decision | Rationale / consequence |
|---|---|---|---|
| ADR-001 | 2026-09-01 | Separate company control layer from ChatDev workers | Persistent authority/state stays independent of workflow runs |
| ADR-002 | 2026-09-01 | Pin upstream commit instead of following main | Reproducible adapter and upgrade validation |
| ADR-003 | 2026-09-01 | Deliver dependency-free offline Python core | Immediate local validation without secrets or provider spend |
| ADR-004 | 2026-09-01 | Hybrid CEO default with root human authority | Supports routine delegation and strategic control |
| ADR-005 | 2026-09-01 | Bind grants and approvals in code | Role prompts are not access controls |
| ADR-006 | 2026-09-01 | Treat building as event projection | Visual state follows accepted operational results |
| ADR-007 | 2026-09-01 | Keep simulated growth separate from actual financial data | Prevent misleading revenue/spend displays |
| ADR-008 | 2026-09-01 | Git branches/workspaces instead of Cursor GUI control | Compatible with ordinary human development workflow |
| ADR-009 | 2026-09-01 | No live adapter until secure execution milestone | Avoid credentialed tools bypassing company authority |
| ADR-010 | 2026-09-01 | FastAPI + Alembic + SQLite-first control service on loopback | Aligns with ChatDev's Python stack; Alembic versions schema; SQLite remains the single-owner store; existing unittest suite stays the invariant gate. PostgreSQL is deferred until multi-worker operation. Provider SDKs are not added. |
| ADR-011 | 2026-09-01 | Hardware firmware gated on certified skills; live doc fetch fail-closed | ESP32/RPi/RockPro64 work is software-for-boards; employees study approved HTTPS metadata; learner cannot self-certify; page text is not policy. |
| ADR-012 | 2026-09-01 | Quality Control inspects product work; HR oversees training | QC is a distinct department; producer/CEO cannot inspect; acceptance requires a passing exact-hash verdict. People catalog id remains `people` with HR naming; HR or CEO certifies skills. |
| ADR-013 | 2026-09-01 | Hired employees, recurring training files, performance trends | Hire stores configurable attributes and background; pertinent skills refresh on an interval; overdue training blocks that employee; HR records goals/reviews; self-review denied. |
| ADR-014 | 2026-09-01 | Subprocess workers with parent-mediated gateway | Workers run in a spawned process without DB credentials; only gateway_check, store_artifact, execute_mock, and mock invoke_model are allowed; container runtime stays fail-closed until a worker image exists. |
| ADR-015 | 2026-09-01 | Mobile CEO companion over Tailscale | Dashboard/read APIs, owner inbox, project dispatch-brief, SSE stream, and a mobile PWA; control service may bind to tailnet IP with --allow-remote; phone is not a trust boundary. |
| ADR-016 | 2026-09-01 | Native control plane + Caddy edge on owned Debian host; Docker for workers only | fs-dev: systemd API on 127.0.0.1:8000; Caddy on 192.168.4.100; workers `--network none`; optional `FS_CORP_GATEWAY_EGRESS=worker_nic` policy-routes `fs-corp` via 192.168.4.101. |
| ADR-019 | 2026-09-02 | Gateway egress via worker NIC for API UID | Keep containers network-none; route `fs-corp` outbound through `.101` with ip rule table 101 when `FS_CORP_GATEWAY_EGRESS=worker_nic`. |
| ADR-017 | 2026-09-01 | Cosmic-restraint visual system | Owner-selected palette and glass chrome for desk + companion. Metrics and HQ tiles bind only to persisted API state. Furnished room art stays deferred. |
| ADR-018 | 2026-09-01 | QR pairing with scoped access levels | CEO desk issues one-time tickets with `read_only`, `user`, or `admin` levels. Redeem creates service principals with explicit scopes — never root owner token or `*`. `FS_CORP_PUBLIC_URL` shapes pair URLs; optional `FS_CORP_TAILSCALE_AUTHKEY` returns only on redeem. PWA cannot join kernel VPN; native shell may consume auth key later. |
| ADR-020 | 2026-09-07 | Impact briefs via HTTP, no auto-publish | List/create/correct exposed at `/api/v1/impact-briefs` and signal correct; briefs remain proposals; signal text never amends policy. |
| ADR-021 | 2026-09-07 | Signed GitHub webhook ingress as the only unauthenticated mutation | `POST /api/v1/github/webhooks` verifies HMAC `X-Hub-Signature-256` instead of a bearer token; deliveries persist for idempotency; payload content is task data, never authority. |
| ADR-022 | 2026-09-07 | Path-scoped Tailscale Funnel for webhooks only | Funnel exposes one path publicly so github.com can reach a LAN host; opt-in per host, no LAN port forwarding, no public exposure of the control API. |
| ADR-023 | 2026-09-07 | Same-host worker plane on `.101` with a soft health signal | `.101` is a second address on the control-plane host, reported as `worker_plane`; degraded state warns but never blocks dispatch, because `--network none` workers never bind it. |
| ADR-024 | 2026-09-07 | ChatDev adapter in three opt-in slices, denied in the control plane by default | Live SDK runs only inside a worker; the control plane refuses it unless `CHATDEV_ALLOW_CONTROL_PLANE` is set; the image pin is verified and surfaced through image labels. |
| ADR-025 | 2026-09-07 | Companion PWA uses generateSW + importScripts for push | Vite 6 + injectManifest hung building `src/sw.ts`; generateSW emits `dist/sw.js`; push lives in `public/sw-push.js`; Node 18 needs a crypto polyfill and Workbox development mode to avoid terser. |
| ADR-026 | 2026-09-07 | Billed cost and revenue tables separate from simulated ledger | Live invoke writes `billed_costs` with honest cents + usage_tokens; revenue via CEO `record_revenue`; status exposes separate sums (ADR-007). |
| ADR-027 | 2026-09-07 | Phone GitHub assign by address with same-owner -corp write repo | Companion pastes upstream URL; API creates/reuses `{repo}-corp`; enrolls both ids; companion-admin may act as CEO mobile for enroll/dispatch. |
| ADR-028 | 2026-09-07 | Department heads assign only through seat, grant, roster, and queue gates | Inbox reads persisted dispatches; assignment requires `work.assign` scope and queues work under the specialist's own grant; head vacancy blocks open work and cancels linked queues. |
| ADR-029 | 2026-09-07 | HQ live activity is a transactional event projection | `_event` applies a deterministic reducer after persisting each event; `started_event_id` is unique and references the audit sequence, so replay cannot invent duplicate occupancy. Sessions use persisted department rooms when available, while the Desk polls the authenticated read API and suppresses pulse animation for reduced-motion users. |
| ADR-030 | 2026-09-07 | Promotions require persisted evidence and separate HR/CEO authority | Department ladders define skills, accepted-artifact/QC thresholds, review score, and quality standards. HR or CEO captures an immutable evaluation in a pending proposal; only CEO/admin companion decides. Approval updates the employee level and missing training targets in one transaction. |
| ADR-031 | 2026-09-07 | Staffing automation stops at an approval-gated proposal | HR/CEO scans use persisted dispatch, floorplan, assignment, and training evidence with a durable cooldown and pending-key deduplication. Scans never hire. Only CEO/admin companion decisions execute a hire, and proposal approval plus employee/training creation commit or roll back together. Promotion staffing approvals remain advisory to the separate Phase 5 promotion API. |
| ADR-032 | 2026-09-07 | Industry packs instantiate divisions through a separate CEO activation gate | Packs persist complete templates. Consultant/CEO/seated heads may propose minimal or full divisions, but only CEO/admin companions activate. Department, position, skill, learning, link, floorplan, status and event writes share one transaction; deactivation rejects open linked work. |
| ADR-033 | 2026-09-07 | Event-projected HQ and governed industry packs remain persisted operational views | Headquarters activity and scorecards derive from persisted events/rows; industry packs are inert templates until CEO activation. UI projections never create operational or financial facts. |
| ADR-034 | 2026-09-07 | A paired admin phone is a CEO actor for operations, never for root authority | `_is_ceo_actor` accepts the owner or a `companion-admin-*` principal, covering policy and consultant decisions, owner-inbox responses, HR actions and division proposals. Pairing, revenue, budget, rollback, model, feed and SLO operations stay strict `_ceo`. Scopes are served by `GET /api/v1/session` so a client never infers its own authority. |
| ADR-035 | 2026-09-07 | Dispatch recommend/autofill is advisory; mock always, live when configured | `GET …/dispatch-options` is the server parameter key. `POST …/dispatch-recommend` returns editable suggestions (`source` mock|live) and never calls `dispatch_project_brief`. Live uses `invoke_model` + validation; unusable/unavailable falls back to mock with notes. |
| ADR-036 | 2026-09-07 | Settings platform uses SQLite overlay; secrets status only; honest restart_required | Allowlisted non-secret knobs persist in `company_settings`; effective resolution is overlay → env → catalog default. PATCH/reset require `company.pause` + CEO/admin companion. Secrets API returns configured/missing only. Rate-limit keys store overlay but apply only after API restart; UI states that honestly. Host-bound IPs are read-only in GET. |
| ADR-037 | 2026-09-07 | ChatDev worker egress is opt-in allowlist + explicit Docker network | Default remains `--network none`. Mode `allowlist` requires host allowlist file, non-empty `https_hosts`, and `FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK`; never bare `bridge`/`host`. Status reports mode/count/ready without listing hosts. |
| ADR-038 | 2026-09-08 | Append-only finance adjustments; invoices are window snapshots | `billed_costs` stay immutable. Voids/partial credits live in `finance_adjustments`. `billed_cost_cents` means net. Internal invoices snapshot billable lines; period close writes `budget_period_closures`. |
| ADR-039 | 2026-09-08 | choose_model may prefer best benchmark quality; work-order replay is append-only | Among eligible profiles, max `quality` for a role wins when benches exist; else ordered pick. `work_order_replays` freezes outcomes; identical digest replay returns prior result without ChatDev re-execution. |
| ADR-040 | 2026-09-08 | Worker host registry without remote dispatch; SVG furniture from room_type | CEO registers remotes + heartbeat → ready/stale/disabled on `/workers/status`. Dispatch stays same-host. TailscaleKit stubbed. Desk furniture glyphs bind only to persisted room types. |
| ADR-041 | 2026-09-08 | Shared cosmic-glass tokens for desk + companion | Single `assets/cosmic-glass-tokens.css` served at `/static` and imported by companion; M10-04 version chrome + HQ keyboard. |
| ADR-042 | 2026-09-08 | Remote pull agent with explicit host routing; mock-complete v1 | `worker_host_id` enqueues `remote_worker_jobs`; agent claims/completes with host token. Default dispatch stays same-host. No remote Docker yet. |
| ADR-043 | 2026-09-08 | Opt-in prefer remotes; fail closed if none ready | `FS_CORP_PREFER_REMOTE_WORKERS` auto-picks first ready host by label/id when `worker_host_id` omitted. Explicit id wins. |
| ADR-044 | 2026-09-08 | Opt-in remote container with host-token gateway relay | Remote agents may opt into container execution with `--network none`; the agent relays allowlisted gateway operations. Default remains mock-complete. No remote egress this slice. |
| ADR-045 | 2026-09-08 | Public `/welcome` landing and marketing campaign furniture | FastAPI serves a cosmic-glass landing while the companion remains at `/`; desk HQ maps persisted marketing room types to `campaign` furniture. |
| ADR-046 | 2026-09-08 | Remote claim embeds fail-closed ChatDev egress policy | Agents attach allowlisted Docker networks only when locally ready; forbidden names coerce to none at claim; no hostnames cross the wire. |
| ADR-047 | 2026-09-10 | Companion domain shell and CEO Needs-you spine | Five primary domains regroup existing capabilities; Home projects persisted decisions/inbox only; shared Syne/Manrope fonts unify companion, desk and welcome. |
| ADR-048 | 2026-09-10 | Local Browse/Manage modes for companion Work and People | Persisted lists/details and in-row actions default to Browse; create/enroll/configure controls move to Manage; Finance retains its existing sub-tabs without a second mode layer. |
| ADR-049 | 2026-09-11 | Desk IA matches companion five domains | Desk rail grouped Home · Work · People · Money · More; page sections reordered; hybrid Home keeps HQ high; Scorecard under Work; no ID renames or domain panes. |
| ADR-050 | 2026-09-11 | Companion Projects Browse split workspace | Projects Browse uses list|detail split; detail holds dispatch workspace; Manage remains enroll/assign; medium empty/section polish on sibling panels; no URL sync or Finance ModeSwitch. |
| ADR-051 | 2026-09-11 | Corporate and Workers Browse section consistency | Corporate Browse lists use section-head + panel-empty; Workers title sits outside the list card; no capability or API changes. |
| ADR-052 | 2026-09-11 | Org Browse and Manage section-head consistency | Organization catalog and Manage forms use section-head titles matching Corporate/Workers; no capability or API changes. |
| ADR-053 | 2026-09-11 | Corporate Browse clusters with narrow sub-tabs | Corporate Browse groups Strategy · Structure · People · Coordination; segmented cluster tabs below 720px; Manage section-head titles only; no URL sync or new APIs. |
| ADR-054 | 2026-09-12 | Projects list-row span + Clear on loading | Projects Browse list rows use span.muted inside buttons; loading detail shows Clear selection; no URL sync or API changes. |
| ADR-055 | 2026-09-12 | Companion URL sync for tab and project | Query `tab`/`project` with replaceState; unknown project clears silently; pairing hash unchanged; no Router. |
| ADR-056 | 2026-09-12 | Manage visual groups with shared hybrid chrome | Org/Corporate/Projects/Workers Manage use ManageClusters + shared useWideViewport; no URL sync or API changes. |
| ADR-057 | 2026-09-12 | Empty-list unknown-project URL clear | Gate unknown `?project=` clear on `projectsLoaded` after successful refresh; failed fetch keeps deep link; silent clear; no new APIs. |
| ADR-058 | 2026-09-12 | Mode/cluster/group companion URL sync | App-owned `mode`/`cluster`/`group` with replaceState; omit defaults; panels controlled; pairing unchanged. |
| ADR-059 | 2026-09-12 | Finance Browse/Manage with URL sync | Finance ModeSwitch + ManageClusters lists-vs-forms; finance in MODE_CAPABLE_TABS; group in browse+manage; close-period stays Browse; no new APIs. |

### ADR-010 detail

**Context.** M1 requires an authenticated local control service, schema migrations, and the proposed `/api/v1` contract. The v0.2.0 core is a standard-library CLI with ad-hoc `CREATE TABLE IF NOT EXISTS` and trusted actor strings.

**Decision.** Implement the control service with Python 3.12, FastAPI, and Uvicorn bound to `127.0.0.1`. Version the schema with Alembic. Keep SQLite for single-owner local operation. Keep `company.core.Company` as the domain engine so the existing unittest suite remains the invariant gate. Identity comes from bearer tokens, never from request bodies.

**Alternatives considered.**

- stdlib `http.server`: no request schemas, no dependency, but weak validation and more custom code for the command envelope.
- Django: batteries included, heavier than a loopback command API and further from ChatDev's FastAPI/Starlette ecosystem.

**Consequences.** `pyproject.toml` gains `fastapi`, `uvicorn`, and `alembic` (Alembic brings SQLAlchemy). The offline demo CLI must still run without talking to the network. The service must not be advertised as a trusted remote API. Live ChatDev, GitHub, and market adapters remain disabled.

### ADR-011 detail

**Context.** The owner asked the company to take firmware and board-support work (ESP32, Raspberry Pi, RockPro64 and similar) and to have pertinent employees learn online when the current skill configuration cannot perform the work.

**Decision.** Treat hardware as software-for-boards, not physical fabrication. Persist a skill catalog, project capability rows, learning assignments, and certified `acquired_skills`. Block `draft` / `review` / `prepare_pr` while required skills are missing. Study uses the same HTTPS metadata ingest as market signals. Certification requires an independent CEO reviewer. `LearningAdapter.fetch` is allowlisted HTTPS only (`config/learning-sources.example.json` / `FS_CORP_LEARNING_SOURCES_FILE`); page text remains task data, not policy.

**Alternatives considered.**

- Immediate live crawl of vendor docs: contradicts fail-closed adapters and would treat untrusted page text as operational input.
- Ungated hardware dispatch with a prompt reminding agents to learn: prompts are not access control.

**Consequences.** Alembic revision `0002_hardware_skills`. Software projects without a hardware capability row remain ungated. Page text cannot amend policy.

### ADR-012 detail

**Context.** The owner required a Quality Control department to verify all work and an HR department to oversee employee development and training.

**Decision.** Add Quality Control as a catalog department. Record `qc_inspections` against the exact artifact hash. The producer and CEO cannot inspect. Acceptance requires the latest inspection to be `pass`. Rename People and Training to Human Resources, keep catalog id `people`, activate it, and let HR Director or Training Specialist certify skills alongside the CEO.

**Alternatives considered.**

- Reuse Engineering QA Engineer as the company-wide gate: that stays in-team testing and is not independent.
- Create a second HR department beside People: duplicate training ownership.

**Consequences.** Alembic revision `0003_quality_control`. Demo and acceptance tests inspect before accept. The Master Consultant remains advisory.

### ADR-013 detail

**Context.** The owner required regular training for all employees, documented training for review, performance goals/reviews/trending, and configurable attributes and backgrounds for new employees.

**Decision.** Persist `employees`, `training_records`, `performance_goals` and `performance_reviews`. Pertinent skills come from `config/employee-development.json`. Hire assigns training. Overdue certified skills (default 90 days) are reassigned by `schedule_company_training`. Hired employees cannot dispatch while overdue. Training records capture study summaries for HR review. Reviews are independent integer scores with a last-two-point trend.

**Alternatives considered.**

- Treat catalog positions as employees: no background or review history.
- Auto-fetch training content: contradicts fail-closed adapters.

**Consequences.** Alembic revision `0004_employee_development`. Demo fixture actors who are not hired remain ungated by the training cycle.

### ADR-014 detail

**Context.** M3 requires isolated workers that cannot read the control-plane database or mutate policy. The queue, gateway recheck, and mock ChatDev adapter already exist in-process.

**Decision.** Add `company.worker` with a `SubprocessWorkerRuntime` that spawns a child process. The child runs `MockChatDevAdapter` locally and requests effects through a pipe to the parent, which enforces an allowlisted gateway. `ContainerWorkerRuntime` runs `--network none` containers over a scratch-directory gateway; it fails closed with `NotImplementedError` when Docker or the worker image is unavailable. Persist `worker_runs` for audit.

**Status update (0.3.41).** `ContainerWorkerRuntime` is implemented and is the fs-dev default when Docker, the image, and scratch are ready (`FS_CORP_DEFAULT_WORKER_RUNTIME=container`). The `NotImplementedError` path is now the unready case, not the whole runtime.

**Alternatives considered.**

- In-process dispatch only: no isolation boundary for upstream tool execution.
- Give workers a read-only DB replica: still exposes grants, approvals, and secrets paths.

**Consequences.** Alembic revision `0005_worker_runs`. API route `POST /api/v1/tasks/{task_id}/dispatch-worker`. Subprocess isolation is not a full sandbox; container mode remains owner-configuration work.

### ADR-015 detail

**Context.** The owner requested a smartphone companion to view company/project statistics, approve proposals, deploy projects to department heads, and respond to team feedback—effectively running the corporation from a phone.

**Decision.** Add M8 APIs: `GET /api/v1/dashboard`, project list/detail, unified decisions inbox, owner inbox with `owner_requests`, `POST /api/v1/projects/{id}/dispatch-brief`, and `GET /api/v1/events/stream` (SSE). Ship a Vite/React PWA in `companion/` and document Tailscale access with `--allow-remote`. Optional Expo shell in `companion-native/` loads the PWA.

**Alternatives considered.**

- Public cloud API without VPN: contradicts loopback-first security posture for v1.
- Native-only app without shared API: duplicates governance logic on the device.

**Consequences.** Alembic revision `0006_mobile_companion`. New scope `owner.escalate` for head escalations. PWA polls every 15s; SSE available for live refresh. Push subscriptions persist from 0.3.9 (`0008_push_notifications`); live Web Push stays fail-closed until VAPID keys exist.

### ADR-016 detail

**Context.** M9 requires a production hosting path on an owned Debian machine (`fs-dev`) so the owner can use the mobile companion on LAN (`192.168.4.100`) and optionally Tailscale, without exposing the raw control API on the network.

**Decision.** Run the control API **natively** under systemd bound to **loopback only** (`127.0.0.1:8000`). Terminate TLS and serve the companion PWA with **Caddy** on the LAN edge. Use **Docker only for isolated workers** (image and compose scaffold); do not containerize the control plane in phase 1. Reserve **`192.168.4.101`** for phase-2 worker/internal traffic.

**Alternatives considered.**

- Containerize the full stack (API + Caddy): adds operational complexity without isolation benefit for the control plane on a single owner host.
- Bind API directly to LAN/Tailscale with `--allow-remote`: acceptable for dev; production fs-dev keeps API on loopback and proxies through Caddy on 443.
- Public internet exposure without VPN: contradicts loopback-first security posture.

**Consequences.** `deploy/fs-dev/` ships `install.sh`, systemd unit, Caddyfile, ufw example, and worker Dockerfile/compose. Runbook in [25-fs-dev-deployment.md](25-fs-dev-deployment.md). Same-host phase 2 sets `FS_CORP_DEFAULT_WORKER_RUNTIME=container`, reports `worker_nic_present` for `.101`, and optionally policy-routes `fs-corp` egress via `.101` (`FS_CORP_GATEWAY_EGRESS=worker_nic`). Workers remain `--network none`. A dedicated second worker host remains optional.

### ADR-018 detail

**Context.** M8 mobile companion needed frictionless phone onboarding without embedding the root owner bearer token in QR codes or URLs. Owners also need to delegate read-only or user-level mobile access separate from full CEO mobile actions.

**Decision.** CEO desk issues one-time pairing tickets stored with an `access_level` (`read_only`, `user`, `admin`). QR encodes only `pair_url` with `#fs-pair={ticket}`. Redeem creates a **service principal** with level-specific scopes; `admin` maps to `COMPANION_SCOPES`, never `kind: owner`. Optional `FS_CORP_TAILSCALE_AUTHKEY` is returned **only** on redeem. `FS_CORP_PUBLIC_URL` sets the recommended origin for pair URLs on fs-dev.

**Alternatives considered.**

- Put owner token in QR: rejected — phone compromise would equal root authority.
- Client-selected level on redeem: rejected — level is bound at issue time in the database.
- Server-side Tailscale join for phones: rejected — kernel VPN join is device-local; PWA cannot join; native shell may consume auth key in phase 2.

**Consequences.** Alembic `0010_pairing_tickets`, `0011_pairing_access_level`. Routes `GET/POST /api/v1/remote-access*`. Companion auto-redeems hash on load and scope-gates UI. Dev preview may set `FS_CORP_ALLOW_CORS=1` for loopback companion on `:4173`.

### ADR-021 detail

**Context.** M4 needed github.com to deliver events into the company. Every other mutation requires a bearer token, but GitHub cannot present one. Recorded retroactively on 2026-09-07 during the full-project audit; the decision shipped in 0.3.39.

**Decision.** `POST /api/v1/github/webhooks` skips the bearer check and authenticates the *request* instead: HMAC SHA-256 over the raw body against `GITHUB_WEBHOOK_SECRET`, compared in constant time. Unsigned, mismatched, or unconfigured requests are rejected. Deliveries persist in `github_webhook_deliveries` keyed by delivery id so a redelivery is a replay, not a second effect. Webhook payload content is task data only; it never changes policy, grants, or budgets.

**Alternatives considered.**

- Poll the GitHub API instead: rejected — higher latency and API cost for the same information, and still needs credentials.
- A shared bearer token in a query string: rejected — leaks into logs and proxy history, and GitHub offers HMAC natively.
- Accept unsigned events when the secret is unset: rejected — that is fail-open. Without a configured secret the route refuses everything.

**Consequences.** Alembic `0012_github_webhook_deliveries`. `GET /api/v1/github/status` reports `webhook_secret_configured` without returning the secret. Live `ping`, `push`, and `pull_request` deliveries returned 200 on fs-dev. Spec: `docs/superpowers/specs/2026-09-07-github-webhooks-design.md`.

### ADR-022 detail

**Context.** fs-dev sits on a private LAN behind `192.168.4.100` with no public address. github.com must reach exactly one path. Recorded retroactively on 2026-09-07; shipped in 0.3.37.

**Decision.** Use Tailscale Funnel scoped to the webhook path rather than opening the LAN. `deploy/fs-dev/tailscale-funnel-webhooks.sh` serves `/api/v1/github/webhooks` at the tailnet DNS name, gated on `FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS`. Off by default; the operator opts in per host and Tailscale requires a separate consent step.

**Alternatives considered.**

- Router port forwarding to `.100`: rejected — exposes the whole Caddy edge, and the control API sits behind it.
- A public cloud relay: rejected — a new vendor and a second place credentials could leak, for one inbound path.
- Funnel the entire site: rejected — the companion and desk have no reason to be internet-reachable.

**Consequences.** `company/tailscale_funnel.py` probes state and reports it in `GET /api/v1/github/status` as `funnel_webhooks`. `FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL` records the URL to paste into the GitHub App. The public surface is one path that already fails closed without a valid HMAC (ADR-021). Spec: `docs/superpowers/specs/2026-09-07-tailscale-funnel-webhooks-design.md`.

### ADR-023 detail

**Context.** ADR-016 reserved `192.168.4.101` for workers, and documentation drifted toward calling it a "worker host". It is a second address on the *same* machine. Operators had no way to see whether it was actually assigned. Shipped in 0.3.41.

**Decision.** Name it the **same-host worker plane** and expose `worker_plane` on `GET /api/v1/workers/status` as `{mode, ip, present, state, reasons}`, where `state` is `healthy` (configured and assigned), `degraded` (configured but absent from every interface), or `unset`. The check is **soft**: a degraded plane never blocks container dispatch. `scripts/verify_fs_dev_workers.py` warns on stderr, and only the explicit `--require-plane` flag turns a degraded plane into a non-zero exit.

**Alternatives considered.**

- Fail closed on a missing `.101`: rejected — workers run `--network none` and never bind the address, so blocking dispatch would deny work for a condition that does not affect it. The one thing `.101` does affect, gateway egress, already reports its own readiness.
- Stay silent when unset: rejected — operators could not tell a deliberate single-address host from a misconfigured one.
- Provision a genuinely separate worker host now: deferred — no capacity case yet; it stays an optional track.

**Consequences.** `company/worker_status.py` gains `worker_plane_summary()`. Flat `worker_nic_ip` / `worker_nic_present` remain inside `gateway_egress` for compatibility. Documentation now says "same-host worker plane" wherever it previously said "worker host". Spec: `docs/superpowers/specs/2026-09-07-worker-plane-design.md`.

### ADR-024 detail

**Context.** ADR-001 and ADR-009 require that upstream workflow code with tool execution never run in the privileged control process. Enabling ChatDev in one step would have coupled the SDK, the worker path, and the image together, with no safe intermediate state. Shipped as 0.3.38 through 0.3.40.

**Decision.** Three opt-in slices, each independently reversible. Slice 1 adds `ChatDevAdapter` calling the pinned `run_workflow` when `CHATDEV_HOME` is set, fail-closed otherwise, tested against a fake SDK. Slice 2 runs it in the worker and makes the control plane **deny** the live SDK unless `CHATDEV_ALLOW_CONTROL_PLANE` is explicitly set. Slice 3 makes the ChatDev pin an optional build argument of the worker image; the default image stays mock-only, and container dispatch does not forward the control-plane allow flag.

**Alternatives considered.**

- Install ChatDev in the control-plane virtualenv: rejected — that is exactly the boundary ADR-001 exists to protect.
- Follow ChatDev `main`: rejected by ADR-002; the pin is verified and reported.
- Bake ChatDev into the default worker image: rejected — every deployment would carry the dependency and its supply-chain surface whether or not it was used.

**Consequences.** `GET /api/v1/chatdev/status` reports `pin`, `home_set`, `configured`, `pin_verified`, `control_plane_allowed`, `worker_live_ready`, and `worker_image_chatdev` read from `org.fs_corporation.chatdev_*` image labels. `CHATDEV_SKIP_PIN_CHECK` exists for offline builds and is surfaced as `pin_check_skipped` rather than hidden. Live ChatDev execution is still unverified: the image carries pinned source, not a full dependency install, and `--network none` workers have no egress. Specs: `docs/superpowers/specs/2026-09-07-chatdev-adapter-slice{1,2,3}-design.md`.

### ADR-025 detail

**Context.** `deploy/fs-dev/install.sh` runs `cd companion && npm run build`. With Vite 6 and `vite-plugin-pwa` 0.21.2 `injectManifest` pointing at `src/sw.ts`, the main bundle finished but the service-worker Vite build hung at 0% CPU and never wrote `dist/sw.js`. Upgrading the plugin alone still hung or crashed on Node 18 (`crypto is not defined` in serialize-javascript / terser).

**Decision.** Use `strategies: "generateSW"` and keep push / notificationclick handlers in `public/sw-push.js`, loaded via Workbox `importScripts`. Pin `vite-plugin-pwa` ^1.2.0. On Node 18, preload `scripts/polyfill-crypto.cjs` and set Workbox `mode: "development"` so SW generation skips terser minify.

**Alternatives considered.**

- Stay on injectManifest and debug the hang: abandoned after repeated indefinite hangs on Node 18 and 20.
- Require Node 20+ only: rejected for fs-dev, which is still on Node 18-compatible tooling.
- Drop the PWA plugin: rejected — offline shell and autoUpdate registration are still wanted.

**Consequences.** Builds exit and emit `dist/sw.js` plus copied `sw-push.js`. Workbox assets are unminified in development mode (acceptable for a private companion). Phone offline / update-on-reload needs an owner smoke check after the next fs-dev companion rebuild. Expo/`companion-native` audit findings remain a separate tree.

### ADR-026 detail

**Context.** R12 and ADR-007 require estimated, reserved, actual billed cost, and simulated credits to stay separate. Through 0.3.47 the schema had ledger/reservations/estimates only; live `invoke_model` returned a mislabeled token count as `cost_cents` and never persisted it. No revenue table existed.

**Decision.** Add `billed_costs` and `revenue` (Alembic `0013`). On successful live invoke, insert a billed row with `usage_tokens` and `amount_cents` from optional pricing (`cents_per_1k_tokens` / `FS_CORP_MODEL_CENTS_PER_1K_TOKENS`), else `0`. Mock writes nothing. CEO `record_revenue` writes revenue only. `status()` exposes `billed_cost_cents` and `revenue_cents` beside `simulated_spend_cents`.

**Alternatives considered.**

- Persist token counts as cents: rejected — dishonest minor units.
- Insert billed rows only when priced: rejected — loses the audit trail of live calls.
- Full invoice/refund engine: deferred.

**Consequences.** Spec: `docs/superpowers/specs/2026-09-07-billed-cost-revenue-design.md`. HTTP command for revenue can follow; core writer is the authority. Benchmark dead-table cleanup remains a separate M10-03 item.

### ADR-027 detail

**Context.** A project brief previously accepted one shared budget for multiple departments and could dispatch dormant departments. That obscured budget ownership and represented unavailable departments as ready.

**Decision.** Require a `department_budgets` mapping, reject dormant departments until the CEO or authenticated admin companion activates them for the project, and record each dispatch as `queued_for_head` only for an active occupied head seat or `blocked_vacant_head` otherwise. Optional grant `departments` scopes fail closed when a department-aware action does not match. Roster and activation controller commands accept the same admin-companion principal class as enroll and dispatch.

**Alternatives considered.** Silently split one budget was rejected because allocation would be invented. Auto-activating departments on dispatch was rejected because activation is an explicit owner decision. Treating vacant seats as queued was rejected because no head can receive the work.

**Consequences.** The dispatch API is intentionally breaking for callers using `departments` plus one `budget_cents`; all in-repository callers now send explicit per-department amounts. Task 4 stores routing status and head identity but does not assign specialists or create the Task 5 head inbox.

### ADR-028 detail

**Context.** Task 4 persisted which occupied head should receive a project dispatch, but
it did not provide an inbox, authorize specialist selection, or create executable queue
work. Treating `queued_for_head` as specialist assignment would bypass both roster and
worker-grant controls.

**Decision.** Read head inboxes from persisted open dispatches. A non-CEO assigner must
occupy the department's active head seat and hold a current `work.assign` grant for the
project and, when present, department. The assignee must be active on that department's
roster or hold a project grant; `queue_task` independently enforces the assignee's action,
budget, skills, and training gates. Vacating a head blocks that head's unassigned
dispatches and cancels queue rows linked through `dispatch_assignments`.

**Alternatives considered.** Prompt-only head authority was rejected because prompts are
not access controls. Queueing under the head identity was rejected because it would charge
and authorize the wrong principal. Automatically re-opening vacancy-blocked dispatches on
appointment was deferred because reassignment should be an explicit state transition.

**Consequences.** The API exposes scoped inbox read and assignment commands, while core
authorization remains authoritative. The queue write precedes the assignment transaction
so queue validation failure cannot mark a dispatch assigned; callers should use the API's
idempotency key for retry-safe command execution. In v0.3.51 the desk and companion expose
this persisted inbox and assignment path alongside honest seat/roster state; the UI does not
derive authority from titles or reporting lines.

### ADR-029 detail

**Context.** Cross-department commitments need ownership, schedule, acceptance, and
escalation metadata before they become executable worker tasks. Adding these mutable
coordination fields to immutable execution `work_orders` would mix organizational acceptance
with the policy-bound runtime envelope.

**Decision.** Persist `cross_department_requests` separately. A non-CEO creator must occupy
the active requesting-department head seat; a non-CEO accepter must occupy the active
delivering-department head seat. CEO and authenticated admin companions are explicit
overrides. Delivering departments must be active for the project. Org-chart edges, titles,
and chat content grant no authority.

**Alternatives considered.** Extending `work_orders` was rejected because accepting a
departmental request is not worker execution authorization. Copying the delivering principal
at creation was rejected because a later vacancy or replacement must take effect immediately.
Auto-activating dormant departments was rejected because activation remains an owner action.

**Consequences.** Alembic `0015_cross_dept_work_orders` adds the table. Create and accept
emit transactional audit events. The authenticated API supports create, actor-scoped delivery
list, and accept; no user-visible UI ships, so the package remains 0.3.51.

### ADR-030 detail

**Context.** Expansion events record earned growth but do not provide a stable editable grid,
department-room ownership, or an explicit way to report missing operational spaces. Rendering
requirements as rooms would invent state.

**Decision.** Persist floorplans and grid-positioned rooms separately from the expansion
ledger. Room types are constrained to the department catalog or requirement catalog; bounds
and overlap fail closed. Requirements record minimum capacity by department and room type.
Only the CEO or authenticated admin companion mutates layouts. Expansion-linked rooms cannot
be removed, preserving their growth provenance.

**Alternatives considered.** Deriving a layout from expansion order was rejected because it
cannot represent department ownership or edits. Storing the plan only in browser state was
rejected because restart and auditability are required. Materializing missing requirements as
placeholder rooms was rejected because the UI must not invent operational state.

**Consequences.** Alembic `0017_floorplans` adds the three tables and seeds catalog
requirements from `config/room-requirements.json`. The Desk renders persisted rooms on the 2D
grid and shows unmet requirements as warning chips; expansion isometric rendering remains the
fallback when no floorplan rooms exist. No package version bump is made for this phase.

### ADR-031 detail

**Context.** Persisted employees and room ownership identify who belongs in a department, but
the headquarters had no validated visual identity or concise, joined worker view. Inventing
sprites or capabilities in the browser would violate the building projection rules.

**Decision.** Store sprite-set catalogs separately from each employee's selected sprite.
Catalog-defined bodies, palettes, layers, and accessories are validated in the core. Human
Resources or the CEO may edit sprite and profile fields. Worker cards join only persisted
employee identity, acquired skills, active position assignments, and an optional sprite.
Missing sprites remain null and are rendered with an explicitly neutral placeholder.

**Alternatives considered.** Browser-only sprite choices were rejected because they would not
survive restart or support consistent validation. Generating a random sprite for every worker
was rejected because it would invent identity. Reusing model profiles as worker identity was
rejected because employees, positions, and model routing are intentionally separate.

**Consequences.** Alembic `0018_worker_identity` adds profile columns, `sprite_sets`, and
`worker_sprites`, seeded from `config/sprite-sets.json`. Organization-scoped APIs expose cards
and mutations, while core HR/CEO checks remain authoritative. Department rooms include
persisted staff with optional sprites; Desk markers fetch the corresponding card. No package
version bump is made for this phase.

### ADR-033 detail

**Context.** Corporate HQ phases added editable organization state, rooms, worker identity,
activity, staffing, divisions, and executive measures. A rich headquarters UI could otherwise
drift into invented occupancy, performance, revenue, or active business units.

**Decision.** Keep headquarters activity event-projected and compute the CEO scorecard only
from persisted operational rows. Accepted artifacts come from persisted acceptance events;
QC, dispatch, reservation/ledger, billed-cost, and revenue measures come from their dedicated
tables. Missing revenue remains zero and missing QC remains unmeasured. Industry packs remain
persisted templates whose departments, skills, learning assignments, and floorplans become
operational only through the existing CEO activation transaction. Objectives are separate
CEO/admin-authored records and do not rewrite measured results.

**Alternatives considered.** Client-side counters and demo revenue were rejected because they
would fabricate company performance. Treating an installed industry pack as an active division
was rejected because templates are not authority. Recomputing HQ occupancy from running model
processes was rejected because process presence is not a durable business event.

**Consequences.** Alembic `0023_ceo_scorecard` adds objectives and optional immutable scorecard
snapshots. The Desk labels the scorecard as measured from persisted operations, and all HQ
projections remain reproducible from durable company state.

### ADR-034 detail

**Context.** The HQ surfaces shipped to the companion were visible on a paired iPhone but inert.
Two independent causes: the native shell wrote a session into the WebView without `scopes`, so
every `canManage*` gate hid its controls; and several actions the `admin` pairing level already
carries scopes for (`policy.approve`, `consultant.decide`, HR and division writes) were checked
in core against the literal CEO string, so they would have returned 403 once visible.

**Decision.** Introduce `_is_ceo_actor(actor)` — the owner string or a `companion-admin-*`
principal — and use it for `_ceo_or_admin_companion`, `_hr_or_ceo` and `_division_proposer`, plus
`approve_policy`, `reject_policy`, `respond_owner_request` and `ConsultantDesk.decide`. Keep
strict `_ceo` on root authority: pairing issue/list/revoke, `record_revenue`, `set_budget_period`,
`rollback_policy`, `assign_model`, feed enrollment and `record_slo_observation`. Add
`GET /api/v1/session` so scopes are always server-derived, and have the companion hydrate from it
rather than trusting injected storage.

**Alternatives considered.** Hiding the HQ controls from phones entirely was rejected because the
`admin` level is documented as CEO mobile and already carries the scopes. Trusting client-injected
scopes was rejected because the server must remain the only authority. Granting root operations to
the phone was rejected: a lost device must not be able to re-pair itself, move money or roll back
policy.

**Consequences.** A stolen unlocked admin phone can approve proposals and edit the organization,
which the pairing level already implied; the owner mitigates by revoking the device from the desk.
Lower levels are unaffected because they redeem as `companion-read_only-*` / `companion-user-*`.
`GET /api/v1/session` is authentication-only by design so a read-only device can discover its own
limits.

### ADR-035 detail

**Context.** Owners needed a parameter key of valid dispatch-brief values and an AI-assisted
autofill of brief, criteria, and department budgets on desk and companion, without inventing
operational state or auto-dispatching.

**Decision.** Add `GET /api/v1/projects/{id}/dispatch-options` (templates, presets, remaining
max cents, full department catalog with `dispatchable`/`status`) and
`POST /api/v1/projects/{id}/dispatch-recommend` (advisory payload). Mock heuristics always work
offline; live uses existing `invoke_model` when model provider status is configured and live,
then validates department ids and clamps integer budgets. Fail closed to mock with
`live_unavailable` / `live_unusable` notes. Humans still submit via `dispatch-brief`. Auth matches
dispatch-brief (`project.enroll` + CEO or admin companion).

**Alternatives considered.** Auto-dispatch from the recommendation was rejected (authority and
safety). Putting heuristics only in the UI was rejected (parameter key must be server-owned).
Requiring Decisions-inbox approval for each recommendation was rejected as too heavy for editable
autofill.

**Consequences.** Live recommends may write `billed_costs` through `invoke_model`. Dormant
departments remain non-dispatchable until activated; UI blocks submit when a checked dept is
dormant. Recommendations never activate seats or invent HQ/revenue state.

### ADR-036 detail

**Context.** Settings **C** requires editing non-secret runtime knobs from the companion without
rewriting host `secrets.env`, while keeping secret values out of API responses and logs. Rate
limits are built at app startup; faking hot reload would mislead operators.

**Decision.** Add `company_settings` overlay with catalog validation and
`settings_runtime.effective(company, key)` resolution (overlay wins, then env, then default).
Expose `GET/PATCH /api/v1/settings`, `POST …/reset`, and `GET …/secrets-status`. PATCH/reset
auth: `company.pause` + `_ceo_or_admin_companion`. Secrets-status lists `configured` booleans
only, aligned with `scripts/check_owner_config.py`. Keys marked `restart_required` persist
overlay but do not change the in-process rate limiter until restart; companion shows explicit
copy. Host-bound LAN/worker/egress keys are GET-only.

**Alternatives considered.** Rewriting `secrets.env` from the phone was rejected (secret store
and audit boundary). Returning secret values for “debugging” was rejected. Hot-reloading the
rate limiter in slice A was rejected in favor of honest `restart_required` metadata.

**Consequences.** Operators can tune SSE idle, public URL, worker runtime default, model pricing,
ChatDev control-plane flag, and idempotency retention without shell access. Desk Settings and
expanded Settings sections (Company, Models, Feeds, …) remain follow-ons. Overlay does not
escalate scopes or invent HQ/financial state.

### ADR-037 detail

**Context.** Container workers stay `--network none` by default. Live ChatDev model calls need
HTTPS egress without opening unrestricted Docker bridge networking.

**Decision.** `FS_CORP_CHATDEV_WORKER_EGRESS` is `none` (default) or `allowlist`. Ready egress
requires a host allowlist file (`FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE` with non-empty
`https_hosts`), plus an explicit Docker network name
(`FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK`). `ContainerWorkerRuntime` uses that network only when
ready; otherwise `--network none`. Never `bridge` or `host`. Status exposes mode, configured,
count, and ready — not the host list.

**Alternatives considered.** Full open worker network was rejected. Phone-editable allowlist was
rejected (host file only). Shipping unrestricted bridge behind a boolean was rejected.

**Consequences.** Operators must create the restricted Docker network and allowlist on the host
before ChatDev containers can egress. Misconfiguration fails closed to network-none.

### ADR-038 detail

**Context.** ADR-026 separated billed cost from simulated spend but deferred refunds, invoices,
and period rollover. Operators need auditable adjustments without rewriting live invoke rows.

**Decision.** Keep `billed_costs` immutable. Add `finance_adjustments` (void / partial_credit),
`invoices` (window snapshots of still-creditable lines), and `budget_period_closures`.
`status().billed_cost_cents` is net of adjustments; expose gross and adjustment totals too.
Finance mutations remain CEO-gated.

**Alternatives considered.** Mutating billed rows in place was rejected (weaker audit).
Provider invoice import / Stripe was rejected for P3.

**Consequences.** Companion Finance tab manages invoices, refunds, and period close.
Companion lists creditable `billed_costs` via `GET /finance/billed-costs` for refund UX; this is
read-only and does not change adjustment math.

### ADR-039 detail

**Context.** Model routing ignored recorded benchmarks; consultant work orders had no
identical-digest replay surface without re-running work.

**Decision.** `choose_model` optionally ranks eligible profiles by max `quality` for a role.
`work_order_replays` stores authorize/complete/replay rows; matching digest replay returns the
frozen outcome and does not invoke ChatDev.

**Alternatives considered.** Cost-first ranking and advisory-only notes were rejected for this
slice. Full workflow re-execution was rejected as out of scope.

**Consequences.** Call sites may pass benches via `Company.choose_model`. Replay APIs are
CEO-gated for mutations; list is `company.read`.

### ADR-040 detail

**Context.** Production P4 needed an honest second-host story without pretending remotes
execute work, plus TailscaleKit and furnished HQ without store binaries or art packs.

**Decision.** Persist `worker_hosts` with hashed heartbeat tokens. Heartbeats set ready/stale;
CEO can disable. `/workers/status` lists `remote_hosts`. Isolated dispatch remains local
subprocess/container only. `companion-native/tailscale_kit.ts` stubs TailscaleKit as
unavailable. Desk isometric adds SVG furniture from persisted `room_type` only.

**Alternatives considered.** Remote enqueue/agent in the same slice was rejected (no agent).
Shipping TailscaleKit binaries and photoreal art packs was rejected as out of repository
scope.

**Consequences.** Operators can register and monitor remotes before remote execution exists.
Org hierarchy milestone 5 docs mark cross-dept as implemented.

### ADR-041 detail

**Context.** Desk and companion duplicated cosmic-glass color tokens; M10-04 still lacked
primary version chrome and HQ keyboard access.

**Decision.** Share `assets/cosmic-glass-tokens.css` via `/static` (desk) and Vite import
(companion). Show backend `health.version` in desk rail footer and above companion tabs.
HQ plan/iso tiles use tabindex + Enter/Space. Light polish is token-driven only.

**Alternatives considered.** Keeping duplicated `:root` blocks (approach 1) was rejected by
owner preference for a shared file. A npm design-system package was rejected as overkill.

**Consequences.** Token edits land once; desk layout CSS and companion shell CSS stay local.

### ADR-042 detail

**Context.** P4 registered remote hosts with heartbeats but dispatch remained same-host.
Operators need an honest path to run work off-box without inventing push/SSH trust.

**Decision.** Explicit `worker_host_id` on `dispatch-worker` enqueues `remote_worker_jobs`
only when the host is `ready`. A pull agent authenticates with the host token, claims a
lease, and posts mock completion. Omitting `worker_host_id` keeps local subprocess/container
dispatch. Remote Docker/file gateway is deferred.

**Alternatives considered.** Auto host placement and push-to-`base_url` were rejected for v1
(surprise routing / inbound trust). Full remote containers were deferred until leases work.

**Consequences.** `scripts/remote_worker_agent.py` is the reference agent. Control plane
never opens remote SSH.

### ADR-043 detail

**Context.** Explicit `worker_host_id` works but operators may want remotes by default
without typing an id each time.

**Decision.** Settings/env `FS_CORP_PREFER_REMOTE_WORKERS` (default false). When true and
dispatch omits `worker_host_id`, pick the first `ready` host ordered by `(label, id)`.
If none are ready, fail closed (422). Explicit `worker_host_id` always wins.

**Alternatives considered.** Silent local fallback was rejected (hides outages). Always-on
auto placement was rejected (surprise off-box runs).

**Consequences.** Enable the flag only when at least one agent is heartbeating.

### ADR-044 detail

**Context.** ADR-042 established explicit remote pull jobs with host-token claim and
mock completion, but did not execute the isolated worker image. Operators need an opt-in
container path without giving the container network access or control-plane credentials.

**Decision.** When `FS_CORP_REMOTE_WORKER_RUNTIME=container`, the pull agent runs the
configured worker image with `--network none`, writes the claimed command envelope to local
scratch, and relays allowlisted file-gateway requests over the existing host-token API.
Gateway activity renews the claim lease, and a dedicated renew route covers idle work.
Default agent behavior remains mock-complete. Remote egress is not enabled in this slice.

**Alternatives considered.** Giving the container direct API credentials or Docker network
access was rejected because it broadens the trust and egress boundary. Replacing the default
mock path was rejected because container execution must remain explicit and fail closed.

**Consequences.** Missing Docker or an unavailable image fails the claimed job rather than
falling back to mock completion. Artifacts relayed from `/work` are rooted by the control
plane. The relay permits only gateway checks, mock execution, and artifact storage; model
invocation remains local-only. Failed remote completion releases non-cancelled queue work for
redispatch, and pre-start failures retain the `remote_agent` runtime. Auto placement, registry
control, and remote ChatDev/provider egress remain separate work. No Alembic revision is
required.

### ADR-045 detail

**Context.** Track C needed a public entry point without moving or authentication-gating the
companion, plus an honest visual distinction for persisted Marketing rooms in the desk HQ.
The landing must not invent company statistics, activity, occupancy, or operational state.

**Decision.** Serve `GET /welcome` as unauthenticated FastAPI HTML styled with the shared
cosmic-glass tokens. Keep the companion at `/` and the CEO desk at `/desk`; the landing links
to both. Exempt `/welcome` from rate limiting and proxy that exact path through Caddy before
the companion SPA catch-all. In the desk projection, room types containing `market` map to
the distinct geometric `campaign` furniture kind, using persisted room data only.

**Alternatives considered.** Moving the companion away from `/` was rejected because it would
break the established same-origin mobile entry point. Serving a static landing from Caddy was
rejected because the existing FastAPI HTML/static-token path is smaller and directly tested.
Photoreal art and a marketing wing were rejected because neither is backed by persisted state.

**Consequences.** `/welcome` is a public read-only shell with no company data. The Caddy edge
routes it to FastAPI while `/` remains the companion. Marketing rooms gain a distinct desk SVG
mark without changing floorplans, occupancy, or companion behavior. No Alembic revision is
required. In v0.3.64 the welcome page gained self-hosted display/text fonts, a constellation
background motif, and stronger motion (reduced-motion respected). Desk `campaign` furniture
became a podium + banner mark. Photoreal art and invented wings remain out of scope.

### ADR-046 detail

**Context.** ADR-044 allowed opt-in remote container execution but fixed every container to
`--network none`. Remote ChatDev workers need the same company egress policy as same-host
workers without distributing allowlist hostnames or silently weakening fail-closed behavior.

**Decision.** Every remote job claim embeds an `egress` object with `mode` and
`docker_network`, derived from the company ChatDev egress setting. Allowlist mode carries only
the configured Docker network name. Missing, blank, `bridge`, or `host` names coerce to
`mode=none` and `docker_network=null` at claim. A container agent uses the named network only
when its local allowlist has at least one host and Docker reports that network; otherwise it
completes the job as failed. Mock execution ignores egress.

**Alternatives considered.** Sending hostnames or allowlist file contents on claims was
rejected because policy data belongs on each managed host. Silent fallback from an unready
allowlist to `--network none` was rejected because it disguises configuration failures.
Permitting Docker's default `bridge` or `host` networks was rejected because they bypass the
named allowlist boundary.

**Consequences.** Remote policy follows the control plane while readiness remains locally
enforced by the agent. Claims never expose allowlist hostnames. Existing none-mode containers
still run with `--network none`, and no Alembic revision is required.

### ADR-047 detail

**Context.** The companion exposed six implementation-oriented tabs and made the CEO move between
separate screens for pending decisions and owner requests. Its operational surfaces also lacked
the Syne/Manrope brand type already established on `/welcome`. The owner selected delivery
approach 1: ship the companion shell and CEO attention spine first, without rewriting every form
or the desk information architecture.

**Decision.** Regroup the companion under five primary domains: **Home · Work · People · Money ·
More**. Home is a Needs-you queue projected from the existing pending-decision and owner-inbox
lists, with the same scope-gated approve, reject and respond actions. Work contains Projects,
Corporate and Workers; People opens Organization; Money opens Finance; More retains Decisions,
Inbox, Diagnostics and Settings. Escalation creation remains only in More → Inbox. Share
self-hosted Syne display and Manrope body fonts through `assets/brand-fonts.css` and the existing
cosmic-glass tokens across companion, desk and welcome. No API contract or operational metric is
added.

**Alternatives considered.** A full companion form redesign and desk sidebar rewrite were
deferred because they would broaden the release beyond the selected shell-first approach.
Keeping six implementation-oriented tabs was rejected because it obscured the CEO's daily
attention loop. Duplicating font declarations per surface was rejected in favor of one
self-hosted asset.

**Consequences.** Existing capabilities remain available under new domain groupings, while Home
provides one persisted attention queue and an honest empty state. Read-only and missing-scope
behavior remains fail-closed. Deep layout polish inside Work, People and Money, and desk
information-architecture alignment remain follow-ups. No schema migration is required.

### ADR-048 detail

**Context.** After ADR-047 grouped the companion into five CEO-facing domains, Work and People
still mixed persisted lists, row decisions and creation/configuration forms in long panels. Money
already had a clear four-tab Finance structure. The owner selected a structure-first pass across
all three domains without new APIs, metrics or a desk redesign.

**Decision.** Give Projects, Corporate, Workers and Organization a reusable, panel-local
**Browse / Manage** segmented control that defaults to Browse. Browse owns persisted lists,
details and in-row actions; Manage owns create, enroll, assign and configure flows. Project
details and dispatch remain reachable from Browse. Finance keeps **Overview · Invoices ·
Adjustments · Periods** and its create flows on those tabs, with no nested Browse/Manage layer.
Mode is ephemeral React state, and existing server-side scope enforcement and inline missing-scope
notices remain authoritative.

**Alternatives considered.** URL-backed modes were deferred because no cross-session mode
identity is required. A nested Finance mode was rejected because it would duplicate its existing
navigation. Moving every write into Manage was rejected because contextual row actions such as
decide, accept, enable/disable and dispatch belong with the records they affect.

**Consequences.** The companion gains a consistent scan-versus-configure hierarchy while
preserving every existing API contract and persisted-data rule. Large Work and People surfaces
are isolated in `ProjectsPanel`, `CorporatePanel`, `WorkersPanel` and `OrgPanel`; `App` retains
data loading and orchestration. No Alembic revision is required. Deeper visual polish,
master-detail project UX and desk five-domain alignment remain follow-ups.

### ADR-049 detail

**Context.** After ADR-047 grouped the companion into five CEO-facing domains and ADR-048
added Browse/Manage inside Work and People, the HTML CEO desk still used a flat sidebar
and a section order that did not match those domains. The owner selected a desk
information-architecture pass — nav plus long-page order — without new APIs, invented
metrics or companion-style domain panes.

**Decision.** Group the desk rail under **Home · Work · People · Money · More** with
always-expanded nested anchors to existing section `id`s. Reorder the main column to the
same map. Home is hybrid: metrics, Decisions and Consultant first, Headquarters kept high,
Status last in Home. Scorecard moves under Work. More is the leftover rail (Intelligence,
Diagnostics, Activity, Pairing). Domain labels are non-linking group headings. Section
`id`s stay unchanged so bookmarks and existing tests remain valid.

**Alternatives considered.** Domain show/hide panes were rejected because the desk remains
one long scroll. Browse/Manage on desk and an HQ interaction redesign were out of scope.
Renaming section `id`s was rejected to preserve deep links. Duplicating Decisions and
Consultant under More was rejected so each surface appears once.

**Consequences.** Desk and companion now share the same five-domain map. Pairing and
head-inbox anchors are present on the rail. No Alembic revision or control-plane API
change is required. Companion Browse/Manage visual polish remains the follow-up.

### ADR-050 detail

**Context.** After ADR-048 added Browse/Manage inside Work and People and ADR-049 aligned
the desk to the same five domains, Projects Browse still stacked list and workspace in
one column. The owner selected a Projects-first master-detail split plus medium shared
shell polish, without new APIs, URL-synced selection or a Finance ModeSwitch.

**Decision.** Projects Browse uses a responsive list|detail split (`project-browse-split`).
Wide viewports (≥720px) place the list beside the selected project workspace; narrow
viewports stack list above detail. The detail pane holds the existing project identity
and dispatch workspace. When nothing is selected, the detail pane shows “Select a
project”. A quiet Clear selection control sets `selectedProject` to null. Manage remains
local enroll and GitHub assign. Corporate, Workers and Organization receive medium
empty-state and section-head polish only.

**Alternatives considered.** URL-synced `?project=` was deferred. Nested Browse/Manage on
Finance was rejected. Deep Corporate/Workers/Org restructure and extracted shared
`PanelChrome` / `ProjectBrowseSplit` components were out of scope. Desk and welcome
changes were not requested.

**Consequences.** Companion Projects Browse is usable as a split workspace outside a
phone column. No Alembic revision or control-plane API change is required. Further
Corporate hierarchy polish, URL sync and reusable split components remain owner-directed
follow-ups.

### ADR-051 detail

**Context.** After ADR-050 added a Projects Browse list|detail split and medium
empty/section polish on sibling panels, Corporate Browse lists still mixed bare
`<h2>` titles with `section-head`, and the Workers “Worker hosts” title sat inside
the list card. The owner selected a consistency pass without groups, Org
restructure, new APIs or URL-synced selection.

**Decision.** Corporate Browse lists use `section-head` titles and `panel-empty`
empty states (Objectives, Industry packs, Divisions, Pending promotions, Staffing
proposals, Cross-department requests, Open activity). The Workers “Worker hosts”
`section-head` sits outside the list card, matching Projects and Corporate
Objectives. Manage forms and capabilities are unchanged.

**Alternatives considered.** Corporate Browse groups or sub-tabs were deferred.
Org hierarchy redesign was out of width. The Projects list-row `div`→`span` HTML
fix and URL-synced `?project=` were deferred. Extracted shared `PanelSection`
components were out of scope. Desk and welcome changes were not requested.

**Consequences.** Corporate and Workers Browse titles and empties match the
Projects/Objectives pattern. No Alembic revision or control-plane API change is
required. Corporate visual groups, Org polish, URL sync and reusable split
components remain owner-directed follow-ups.

### ADR-052 detail

**Context.** After ADR-051 aligned Corporate and Workers Browse titles, Organization
still used a mix of bare Manage `<h2>` titles and a Departments catalog without a
`section-head`. The owner selected an in-place Org polish without Manage grouping,
Corporate groups, new APIs or URL-synced selection.

**Decision.** Organization Browse adds a **Departments** `section-head` above the
catalog cards and keeps the existing Head inbox `section-head` + `panel-empty`
(including inline assign). Each Manage form title uses `section-head` outside the
form card: Create department, Appoint department head, Vacate department head,
Assign position, Release assignment, Create position, Reorder departments,
Activate dormant department for project, and Worker card. Fields, `runAction`
handlers and scope notices stay unchanged.

**Alternatives considered.** Manage visual groups (Catalog · Seats · Positions)
were deferred. Corporate Browse groups/sub-tabs, the Projects list-row HTML nit
and URL-synced `?project=` were out of width. Extracted shared `PanelSection`
components were out of scope. Desk and welcome changes were not requested.

**Consequences.** Org Browse and Manage titles match the Corporate/Workers
section-head pattern. No Alembic revision or control-plane API change is
required. Manage grouping, Corporate visual groups, URL sync and reusable split
components remain owner-directed follow-ups.

### ADR-053 detail

**Context.** After ADR-051/052 aligned Browse section-head titles across Work and
People panels, Corporate Browse remained a long ungrouped scroll of eight
lists. The owner selected in-place cluster grouping with a hybrid viewport
pattern rather than new APIs, URL sync or Manage regrouping.

**Decision.** Corporate Browse groups lists into four fixed clusters — **Strategy**
(CEO scorecard, Objectives), **Structure** (Industry packs, Divisions),
**People** (Pending promotions, Staffing proposals), **Coordination**
(Cross-department requests, Open activity) — each labeled with `cluster-head`.
At viewport width ≥720px all clusters render as labeled scroll sections; below
720px a segmented `role="tablist"` switches among clusters (default Strategy)
while keeping the cluster label in the active pane. Manage adds `section-head`
titles outside form cards for Corporate operations, Create objective, Propose
division, and Create cross-department request only; fields and `runAction`
handlers are unchanged.

**Alternatives considered.** Always-on segmented tabs (rejected — wide viewports
should show full scroll context). CSS-only grouping without local cluster state
(rejected — narrow viewports need explicit tab switching). Extracted
`ClusterSwitch` component (deferred). URL-synced cluster selection, Manage
visual groups and Projects list-row HTML nit remain out of scope.

**Consequences.** Companion v0.3.71 ships Corporate Browse clusters and light
Manage titles with no Alembic revision or control-plane API change. URL sync,
Manage grouping and shared cluster/tab extraction remain owner-directed
follow-ups.

### ADR-054 detail

**Context.** After ADR-050 split Projects Browse into list|detail, list-row buttons
still wrapped brief and blockers in `<div className="muted">`, which is invalid
HTML inside `<button>`. The loaded detail pane already exposed **Clear selection**
via `detail-toolbar`, but the loading card showed only a muted “Loading…” line
with no way to deselect until fetch completed. The empty “Select a project” pane
correctly omits Clear.

**Decision.** Replace list-row muted lines with `<span className="muted">` and
ensure `.list-row .muted { display: block; }` preserves stacked layout. When
`selectedProject && !projectDetail`, render a `detail-toolbar` with the project id
and **Clear selection** (`setSelectedProject(null)`) above a muted “Loading…”
line — matching the loaded-detail toolbar pattern. Leave the empty pane and Manage
enroll/assign unchanged.

**Alternatives considered.** CSS-only fix without span swap (rejected — does not
fix invalid HTML). Clear on the empty pane (rejected — owner lock). Extract shared
`DetailToolbar` component (deferred). URL-synced project selection remains out of
scope.

**Consequences.** Companion v0.3.72 ships the span fix and loading Clear with no
Alembic revision, control-plane API change or URL sync. Manage visual groups and
shared detail-toolbar extraction remain owner-directed follow-ups.

### ADR-055 detail

**Context.** After ADR-054, companion tab and Projects selection lived only in
React state — refresh or share lost context. Owner wanted shareable deep links
without React Router, Browse/Manage in the URL, or new APIs. Pairing via
`#fs-pair=` must remain unchanged.

**Decision.** Add pure `parseCompanionSearch` / `serializeCompanionSearch` helpers
(in `companion/src/urlState.ts`) and wire `App.tsx` to boot from
`window.location.search`, write canonical `?tab=` / `?project=` on every tab or
selection change via `history.replaceState`, re-parse on `popstate`, clear
`selectedProject` when leaving Projects or using Clear selection, and silently
drop unknown project ids after the enrolled list loads (no toast). Hash reserved
for pairing; pathname unchanged.

**Alternatives considered.** React Router (rejected — dependency and scope).
Hash-based tab routing (rejected — conflicts with `#fs-pair=`). `pushState` Back
stacks (rejected — owner lock for replace-only). URL sync for Browse/Manage or
Corporate clusters (deferred).

**Consequences.** Companion v0.3.73 ships tab/project URL sync with no Alembic
revision or control-plane API change. Manage visual groups and Browse/Manage or
cluster URL sync remain owner-directed follow-ups.

### ADR-056 detail

**Context.** After ADR-053/055, Corporate Browse had hybrid cluster chrome with a
private `useWideViewport` hook while Organization, Corporate, Projects and Workers
Manage remained long ungrouped scrolls of forms. The owner selected one release
wiring shared hybrid chrome across all four Manage panels without URL sync, new
APIs or regrouping Corporate Browse clusters.

**Decision.** Extract shared `useWideViewport` (`matchMedia("(min-width: 720px)"`)
and `ManageClusters` (labeled scroll on wide viewports; segmented group tabs on
narrow). Wire Manage groups on Organization (Catalog · Seats · Positions ·
Lookup), Corporate (Goals · Structure · Coordination · Ops), Projects (Enroll ·
GitHub) and Workers (Hosts · Token with honest empty when no token). Corporate
Browse switches to the shared hook; Browse cluster markup stays in
`CorporatePanel`. Preserve all fields, `runAction` keys, scope notices and Browse
modes.

**Alternatives considered.** Per-panel private hooks (rejected — duplicates
720px logic). URL-synced Manage group selection (rejected — owner lock). Finance
ModeSwitch (rejected — out of scope). Regrouping Corporate Browse clusters
(rejected — Browse membership unchanged).

**Consequences.** Companion v0.3.74 ships Manage visual groups with no Alembic
revision or control-plane API change. Manage/Browse URL sync, Finance ModeSwitch
and empty-list unknown-project URL edge nit remain owner-directed follow-ups.

### ADR-057 detail

**Context.** ADR-055 cleared unknown `?project=` ids only when the enrolled
projects list was non-empty (`!projects.length` early-return). A stale deep link
therefore survived when enroll was loaded and empty — the same “unknown id” case
with zero rows.

**Decision.** Add `projectsLoaded` (default `false`); set `true` only on the
successful refresh path that applies `setProjects`. Replace the clear effect gate
with `!projectsLoaded || !selectedProject` so empty lists after a successful load
still clear silently via existing `setSelectedProject(null)` and replaceState.
Refresh failure leaves `projectsLoaded` false and preserves boot/`popstate`
selection until a later success.

**Alternatives considered.** Nullable `projects: null | array` (rejected — owner
lock for boolean flag). Clearing before first successful fetch (rejected — would
drop valid deep links during loading). Error toasts for unknown ids (rejected —
non-goal).

**Consequences.** Companion v0.3.75 closes the empty-list URL edge with no
Alembic revision, control-plane API change or new serialize/parse semantics.
Manage/Browse URL sync and Finance ModeSwitch remain owner-directed follow-ups.

### ADR-058 detail

**Context.** After ADR-055/056/057, companion tab and project deep links worked
via `replaceState`, but Browse/Manage mode, Corporate Browse clusters and Manage
visual groups lived only in panel-local React state — refresh or share lost
context. Owner wanted shareable `mode`/`cluster`/`group` params without React
Router, `pushState` Back stacks, Finance ModeSwitch or new APIs. Pairing via
`#fs-pair=` must remain unchanged.

**Decision.** Extend `urlState.ts` with parse/serialize for `mode` (`browse` |
`manage`), `cluster` (Corporate Browse ids) and `group` (Manage ids per tab);
omit defaults (`browse`, `strategy`, tab default group). Lift `panelMode`,
`corporateCluster` and `manageGroup` to `App.tsx`; pass controlled props to
Org/Corporate/Projects/Workers panels and optional controlled `activeGroupId` to
`ManageClusters`. Write canonical search on every relevant state change via
`history.replaceState`; re-parse on `popstate`. Workers token-after-create forces
`group=token`. Existing `tab`/`project` rules unchanged.

**Alternatives considered.** React Router (rejected — dependency and scope).
`pushState` Back stacks (rejected — owner lock for replace-only). Finance
ModeSwitch in the same release (rejected — out of scope). Panel-local URL writes
(rejected — owner lock for App-owned state).

**Consequences.** Companion v0.3.76 ships mode/cluster/group URL sync with no
Alembic revision or control-plane API change. Finance ModeSwitch and `pushState`
Back stacks remain owner-directed follow-ups.

### ADR-059 detail

**Context.** After ADR-058, Work and People panels deep-linked Browse/Manage mode
and Manage visual groups via App-owned URL state, but Finance still used flat
sub-tabs with create forms mixed into Browse. Owner wanted the same lists-vs-forms
split and full `mode`/`group` URL sync on Money without new finance APIs or
changing ADR-038 money math.

**Decision.** Add `finance` to `MODE_CAPABLE_TABS` with mode-aware browse and manage
group tables. Split `FinancePanel` with `ModeSwitch` and hybrid `ManageClusters`:
Browse holds Overview, Invoices, Adjustments and Periods (Close period stays an
in-row Browse action); Manage holds Create invoice, Post adjustment and Set period
forms. App wires controlled `mode` and `group` like other panels; serialize `group`
in both Browse and Manage for finance; omit default groups from the URL.

**Alternatives considered.** Nested Browse/Manage only inside Finance without URL
sync (rejected — inconsistent with 0.3.76). Moving Close period to Manage
(rejected — owner lock). New finance APIs or desk surface (rejected — out of scope).

**Consequences.** Companion v0.3.77 ships Finance Browse/Manage with URL sync and
no Alembic revision or control-plane API change. `pushState` Back stacks and desk
Finance surface remain owner-directed follow-ups.

For each future decision, add context, alternatives, rationale, consequences and superseded decision if any. Never rewrite history to suggest an untested choice was validated.
