# Design: ChatDev adapter slice 2 (worker path + control-plane deny)

Date: 2026-09-07. Status: **implemented** (v0.3.39).

## Goal

Move live ChatDev execution off the default control-plane path and into the **isolated subprocess worker**, then harden so the API process cannot run the upstream SDK unless an explicit escape hatch is set.

Builds on [2026-09-07-chatdev-adapter-slice1-design.md](2026-09-07-chatdev-adapter-slice1-design.md).

## Pin (unchanged)

`4fb2db0ea90375ce1059f44fe03ffbd191a7a169` via `CHATDEV_HOME` + git HEAD check (slice 1).

## Phase A — Worker opt-in

### Behavior

In `company/worker.py` `run_isolated_work`:

1. Build `WorkOrder` as today (tools default `["none"]`).
2. Choose adapter:
   - Use **live** path when **all** of:
     - `chatdev_runtime.chatdev_home_ready()` is true (pin verified), and
     - envelope/payload requests ChatDev: `payload.get("chatdev") is True` **or** `envelope["workflow_digest"]` equals `chatdev_runtime.workflow_digest()` (fixture/default workflow), and
     - tools remain within `{none, mock_fs}`.
   - Otherwise keep `MockChatDevAdapter`.
3. Live path calls `ChatDevAdapter().run(order)` (same normalize / digest / cost rules as slice 1). Child still must not import `Company` or open the DB.
4. On live failure (`NotImplementedError`, digest mismatch, etc.), return `{"type": "error", "reason": ...}` — do not fall through to mock silently when `chatdev: true` was requested.

### Tests

- `tests/test_worker_chatdev.py` (or extend existing worker tests):
  - Default / no home → still `MockChatDevAdapter` behavior (patch mock or assert message).
  - With `chatdev: true` + patched `ChatDevAdapter.run` / `chatdev_home_ready` → live result used for artifact text; `accepted` remains false in adapter payload.
  - `chatdev: true` but home not ready → error result, not mock success.

### Non-goals (A)

- Container image ChatDev install
- New gateway ops
- Changing `execute_mock` semantics beyond using live adapter output as the scratch artifact text

## Phase B — Control-plane deny

### Behavior

In `chatdev_runtime.run_work_order` (or adapter entry):

- Refuse live SDK in the control-plane process unless `CHATDEV_ALLOW_CONTROL_PLANE=1`.
- Detection: prefer explicit env; optionally also refuse when `multiprocessing.current_process().name == "MainProcess"` **and** no allow flag — **do not** use MainProcess alone (worker child may still be MainProcess in some spawn modes). **Primary gate is the env flag.**
- Default (unset): `NotImplementedError` with message pointing at worker dispatch + docs/07.
- `CHATDEV_ALLOW_CONTROL_PLANE=1`: preserve slice 1 desk/dev behavior.
- Worker child: set `CHATDEV_ALLOW_CONTROL_PLANE=1` in the subprocess environment when dispatching isolated work **only for that child** (parent API process keeps it unset). Alternatively: pass a process-local allow via envelope flag checked only inside `run_isolated_work` before calling the adapter, without exporting to the API service env.

**Preferred B mechanism:**  
`run_work_order(..., *, allow_control_plane: bool | None = None)`  
- If `allow_control_plane is True` → allowed (worker passes True).  
- Else if env `CHATDEV_ALLOW_CONTROL_PLANE=1` → allowed.  
- Else → deny.  
Worker calls `ChatDevAdapter` via a thin helper `run_work_order(order, allow_control_plane=True)`. Desk/`ChatDevAdapter().run` uses default deny.

### Status

Extend `GET /api/v1/chatdev/status`:

```text
control_plane_allowed: bool  # env escape hatch
worker_live_ready: bool      # home ready (same as configured/pin_verified)
```

### Tests

- Default: `ChatDevAdapter().run` → `NotImplementedError` even if `CHATDEV_HOME` ready (patch home ready True).
- With `CHATDEV_ALLOW_CONTROL_PLANE=1` + fake SDK → succeeds (slice 1 path).
- Worker path with `allow_control_plane=True` + fake → succeeds without setting global env.

## Acceptance

1. Unconfigured / mock path: existing worker tests still pass.
2. Worker + `chatdev: true` + ready home (patched): artifact comes from live adapter; not mock string when live returns distinct text.
3. Worker + `chatdev: true` + not ready: error, not silent mock.
4. Control-plane default deny even when home ready.
5. Escape hatch `CHATDEV_ALLOW_CONTROL_PLANE=1` restores slice 1.
6. Docs/handoff/version bump; no ChatDev in `pyproject.toml`; workers still never get DB credentials.

## Non-goals (slice 2)

- TailscaleKit / dedicated worker host
- ChatDev inside Docker worker image
- Full YAML capability sanitizer
- Live model provider inside ChatDev CI

## Verify

```bash
.venv/bin/python -m unittest tests.test_chatdev_adapter tests.test_m2 tests.test_worker_chatdev -v
# plus existing worker isolation tests if present
```
