#!/usr/bin/env python3
"""Pull agent for registered worker hosts (heartbeat + claim + mock complete).

Environment:
  FS_CORP_CONTROL_URL     Base URL of the control plane (e.g. https://192.168.4.100)
  FS_CORP_WORKER_HOST_ID  Host id from CEO create
  FS_CORP_WORKER_HOST_TOKEN  Host token (or FS_CORP_WORKER_HOST_TOKEN_FILE)

Does not open the company database. Mock-complete only (no remote Docker in v1).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


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
        result = mock_execute(claimed)
        request(
            "POST",
            f"{base}/api/v1/worker-hosts/{host_id}/jobs/{job['id']}/complete",
            token,
            {"status": "completed", "result": result},
        )
        handled += 1
        print(f"completed job={job['id']} task={job.get('task_id')}", flush=True)
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
