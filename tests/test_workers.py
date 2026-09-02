import multiprocessing
import tempfile
import unittest
from pathlib import Path
from company.core import Company
from company.worker import (
    ContainerWorkerRuntime, SubprocessWorkerRuntime, build_worker_envelope, worker_entrypoint)
from tests.test_core import install, policy


class WorkerIsolationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.addCleanup(self.c.close)

    def test_envelope_excludes_control_plane_secrets(self):
        self.c.queue_task("head", "app", "draft", 10, "w1")
        env = build_worker_envelope(self.c, "worker-1", "w1")
        blob = str(env)
        self.assertNotIn(".db", blob)
        self.assertNotIn("company.db", blob)
        self.assertNotIn("token", blob.lower())
        self.assertEqual(env["worker_id"], "worker-1")

    def test_subprocess_worker_completes_queued_task(self):
        self.c.queue_task("head", "app", "draft", 10, "w2")
        self.c.claim_lease("worker-1", "w2")
        result = SubprocessWorkerRuntime().dispatch(
            self.c, "worker-1", "w2", Path(self.scratch.name))
        self.assertEqual(result["status"], "produced")
        row = self.c.db.execute("SELECT status FROM queue WHERE task_id='w2'").fetchone()
        self.assertEqual(row["status"], "done")
        run = self.c.db.execute("SELECT * FROM worker_runs WHERE task_id='w2'").fetchone()
        self.assertEqual(run["runtime"], "subprocess")
        self.assertEqual(run["status"], "completed")

    def test_container_file_gateway_completes_queued_task(self):
        repo = Path(__file__).resolve().parents[1]
        fake_docker = Path(self.scratch.name) / "fake-docker"
        fake_docker.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            f"sys.path.insert(0, {str(repo)!r})\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "host = None\n"
            "for i, a in enumerate(args):\n"
            "    if a == '-v':\n"
            "        host = args[i + 1].split(':')[0]\n"
            "        break\n"
            "if not host:\n"
            "    raise SystemExit('fake-docker: missing -v scratch mount')\n"
            "from company.worker import main\n"
            "sys.argv = ['company.worker', '--envelope', str(Path(host) / 'envelope.json'), '--scratch', host]\n"
            "main()\n",
            encoding="utf-8",
        )
        fake_docker.chmod(0o755)
        self.c.queue_task("head", "app", "draft", 10, "w-container")
        self.c.claim_lease("worker-1", "w-container")
        result = ContainerWorkerRuntime().dispatch(
            self.c, "worker-1", "w-container", Path(self.scratch.name), docker_path=str(fake_docker))
        self.assertEqual(result["status"], "produced")
        row = self.c.db.execute("SELECT status FROM queue WHERE task_id='w-container'").fetchone()
        self.assertEqual(row["status"], "done")
        run = self.c.db.execute("SELECT * FROM worker_runs WHERE task_id='w-container'").fetchone()
        self.assertEqual(run["runtime"], "container")
        self.assertEqual(run["status"], "completed")

    def test_worker_gateway_denies_policy_mutation(self):
        conn_recv, conn_send = multiprocessing.Pipe(duplex=True)
        try:
            conn_send.send({"type": "request", "op": "propose_policy", "policy": {}})
            with self.assertRaises(PermissionError):
                SubprocessWorkerRuntime.handle_request(self.c, conn_recv.recv())
        finally:
            conn_recv.close()
            conn_send.close()

    def test_revoked_queue_blocks_isolated_dispatch(self):
        self.c.queue_task("head", "app", "draft", 10, "w3")
        self.c.cancel_queued("human-ceo", "w3")
        with self.assertRaises(PermissionError):
            SubprocessWorkerRuntime().dispatch(self.c, "worker-1", "w3", Path(self.scratch.name))

    def test_container_runtime_fail_closed_without_docker(self):
        runtime = ContainerWorkerRuntime()
        self.c.queue_task("head", "app", "draft", 10, "w4")
        self.c.claim_lease("worker-1", "w4")
        with self.assertRaises(NotImplementedError):
            runtime.dispatch(self.c, "worker-1", "w4", Path(self.scratch.name), docker_path="/nonexistent/docker")

    def test_worker_entrypoint_runs_without_company_db(self):
        self.c.queue_task("head", "app", "draft", 10, "w5")
        env = build_worker_envelope(self.c, "worker-1", "w5")
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe(duplex=True)
        proc = ctx.Process(
            target=worker_entrypoint,
            args=(child, env, Path(self.scratch.name) / "w5"))
        proc.start()
        child.close()
        requests = 0
        try:
            while proc.is_alive() or parent.poll():
                if not parent.poll(0.5):
                    continue
                msg = parent.recv()
                if msg.get("type") == "request":
                    requests += 1
                    parent.send(SubprocessWorkerRuntime.handle_request(self.c, msg))
                elif msg.get("type") == "done":
                    self.assertEqual(msg["task"]["id"], "w5")
                    break
            proc.join(timeout=5)
            self.assertGreaterEqual(requests, 2)
        finally:
            parent.close()
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
