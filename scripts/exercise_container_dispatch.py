#!/usr/bin/env python3
"""Exercise container worker dispatch against the local loopback API."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def api(base: str, method: str, path: str, token: str, body: dict | None = None, idem: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idem:
        headers["Idempotency-Key"] = idem
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def queue_and_lease_in_container(project: str, task_id: str, worker_id: str) -> None:
    code = (
        "from company.core import Company\n"
        "import os\n"
        f"tid={task_id!r}; project={project!r}; worker={worker_id!r}\n"
        "c = Company(os.environ['FS_CORP_DB'])\n"
        "row = c.db.execute('SELECT status FROM queue WHERE task_id=?', (tid,)).fetchone()\n"
        "if not row:\n"
        "    c.queue_task('head', project, 'draft', 10, tid)\n"
        "c.claim_lease(worker, tid)\n"
        "c.close()\n"
    )
    subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue and container-dispatch a mock draft task")
    parser.add_argument("--base", default=os.environ.get("FS_CORP_API_BASE", "http://localhost:8013"))
    parser.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE", ""))
    parser.add_argument("--project", default="app")
    parser.add_argument("--task-id", default="container-pilot-1")
    parser.add_argument("--worker-id", default="container-pilot")
    args = parser.parse_args()
    if not args.token_file:
        print("Set --token-file or FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    token = Path(args.token_file).read_text().strip()
    tid = args.task_id
    try:
        queue_and_lease_in_container(args.project, tid, args.worker_id)
        print(f"queued and leased task {tid} as head (in-container)")
        dispatched = api(args.base, "POST", f"/api/v1/tasks/{tid}/dispatch-worker", token, {
            "payload": {"runtime": "container", "worker_id": args.worker_id},
        }, idem=f"dispatch-{tid}")
        print("dispatch:", json.dumps(dispatched, indent=2))
        status = dispatched.get("result", {}).get("status")
        return 0 if status == "produced" else 2
    except (urllib.error.HTTPError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, urllib.error.HTTPError):
            print(exc.read().decode(), file=sys.stderr)
        else:
            print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
