# Settings Platform P1 Slice A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship companion Settings overlay for allowlisted non-secret runtime knobs plus secrets configured/missing status, without writing host secrets or desk UI.

**Architecture:** `company/settings_catalog.py` defines keys/types/defaults; SQLite `company_settings` stores overlay rows; `company/settings_runtime.py` resolves overlay → env → default; `Company` exposes list/patch/reset/secrets-status; FastAPI routes under `/api/v1/settings*`; companion Settings tab gains Runtime / Host / Secrets sections. Rate-limit keys are stored with `restart_required: true` (honest; in-process limiter built at startup).

**Tech Stack:** Python 3.12+, FastAPI, SQLite/`Company`, Alembic, unittest, companion React/TypeScript.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-07-settings-platform-design.md`.
- Overlay wins when set; never return secret values.
- Do not reuse the existing `settings` table (ceo/paused only) — use new `company_settings`.
- PATCH/reset: `_ceo_or_admin_companion` + scope `company.pause`.
- GET settings + secrets-status: scope `company.read`.
- Fail closed on unknown keys / wrong types.
- Desk Settings UI is out of scope.

## File map

| File | Responsibility |
|---|---|
| Create `company/settings_catalog.py` | Allowlisted key definitions + validate |
| Create `company/settings_runtime.py` | effective(), secrets_status() |
| Modify `company/schema.py` | `company_settings` DDL |
| Create `alembic/versions/0024_company_settings.py` | Migration |
| Modify `company/core.py` | list/patch/reset wrappers + wire effective readers where listed |
| Modify `company/service.py` | GET/PATCH/reset/secrets-status routes |
| Modify `company/idempotency_prune.py` | Use effective retention days when company available, or keep env+default with Company method already using retention_days_from_env — update to accept override from effective |
| Modify `companion/src/api/client.ts` | client methods + types |
| Modify `companion/src/App.tsx` | Settings Runtime / Host / Secrets UI |
| Create `tests/test_settings_platform.py` | Core + API tests |
| Modify `tests/test_companion_api.py` | Source assertions |
| Modify `docs/16-api-contract.md`, `docs/18-handoff.md`, `docs/24-mobile-companion.md`, `docs/decisions.md` (ADR-036) | Docs |

---

### Task 1: Catalog + runtime resolver + table

**Files:**
- Create: `company/settings_catalog.py`
- Create: `company/settings_runtime.py`
- Modify: `company/schema.py` (append DDL near other CREATE TABLE)
- Create: `alembic/versions/0024_company_settings.py`
- Test: `tests/test_settings_platform.py`

**Interfaces:**
- Produces:
  - `CATALOG: dict[str, SettingDef]` with fields `key, type, default, editable, restart_required, description, min, max, enum_values`
  - `EDITABLE_KEYS`, `READONLY_KEYS`
  - `validate_value(key, raw) -> typed`
  - `effective(company, key) -> {value, source, default, …meta}`
  - `list_settings(company) -> list[dict]`
  - `secrets_status() -> list[{name, configured}]`
  - Table `company_settings(key, value_json, updated_at, updated_by)`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_settings_platform.py
import os
import unittest
from unittest.mock import patch
from company.core import Company
from company.settings_catalog import EDITABLE_KEYS, validate_value
from company.settings_runtime import effective, list_settings, secrets_status
from tests.test_core import install, policy

class CatalogTests(unittest.TestCase):
    def test_validate_and_unknown(self):
        self.assertEqual(validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", 14), 14)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", 0)
        with self.assertRaises(ValueError):
            validate_value("NOT_A_KEY", 1)

    def test_effective_overlay_wins(self):
        c = Company(); install(c, policy(c)); self.addCleanup(c.close)
        with patch.dict(os.environ, {"FS_CORP_SSE_IDLE_SEC": "9"}, clear=False):
            env_hit = effective(c, "FS_CORP_SSE_IDLE_SEC")
            self.assertEqual(env_hit["source"], "env")
            self.assertEqual(env_hit["value"], 9.0)
            with c.tx():
                c.db.execute(
                    "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                    ("FS_CORP_SSE_IDLE_SEC", "2.5", "2026-09-07T00:00:00+00:00", "human-ceo"),
                )
            over = effective(c, "FS_CORP_SSE_IDLE_SEC")
            self.assertEqual(over["source"], "overlay")
            self.assertEqual(over["value"], 2.5)
        items = list_settings(c)
        keys = {i["key"] for i in items}
        self.assertIn("FS_CORP_SSE_IDLE_SEC", keys)
        self.assertIn("FS_CORP_LAN_IP", keys)
        with patch.dict(os.environ, {"MODEL_PROVIDER_API_KEY": "sekrit"}, clear=False):
            rows = secrets_status()
        names = {r["name"] for r in rows}
        self.assertIn("MODEL_PROVIDER_API_KEY", names)
        hit = next(r for r in rows if r["name"] == "MODEL_PROVIDER_API_KEY")
        self.assertTrue(hit["configured"])
        self.assertEqual(set(hit.keys()), {"name", "configured"})
```

Fix the test to use a single `with c.tx()` insert (remove the duplicate execute). Assert `list_settings` includes editable + readonly keys.

- [ ] **Step 2: Run — expect FAIL** (modules / table missing)

Run: `.venv/bin/python -m unittest tests.test_settings_platform -v`

- [ ] **Step 3: Implement catalog + runtime + schema + alembic**

`settings_catalog.py` — define all keys from the spec table (editable + readonly).

`settings_runtime.py`:

```python
def effective(company, key: str) -> dict:
    meta = CATALOG[key]
    row = company.db.execute(
        "SELECT value_json FROM company_settings WHERE key=?", (key,)
    ).fetchone()
    if row:
        return {**meta_public(meta), "value": json.loads(row["value_json"]), "source": "overlay"}
    env_name = meta.get("env_name") or key
    raw = os.environ.get(env_name)
    if raw is not None and str(raw).strip() != "":
        return {**meta_public(meta), "value": validate_value(key, _parse_env(meta, raw)), "source": "env"}
    return {**meta_public(meta), "value": meta["default"], "source": "default"}
```

`secrets_status`: check env non-empty; for `GITHUB_PRIVATE_KEY_FILE` also `Path(raw).is_file()`.

Alembic `0024_company_settings.py`: `down_revision = "0023_ceo_scorecard"`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add company/settings_catalog.py company/settings_runtime.py company/schema.py \
  alembic/versions/0024_company_settings.py tests/test_settings_platform.py
git commit -m "Add settings catalog, overlay table, and effective resolver."
```

---

### Task 2: Company methods + API routes

**Files:**
- Modify: `company/core.py`
- Modify: `company/service.py`
- Modify: `tests/test_settings_platform.py`
- Optionally wire: `company/idempotency_prune.retention_days_from_env` callers via `Company.prune_idempotency_keys` to use `effective(self, "FS_CORP_IDEMPOTENCY_RETENTION_DAYS")["value"]` when `older_than_days is None`

**Interfaces:**
- Produces:
  - `Company.list_company_settings() -> {"items": [...]}`
  - `Company.patch_company_settings(actor, updates: dict) -> {"items": [...]}`
  - `Company.reset_company_settings(actor, keys=None, all_overlay=False) -> {"items": [...]}`
  - `Company.secrets_status() -> {"secrets": [...]}`
  - Routes: `GET/PATCH /api/v1/settings`, `POST /api/v1/settings/reset`, `GET /api/v1/settings/secrets-status`

- [ ] **Step 1: Failing API tests**

```python
from tests.test_api import owner_client

class SettingsApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.h = {"Authorization": "Bearer owner-token"}

    def test_get_patch_reset(self):
        g = self.client.get("/api/v1/settings", headers=self.h)
        self.assertEqual(g.status_code, 200, g.text)
        keys = {i["key"] for i in g.json()["items"]}
        self.assertIn("FS_CORP_SSE_IDLE_SEC", keys)
        self.assertIn("FS_CORP_LAN_IP", keys)
        p = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"FS_CORP_SSE_IDLE_SEC": 2}}},
            headers={**self.h, "Idempotency-Key": "set-1"},
        )
        self.assertEqual(p.status_code, 200, p.text)
        item = p.json()["result"]["items"][0]
        self.assertEqual(item["value"], 2.0)
        self.assertEqual(item["source"], "overlay")
        r = self.client.post(
            "/api/v1/settings/reset",
            json={"payload": {"keys": ["FS_CORP_SSE_IDLE_SEC"]}},
            headers={**self.h, "Idempotency-Key": "set-reset"},
        )
        self.assertEqual(r.status_code, 200, r.text)

    def test_unknown_key_422(self):
        p = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"NOT_A_KEY": 1}}},
            headers={**self.h, "Idempotency-Key": "bad"},
        )
        self.assertEqual(p.status_code, 422)

    def test_secrets_status(self):
        s = self.client.get("/api/v1/settings/secrets-status", headers=self.h)
        self.assertEqual(s.status_code, 200)
        for row in s.json()["secrets"]:
            self.assertEqual(set(row.keys()), {"name", "configured"})
```

Also add paired-admin allow + companion-user deny using existing pairing helpers from `tests/test_companion_api.py` / register_identity patterns.

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement Company + routes**

```python
# core.py
def list_company_settings(self):
    from company.settings_runtime import list_settings
    return {"items": list_settings(self)}

def patch_company_settings(self, actor, updates):
    self._ceo_or_admin_companion(actor)
    from company.settings_catalog import EDITABLE_KEYS, validate_value
    from company.core import canonical  # already have canonical
    if not isinstance(updates, dict) or not updates:
        raise ValueError("updates mapping required")
    changed = []
    with self.tx():
        for key, raw in updates.items():
            if key not in EDITABLE_KEYS:
                raise ValueError(f"Unknown or read-only setting: {key}")
            value = validate_value(key, raw)
            self.db.execute(
                "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                (key, canonical(value), now().isoformat(), actor),
            )
            changed.append(key)
        self._event("settings.updated", {"keys": changed}, actor_id=actor)
    from company.settings_runtime import effective
    return {"items": [effective(self, k) for k in changed]}
```

Similar for reset. Routes follow `ops/idempotency/prune` pattern with `envelope` + unknown field checks: PATCH allows only `updates`; reset allows `keys` | `all_overlay`.

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit**

```bash
git add company/core.py company/service.py tests/test_settings_platform.py
git commit -m "Expose settings GET/PATCH/reset and secrets-status APIs."
```

---

### Task 3: Wire effective() into hot-apply call sites

**Files:**
- Modify: `company/core.py` (`prune_idempotency_keys` default days)
- Modify: readers of `FS_CORP_SSE_IDLE_SEC`, `FS_CORP_PUBLIC_URL`, `FS_CORP_DEFAULT_WORKER_RUNTIME`, `FS_CORP_MODEL_CENTS_PER_1K_TOKENS`, `CHATDEV_ALLOW_CONTROL_PLANE` (grep and switch to `effective` or thin Company helpers)
- Test: extend `tests/test_settings_platform.py` with one behavioral test (e.g. overlay retention days used by prune)

**Interfaces:**
- Consumes: `effective(company, key)["value"]`
- Produces: overlay-visible behavior for non-`restart_required` keys

- [ ] **Step 1: Failing test** — set overlay retention to 1 day, insert 2-day-old idempotency key, prune with `older_than_days=None`, assert deleted.

- [ ] **Step 2: Implement wiring** — at minimum:
  - `prune_idempotency_keys` uses effective retention
  - SSE idle in `events_stream` uses effective (needs `company` in closure — already has it)
  - `FS_CORP_PUBLIC_URL` pairing URL builder
  - model cents in `model_provider.price_tokens` — may need optional company or keep env for provider module and document; prefer passing effective value from `invoke_model` path if priced there
  - ChatDev control plane gate
  - default worker runtime lookup

If a call site has no `company` handle, add a function `effective_env(key)` that only reads env+default (no overlay) **or** thread company in — prefer threading company. Rate-limit middleware stays env-at-startup (restart_required).

- [ ] **Step 3: PASS + commit**

```bash
git commit -m "Honor settings overlay for hot-apply runtime knobs."
```

---

### Task 4: Companion client + Settings UI

**Files:**
- Modify: `companion/src/api/client.ts`
- Modify: `companion/src/App.tsx`
- Modify: `tests/test_companion_api.py`

**Interfaces:**
- Produces: `companySettings()`, `patchCompanySettings(updates)`, `resetCompanySettings(...)`, `secretsStatus()`
- UI: Runtime form, Host read-only, Secrets list

- [ ] **Step 1: Source assertion test**

```python
def test_companion_wires_company_settings(self):
    root = Path(__file__).resolve().parents[1] / "companion" / "src"
    client = (root / "api" / "client.ts").read_text()
    app = (root / "App.tsx").read_text()
    self.assertIn("/api/v1/settings", client)
    self.assertIn("/api/v1/settings/secrets-status", client)
    self.assertIn("patchCompanySettings", client)
    self.assertIn("Runtime", app)
    self.assertIn("secrets-status", app.lower() or "Secrets")
    self.assertIn("Takes effect after API restart", app)
```

- [ ] **Step 2: FAIL then implement client + UI**

On Settings tab load (when token present): fetch settings + secrets-status.  
Runtime: for each `editable` item, input by type; Save calls PATCH with dirty keys; Reset overlay button for selected/all.  
Show source badge; if `restart_required`, show restart note.  
Host: readonly keys.  
Secrets: name + configured/missing.

- [ ] **Step 3: `cd companion && npm run build` + unittest PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "Add companion Settings runtime overlay and secrets status."
```

---

### Task 5: Docs + ADR-036

**Files:**
- Modify: `docs/16-api-contract.md`, `docs/18-handoff.md`, `docs/24-mobile-companion.md`, `docs/decisions.md`
- Modify: `docs/superpowers/specs/2026-09-07-settings-platform-design.md` status → implemented when done

- [ ] Document routes + ADR-036 (overlay wins; secrets status only; restart_required honesty).
- [ ] Handoff next → P2 or expand Settings sections.
- [ ] Full suite: `.venv/bin/python -m unittest discover -s tests` and companion build.
- [ ] Commit docs.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| `company_settings` table + migration | 1 |
| Catalog + validate + effective order | 1 |
| secrets-status no values | 1, 2 |
| GET/PATCH/reset APIs + auth | 2 |
| Wire hot-apply keys | 3 |
| Rate limits restart_required only | 3 (no fake hot reload) |
| Companion Runtime/Host/Secrets | 4 |
| Docs / ADR | 5 |
| Desk UI | out of scope |

## Plan self-review

- No TBD steps; concrete keys and routes from spec.
- Existing `settings` table left alone.
- Types consistent: `effective` returns dict with `value`/`source`.
- Slice A only — desk deferred.
