#!/usr/bin/env python3
"""Pull agent for registered worker hosts (heartbeat + claim + execute).

Environment:
  FS_CORP_CONTROL_URL     Base URL of the control plane (e.g. https://192.168.4.100)
  FS_CORP_WORKER_HOST_ID  Host id from CEO create
  FS_CORP_WORKER_HOST_TOKEN  Host token (or FS_CORP_WORKER_HOST_TOKEN_FILE)
  FS_CORP_REMOTE_WORKER_RUNTIME  Set to "container" to opt into Docker execution
  FS_CORP_WORKER_IMAGE    Docker image (default fs-corporation-worker:local)
  FS_CORP_WORKER_SCRATCH  Optional parent directory for temporary job scratch

Does not open the company database. Container workers always use network none.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_WORKER_IMAGE = "fs-corporation-worker:local"


def _token_from_env() -> str:
    path = (os.environ.get("FS_CORP_WORKER_HOST_TOKEN_FILE") or "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    token = (os.environ.get("FS_CORP_WORKER_HOST_TOKEN") or "").strip()
    if not token:
        raise SystemExit("Set FS_CORP_WORKER_HOST_TOKEN or FS_CORP_WORKER_HOST_TOKEN_FILE")
    return token


def request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {url} -> {exc.code}: {detail}") from exc


def mock_execute(job: dict) -> dict:
    """Deterministic mock outcome — no secrets, no DB."""
    task_id = job.get("task_id") or "unknown"
    return {
        "type": "remote_mock",
        "task_id": task_id,
        "artifact_hint": f"remote-mock-{task_id}",
    }


def runtime_mode() -> str:
    return (os.environ.get("FS_CORP_REMOTE_WORKER_RUNTIME") or "").strip().lower()


def docker_ready(image: str, docker_bin: str | None = None) -> tuple[bool, str]:
    docker = docker_bin or shutil.which("docker")
    if not docker:
        return False, "Docker executable not found"
    try:
        inspected = subprocess.run(
            [docker, "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Docker image inspection failed for {image}: {exc}"
    if inspected.returncode != 0:
        detail = (inspected.stderr or inspected.stdout or "").strip()
        reason = f"Docker image unavailable: {image}"
        return False, f"{reason}: {detail}" if detail else reason
    return True, ""


def build_docker_cmd(docker: str, image: str, scratch: Path) -> list[str]:
    mount = str(scratch.resolve())
    return [
        docker,
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{mount}:/work:rw",
        "-e",
        "COMPANY_WORKER_MODE=container",
        "--label",
        "fs.corp.runtime=remote_container",
        "--label",
        "fs.corp.network=none",
        image,
        "--envelope",
        "/work/envelope.json",
        "--scratch",
        "/work",
    ]


def pump_remote_gateway(scratch, post_gateway, renew, timeout=120):
    scratch = Path(scratch)
    request_path = scratch / "gw-request.json"
    response_path = scratch / "gw-response.json"
    result_path = scratch / "result.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if request_path.exists() and not response_path.exists():
            try:
                message = json.loads(request_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(0.05)
                continue
            reply = post_gateway(message)
            tmp = scratch / "gw-response.json.tmp"
            tmp.write_text(json.dumps(reply), encoding="utf-8")
            tmp.replace(response_path)
            renew()
        if result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise TimeoutError("Remote container worker did not finish")


def execute_claimed_job(
    base: str, host_id: str, token: str, claimed: dict
) -> tuple[str, dict]:
    image = (os.environ.get("FS_CORP_WORKER_IMAGE") or DEFAULT_WORKER_IMAGE).strip()
    docker = shutil.which("docker")
    if not docker:
        return "failed", {
            "error": "Docker executable not found",
            "type": "remote_container_unready",
        }
    scratch_parent = (os.environ.get("FS_CORP_WORKER_SCRATCH") or "").strip()
    if scratch_parent:
        Path(scratch_parent).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"remote-worker-{claimed['id']}-",
        dir=scratch_parent or None,
    ) as scratch_name:
        scratch = Path(scratch_name)
        (scratch / "envelope.json").write_text(
            json.dumps(claimed["envelope"]), encoding="utf-8"
        )
        try:
            proc = subprocess.Popen(
                build_docker_cmd(docker, image, scratch),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            return "failed", {
                "error": str(exc),
                "type": "remote_container_error",
            }
        job_url = (
            f"{base}/api/v1/worker-hosts/{host_id}/jobs/{claimed['id']}"
        )
        try:
            result = pump_remote_gateway(
                scratch,
                lambda message: request(
                    "POST", f"{job_url}/gateway", token, message
                ),
                lambda: request("POST", f"{job_url}/renew", token),
            )
            _stdout, stderr = proc.communicate(timeout=30)
            if proc.returncode != 0:
                detail = (stderr or "").strip()
                return "failed", {
                    "error": f"Remote container exited {proc.returncode}: {detail}",
                    "type": "remote_container_error",
                }
            return "completed", result
        except Exception as exc:  # noqa: BLE001 — return a failed job outcome
            if proc.poll() is None:
                proc.kill()
            proc.communicate()
            return "failed", {
                "error": str(exc),
                "type": "remote_container_error",
            }


def once(base: str, host_id: str, token: str) -> int:
    request("POST", f"{base}/api/v1/worker-hosts/{host_id}/heartbeat", token, {"meta": {"agent": "remote_worker_agent"}})
    listed = request("GET", f"{base}/api/v1/worker-hosts/{host_id}/jobs?status=queued", token)
    jobs = listed.get("jobs") or []
    handled = 0
    for job in jobs:
        claimed = request(
            "POST",
            f"{base}/api/v1/worker-hosts/{host_id}/jobs/{job['id']}/claim",
            token,
        )
        completion: dict = {}
        if runtime_mode() != "container":
            status, result = "completed", mock_execute(claimed)
        else:
            image = (
                os.environ.get("FS_CORP_WORKER_IMAGE") or DEFAULT_WORKER_IMAGE
            ).strip()
            ready, reason = docker_ready(image)
            if not ready:
                status, result = "failed", {
                    "error": reason,
                    "type": "remote_container_unready",
                }
            else:
                status, result = execute_claimed_job(base, host_id, token, claimed)
            completion["runtime"] = "remote_container"
        request(
            "POST",
            f"{base}/api/v1/worker-hosts/{host_id}/jobs/{job['id']}/complete",
            token,
            {"status": status, "result": result, **completion},
        )
        handled += 1
        print(
            f"{status} job={job['id']} task={job.get('task_id')}",
            flush=True,
        )
    return handled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Single poll cycle then exit")
    parser.add_argument("--sleep", type=float, default=5.0, help="Seconds between polls")
    args = parser.parse_args(argv)
    base = (os.environ.get("FS_CORP_CONTROL_URL") or "").rstrip("/")
    host_id = (os.environ.get("FS_CORP_WORKER_HOST_ID") or "").strip()
    if not base or not host_id:
        raise SystemExit("FS_CORP_CONTROL_URL and FS_CORP_WORKER_HOST_ID are required")
    token = _token_from_env()
    if args.once:
        once(base, host_id, token)
        return 0
    while True:
        try:
            once(base, host_id, token)
        except Exception as exc:  # noqa: BLE001 — agent loop must stay up
            print(f"agent error: {exc}", file=sys.stderr, flush=True)
        time.sleep(max(0.5, args.sleep))


if __name__ == "__main__":
    raise SystemExit(main())
