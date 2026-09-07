# ChatDev Adapter Slice 2 Implementation Plan

**Status: implemented (v0.3.39).** The step checkboxes below are the original working list
and are left unticked as a historical record; they are not open work.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase A — subprocess worker can run live ChatDev when opted in; Phase B — control-plane denies live SDK unless explicit allow.

**Architecture:** Extend `run_isolated_work` adapter selection; add `allow_control_plane` to `run_work_order`; worker passes `True`; default API path denied.

**Tech Stack:** Existing `company/worker.py`, `company/chatdev_runtime.py`, `unittest` + `unittest.mock`.

## Global Constraints

- Pin: `4fb2db0ea90375ce1059f44fe03ffbd191a7a169`
- No ChatDev in `pyproject.toml`
- Do not commit unless user asks
- Workers never open Company DB / receive owner token
- Mock path remains default; `chatdev: true` must not silently fall back to mock on failure
- Version bump to `0.3.39` at end of Phase B

---

### Task 1: Phase A — failing worker ChatDev tests

**Files:**
- Create: `tests/test_worker_chatdev.py`

- [ ] **Step 1: Write failing tests**

```python
"""Worker ChatDev opt-in (slice 2 Phase A)."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from multiprocessing import Pipe

from company.adapters import WorkOrder
from company.core import Company
from company.worker import run_isolated_work, worker_entrypoint
from tests.test_core import install, policy


class WorkerChatDevTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Worker chatdev")
        self.addCleanup(self.c.close)
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        os.environ.pop("CHATDEV_HOME", None)
        os.environ.pop("CHATDEV_ALLOW_CONTROL_PLANE", None)

    def _envelope(self, task_id, *, chatdev=False, digest="mock-workflow"):
        self.c.db.execute(
            "INSERT INTO queue VALUES(?,?,?,?,?,?,?,?,?)",
            (task_id, "human-ceo", "app", "produce_artifact", 0, "queued", None, None,
             json.dumps({"actor": "human-ceo", "project": "app", "action": "produce_artifact",
                         "cost": 0, "chatdev": chatdev})))
        return {
            "worker_id": "w1", "task_id": task_id, "approval": None,
            "workflow_digest": digest,
            "payload": {"actor": "human-ceo", "project": "app", "action": "produce_artifact",
                        "cost": 0, "chatdev": chatdev, "task_prompt": "hi"},
        }

    def test_default_uses_mock(self):
        env = self._envelope("t-mock")
        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            if op == "store_artifact":
                return {"hash": "a" * 64}
            if op == "execute_mock":
                return {"status": "done"}
            raise AssertionError(op)
        out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "done")
        self.assertEqual(out["adapter"]["final_message"], "mock workflow complete")

    def test_chatdev_true_uses_live_when_ready(self):
        env = self._envelope("t-live", chatdev=True)
        live = {"final_message": "live-chatdev-output", "meta_info": {"session_name": "s", "usage": {"input_tokens": 0, "output_tokens": 0, "cost_cents": 0}, "cancelled": False, "failed": False}, "artifact_hash": None, "accepted": False}
        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            if op == "store_artifact":
                self.assertIn(b"live-chatdev-output", kw.get("content") or kw.get("content_text", "").encode())
                return {"hash": "b" * 64}
            if op == "execute_mock":
                return {"status": "done"}
            raise AssertionError(op)
        with patch("company.worker.chatdev_home_ready", return_value=True):
            with patch("company.adapters.ChatDevAdapter.run", return_value=live):
                out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "done")
        self.assertEqual(out["adapter"]["final_message"], "live-chatdev-output")

    def test_chatdev_true_not_ready_errors(self):
        env = self._envelope("t-fail", chatdev=True)
        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            raise AssertionError(f"should not reach {op}")
        with patch("company.worker.chatdev_home_ready", return_value=False):
            out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "error")


if __name__ == "__main__":
    unittest.main()
```

Adjust queue INSERT to match actual schema columns — read `schema.py` / `test_workers.py` and match exactly.

- [ ] **Step 2: Run RED**

`.venv/bin/python -m unittest tests.test_worker_chatdev -v` — expect FAIL until Task 2.

---

### Task 2: Phase A — worker adapter selection

**Files:**
- Modify: `company/worker.py` (`run_isolated_work`)

- [ ] **Step 1: Implement selection**

```python
from company.adapters import ChatDevAdapter, MockChatDevAdapter, WorkOrder

def _want_live_chatdev(envelope: dict) -> bool:
    payload = envelope.get("payload") or {}
    if payload.get("chatdev") is True:
        return True
    try:
        from company.chatdev_runtime import workflow_digest
        return envelope.get("workflow_digest") == workflow_digest()
    except Exception:
        return False

# inside run_isolated_work after WorkOrder built:
tools = list((payload.get("tools") or ["none"]))
order = WorkOrder(..., {"tools": tools, "task_prompt": payload.get("task_prompt") or payload.get("prompt") or f"task {task_id}"})
if _want_live_chatdev(envelope):
    from company.chatdev_runtime import chatdev_home_ready, run_work_order
    if not chatdev_home_ready():
        return {"type": "error", "reason": "ChatDev requested but CHATDEV_HOME not ready"}
    try:
        adapter_result = run_work_order(order, allow_control_plane=True)
    except Exception as exc:
        return {"type": "error", "reason": str(exc)}
else:
    adapter_result = MockChatDevAdapter().run(order)
```

Note: `allow_control_plane` lands in Task 3; until then either implement the kwarg as no-op accepting True, or call `ChatDevAdapter().run` and add kwarg in Task 3. **Prefer adding kwarg stub in Task 2** (`allow_control_plane=False` default, ignored until Task 3 enforces).

- [ ] **Step 2: GREEN** `tests.test_worker_chatdev` + `tests.test_workers`

---

### Task 3: Phase B — control-plane deny

**Files:**
- Modify: `company/chatdev_runtime.py` (`run_work_order` signature + gate)
- Modify: `company/adapters.py` if needed
- Modify: `tests/test_chatdev_adapter.py` — set `CHATDEV_ALLOW_CONTROL_PLANE=1` or `allow_control_plane=True` in fake-SDK tests; add deny test

- [ ] **Step 1: Gate**

```python
def run_work_order(order, *, allow_control_plane: bool | None = None) -> dict:
    allowed = bool(allow_control_plane) or (os.environ.get("CHATDEV_ALLOW_CONTROL_PLANE") or "").strip() == "1"
    if not allowed:
        raise NotImplementedError(
            "Live ChatDev is denied in the control plane; dispatch via isolated worker "
            "or set CHATDEV_ALLOW_CONTROL_PLANE=1 for local desk experiments; see docs/07"
        )
    # ... existing body
```

- [ ] **Step 2: status_summary** add `control_plane_allowed`, `worker_live_ready` (= configured/pin_verified)

- [ ] **Step 3: Tests GREEN** including new deny-without-allow test

---

### Task 4: Docs + version 0.3.39

**Files:** docs/07, 16, 18-handoff, 14-roadmap, README, design status → implemented; `__init__.py` + `pyproject.toml` → 0.3.39

- [ ] Verify: `.venv/bin/python -m unittest tests.test_worker_chatdev tests.test_chatdev_adapter tests.test_m2 tests.test_workers -v`

---

## Spec coverage

| Spec | Task |
|---|---|
| Worker live when chatdev + ready | 1–2 |
| Fail when chatdev + not ready | 1–2 |
| Default mock | 1–2 |
| Control-plane deny | 3 |
| Escape hatch env | 3 |
| Status fields | 3–4 |
| Docs / version | 4 |
