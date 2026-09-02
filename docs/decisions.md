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
| ADR-016 | 2026-09-01 | Native control plane + Caddy edge on owned Debian host; Docker for workers only | fs-dev phase 1: systemd runs API on 127.0.0.1:8000; Caddy terminates TLS on 192.168.4.100 and serves companion + /api proxy; ufw denies LAN:8000. Container workers and 192.168.4.101 are phase 2. |
| ADR-017 | 2026-09-01 | Cosmic-restraint visual system | Owner-selected palette and glass chrome for desk + companion. Metrics and HQ tiles bind only to persisted API state. Furnished room art stays deferred. |
| ADR-018 | 2026-09-01 | QR pairing with scoped access levels | CEO desk issues one-time tickets with `read_only`, `user`, or `admin` levels. Redeem creates service principals with explicit scopes — never root owner token or `*`. `FS_CORP_PUBLIC_URL` shapes pair URLs; optional `FS_CORP_TAILSCALE_AUTHKEY` returns only on redeem. PWA cannot join kernel VPN; native shell may consume auth key later. |

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

**Decision.** Add `company.worker` with a `SubprocessWorkerRuntime` that spawns a child process. The child runs `MockChatDevAdapter` locally and requests effects through a pipe to the parent, which enforces an allowlisted gateway. `ContainerWorkerRuntime` is defined but raises `NotImplementedError` until Docker and a worker image are available. Persist `worker_runs` for audit.

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

**Consequences.** `deploy/fs-dev/` ships `install.sh`, systemd unit, Caddyfile, ufw example, and worker Dockerfile/compose (scaffold). Runbook in [25-fs-dev-deployment.md](25-fs-dev-deployment.md). Live adapter dispatch and worker host on `.101` remain owner-configuration work (phase 2).

### ADR-018 detail

**Context.** M8 mobile companion needed frictionless phone onboarding without embedding the root owner bearer token in QR codes or URLs. Owners also need to delegate read-only or user-level mobile access separate from full CEO mobile actions.

**Decision.** CEO desk issues one-time pairing tickets stored with an `access_level` (`read_only`, `user`, `admin`). QR encodes only `pair_url` with `#fs-pair={ticket}`. Redeem creates a **service principal** with level-specific scopes; `admin` maps to `COMPANION_SCOPES`, never `kind: owner`. Optional `FS_CORP_TAILSCALE_AUTHKEY` is returned **only** on redeem. `FS_CORP_PUBLIC_URL` sets the recommended origin for pair URLs on fs-dev.

**Alternatives considered.**

- Put owner token in QR: rejected — phone compromise would equal root authority.
- Client-selected level on redeem: rejected — level is bound at issue time in the database.
- Server-side Tailscale join for phones: rejected — kernel VPN join is device-local; PWA cannot join; native shell may consume auth key in phase 2.

**Consequences.** Alembic `0010_pairing_tickets`, `0011_pairing_access_level`. Routes `GET/POST /api/v1/remote-access*`. Companion auto-redeems hash on load and scope-gates UI. Dev preview may set `FS_CORP_ALLOW_CORS=1` for loopback companion on `:4173`.

For each future decision, add context, alternatives, rationale, consequences and superseded decision if any. Never rewrite history to suggest an untested choice was validated.
