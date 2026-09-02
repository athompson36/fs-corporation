"""Isolated worker runtime. Workers never receive control-plane database credentials."""
from __future__ import annotations
import json
import multiprocessing
import shutil
import subprocess
import time
from pathlib import Path
from company.adapters import MockChatDevAdapter, WorkOrder

ALLOWED_WORKER_OPS = frozenset({"gateway_check", "execute_mock", "store_artifact", "invoke_model"})
GW_REQUEST = "gw-request.json"
GW_RESPONSE = "gw-response.json"
GW_RESULT = "result.json"


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


def run_isolated_work(envelope: dict, scratch_root: Path, request, text_artifacts=False):
    """Child-side work. Must not import or open Company."""
    scratch_root = Path(scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    payload = envelope["payload"]
    task_id = envelope["task_id"]

    check = request(
        "gateway_check",
        actor=payload["actor"], project=payload["project"], action=payload["action"],
        cost=payload["cost"], task_id=task_id)
    if not check.get("allow"):
        return {"type": "error", "reason": check.get("reason", "denied")}

    order = WorkOrder(
        task_id, payload["project"], check["policy_version"],
        envelope.get("workflow_digest") or "mock-workflow", payload["cost"], {"tools": ["none"]})
    adapter_result = MockChatDevAdapter().run(order)
    scratch_file = scratch_root / f"{task_id}.txt"
    scratch_file.write_text(adapter_result["final_message"], encoding="utf-8")

    artifact = {"producer": payload["actor"], "task_id": task_id, "project": payload["project"],
                "root": str(scratch_root)}
    if text_artifacts:
        artifact["content_text"] = adapter_result["final_message"]
    else:
        artifact["content"] = adapter_result["final_message"].encode()
    request("store_artifact", **artifact)

    task = request(
        "execute_mock",
        actor=payload["actor"], project=payload["project"], action=payload["action"],
        cost=payload["cost"], task_id=task_id, approval=envelope.get("approval"))
    return {"type": "done", "task": task, "adapter": adapter_result}


def worker_entrypoint(conn, envelope: dict, scratch_root: Path):
    """Child-side worker loop over a pipe. Must not import or open Company."""
    def request(op, **kwargs):
        conn.send({"type": "request", "op": op, **kwargs})
        return conn.recv()

    result = run_isolated_work(envelope, scratch_root, request)
    conn.send(result)


def file_gateway_request(scratch_root: Path, op: str, timeout=30, **kwargs):
    scratch_root = Path(scratch_root)
    req = scratch_root / GW_REQUEST
    res = scratch_root / GW_RESPONSE
    if res.exists():
        res.unlink()
    tmp = scratch_root / f"{GW_REQUEST}.tmp"
    tmp.write_text(json.dumps({"type": "request", "op": op, **kwargs}), encoding="utf-8")
    tmp.replace(req)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if res.exists():
            data = json.loads(res.read_text(encoding="utf-8"))
            res.unlink()
            if req.exists():
                req.unlink()
            return data
        time.sleep(0.05)
    raise TimeoutError("Gateway did not respond")


def pump_file_gateway(company, scratch_root: Path, approval=None, artifact_root=None, timeout=30):
    scratch_root = Path(scratch_root)
    req = scratch_root / GW_REQUEST
    res = scratch_root / GW_RESPONSE
    result_path = scratch_root / GW_RESULT
    deadline = time.time() + timeout
    while time.time() < deadline:
        if req.exists() and not res.exists():
            try:
                msg = json.loads(req.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(0.05)
                continue
            reply = SubprocessWorkerRuntime.handle_request(
                company, msg, approval=approval, artifact_root=artifact_root)
            tmp = scratch_root / f"{GW_RESPONSE}.tmp"
            tmp.write_text(json.dumps(reply), encoding="utf-8")
            tmp.replace(res)
        if result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise TimeoutError("Worker did not finish")


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
            content = msg.get("content")
            if content is None:
                content = msg["content_text"].encode()
            digest_hex = company.store_artifact(
                msg["producer"], msg["task_id"], msg["project"], content, root)
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
    """Docker-backed runtime with a scratch-directory gateway. Fail-closed without Docker."""

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
        image = "fs-corporation-worker:local"
        cmd = [
            docker, "run", "--rm", "--network", "none",
            "-v", f"{scratch_root.resolve()}:/work:rw",
            "-e", "COMPANY_WORKER_MODE=container",
            image,
            "python", "-m", "company.worker", "--envelope", "/work/envelope.json", "--scratch", "/work",
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError as exc:
            company._finish_worker_run(run_id, "failed")
            raise NotImplementedError(
                "Container worker requires Docker; use SubprocessWorkerRuntime locally. See docs/23-isolated-workers.md") from exc
        try:
            result = pump_file_gateway(company, scratch_root, approval=approval, artifact_root=scratch_root)
            stdout, stderr = proc.communicate(timeout=30)
            if proc.returncode != 0:
                company._finish_worker_run(run_id, "failed")
                raise NotImplementedError(
                    "Container worker image is not built; local subprocess runtime is available. "
                    f"stderr={(stderr or '').strip()}")
            company._finish_worker_run(run_id, "completed")
            company.db.execute("UPDATE queue SET status='done' WHERE task_id=?", (task_id,))
            company._event("task.worker_completed", {"task_id": task_id, "worker": worker_id, "runtime": self.runtime_name})
            return result
        except Exception:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
            company._finish_worker_run(run_id, "failed")
            raise


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Isolated worker entrypoint")
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--scratch", required=True)
    args = parser.parse_args()
    envelope = json.loads(Path(args.envelope).read_text())
    scratch = Path(args.scratch)

    def request(op, **kwargs):
        return file_gateway_request(scratch, op, **kwargs)

    result = run_isolated_work(envelope, scratch, request, text_artifacts=True)
    if result.get("type") == "error":
        raise PermissionError(result.get("reason", "denied"))
    (scratch / GW_RESULT).write_text(json.dumps(result["task"]), encoding="utf-8")
    print(json.dumps(result["task"]))


if __name__ == "__main__":
    main()
