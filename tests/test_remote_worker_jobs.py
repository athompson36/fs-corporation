"""Remote pull-agent job lease and mock complete."""
import unittest

from company.core import Company
from company.remote_jobs import claim_job, complete_job, enqueue_remote_job, list_host_jobs
from company.worker_hosts import create_worker_host, record_worker_host_heartbeat
from tests.test_api import owner_client
from tests.test_core import install, policy


class RemoteJobTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        created = create_worker_host(
            self.c, "human-ceo", label="lab", base_url="https://lab.example.com"
        )
        self.host_id = created["id"]
        self.token = created["token"]
        record_worker_host_heartbeat(self.c, self.host_id, self.token)
        self.c.queue_task("head", "app", "draft", 10, "remote-t1")

    def test_enqueue_requires_ready_host(self):
        other = create_worker_host(
            self.c, "human-ceo", label="cold", base_url="https://cold.example.com"
        )
        with self.assertRaises(ValueError):
            enqueue_remote_job(
                self.c, "human-ceo",
                host_id=other["id"], task_id="remote-t1", worker_id="worker-r",
            )

    def test_claim_complete_happy_path(self):
        job = enqueue_remote_job(
            self.c, "human-ceo",
            host_id=self.host_id, task_id="remote-t1", worker_id="worker-r",
        )
        self.assertEqual(job["status"], "queued")
        jobs = list_host_jobs(self.c, self.host_id, self.token)
        self.assertEqual(len(jobs), 1)
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        self.assertEqual(claimed["status"], "claimed")
        self.assertIn("payload", claimed)
        with self.assertRaises(PermissionError):
            claim_job(self.c, self.host_id, self.token, job["id"])
        done = complete_job(
            self.c, self.host_id, self.token, job["id"],
            status="completed", result={"mock": True},
        )
        self.assertEqual(done["status"], "completed")
        q = self.c.db.execute(
            "SELECT status FROM queue WHERE task_id=?", ("remote-t1",)
        ).fetchone()
        self.assertEqual(q["status"], "done")
        run = self.c.db.execute(
            "SELECT status, runtime FROM worker_runs WHERE task_id=?", ("remote-t1",)
        ).fetchone()
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["runtime"], "remote_agent")

    def test_dispatch_isolated_branches(self):
        job = self.c.dispatch_queued_isolated(
            "worker-r", "remote-t1", "/tmp", worker_host_id=self.host_id,
            actor="human-ceo",
        )
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["host_id"], self.host_id)


class RemoteJobHttpTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.headers = {"Authorization": "Bearer owner-token"}
        created = self.client.post(
            "/api/v1/worker-hosts",
            json={"payload": {"label": "lab", "base_url": "https://lab.example.com"}},
            headers={**self.headers, "Idempotency-Key": "rh-1"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        body = created.json()["result"]
        self.host_id = body["id"]
        self.token = body["token"]
        hb = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/heartbeat",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(hb.status_code, 200)
        self.c.queue_task("head", "app", "draft", 10, "http-remote-1")

    def test_http_enqueue_claim_complete(self):
        disp = self.client.post(
            "/api/v1/tasks/http-remote-1/dispatch-worker",
            json={"payload": {"worker_host_id": self.host_id}},
            headers={**self.headers, "Idempotency-Key": "disp-r1"},
        )
        self.assertEqual(disp.status_code, 200, disp.text)
        job = disp.json()["result"]
        self.assertEqual(job["status"], "queued")
        listed = self.client.get(
            f"/api/v1/worker-hosts/{self.host_id}/jobs",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["jobs"]), 1)
        claimed = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{job['id']}/claim",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(claimed.status_code, 200, claimed.text)
        done = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{job['id']}/complete",
            json={"status": "completed", "result": {"ok": True}},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["status"], "completed")


if __name__ == "__main__":
    unittest.main()
