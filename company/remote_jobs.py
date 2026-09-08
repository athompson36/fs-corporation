"""Remote pull-agent jobs: enqueue, claim, complete (mock path)."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path

from company.core import now
from company.worker import SubprocessWorkerRuntime, build_worker_envelope
from company.worker_hosts import heartbeat_ttl_sec, host_state, require_host_token


LEASE_SEC = 120
MAX_ATTEMPTS = 3
REMOTE_GATEWAY_OPS = frozenset({"gateway_check", "execute_mock", "store_artifact"})


def _job_public(row) -> dict:
    return {
        "id": row["id"],
        "host_id": row["host_id"],
        "task_id": row["task_id"],
        "worker_run_id": row["worker_run_id"],
        "status": row["status"],
        "lease_owner": row["lease_owner"],
        "lease_expires_at": row["lease_expires_at"],
        "attempts": int(row["attempts"]),
        "result": json.loads(row["result_json"] or "null"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_by": row["created_by"],
    }


def _expire_stale_claims(company, host_id: str | None = None):
    """Caller must already hold company.tx()."""
    stamp = now().isoformat()
    q = "SELECT * FROM remote_worker_jobs WHERE status='claimed'"
    args: list = []
    if host_id:
        q += " AND host_id=?"
        args.append(host_id)
    rows = company.db.execute(q, args).fetchall()
    for row in rows:
        expires = row["lease_expires_at"]
        if not expires or expires > stamp:
            continue
        attempts = int(row["attempts"])
        if attempts >= MAX_ATTEMPTS:
            company.db.execute(
                "UPDATE remote_worker_jobs SET status=?, updated_at=?, lease_owner=NULL, lease_expires_at=NULL WHERE id=?",
                ("failed", stamp, row["id"]),
            )
            if row["worker_run_id"]:
                company.db.execute(
                    "UPDATE worker_runs SET status=?, finished_at=? WHERE id=?",
                    ("failed", stamp, row["worker_run_id"]),
                )
                company._event(
                    "worker.finished",
                    {"run_id": row["worker_run_id"], "status": "failed"},
                )
            company._event(
                "remote_job.failed",
                {"id": row["id"], "reason": "lease_exhausted"},
            )
        else:
            company.db.execute(
                "UPDATE remote_worker_jobs SET status=?, updated_at=?, lease_owner=NULL, lease_expires_at=NULL WHERE id=?",
                ("queued", stamp, row["id"]),
            )
            company._event("remote_job.requeued", {"id": row["id"]})


def enqueue_remote_job(company, actor: str, *, host_id: str, task_id: str, worker_id: str) -> dict:
    host = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    if not host:
        raise ValueError("Worker host not found")
    state = host_state(host, ttl_sec=heartbeat_ttl_sec(company))
    if state != "ready":
        raise ValueError(f"Worker host is not ready (state={state})")
    qrow = company.db.execute("SELECT * FROM queue WHERE task_id=?", (task_id,)).fetchone()
    if not qrow:
        raise ValueError("Queued task not found")
    if qrow["status"] == "cancelled":
        raise PermissionError("Revoked or cancelled work cannot dispatch")
    if qrow["status"] not in {"queued", "leased"}:
        raise ValueError("Queued task not available")
    if qrow["status"] == "leased" and qrow["lease_owner"] not in {
        worker_id,
        f"remote-host:{host_id}",
    }:
        raise PermissionError("Task is leased to another worker")

    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    stamp = now().isoformat()
    lease_owner = f"remote-host:{host_id}"
    with company.tx():
        company.db.execute(
            "INSERT INTO worker_runs VALUES(?,?,?,?,?,?,?,?)",
            (run_id, worker_id, task_id, "remote_agent", "", "running", stamp, None),
        )
        company._event(
            "worker.started",
            {
                "run_id": run_id,
                "worker": worker_id,
                "task_id": task_id,
                "runtime": "remote_agent",
            },
        )
        company.db.execute(
            "UPDATE queue SET status='leased', lease_owner=?, lease_until=?, attempts=attempts+1 WHERE task_id=?",
            (lease_owner, (now() + timedelta(seconds=LEASE_SEC * 2)).isoformat(), task_id),
        )
        company.db.execute(
            "INSERT INTO remote_worker_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                host_id,
                task_id,
                run_id,
                "queued",
                None,
                None,
                0,
                None,
                stamp,
                stamp,
                actor,
            ),
        )
        company._event(
            "remote_job.enqueued",
            {"id": job_id, "host_id": host_id, "task_id": task_id, "run_id": run_id},
            actor_id=actor,
        )
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=?", (job_id,)
    ).fetchone()
    return _job_public(row)


def list_host_jobs(company, host_id: str, token: str, *, status: str | None = "queued") -> list[dict]:
    require_host_token(company, host_id, token)
    with company.tx():
        _expire_stale_claims(company, host_id)
    q = "SELECT * FROM remote_worker_jobs WHERE host_id=?"
    args: list = [host_id]
    if status:
        q += " AND status=?"
        args.append(status)
    q += " ORDER BY created_at, id"
    return [_job_public(r) for r in company.db.execute(q, args).fetchall()]


def claim_job(company, host_id: str, token: str, job_id: str) -> dict:
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    expires = (now() + timedelta(seconds=LEASE_SEC)).isoformat()
    lease_owner = f"agent:{host_id}"
    with company.tx():
        _expire_stale_claims(company, host_id)
        row = company.db.execute(
            "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if not row:
            raise PermissionError("Unknown remote job")
        if row["status"] != "queued":
            raise PermissionError("Job is not available to claim")
        company.db.execute(
            """UPDATE remote_worker_jobs
               SET status='claimed', lease_owner=?, lease_expires_at=?, attempts=attempts+1, updated_at=?
               WHERE id=?""",
            (lease_owner, expires, stamp, job_id),
        )
        company._event(
            "remote_job.claimed",
            {"id": job_id, "host_id": host_id, "lease_expires_at": expires},
        )
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=?", (job_id,)
    ).fetchone()
    out = _job_public(row)
    qrow = company.db.execute(
        "SELECT payload FROM queue WHERE task_id=?", (row["task_id"],)
    ).fetchone()
    out["payload"] = json.loads(qrow["payload"]) if qrow else {}
    worker_id = f"remote-host:{host_id}"
    out["envelope"] = build_worker_envelope(company, worker_id, row["task_id"])
    return out


def renew_job_lease(company, host_id: str, token: str, job_id: str) -> dict:
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    expires = (now() + timedelta(seconds=LEASE_SEC)).isoformat()
    with company.tx():
        _expire_stale_claims(company, host_id)
        row = company.db.execute(
            "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if not row:
            raise PermissionError("Unknown remote job")
        if row["status"] != "claimed":
            raise PermissionError("Job is not claimed")
        if row["lease_expires_at"] and row["lease_expires_at"] < stamp:
            raise PermissionError("Job lease expired")
        company.db.execute(
            "UPDATE remote_worker_jobs SET lease_expires_at=?, updated_at=? WHERE id=?",
            (expires, stamp, job_id),
        )
        company._event(
            "remote_job.lease_renewed", {"id": job_id, "host_id": host_id}
        )
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=?", (job_id,)
    ).fetchone()
    return _job_public(row)


def relay_gateway(
    company, host_id: str, token: str, job_id: str, message: dict
) -> dict:
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    with company.tx():
        _expire_stale_claims(company, host_id)
        row = company.db.execute(
            "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if not row:
            raise PermissionError("Unknown remote job")
        if row["status"] != "claimed":
            raise PermissionError("Job is not claimed")
        if row["lease_expires_at"] and row["lease_expires_at"] < stamp:
            raise PermissionError("Job lease expired")

    task_id = row["task_id"]
    msg = dict(message)
    op = msg.get("op")
    if op is None:
        raise ValueError("Gateway message requires op")
    if op not in REMOTE_GATEWAY_OPS:
        raise PermissionError(f"Worker cannot invoke {op}")
    message_task_id = msg.get("task_id")
    if message_task_id is None:
        raise PermissionError(f"Worker operation {op} requires task_id")
    if message_task_id != task_id:
        raise PermissionError("Gateway task does not match claimed job")

    base = (os.environ.get("FS_CORP_WORKER_SCRATCH") or "").strip()
    if base:
        artifact_root = Path(base) / "remote-artifacts" / task_id
    else:
        artifact_root = Path(tempfile.mkdtemp(prefix=f"remote-art-{task_id}-"))
    artifact_root.mkdir(parents=True, exist_ok=True)

    if str(msg.get("root") or "").startswith("/work"):
        msg.pop("root", None)
    reply = SubprocessWorkerRuntime.handle_request(
        company, msg, approval=None, artifact_root=str(artifact_root)
    )
    renewed_at = now().isoformat()
    expires = (now() + timedelta(seconds=LEASE_SEC)).isoformat()
    with company.tx():
        current = company.db.execute(
            "SELECT status FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if current and current["status"] == "claimed":
            company.db.execute(
                "UPDATE remote_worker_jobs SET lease_expires_at=?, updated_at=? WHERE id=?",
                (expires, renewed_at, job_id),
            )
        # The operation may already have committed side effects. A lost claim only
        # prevents renewal; it must not turn a successful reply into an error.
    return reply


def complete_job(
    company,
    host_id: str,
    token: str,
    job_id: str,
    *,
    status: str,
    result: dict | None = None,
    runtime: str | None = None,
) -> dict:
    require_host_token(company, host_id, token)
    if status not in {"completed", "failed"}:
        raise ValueError("status must be completed or failed")
    if runtime is not None and runtime not in {"remote_agent", "remote_container"}:
        raise ValueError("runtime must be remote_agent or remote_container")
    stamp = now().isoformat()
    with company.tx():
        row = company.db.execute(
            "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if not row:
            raise PermissionError("Unknown remote job")
        if row["status"] != "claimed":
            raise PermissionError("Job is not claimed")
        if row["lease_expires_at"] and row["lease_expires_at"] < stamp:
            raise PermissionError("Job lease expired")
        company.db.execute(
            """UPDATE remote_worker_jobs
               SET status=?, result_json=?, updated_at=?, lease_owner=NULL, lease_expires_at=NULL
               WHERE id=?""",
            (status, json.dumps(result) if result is not None else None, stamp, job_id),
        )
        run_id = row["worker_run_id"]
        task_id = row["task_id"]
        recorded_runtime = "remote_container" if runtime == "remote_container" else "remote_agent"
        if status == "completed" and run_id:
            if runtime == "remote_container":
                company.db.execute(
                    "UPDATE worker_runs SET status=?, finished_at=?, runtime=? WHERE id=?",
                    ("completed", stamp, "remote_container", run_id),
                )
            else:
                company.db.execute(
                    "UPDATE worker_runs SET status=?, finished_at=? WHERE id=?",
                    ("completed", stamp, run_id),
                )
            company._event("worker.finished", {"run_id": run_id, "status": "completed"})
            company.db.execute("UPDATE queue SET status='done' WHERE task_id=?", (task_id,))
            company._event(
                "task.worker_completed",
                {
                    "task_id": task_id,
                    "worker": f"remote-host:{host_id}",
                    "runtime": recorded_runtime,
                },
            )
        elif status == "failed":
            if run_id:
                if runtime == "remote_container":
                    company.db.execute(
                        "UPDATE worker_runs SET status=?, finished_at=?, runtime=? WHERE id=?",
                        ("failed", stamp, "remote_container", run_id),
                    )
                else:
                    company.db.execute(
                        "UPDATE worker_runs SET status=?, finished_at=? WHERE id=?",
                        ("failed", stamp, run_id),
                    )
                company._event(
                    "worker.finished", {"run_id": run_id, "status": "failed"}
                )
            released = company.db.execute(
                """UPDATE queue
                   SET status='queued', lease_owner=NULL, lease_until=NULL
                   WHERE task_id=? AND status!='cancelled'""",
                (task_id,),
            )
            if released.rowcount:
                company._event(
                    "remote_job.queue_released",
                    {"id": job_id, "task_id": task_id},
                )
        company._event(
            "remote_job.completed" if status == "completed" else "remote_job.failed",
            {"id": job_id, "host_id": host_id, "status": status},
        )
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=?", (job_id,)
    ).fetchone()
    return _job_public(row)
