# Companion Workers Tab + Remote Agent Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a primary companion **Workers** tab for CEO host CRUD (list/create with one-time token / enable / disable / delete) plus a short remote-agent runbook — using existing `/api/v1/worker-hosts*` only.

**Architecture:** No new backend routes. Add `ApiClient` worker-host methods (including generic `delete`), extract `WorkersPanel.tsx`, add primary tab **Workers**, update nav assertion 4→5, document agent env vars, bump **0.3.63**.

**Tech Stack:** Existing FastAPI worker-host APIs, companion React/TypeScript, unittest source assertions.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-workers-tab-runbook-design.md` (approved).
- Version **0.3.63**; no Alembic; no new worker-host routes; TailscaleKit stub unchanged.
- Host `state` and list data come from API only — never invent ready/stale.
- One-time `token` shown only from create response; never re-fetched.
- Delete requires `confirm`.
- Branch: `feature/workers-tab-runbook` from `main`.
- Do not commit `local repos/service-department/`.

## File map

| File | Responsibility |
|---|---|
| `companion/src/api/client.ts` | `delete` helper + worker-host methods |
| `companion/src/WorkersPanel.tsx` | Workers UI |
| `companion/src/App.tsx` | Primary tab + panel wiring |
| `tests/test_companion_api.py` | Nav count + Workers assertions |
| `docs/24-mobile-companion.md` | Workers primary screen |
| `docs/25-fs-dev-deployment.md` | Remote agent runbook |
| `docs/14-roadmap.md`, `docs/18-handoff.md` | Next → marketing |
| `company/__init__.py`, `companion/package.json` | 0.3.63 |
| Spec status | Mark implemented when shipping |

---

### Task 1: Client + WorkersPanel + primary tab

**Files:**
- Modify: `companion/src/api/client.ts`
- Create: `companion/src/WorkersPanel.tsx`
- Modify: `companion/src/App.tsx`
- Test: `tests/test_companion_api.py`

**Interfaces:**
- Produces:
  - `ApiClient.delete<T>(path, idempotency?)`
  - `workerHosts(): Promise<{ hosts: Record<string, unknown>[] }>`
  - `createWorkerHost(label, baseUrl): Promise<{ result: { id, label, base_url, token, ... } }>` (POST envelope returns `result` with one-time `token`)
  - `enableWorkerHost(id)`, `disableWorkerHost(id)`, `deleteWorkerHost(id)`
  - `export function WorkersPanel(props)` matching FinancePanel props shape (`api`, `hasToken`, `canPause`, `scopeNotice`, `runAction`, `status`)

- [ ] **Step 1: Update failing companion assertions**

In `tests/test_companion_api.py`:

1. Change `test_companion_nav_is_five_tabs_with_more_switcher` so primary tab count is **5** (today asserts `4`):

```python
self.assertEqual(len(re.findall(r'\["', primary)), 5)
self.assertIn('["workers", "Workers"]', primary)
```

2. Add (or extend) a finance-style source test:

```python
def test_companion_wires_worker_hosts(self):
    root = Path(__file__).resolve().parents[1] / "companion" / "src"
    client = (root / "api" / "client.ts").read_text()
    app = (root / "App.tsx").read_text()
    panel = (root / "WorkersPanel.tsx").read_text()
    self.assertIn("workerHosts", client)
    self.assertIn("createWorkerHost", client)
    self.assertIn("enableWorkerHost", client)
    self.assertIn("disableWorkerHost", client)
    self.assertIn("deleteWorkerHost", client)
    self.assertIn('["workers", "Workers"]', app)
    self.assertIn("tab === \"workers\"", app)
    self.assertIn("WorkersPanel", app)
    self.assertIn("shown once", panel)
    self.assertIn("confirm(", panel)
    self.assertIn("workerHosts", panel)
```

- [ ] **Step 2: Run assertions — expect fail**

```bash
.venv/bin/python -m unittest \
  tests.test_companion_api.CompanionApiTests.test_companion_nav_is_five_tabs_with_more_switcher \
  tests.test_companion_api.CompanionApiTests.test_companion_wires_worker_hosts -v
```

Expected: FAIL (count still 4 / missing `WorkersPanel.tsx`).

- [ ] **Step 3: Add `delete` + worker-host client methods**

In `companion/src/api/client.ts`, after `patch`:

```typescript
  async delete<T>(path: string, idempotency?: string): Promise<T> {
    const r = await fetch(this.url(path), {
      method: "DELETE",
      headers: headers(this.settings.token, idempotency),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    const text = await r.text();
    return (text ? JSON.parse(text) : {}) as T;
  }
```

Near other API helpers (e.g. after finance methods):

```typescript
  workerHosts() {
    return this.get<{ hosts: Record<string, unknown>[] }>("/api/v1/worker-hosts");
  }

  createWorkerHost(label: string, baseUrl: string) {
    return this.post<{
      result: {
        id: string;
        label: string;
        base_url: string;
        token: string;
        enabled?: boolean;
        state?: string;
      };
    }>(
      "/api/v1/worker-hosts",
      { label, base_url: baseUrl },
      `worker-host-create-${Date.now()}`,
    );
  }

  enableWorkerHost(hostId: string) {
    return this.post(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}/enable`,
      {},
      `worker-host-enable-${hostId}-${Date.now()}`,
    );
  }

  disableWorkerHost(hostId: string) {
    return this.post(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}/disable`,
      {},
      `worker-host-disable-${hostId}-${Date.now()}`,
    );
  }

  deleteWorkerHost(hostId: string) {
    return this.delete(
      `/api/v1/worker-hosts/${encodeURIComponent(hostId)}`,
      `worker-host-delete-${hostId}-${Date.now()}`,
    );
  }
```

- [ ] **Step 4: Implement `WorkersPanel.tsx`**

Create `companion/src/WorkersPanel.tsx`:

- Props identical shape to FinancePanel (`ApiClient`, `hasToken`, `canPause`, `scopeNotice`, `runAction`, `status`).
- State: `hosts`, `loadError`, create `label` / `baseUrl`, `issuedToken: { hostId, label, token } | null`.
- `loadAll`: if `!hasToken` return; else `api.workerHosts()`; on error clear hosts + set loadError (do not invent rows). Effect with cancel flag like FinancePanel.
- List: for each host show `label`, short `id`, `base_url`, **`state`** (String from API), `last_heartbeat_at`.
- Create form when `canPause`: submit → `createWorkerHost` → set `issuedToken` from `res.result` (token + id + label); clear label/baseUrl; reload list. Show panel with exact phrase **shown once** and a Copy button (`navigator.clipboard.writeText`). Dismiss button clears `issuedToken` only.
- Per row when `canPause`: if state is `disabled` show Enable else Disable; Delete calls `confirm("Delete this worker host? The host token will stop working.")` then `deleteWorkerHost`.
- Scope notices when `!canPause` for mutate actions.

Skeleton:

```tsx
import { FormEvent, useCallback, useEffect, useState, type ReactNode } from "react";
import type { ApiClient } from "./api/client";

type WorkersPanelProps = {
  api: ApiClient;
  hasToken: boolean;
  canPause: boolean;
  scopeNotice: (action: string, scope: string) => ReactNode;
  runAction: (key: string, okMessage: string, run: () => Promise<void>) => Promise<void>;
  status: (key: string) => ReactNode;
};

export function WorkersPanel(props: WorkersPanelProps) {
  // ... loadAll, create, enable/disable/delete as above
}
```

- [ ] **Step 5: Wire `App.tsx`**

1. Extend `Tab` union with `"workers"`.
2. Add to PRIMARY_TABS:

```typescript
const PRIMARY_TABS: [Tab, string][] = [
  ["dashboard", "Home"],
  ["projects", "Projects"],
  ["organization", "Org"],
  ["corporate", "Corporate"],
  ["workers", "Workers"],
];
```

3. `import { WorkersPanel } from "./WorkersPanel";`
4. Render (mirror FinancePanel wiring):

```tsx
{tab === "workers" && (
  <WorkersPanel
    api={api}
    hasToken={Boolean(settings.token)}
    canPause={canPause(scopes)}
    scopeNotice={scopeNotice}
    runAction={async (key, okMessage, run) => {
      await runAction(key, okMessage, run);
    }}
    status={status}
  />
)}
```

(Adapt `runAction` wrapper to match the existing `runAction` signature in App — same pattern as FinancePanel.)

- [ ] **Step 6: Build + tests**

```bash
cd companion && npm run build
cd .. && .venv/bin/python -m unittest \
  tests.test_companion_api.CompanionApiTests.test_companion_nav_is_five_tabs_with_more_switcher \
  tests.test_companion_api.CompanionApiTests.test_companion_wires_worker_hosts -v
```

Expected: build OK; both tests OK.

- [ ] **Step 7: Commit**

```bash
git add companion/src/api/client.ts companion/src/WorkersPanel.tsx companion/src/App.tsx tests/test_companion_api.py
git commit -m "$(cat <<'EOF'
Add companion Workers tab for remote host management.

EOF
)"
```

---

### Task 2: Docs, version 0.3.63, handoff

**Files:**
- Modify: `docs/24-mobile-companion.md`
- Modify: `docs/25-fs-dev-deployment.md`
- Modify: `docs/14-roadmap.md`
- Modify: `docs/18-handoff.md`
- Modify: `company/__init__.py` → `0.3.63`
- Modify: `companion/package.json` → `0.3.63`
- Modify: `docs/superpowers/specs/2026-09-08-workers-tab-runbook-design.md` status → **implemented**

- [ ] **Step 1: Companion doc**

In the screen table in `docs/24-mobile-companion.md`, add a **Workers** primary-row (not under More):

```markdown
| Workers | List remote worker hosts (API `state`); create host (one-time token shown once); enable/disable/delete when `company.pause` + CEO |
```

Add API bullets for worker-hosts list/create/enable/disable/delete if missing.

- [ ] **Step 2: Remote agent runbook**

In `docs/25-fs-dev-deployment.md`, after the same-host worker plane paragraph (near “dedicated second physical host”), add a section **Remote worker agent (second host)** covering:

- Register from companion **Workers**; copy one-time token immediately; list/GET never returns it; lost token → delete + recreate.
- Required env: `FS_CORP_CONTROL_URL`, `FS_CORP_WORKER_HOST_ID`, `FS_CORP_WORKER_HOST_TOKEN` (or `FS_CORP_WORKER_HOST_TOKEN_FILE`).
- Optional: `FS_CORP_REMOTE_WORKER_RUNTIME=container`, `FS_CORP_WORKER_IMAGE`.
- Example command: `python3 scripts/remote_worker_agent.py` with those env vars set.
- Note: agent does not open the company DB; TailscaleKit remains stubbed; phone join stays clipboard + system Tailscale app.

Use a single top-level ` ```bash ` example block (do not nest fences).

- [ ] **Step 3: Roadmap + handoff + version**

- Roadmap: mark Workers tab / second-host ops polish; next → marketing redesign.
- Handoff: version **0.3.63**; Workers tab shipped; next → deeper marketing redesign.
- `__version__ = "0.3.63"`; companion `"version": "0.3.63"`.
- Spec status line → implemented in v0.3.63.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests pass; build OK.

- [ ] **Step 5: Commit**

```bash
git add docs/24-mobile-companion.md docs/25-fs-dev-deployment.md docs/14-roadmap.md docs/18-handoff.md company/__init__.py companion/package.json docs/superpowers/specs/2026-09-08-workers-tab-runbook-design.md
git commit -m "$(cat <<'EOF'
Document Workers tab runbook and release 0.3.63.

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Primary Workers tab | 1 |
| WorkersPanel list/create/token/enable/disable/delete | 1 |
| Client methods + DELETE helper | 1 |
| Nav test 5 primary tabs | 1 |
| Companion + fs-dev runbook docs | 2 |
| 0.3.63 + handoff → marketing | 2 |
| No new routes / no Alembic / TailscaleKit unchanged | Global |

## Verification (merge gate)

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```
