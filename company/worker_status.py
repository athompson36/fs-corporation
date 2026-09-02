"""Container worker runtime readiness (Docker image, scratch directory)."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path


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
    return out
