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

### ADR-010 detail

**Context.** M1 requires an authenticated local control service, schema migrations, and the proposed `/api/v1` contract. The v0.2.0 core is a standard-library CLI with ad-hoc `CREATE TABLE IF NOT EXISTS` and trusted actor strings.

**Decision.** Implement the control service with Python 3.12, FastAPI, and Uvicorn bound to `127.0.0.1`. Version the schema with Alembic. Keep SQLite for single-owner local operation. Keep `company.core.Company` as the domain engine so the existing unittest suite remains the invariant gate. Identity comes from bearer tokens, never from request bodies.

**Alternatives considered.**

- stdlib `http.server`: no request schemas, no dependency, but weak validation and more custom code for the command envelope.
- Django: batteries included, heavier than a loopback command API and further from ChatDev's FastAPI/Starlette ecosystem.

**Consequences.** `pyproject.toml` gains `fastapi`, `uvicorn`, and `alembic` (Alembic brings SQLAlchemy). The offline demo CLI must still run without talking to the network. The service must not be advertised as a trusted remote API. Live ChatDev, GitHub, and market adapters remain disabled.

### ADR-011 detail

**Context.** The owner asked the company to take firmware and board-support work (ESP32, Raspberry Pi, RockPro64 and similar) and to have pertinent employees learn online when the current skill configuration cannot perform the work.

**Decision.** Treat hardware as software-for-boards, not physical fabrication. Persist a skill catalog, project capability rows, learning assignments, and certified `acquired_skills`. Block `draft` / `review` / `prepare_pr` while required skills are missing. Study uses the same HTTPS metadata ingest as market signals. Certification requires an independent CEO reviewer. `LearningAdapter.fetch` stays fail-closed until an approved source list and the action gateway exist.

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

For each future decision, add context, alternatives, rationale, consequences and superseded decision if any. Never rewrite history to suggest an untested choice was validated.
