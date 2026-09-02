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


def queue_and_lease(project: str, task_id: str, worker_id: str, *, db_path: str | None) -> None:
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
    if db_path:
        env = os.environ.copy()
        env["FS_CORP_DB"] = db_path
        subprocess.run([sys.executable, "-c", code], check=True, env=env)
        return
    subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue and container-dispatch a mock draft task")
    parser.add_argument(
        "--base",
        default=os.environ.get("FS_CORP_API_BASE", "http://localhost:8013"),
        help="API base URL (fs-dev loopback: http://127.0.0.1:8000)",
    )
    parser.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE", ""))
    parser.add_argument("--db", default=os.environ.get("FS_CORP_DB", ""), help="SQLite path for native/fs-dev mode")
    parser.add_argument("--project", default="app")
    parser.add_argument("--task-id", default="container-pilot-1")
    parser.add_argument("--worker-id", default="container-pilot")
    args = parser.parse_args()
    if not args.token_file:
        print("Set --token-file or FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    token = Path(args.token_file).read_text().strip()
    tid = args.task_id
    db_path = args.db.strip() or None
    try:
        queue_and_lease(args.project, tid, args.worker_id, db_path=db_path)
        mode = "native" if db_path else "docker-compose"
        print(f"queued and leased task {tid} as head ({mode})")
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
