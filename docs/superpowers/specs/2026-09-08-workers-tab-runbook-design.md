# Design: Companion Workers tab + remote agent runbook

Date: 2026-09-08. Status: **implemented** in v0.3.63.

## Goal

Let the CEO manage registered remote worker hosts from the companion and follow a
short remote-agent runbook — without inventing host state, shipping TailscaleKit
binaries, or adding new control-plane routes.

Sequence after this track: deeper marketing redesign.

## Locks (owner brainstorming)

| Topic | Choice |
|---|---|
| Intent | Second-host **ops polish** (not real TailscaleKit) |
| Depth | Companion Workers UI + short agent runbook |
| Tab placement | Primary tab (beside Home / Projects / Org / Corporate) |
| Approach | Companion-first on existing `/api/v1/worker-hosts*` + docs |

## Non-goals

- Real TailscaleKit / libtailscale / store VPN embedding
- Settings UI for `FS_CORP_PREFER_REMOTE_WORKERS` (already in catalog; defer)
- Desk Workers surface, systemd unit packaging
- Job claim/list UI, companion-originated heartbeats
- Alembic / schema changes
- New ADR number (surfaces ADR-040 / ADR-042)

## Architecture

### Backend

No new routes. Use existing CEO APIs:

| Method | Path | Scope | Notes |
|---|---|---|---|
| GET | `/api/v1/worker-hosts` | company.read | Includes computed `state` |
| POST | `/api/v1/worker-hosts` | company.pause + CEO | Body `label`, https `base_url`; response includes one-time `token` |
| POST | `/api/v1/worker-hosts/{id}/enable` | company.pause + CEO | |
| POST | `/api/v1/worker-hosts/{id}/disable` | company.pause + CEO | |
| DELETE | `/api/v1/worker-hosts/{id}` | company.pause + CEO | |

`base_url` remains an https origin (no path/query/credentials) per `worker_hosts.py`.

### Companion

- Add `"workers"` to the `Tab` union and **PRIMARY_TABS** as **Workers**.
- Update `tests/test_companion_api.py` `test_companion_nav_is_five_tabs_with_more_switcher`:
  primary tab count **4 → 5** (test name may stay or be renamed to match).
- Create `companion/src/WorkersPanel.tsx` (FinancePanel-style props: `api`, `hasToken`,
  `canPause`, `scopeNotice`, `runAction`, `status`).
- Client methods on `ApiClient`: `workerHosts`, `createWorkerHost`, `enableWorkerHost`,
  `disableWorkerHost`, `deleteWorkerHost`.
- Wire `{tab === "workers" && <WorkersPanel … />}` from `App.tsx`.

**UX**

1. On tab enter (when `hasToken`): `GET` hosts; show load error without inventing rows.
2. List each host: label, id (short), `base_url`, **state** from API (`ready` / `stale` /
   `disabled`), `last_heartbeat_at`.
3. Create form (CEO/`company.pause`): label + https base URL → on success show token
   panel (“shown once — copy now”) with Copy; never re-fetch or re-display after dismiss/reload.
4. Per row: Enable or Disable; Delete with `window.confirm`.
5. After mutations, reload list. Clear create fields after success (token panel may remain
   until dismissed or next create).

Mutate controls gated on `canPause`; server remains authoritative (`_ceo`).

### Docs

Add a short **Remote worker agent** section (prefer `docs/25-fs-dev-deployment.md`,
cross-link from `docs/24-mobile-companion.md`):

- Script: `scripts/remote_worker_agent.py`
- Env: `FS_CORP_CONTROL_URL`, `FS_CORP_WORKER_HOST_ID`, `FS_CORP_WORKER_HOST_TOKEN` or
  `_TOKEN_FILE`, optional `FS_CORP_REMOTE_WORKER_RUNTIME=container`, image/scratch
- Control URL must be reachable from the agent host (LAN or tailnet)
- Token comes from companion create (one-time); lost token → delete host and recreate
- TailscaleKit remains stubbed; clipboard + system Tailscale app path unchanged

## Failure modes

| Case | Result |
|---|---|
| Missing `company.read` | Load fails; error message; no fake hosts |
| Non-CEO / missing `company.pause` | Forms gated; server 403 |
| Invalid `base_url` | Server reject; show API error |
| Delete without confirm | No DELETE |
| Token lost after create | Honest copy: recreate host; no second reveal |

## Testing

- Companion source assertions: primary **Workers**, `WorkersPanel`, client methods.
- Nav test expects **5** primary tabs.
- `cd companion && npm run build`
- `.venv/bin/python -m unittest discover -s tests` before merge

## Docs / version

- `docs/24-mobile-companion.md` — Workers primary tab
- `docs/25-fs-dev-deployment.md` — remote agent runbook
- `docs/14-roadmap.md` / `docs/18-handoff.md` — next → marketing redesign
- Version **0.3.63** (`company/__init__.py`, `companion/package.json`)

Do not commit `local repos/service-department/`.

## Acceptance

1. Primary **Workers** tab lists hosts with API `state` only.
2. Create shows one-time token once; never invents a second reveal.
3. Enable / disable / delete work; delete requires confirm.
4. Runbook documents agent env vars and reachability.
5. TailscaleKit stub unchanged; no Alembic; no new worker-host routes.
