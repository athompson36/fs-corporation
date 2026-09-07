# Design: Settings platform (P1 slice A)

Date: 2026-09-07. Status: **approved for planning** (not implemented).

## Goal

1. Let the owner (or paired admin) **view and edit** a small allowlisted set of **non-secret** runtime knobs from the **companion Settings** tab.
2. Persist those knobs in a **SQLite overlay** so Settings changes do not rewrite host `secrets.env`.
3. Expose **secrets configured/missing status only** — never secret values in API responses, UI, or logs.
4. Fail closed on unknown keys and unauthorized writers.

Owner-approved scope: Settings **C**, delivery slice **A**, architecture **Approach 1**, resolution **overlay wins** for allowlisted keys.

## Decisions

| Topic | Choice |
|---|---|
| Scope | Slice A: API + SQLite overlay + companion Settings; desk Settings later |
| Architecture | Catalog module + `company_settings` table |
| Resolution | Overlay → env → catalog default (overlay wins when set) |
| Secrets | Status only (`configured: true\|false`); host `secrets.env` remains sole secret store |
| Host-bound | LAN IP, worker NIC IP, gateway egress: read-only in GET; not PATCHABLE |
| Rate limits | Mark `restart_required: true` in this slice (limiter built at app start); honest, not fake hot-apply |
| Auth write | `_ceo_or_admin_companion` + `company.pause` |
| Auth read | `company.read` for settings catalog and secrets-status |

## Non-goals (this slice)

- Desk Settings UI.
- Writing or reading secret values via API.
- Editing host-bound IPs / install paths from the phone.
- Full Company / Models / Feeds / SLO CRUD inside Settings (existing endpoints remain; later sections).
- Inventing HQ occupancy or financial state from Settings.
- Auto-restart of systemd after PATCH.

## Persistence

### Table `company_settings`

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PRIMARY KEY | Must be in catalog and `editable` |
| `value_json` | TEXT NOT NULL | Canonical JSON encoding of typed value |
| `updated_at` | TEXT NOT NULL | ISO-8601 UTC |
| `updated_by` | TEXT NOT NULL | Actor principal id |

Alembic migration for file-backed DBs; `:memory:` via `SCHEMA` update.

### Catalog module `company/settings_catalog.py`

Each entry: `key`, `type` (`int` \| `float` \| `string` \| `bool` \| `enum`), `default`, optional `min`/`max`/`enum_values`, `editable`, `restart_required`, `description`, optional `env_name` (same as key for `FS_CORP_*`).

Unknown keys rejected. Type coercion fail closed (422).

### Effective value

```
if overlay row exists: use overlay (source=overlay)
else if env set (non-empty): use parsed env (source=env)
else: catalog default (source=default)
```

`POST …/reset` deletes overlay row(s) for allowlisted editable keys only.

## Allowlisted keys (editable)

| Key | Type | Default | restart_required |
|---|---|---|---|
| `FS_CORP_RATE_LIMIT_AUTH` | int ≥ 1 | 120 | true |
| `FS_CORP_RATE_LIMIT_UNAUTH` | int ≥ 1 | 60 | true |
| `FS_CORP_RATE_LIMIT_WINDOW_SEC` | float > 0 | 60 | true |
| `FS_CORP_SSE_IDLE_SEC` | float ≥ 0 | 1 | false (read per stream) |
| `FS_CORP_PUBLIC_URL` | string | `""` | false |
| `FS_CORP_DEFAULT_WORKER_RUNTIME` | enum `subprocess` \| `container` | `container` | false (read at dispatch) |
| `FS_CORP_MODEL_CENTS_PER_1K_TOKENS` | int ≥ 0 | 0 | false (read at price) |
| `CHATDEV_ALLOW_CONTROL_PLANE` | bool | false | false (read at ChatDev run) |
| `FS_CORP_IDEMPOTENCY_RETENTION_DAYS` | int ≥ 1 | 7 | false (read at prune) |

## Read-only host-bound (GET only)

| Key | Notes |
|---|---|
| `FS_CORP_LAN_IP` | env or unset; `editable: false` |
| `FS_CORP_WORKER_NIC_IP` | env or unset; `editable: false` |
| `FS_CORP_GATEWAY_EGRESS` | env or unset; `editable: false` |

## API

Base path `/api/v1`. Actor from bearer token. Payload must not supply actor identity.

### `GET /api/v1/settings`

Scope: `company.read`.

```json
{
  "items": [
    {
      "key": "FS_CORP_SSE_IDLE_SEC",
      "value": 1.0,
      "default": 1.0,
      "source": "default",
      "type": "float",
      "editable": true,
      "restart_required": false,
      "description": "SSE idle sleep seconds between event pages"
    }
  ]
}
```

Includes editable + read-only host-bound entries.

### `PATCH /api/v1/settings`

Scope: `company.pause` + `_ceo_or_admin_companion`.  
Body: `{ "updates": { "FS_CORP_SSE_IDLE_SEC": 2 } }` — only known editable keys.  
Empty updates → 422. Success returns `{ "items": [ …changed… ] }` and emits `settings.updated`.

### `POST /api/v1/settings/reset`

Same auth as PATCH.  
Body: `{ "keys": ["FS_CORP_SSE_IDLE_SEC"] }` **or** `{ "all_overlay": true }`.  
Deletes overlay rows; emits `settings.reset`. Returns refreshed items for affected keys.

### `GET /api/v1/settings/secrets-status`

Scope: `company.read`.

```json
{
  "secrets": [
    { "name": "MODEL_PROVIDER_API_KEY", "configured": false },
    { "name": "ANTHROPIC_API_KEY", "configured": false },
    { "name": "GITHUB_APP_ID", "configured": false },
    { "name": "GITHUB_INSTALLATION_ID", "configured": false },
    { "name": "GITHUB_PRIVATE_KEY_FILE", "configured": false },
    { "name": "GITHUB_WEBHOOK_SECRET", "configured": false },
    { "name": "FEED_API_KEY", "configured": false },
    { "name": "IMAGE_PROVIDER_API_KEY", "configured": false },
    { "name": "VAPID_PUBLIC_KEY", "configured": false },
    { "name": "VAPID_PRIVATE_KEY", "configured": false },
    { "name": "FS_CORP_TAILSCALE_AUTHKEY", "configured": false }
  ]
}
```

`configured` is true iff the env var is non-empty (for `*_FILE` keys: path set and file exists, matching `scripts/check_owner_config.py` intent). **Never return values or path contents.** Align the name list with `scripts/check_owner_config.py` secret-bearing checks (plus GitHub core ids as configured/missing).

## Companion UX

Settings tab:

1. **Connection** — existing base URL, token, session scopes (unchanged).
2. **Runtime** — form bound to editable catalog items; show `source` badge; if `restart_required` and value changed from env/default via overlay, show “Takes effect after API restart”.
3. **Host (read-only)** — LAN / worker NIC / gateway egress display.
4. **Secrets** — list from secrets-status; green/muted configured vs missing; no inputs.

Use existing touch styles (44px / 16px). `runAction` for PATCH/reset feedback.

## Resolver usage

Call sites that today read `os.environ.get("FS_CORP_…")` for allowlisted keys should use a single helper, e.g. `company.settings_runtime.effective(company, key)`, so overlay wins. Slice A minimum: wire helper for every allowlisted key that is not restart-gated; rate-limit keys keep env-at-startup behavior until restart (still store overlay).

## Safety

- Secret names never appear as editable catalog keys.
- Fail closed: unknown PATCH key, wrong type, companion-user / read_only writer → 403/422.
- Audit events carry keys and new values for non-secrets only.
- Retrieved settings cannot escalate scopes.

## Testing

- Unit: effective resolution order; validation; reset; unknown key rejected.
- API: GET shape; PATCH as owner; PATCH as companion-admin; deny companion-user; secrets-status never includes values.
- Companion source assertions: Runtime section, secrets-status client, no secret value fields.
- Migration applies on file-backed Company.

## Out of scope follow-ons

- Desk Settings mirror.
- Hot-reload rate limiter without restart.
- Expanding catalog to all remaining `FS_CORP_*`.
- Settings sections for policy budget drafts, model enable toggles, feed CRUD (P2+).

## Spec self-review

- No TBD placeholders in API or key table.
- Overlay-wins consistent with owner choice; rate-limit honesty via `restart_required`.
- Slice A does not claim desk UI or secret editing.
- Auth matches existing CEO/admin companion pattern (ADR-034).
