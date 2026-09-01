"""Isolated worker runtime. Workers never receive control-plane database credentials."""
from __future__ import annotations
import json
import multiprocessing
import shutil
import subprocess
import sys
from pathlib import Path
from company.adapters import MockChatDevAdapter, WorkOrder

ALLOWED_WORKER_OPS = frozenset({"gateway_check", "execute_mock", "store_artifact", "invoke_model"})


def _normalize_digest(row):
    if not row:
        return "mock-workflow"
    return row[0] if isinstance(row, tuple) else row["workflow_digest"]


def build_worker_envelope(company, worker_id: str, task_id: str, approval=None):
    row = company.db.execute("SELECT * FROM queue WHERE task_id=?", (task_id,)).fetchone()
    if not row:
        raise ValueError("Queued task not found")
    if row["status"] == "cancelled":
        raise PermissionError("Revoked or cancelled work cannot dispatch")
    if row["status"] not in {"queued", "leased"}:
        raise ValueError("Queued task not found")
    if row["status"] == "leased" and row["lease_owner"] != worker_id:
        raise PermissionError("Task is leased to another worker")
    payload = json.loads(row["payload"])
    digest_row = company.db.execute(
        "SELECT workflow_digest FROM work_orders WHERE task_id=? ORDER BY rowid DESC LIMIT 1",
        (task_id,)).fetchone()
    return {
        "worker_id": worker_id,
        "task_id": task_id,
        "approval": approval,
        "workflow_digest": _normalize_digest(digest_row),
        "payload": payload,
    }


def worker_entrypoint(conn, envelope: dict, scratch_root: Path):
    """Child-side worker loop. Must not import or open Company."""
    scratch_root = Path(scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    payload = envelope["payload"]
    task_id = envelope["task_id"]

    def request(op, **kwargs):
        conn.send({"type": "request", "op": op, **kwargs})
        return conn.recv()

    check = request(
        "gateway_check",
        actor=payload["actor"], project=payload["project"], action=payload["action"],
        cost=payload["cost"], task_id=task_id)
    if not check.get("allow"):
        conn.send({"type": "error", "reason": check.get("reason", "denied")})
        return

    order = WorkOrder(
        task_id, payload["project"], check["policy_version"],
        envelope.get("workflow_digest") or "mock-workflow", payload["cost"], {"tools": ["none"]})
    adapter_result = MockChatDevAdapter().run(order)
    scratch_file = scratch_root / f"{task_id}.txt"
    scratch_file.write_text(adapter_result["final_message"], encoding="utf-8")

    request(
        "store_artifact",
        producer=payload["actor"], task_id=task_id, project=payload["project"],
        content=adapter_result["final_message"].encode(), root=str(scratch_root))

    task = request(
        "execute_mock",
        actor=payload["actor"], project=payload["project"], action=payload["action"],
        cost=payload["cost"], task_id=task_id, approval=envelope.get("approval"))
    conn.send({"type": "done", "task": task, "adapter": adapter_result})


class SubprocessWorkerRuntime:
    """Local isolation via a spawned subprocess and a parent-mediated gateway."""

    runtime_name = "subprocess"

    @staticmethod
    def handle_request(company, msg: dict, approval=None, artifact_root=None):
        op = msg["op"]
        if op not in ALLOWED_WORKER_OPS:
            raise PermissionError(f"Worker cannot invoke {op}")
        if op == "gateway_check":
            return company.gateway_check(
                msg["actor"], msg["project"], msg["action"], msg["cost"], msg["task_id"],
                target=msg.get("target"))
        if op == "execute_mock":
            return company.execute_mock(
                actor=msg["actor"], project=msg["project"], action=msg["action"],
                cost=msg["cost"], task_id=msg["task_id"], approval=approval or msg.get("approval"))
        if op == "store_artifact":
            root = artifact_root or msg["root"]
            digest_hex = company.store_artifact(
                msg["producer"], msg["task_id"], msg["project"], msg["content"], root)
            return {"hash": digest_hex}
        if op == "invoke_model":
            return company.invoke_model(msg["profile_id"], msg["prompt"], msg["registry"])
        raise PermissionError(f"Unknown worker operation {op}")

    def dispatch(self, company, worker_id: str, task_id: str, scratch_root: Path, approval=None):
        envelope = build_worker_envelope(company, worker_id, task_id, approval)
        scratch_root = Path(scratch_root) / task_id
        scratch_root.mkdir(parents=True, exist_ok=True)
        run_id = company._start_worker_run(worker_id, task_id, self.runtime_name, str(scratch_root))
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(target=worker_entrypoint, args=(child, envelope, scratch_root))
        proc.start()
        child.close()
        try:
            result = self._pump(company, parent, approval=approval, artifact_root=scratch_root)
            company._finish_worker_run(run_id, "completed")
            company.db.execute("UPDATE queue SET status='done' WHERE task_id=?", (task_id,))
            company._event("task.worker_completed", {"task_id": task_id, "worker": worker_id, "runtime": self.runtime_name})
            return result
        except Exception:
            company._finish_worker_run(run_id, "failed")
            raise
        finally:
            parent.close()
            proc.join(timeout=5)

    def _pump(self, company, parent, approval=None, artifact_root=None):
        while True:
            if not parent.poll(30):
                raise TimeoutError("Worker did not respond")
            msg = parent.recv()
            if msg.get("type") == "request":
                parent.send(self.handle_request(company, msg, approval=approval, artifact_root=artifact_root))
            elif msg.get("type") == "done":
                return msg["task"]
            elif msg.get("type") == "error":
                raise PermissionError(msg.get("reason", "worker denied"))


class ContainerWorkerRuntime:
    """Optional Docker-backed runtime. Fail-closed when Docker is unavailable."""

    runtime_name = "container"

    def dispatch(self, company, worker_id: str, task_id: str, scratch_root: Path, approval=None, docker_path=None):
        docker = docker_path or shutil.which("docker")
        if not docker:
            raise NotImplementedError(
                "Container worker requires Docker; use SubprocessWorkerRuntime locally. See docs/23-isolated-workers.md")
        envelope = build_worker_envelope(company, worker_id, task_id, approval)
        scratch_root = Path(scratch_root) / task_id
        scratch_root.mkdir(parents=True, exist_ok=True)
        envelope_path = scratch_root / "envelope.json"
        envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        run_id = company._start_worker_run(worker_id, task_id, self.runtime_name, str(scratch_root))
        image = "fs-tech-ai-company-worker:local"
        cmd = [
            docker, "run", "--rm", "--network", "none",
            "-v", f"{scratch_root.resolve()}:/work:rw",
            "-e", "COMPANY_WORKER_MODE=container",
            image,
            "python", "-m", "company.worker", "--envelope", "/work/envelope.json", "--scratch", "/work",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:
            company._finish_worker_run(run_id, "failed")
            raise NotImplementedError(
                "Container worker requires Docker; use SubprocessWorkerRuntime locally. See docs/23-isolated-workers.md") from exc
        if proc.returncode != 0:
            company._finish_worker_run(run_id, "failed")
            raise NotImplementedError(
                "Container worker image is not built; local subprocess runtime is available. "
                f"stderr={proc.stderr.strip()}")
        result = json.loads(proc.stdout)
        company._finish_worker_run(run_id, "completed")
        company.db.execute("UPDATE queue SET status='done' WHERE task_id=?", (task_id,))
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Isolated worker entrypoint")
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--scratch", required=True)
    args = parser.parse_args()
    envelope = json.loads(Path(args.envelope).read_text())
    raise NotImplementedError(
        "Container worker gateway proxy requires a built worker image; use subprocess runtime locally")


if __name__ == "__main__":
    main()
