"""Opt-in ChatDev SDK bridge. No ChatDev package dependency."""
from __future__ import annotations
import importlib.util
import json
import os
import shutil
import subprocess
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


def pin_check_skipped() -> bool:
    return os.environ.get("CHATDEV_SKIP_PIN_CHECK", "").strip() == "1"


def _commits_match(head: str, pinned: str) -> bool:
    head, pinned = head.lower(), pinned.lower()
    if not head or not pinned:
        return False
    if head == pinned:
        return True
    n = min(len(head), len(pinned))
    return n >= 7 and head[:n] == pinned[:n]


def checkout_head(home: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(home), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def pin_verified(home: Path | None = None) -> bool:
    if pin_check_skipped():
        return False
    target = home or chatdev_home()
    if not target:
        return False
    head = checkout_head(target)
    return head is not None and _commits_match(head, PINNED_COMMIT)


def _pin_ready(home: Path) -> bool:
    if pin_check_skipped():
        return True
    head = checkout_head(home)
    return head is not None and _commits_match(head, PINNED_COMMIT)


def chatdev_home_ready() -> bool:
    home = chatdev_home()
    if not home or not (home / "runtime" / "sdk.py").is_file():
        return False
    return _pin_ready(home)


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


def _control_plane_allowed(*, allow_control_plane: bool | None = None, company=None) -> bool:
    if allow_control_plane:
        return True
    if company is not None:
        return bool(company.effective_setting("CHATDEV_ALLOW_CONTROL_PLANE"))
    return (os.environ.get("CHATDEV_ALLOW_CONTROL_PLANE") or "").strip() == "1"


def run_work_order(order, *, allow_control_plane: bool | None = None, company=None) -> dict:
    if not _control_plane_allowed(
        allow_control_plane=allow_control_plane, company=company
    ):
        raise NotImplementedError(
            "Live ChatDev is denied in the control plane; dispatch via isolated worker "
            "or set CHATDEV_ALLOW_CONTROL_PLANE=1 for local desk experiments; see docs/07"
        )
    if not order.task_id or not order.workflow_digest:
        raise ValueError("WorkOrder requires task_id and workflow_digest")
    if type(order.max_cost_cents) is not int or order.max_cost_cents < 0:
        raise ValueError("max_cost_cents must be a non-negative int")
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


LABEL_CHATDEV_ENABLE = "org.fs_corporation.chatdev_enable"
LABEL_CHATDEV_PIN = "org.fs_corporation.chatdev_pin"
DEFAULT_WORKER_IMAGE = "fs-corporation-worker:local"


def worker_image() -> str:
    return (os.environ.get("FS_CORP_WORKER_IMAGE") or DEFAULT_WORKER_IMAGE).strip()


def worker_image_chatdev_summary() -> dict | None:
    """Probe worker image ChatDev labels via docker image inspect; fail-closed."""
    image = worker_image()
    docker = shutil.which("docker")
    if not docker:
        return None
    try:
        proc = subprocess.run(
            [docker, "image", "inspect", image, "--format", "{{json .Config.Labels}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        labels = json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(labels, dict):
        return None
    enable_raw = labels.get(LABEL_CHATDEV_ENABLE)
    pin_raw = labels.get(LABEL_CHATDEV_PIN)
    out: dict = {"image": image}
    if enable_raw is not None:
        out["enabled"] = str(enable_raw).strip() == "1"
    else:
        out["enabled"] = False
    if pin_raw:
        out["pin"] = str(pin_raw).strip()
    return out


def status_summary(*, company=None) -> dict:
    home = chatdev_home()
    ready = chatdev_home_ready()
    skipped = pin_check_skipped()
    out = {
        "pin": PINNED_COMMIT,
        "home_set": home is not None,
        "configured": ready,
        "pin_verified": pin_verified(home),
        "control_plane_allowed": _control_plane_allowed(company=company),
        "worker_live_ready": ready,
        "workflow": str(workflow_path()),
        "worker_image_chatdev": worker_image_chatdev_summary(),
    }
    if skipped:
        out["pin_check_skipped"] = True
    return out
