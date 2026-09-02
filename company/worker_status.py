"""Container worker runtime readiness (Docker image, scratch directory, worker NIC, gateway egress)."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path

EGRESS_TABLE = int(os.environ.get("FS_CORP_GATEWAY_EGRESS_TABLE") or "101")
EGRESS_PRIORITY = int(os.environ.get("FS_CORP_GATEWAY_EGRESS_PRIORITY") or "1000")


def host_has_ipv4(address: str) -> bool:
    """True when *address* is assigned to a local interface (e.g. 192.168.4.101 on eno2)."""
    if not address:
        return False
    try:
        proc = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0:
        return False
    needle = f" {address}/"
    return any(needle in line for line in proc.stdout.splitlines())


def default_worker_runtime() -> str:
    """Configured default for dispatch-worker when the client omits runtime."""
    value = (os.environ.get("FS_CORP_DEFAULT_WORKER_RUNTIME") or "subprocess").strip().lower()
    if value not in {"subprocess", "container"}:
        return "subprocess"
    return value


def gateway_egress_mode() -> str:
    value = (os.environ.get("FS_CORP_GATEWAY_EGRESS") or "default").strip().lower()
    if value not in {"default", "worker_nic"}:
        return "default"
    return value


def _service_uid(user: str = "fs-corp") -> int | None:
    try:
        proc = subprocess.run(
            ["id", "-u", user],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def _ip_rule_has_uid_table(uid: int, table: int = EGRESS_TABLE) -> bool:
    try:
        proc = subprocess.run(
            ["ip", "-4", "rule", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0:
        return False
    pattern = re.compile(rf"uidrange\s+{uid}-{uid}\s+lookup\s+{table}\b")
    return any(pattern.search(line) for line in proc.stdout.splitlines())


def _table_default_src(table: int = EGRESS_TABLE) -> str | None:
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "show", "table", str(table)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if not line.startswith("default"):
            continue
        parts = line.split()
        if "src" in parts:
            return parts[parts.index("src") + 1]
        return ""
    return None


def gateway_egress_summary() -> dict:
    """Report configured gateway egress mode and whether host policy routing is active."""
    mode = gateway_egress_mode()
    worker_nic = (os.environ.get("FS_CORP_WORKER_NIC_IP") or "").strip()
    present = host_has_ipv4(worker_nic) if worker_nic else False
    uid = _service_uid(os.environ.get("FS_CORP_SERVICE_USER") or "fs-corp")
    src = _table_default_src()
    active = bool(uid is not None and _ip_rule_has_uid_table(uid) and src is not None)
    out: dict = {
        "mode": mode,
        "egress_active": active,
        "egress_table": EGRESS_TABLE,
    }
    if worker_nic:
        out["worker_nic_ip"] = worker_nic
        out["worker_nic_present"] = present
    if active and src:
        out["egress_source_ip"] = src
    if mode == "worker_nic" and not active:
        out["egress_ready"] = False
        reasons = []
        if not worker_nic:
            reasons.append("FS_CORP_WORKER_NIC_IP unset")
        elif not present:
            reasons.append("worker NIC IP not on host")
        elif uid is None:
            reasons.append("service user missing")
        else:
            reasons.append("policy routing not installed")
        out["egress_blockers"] = reasons
    elif mode == "worker_nic":
        out["egress_ready"] = True
    return out


def resolve_worker_runtime(requested: str | None = None) -> str:
    """Resolve the worker runtime. Container default fails closed when not ready."""
    explicit = (requested or "").strip().lower()
    if explicit:
        if explicit not in {"subprocess", "container"}:
            raise ValueError("runtime must be subprocess or container")
        return explicit
    chosen = default_worker_runtime()
    if chosen != "container":
        return "subprocess"
    summary = status_summary()
    if not summary.get("container_dispatch_ready"):
        raise NotImplementedError(
            "FS_CORP_DEFAULT_WORKER_RUNTIME=container but container dispatch is not ready "
            f"(docker={summary.get('docker_available')} image={summary.get('image_present')} "
            f"scratch={summary.get('scratch_writable')}). "
            "Pass runtime=subprocess explicitly or finish worker install."
        )
    return "container"


def status_summary() -> dict:
    docker = shutil.which("docker")
    scratch = (os.environ.get("FS_CORP_WORKER_SCRATCH") or "").strip()
    image = (os.environ.get("FS_CORP_WORKER_IMAGE") or "fs-corporation-worker:local").strip()
    worker_nic = (os.environ.get("FS_CORP_WORKER_NIC_IP") or "").strip()
    out: dict = {
        "docker_available": bool(docker),
        "scratch_configured": bool(scratch),
        "scratch_writable": False,
        "image": image,
        "image_present": False,
        "container_dispatch_ready": False,
        "default_runtime": default_worker_runtime(),
        "gateway_egress": gateway_egress_summary(),
    }
    if scratch:
        path = Path(scratch)
        out["scratch_writable"] = path.is_dir() and os.access(path, os.W_OK)
    if docker:
        try:
            proc = subprocess.run(
                [docker, "image", "inspect", image],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            out["image_present"] = proc.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            out["image_present"] = False
    out["container_dispatch_ready"] = (
        out["docker_available"]
        and out["scratch_configured"]
        and out["scratch_writable"]
        and out["image_present"]
    )
    if worker_nic:
        out["worker_nic_ip"] = worker_nic
        out["worker_nic_present"] = host_has_ipv4(worker_nic)
    return out
