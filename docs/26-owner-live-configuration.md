# Owner live-configuration checklist

Phased inventory of credentials and decisions needed to move from the offline/fs-dev scaffold to live integrations. **Nothing requires going full-live at once.** Live adapters remain fail-closed until credentials exist and the corresponding adapter slice is wired.

See also: [25-fs-dev-deployment.md](25-fs-dev-deployment.md), [08-github-cursor.md](08-github-cursor.md), [06-model-routing.md](06-model-routing.md), [09-market-intelligence.md](09-market-intelligence.md).

Track progress in a private copy of [`config/owner-live.checklist.template.json`](../config/owner-live.checklist.template.json) (save as `config/owner-live.checklist.json`, gitignored).

Check status without printing secrets:

```bash
python3 scripts/check_owner_config.py
# or against production env file:
python3 scripts/check_owner_config.py --env-file /etc/fs-corporation/secrets.env
```

## What already works without live credentials

| Capability | Requirement |
|---|---|
| CEO desk + companion (LAN or Docker dev) | Host or `docker compose up`; owner token |
| QR pairing with access levels | `FS_CORP_PUBLIC_URL` |
| Scoped companion tokens + revoke | No extra secrets |
| Governance, mock tasks, audit, SLO catalog | None |

## Tier A — Host and network

| Item | Where | Unlocks |
|---|---|---|
| fs-dev host | Debian 12+ you control | Production install |
| Primary LAN IP | `FS_CORP_LAN_IP`, Caddyfile | Phone on Wi‑Fi |
| Worker NIC (phase 2) | `FS_CORP_WORKER_NIC_IP=192.168.4.101` | Container workers |
| TLS | Caddy `tls internal` or real cert | HTTPS companion |
| SSH/sudo | Operator access | Install, updates |
| Firewall | ufw: 22/443; deny LAN:8000 | Security model |
| Backups | SQLite + `/etc/fs-corporation` | Recovery |

**Optional**

| Item | Env var | Unlocks |
|---|---|---|
| Tailscale IP | `FS_CORP_TAILSCALE_IP` + Caddy block | Off-LAN HTTPS |
| Tailscale auth key | `FS_CORP_TAILSCALE_AUTHKEY` (redeem only) | Off-LAN pairing handoff |
| Dev CORS | `FS_CORP_ALLOW_CORS=1` | Companion Vite → Docker API |
| Docker dev API | `docker compose up` | Local API on :8013 |

## Tier B — First live slice (recommended order)

### 1. GitHub pilot

| Credential / info | Env / storage |
|---|---|
| GitHub App ID | `GITHUB_APP_ID` |
| Installation ID | `GITHUB_INSTALLATION_ID` |
| App private key | `GITHUB_PRIVATE_KEY_FILE` (PEM on host, mode 600) |
| Webhook secret | `GITHUB_WEBHOOK_SECRET` |
| Disposable repo | owner/name + numeric **repo ID** |
| Optional upstream repo ID | Fork workflow |
| Branch policy | Protected branches, prefix (`company/`), permitted actions |

Enroll via `enroll_github` (CEO): `upstream_repo_id`, `fork_repo_id`, `protected_branches`, `branch_prefix`, `permitted_actions`.

**Acceptance:** small file change → PR on a repo with no production secrets.

### 2. One text model

| Credential / info | Env / storage |
|---|---|
| Provider | OpenAI-compatible (`openai`, `openai-compatible`) or Anthropic (`anthropic`, `claude`) |
| Exact model ID | Provider-supported string |
| API key | `MODEL_PROVIDER_API_KEY` (OpenAI-compatible) and/or `ANTHROPIC_API_KEY` (Claude) |
| Profile config | Copy `config/models.example.json` → enable one profile |
| Data class | Per-project `public` / `internal` / `restricted` |
| Spending caps | Policy `company_budget_cents` and grants |

Today `invoke_model` uses `mock` offline, OpenAI-compatible `/chat/completions` when `MODEL_PROVIDER_API_KEY` is set, and Anthropic `/v1/messages` when `ANTHROPIC_API_KEY` is set. Enable profiles in `config/models.example.json` (see `reasoning-cloud` and `claude-reasoning`).

### 3. One market feed

| Credential / info | Notes |
|---|---|
| HTTPS feed URL | CEO `approve_feed_source` |
| Optional API key | Vendor-specific (add named env when chosen) |
| Poll cadence / budget | Operational decision |

### 4. Container worker

| Item | Notes |
|---|---|
| Docker on worker host | `.101` or same host for build test |
| Image | `docker compose --profile workers build` or `docker build -f deploy/fs-dev/Dockerfile.worker -t fs-corporation-worker:local .` |
| No owner token in worker | Scratch gateway only |

## Tier C — Optional / second wave

| Integration | Credentials | Code status |
|---|---|---|
| Web Push | VAPID public/private + contact email | Live when keys set; `scripts/verify_vapid.py` |
| Image model | `IMAGE_PROVIDER_API_KEY` | Profile placeholder only |
| Learning fetch | Approved HTTPS URLs + egress allowlist | `LearningAdapter` fail-closed |
| ChatDev live | Pinned checkout + workflow YAML + model in worker | `ChatDevAdapter` fail-closed |
| GitHub webhooks | Public HTTPS URL + webhook secret | Outbound pilot does not require |
| Production SLOs | Measurement source + windows | API ready; no samples |
| Real billing | Payment provider | Separate from simulated credits |

## Tier D — Policy decisions (not secrets)

| Decision | Why |
|---|---|
| Pilot project id + brief | First enrolled project |
| Active departments | Start small per roadmap |
| Delegation grants | Head/specialist scopes |
| Company budget (cents) | Policy limits |
| Fork vs branch-only | Org policy |
| Data classes per project | Model routing |
| Feed topics | Intelligence scope |
| Off-LAN model | LAN vs Tailscale |

## Never commit

Owner token, App private key, model keys, Tailscale auth keys, VAPID private key, webhook secrets, or filled `owner-live.checklist.json`.

## Recommended collection order

1. Host + `FS_CORP_PUBLIC_URL` (or Docker dev)
2. GitHub App + disposable repo IDs
3. One model key + model ID
4. One feed URL
5. Worker image build on `.101`
6. Tailscale (if off-LAN)
7. VAPID (if push beats polling)
