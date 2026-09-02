"""Container worker runtime readiness (Docker image, scratch directory, worker NIC)."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path


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
    }
    if scratch:
        path = Path(scratch)
        out["scratch_writable"] = path.is_dir() and os.access(path, os.W_OK)
    if docker:
        proc = subprocess.run(
            [docker, "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        out["image_present"] = proc.returncode == 0
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
