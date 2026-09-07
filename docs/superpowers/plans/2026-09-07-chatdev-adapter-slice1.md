# ChatDev Adapter Slice 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opt-in `ChatDevAdapter` that calls pinned ChatDev `run_workflow` when `CHATDEV_HOME` is set; fail-closed otherwise; contract tests with a fake SDK.

**Architecture:** Keep ChatDev out of `pyproject.toml`. Resolve home + workflow YAML, enforce tool allowlist and workflow digest, import `run_workflow` from `CHATDEV_HOME` via `importlib` (or inject callable for tests), normalize `WorkflowRunResult` to the existing mock adapter shape with `accepted: false`.

**Tech Stack:** Python 3.12+, stdlib `importlib`/`unittest.mock`, existing `company.adapters.WorkOrder`, `company.chatdev_pin.PINNED_COMMIT`, `company.core.digest`.

## Global Constraints

- Pin commit: `4fb2db0ea90375ce1059f44fe03ffbd191a7a169` (must match `company/chatdev_pin.py` / `config/upstream.lock.json`).
- Do not add ChatDev to `pyproject.toml` or control-plane venv.
- Final message never means acceptance (`accepted: false`).
- Tools allowlist: `{none, mock_fs}` only.
- Workers keep using `MockChatDevAdapter` (no change to `company/worker.py` in this slice).
- Do not commit unless the user asks.

---

## File map

| Path | Responsibility |
|---|---|
| `fixtures/chatdev/minimal_workflow.yaml` | Company-owned minimal workflow bytes for digest + default path |
| `company/chatdev_runtime.py` | Home/workflow resolution, SDK import, normalize result, status probe |
| `company/adapters.py` | `ChatDevAdapter.run` delegates to runtime when configured |
| `tests/test_chatdev_adapter.py` | Fail-closed, fake SDK, tools, digest mismatch |
| `company/service.py` | Optional `GET /api/v1/chatdev/status` |
| Docs | `07`, handoff, README matrix, `16-api-contract` if status added |

---

### Task 1: Fixture + failing adapter tests

**Files:**
- Create: `fixtures/chatdev/minimal_workflow.yaml`
- Create: `tests/test_chatdev_adapter.py`
- Modify: none yet

**Interfaces:**
- Produces: fixture file on disk; tests expecting `company.chatdev_runtime` helpers and live `ChatDevAdapter` behavior

- [ ] **Step 1: Write minimal workflow fixture**

Create `fixtures/chatdev/minimal_workflow.yaml` with a minimal pinned-shaped stub (enough for digest; not executed in CI):

```yaml
# Company fixture for ChatDev adapter digest tests. Not a claimed runnable production graph.
version: "2"
vars: {}
graph:
  nodes:
    - id: start
      type: start
    - id: end
      type: end
  edges:
    - from: start
      to: end
  start: start
  end: end
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_chatdev_adapter.py`:

```python
"""ChatDevAdapter opt-in runtime — fail-closed; fake SDK in CI."""
from __future__ import annotations
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from company.adapters import ChatDevAdapter, WorkOrder
from company.core import digest
from company.chatdev_pin import PINNED_COMMIT

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "chatdev" / "minimal_workflow.yaml"


def _digest() -> str:
    return digest({"workflow": FIXTURE.read_bytes().decode()})


class ChatDevAdapterTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: os.environ.pop("CHATDEV_HOME", None))
        self.addCleanup(lambda: os.environ.pop("CHATDEV_WORKFLOW", None))
        os.environ.pop("CHATDEV_HOME", None)
        os.environ.pop("CHATDEV_WORKFLOW", None)

    def test_fail_closed_without_home(self):
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "hi"})
        with self.assertRaises(NotImplementedError):
            ChatDevAdapter().run(order)

    def test_unapproved_tool(self):
        os.environ["CHATDEV_HOME"] = str(ROOT)  # any existing path; will fail later or on tools first
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["shell"], "task_prompt": "hi"})
        with self.assertRaises(PermissionError):
            ChatDevAdapter().run(order)

    def test_digest_mismatch(self):
        os.environ["CHATDEV_HOME"] = "/tmp/missing-chatdev-home-for-test"
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, "wrong-digest", 10, {"tools": ["none"], "task_prompt": "hi"})
        with self.assertRaises(ValueError):
            ChatDevAdapter().run(order)

    def test_fake_sdk_normalizes(self):
        os.environ["CHATDEV_HOME"] = str(ROOT / "company")  # path exists; import patched
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        fake_result = SimpleNamespace(
            final_message=SimpleNamespace(content="done"),
            meta_info=SimpleNamespace(
                session_name="company-p1-t1",
                token_usage={"input_tokens": 2, "output_tokens": 3},
                output_dir=Path("/tmp/out"),
            ),
        )
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "Ship it"})
        with patch("company.chatdev_runtime.load_run_workflow", return_value=lambda **kw: fake_result):
            with patch("company.chatdev_runtime.chatdev_home_ready", return_value=True):
                out = ChatDevAdapter().run(order)
        self.assertFalse(out["accepted"])
        self.assertEqual(out["final_message"], "done")
        self.assertEqual(out["meta_info"]["session_name"], "company-p1-t1")
        self.assertEqual(out["meta_info"]["usage"]["input_tokens"], 2)
        self.assertEqual(out["meta_info"]["usage"]["cost_cents"], 0)
        self.assertFalse(out["meta_info"]["failed"])

    def test_status_probe(self):
        from company.chatdev_runtime import status_summary
        s = status_summary()
        self.assertEqual(s["pin"], PINNED_COMMIT)
        self.assertFalse(s["configured"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_chatdev_adapter -v`

Expected: import errors or `NotImplementedError` / missing module `company.chatdev_runtime`.

---

### Task 2: `chatdev_runtime` + adapter wiring

**Files:**
- Create: `company/chatdev_runtime.py`
- Modify: `company/adapters.py` (`ChatDevAdapter` class)

**Interfaces:**
- Consumes: `WorkOrder`, `PINNED_COMMIT`, `digest`
- Produces:
  - `workflow_digest(path: Path) -> str`
  - `chatdev_home_ready() -> bool`
  - `load_run_workflow() -> Callable`
  - `run_work_order(order: WorkOrder) -> dict`
  - `status_summary() -> dict`

- [ ] **Step 1: Implement `company/chatdev_runtime.py`**

```python
"""Opt-in ChatDev SDK bridge. No ChatDev package dependency."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
from typing import Any, Callable

from company.chatdev_pin import PINNED_COMMIT
from company.core import digest

ALLOWED_TOOLS = frozenset({"none", "mock_fs"})
DEFAULT_WORKFLOW = Path(__file__).resolve().parents[1] / "fixtures" / "chatdev" / "minimal_workflow.yaml"


def workflow_path() -> Path:
    raw = (os.environ.get("CHATDEV_WORKFLOW") or "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_WORKFLOW


def workflow_digest(path: Path | None = None) -> str:
    p = path or workflow_path()
    return digest({"workflow": p.read_bytes().decode()})


def chatdev_home() -> Path | None:
    raw = (os.environ.get("CHATDEV_HOME") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def chatdev_home_ready() -> bool:
    home = chatdev_home()
    return bool(home and (home / "runtime" / "sdk.py").is_file())


def load_run_workflow() -> Callable[..., Any]:
    home = chatdev_home()
    if not home or not (home / "runtime" / "sdk.py").is_file():
        raise NotImplementedError(
            "Live ChatDev requires CHATDEV_HOME pointing at pin "
            f"{PINNED_COMMIT}; see docs/07-chatdev-integration.md"
        )
    sdk_path = home / "runtime" / "sdk.py"
    spec = importlib.util.spec_from_file_location("chatdev_runtime_sdk", sdk_path)
    if spec is None or spec.loader is None:
        raise NotImplementedError("Unable to load ChatDev runtime.sdk")
    module = importlib.util.module_from_spec(spec)
    # Ensure ChatDev package imports resolve relative to home
    import sys
    home_s = str(home)
    inserted = home_s not in sys.path
    if inserted:
        sys.path.insert(0, home_s)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted and sys.path and sys.path[0] == home_s:
            sys.path.pop(0)
    fn = getattr(module, "run_workflow", None)
    if not callable(fn):
        raise NotImplementedError("ChatDev runtime.sdk.run_workflow missing")
    return fn


def _message_text(final_message: Any) -> str | None:
    if final_message is None:
        return None
    if isinstance(final_message, str):
        return final_message
    content = getattr(final_message, "content", None)
    if content is not None:
        return str(content)
    return str(final_message)


def normalize_result(raw: Any, *, session_name: str, max_cost_cents: int) -> dict:
    meta = getattr(raw, "meta_info", None) or raw
    usage_src = getattr(meta, "token_usage", None) or {}
    if not isinstance(usage_src, dict):
        usage_src = {}
    in_tok = int(usage_src.get("input_tokens") or usage_src.get("prompt_tokens") or 0)
    out_tok = int(usage_src.get("output_tokens") or usage_src.get("completion_tokens") or 0)
    cost = int(usage_src.get("cost_cents") or 0)
    if cost > max_cost_cents:
        raise PermissionError("ChatDev reported cost exceeds work order max_cost_cents")
    out_dir = getattr(meta, "output_dir", None)
    return {
        "final_message": _message_text(getattr(raw, "final_message", None)),
        "meta_info": {
            "session_name": getattr(meta, "session_name", None) or session_name,
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok, "cost_cents": cost},
            "output_dir": str(out_dir) if out_dir is not None else None,
            "cancelled": False,
            "failed": False,
        },
        "artifact_hash": None,
        "accepted": False,
    }


def run_work_order(order) -> dict:
    if not order.task_id or not order.workflow_digest:
        raise ValueError("WorkOrder requires task_id and workflow_digest")
    tools = order.payload.get("tools") or []
    if any(t not in ALLOWED_TOOLS for t in tools):
        raise PermissionError("Unapproved tool")
    path = workflow_path()
    if not path.is_file():
        raise ValueError(f"Workflow YAML not found: {path}")
    expected = workflow_digest(path)
    if order.workflow_digest != expected:
        raise ValueError("Workflow digest mismatch")
    if not chatdev_home_ready():
        raise NotImplementedError(
            "Live ChatDev requires CHATDEV_HOME pointing at pin "
            f"{PINNED_COMMIT}; see docs/07-chatdev-integration.md"
        )
    prompt = (order.payload.get("task_prompt") or order.payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("task_prompt required for ChatDev work order")
    session = f"company-{order.project_id}-{order.task_id}"
    run_workflow = load_run_workflow()
    raw = run_workflow(str(path), task_prompt=prompt, session_name=session)
    return normalize_result(raw, session_name=session, max_cost_cents=order.max_cost_cents)


def status_summary() -> dict:
    home = chatdev_home()
    ready = chatdev_home_ready()
    return {
        "pin": PINNED_COMMIT,
        "home_set": home is not None,
        "configured": ready,
        "workflow": str(workflow_path()),
    }
```

- [ ] **Step 2: Wire `ChatDevAdapter`**

Replace `ChatDevAdapter` in `company/adapters.py`:

```python
class ChatDevAdapter:
    def run(self, order: WorkOrder) -> dict:
        from company import chatdev_runtime
        return chatdev_runtime.run_work_order(order)
```

- [ ] **Step 3: Run tests — expect PASS**

Run: `.venv/bin/python -m unittest tests.test_chatdev_adapter tests.test_m2 -v`

Expected: OK (including existing fail-closed `ChatDevAdapter` test without env).

Adjust `test_unapproved_tool` / `test_digest_mismatch` if tool check runs before home-ready (preferred: tools then digest then home).

---

### Task 3: Status route + docs + version

**Files:**
- Modify: `company/service.py` (add GET near model/workers status)
- Modify: `docs/07-chatdev-integration.md`, `docs/16-api-contract.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`, `README.md`
- Modify: `company/__init__.py` → `0.3.38`
- Modify: spec status line to implemented

- [ ] **Step 1: Add status route**

```python
@app.get("/api/v1/chatdev/status")
def chatdev_status(authorization: str | None = Header(default=None)):
    ident = principal(authorization)
    scoped(ident, "company.read")
    from company.chatdev_runtime import status_summary
    return status_summary()
```

- [ ] **Step 2: API test (optional thin) or assert via TestClient in `test_chatdev_adapter`**

Add:

```python
def test_status_api(self):
    from fastapi.testclient import TestClient
    from company.core import Company
    from company.service import create_app
    from tests.test_core import install, policy
    c = Company(); install(c, policy(c)); c.register_identity("human-ceo", "owner", "t")
    self.addCleanup(c.close)
    r = TestClient(create_app(c)).get("/api/v1/chatdev/status", headers={"Authorization": "Bearer t"})
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.json()["pin"], PINNED_COMMIT)
```

- [ ] **Step 3: Docs + handoff + bump version to 0.3.38**

- [ ] **Step 4: Full targeted verify**

Run: `.venv/bin/python -m unittest tests.test_chatdev_adapter tests.test_m2 -v && .venv/bin/python scripts/check_bundle.py`

- [ ] **Step 5: Deploy version to fs-dev only if API status is exposed (optional rsync + restart)**

Do not `git commit` unless the user asks.

---

## Spec coverage check

| Spec item | Task |
|---|---|
| Fail-closed without home | 1–2 |
| Normalize SDK result / accepted false | 2 |
| Tool allowlist | 2 |
| Digest match | 2 |
| Fixture + digest | 1–2 |
| Fake SDK tests | 1–2 |
| Status probe | 2–3 |
| No pyproject ChatDev | global |
| Docs | 3 |
| Worker still mock | global (no worker.py edit) |

## Placeholder scan

None intentional.
