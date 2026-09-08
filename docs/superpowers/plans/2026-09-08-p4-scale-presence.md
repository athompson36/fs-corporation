# P4 Scale and Presence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship software-completeable P4: remote worker-host registry + heartbeat (no remote dispatch), TailscaleKit stub, SVG furnished HQ, org m5 docs honesty.

**Architecture:** New `company/worker_hosts.py` + Alembic `0027_worker_hosts`; extend `status_summary` with `remote_hosts`; desk isometric furniture from persisted `room_type`; companion-native TailscaleKit stub; docs/ADR-040.

**Tech Stack:** Python 3.12+, SQLite/Alembic, unittest, desk inline SVG JS, TypeScript stub.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-p4-scale-presence-design.md` (approved).
- Dispatch remains same-host only. Never invent HQ occupancy or remote execution.
- Host tokens: hash with prefix `fs-corporation-worker-host:`; plaintext only on create.
- Branch: `feature/p4-scale-presence`. Do not commit `local repos/service-department/`.
- Bump `__version__` to `0.3.54` in docs task.

## File map

| Path | Role |
|---|---|
| `alembic/versions/0027_worker_hosts.py` | Migration |
| `company/schema.py` | Fresh-DB DDL |
| `company/migrate.py` | `HEAD_REVISION` |
| `company/worker_hosts.py` | Registry CRUD + heartbeat + status rows |
| `company/worker_status.py` | Attach `remote_hosts` |
| `company/core.py` | Thin Company wrappers |
| `company/service.py` | HTTP routes + desk furniture SVG |
| `companion-native/tailscale_kit.ts` | Stub |
| `companion-native/README.md` | TailscaleKit honesty |
| `tests/test_worker_hosts.py` | Registry/heartbeat |
| `tests/test_desk_furniture.py` | Source assertions for furniture |
| `tests/test_tailscale_kit_stub.py` | Stub + README |
| Docs | ADR-040, handoff, roadmap, org design, production plan |

---

### Task 1: Worker hosts schema + module

**Files:**
- Create: `alembic/versions/0027_worker_hosts.py`, `company/worker_hosts.py`, `tests/test_worker_hosts.py`
- Modify: `company/schema.py`, `company/migrate.py`, `tests/test_staffing_proposals.py` (and scorecard/divisions/career HEAD pins) → `0027_worker_hosts`

**Interfaces:**
- Produces: `create_worker_host(company, actor, *, label, base_url) -> dict` (includes `token` once), `list_worker_hosts`, `set_worker_host_enabled`, `delete_worker_host`, `record_worker_host_heartbeat(company, host_id, token, meta=None)`, `remote_host_status_rows(company) -> list[dict]`, `hash_worker_host_token(token) -> str`, TTL via env/`effective_setting` `FS_CORP_WORKER_HOST_HEARTBEAT_TTL_SEC` default 120.

- [ ] **Step 1: Failing tests** in `tests/test_worker_hosts.py`:
  - create returns id/label/base_url/token; second list never includes token
  - https-only base_url
  - heartbeat with correct token → ready within TTL; bad token raises PermissionError
  - disable → state disabled; no heartbeat past TTL → stale
  - CEO required for create

- [ ] **Step 2: Migration + SCHEMA** matching design SQL.

- [ ] **Step 3: Implement `company/worker_hosts.py`** and wire thin methods on `Company`.

- [ ] **Step 4: Update HEAD_REVISION + pinned tests**; run `tests/test_worker_hosts.py` + migrate tests.

- [ ] **Step 5: Commit** `feat(p4): worker host registry and heartbeat`

---

### Task 2: HTTP API + workers/status

**Files:**
- Modify: `company/service.py`, `company/worker_status.py`
- Extend: `tests/test_worker_hosts.py` (HTTP via TestClient if used elsewhere) or keep module-level + service smoke

**Routes:**
- `GET /api/v1/worker-hosts` — `company.read`
- `POST /api/v1/worker-hosts` — CEO + `company.pause`, body `{label, base_url}`
- `POST /api/v1/worker-hosts/{id}/enable` / `disable` — CEO + pause
- `DELETE /api/v1/worker-hosts/{id}` — CEO + pause
- `POST /api/v1/worker-hosts/{id}/heartbeat` — **no principal**; `Authorization: Bearer <host-token>` or `X-Worker-Host-Token`; optional JSON meta
- `GET /api/v1/workers/status` — include `remote_hosts` from `remote_host_status_rows`

- [ ] Implement routes + status attachment; tests for status never leaking token; commit `feat(p4): worker-hosts HTTP and status`

---

### Task 3: TailscaleKit stub

**Files:**
- Create: `companion-native/tailscale_kit.ts`
- Modify: `companion-native/README.md`
- Create: `tests/test_tailscale_kit_stub.py` (read source files)

```ts
export function isTailscaleKitAvailable(): boolean {
  return false;
}
export async function joinWithAuthKey(_key: string): Promise<{ ok: false; reason: "not_implemented" }> {
  return { ok: false, reason: "not_implemented" };
}
```

- [ ] README section on future TailscaleKit / userspace node
- [ ] Commit `docs(p4): TailscaleKit stub and honesty`

---

### Task 4: Furnished HQ SVG

**Files:**
- Modify: `company/service.py` (iso render loop ~1332–1356)
- Create: `tests/test_desk_furniture.py` (assert desk HTML/JS contains furniture helper + room_type map)

Behavior: for `built` rooms only, append `<g class="iso-furniture" data-furniture="…">` with small rects/polygons from catalog:
- `engineering` / `hardware` → workstation
- `executive` / `ceo` → conference
- `ops` / `infrastructure` → rack
- default → desk

Deterministic from `room.id` + `room_type` only. No worker invention.

- [ ] Implement + tests; commit `feat(p4): SVG furniture from room_type`

---

### Task 5: Org m5 docs + ADR + handoff

**Files:**
- `docs/superpowers/specs/2026-09-07-org-hierarchy-handoff-design.md` — m5 implemented
- `docs/decisions.md` — ADR-040
- `docs/14-roadmap.md`, production plan P4 checkbox
- `docs/11-user-experience.md` — furnished SVG note
- `docs/18-handoff.md` — next → P5
- `company/__init__.py` → `0.3.54`
- README / VERIFICATION version lines as needed
- Spec status → approved/implemented

- [ ] Commit `docs(p4): ADR-040 and capability sync; v0.3.54`

---

### Task 6: Full verification

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all pass (prior ~408 + new).

---

## Spec coverage (self-review)

| Spec slice | Task |
|---|---|
| A registry + heartbeat + status | 1–2 |
| B TailscaleKit stub | 3 |
| C Furnished SVG | 4 |
| D Org m5 honesty | 5 |
| No remote dispatch | 1–2 (no enqueue changes) |
| ADR-040 | 5 |
