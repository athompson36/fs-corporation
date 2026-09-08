"""Remote container-on-agent: envelope, gateway relay, renew."""
import unittest
from company.core import Company
from company.remote_jobs import claim_job, enqueue_remote_job
from company.worker_hosts import create_worker_host, record_worker_host_heartbeat
from tests.test_core import install, policy


class ClaimEnvelopeTests(unittest.TestCase):
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
        self.c.queue_task("head", "app", "draft", 10, "env-t1")

    def test_claim_includes_envelope(self):
        job = enqueue_remote_job(
            self.c, "human-ceo",
            host_id=self.host_id, task_id="env-t1", worker_id="worker-r",
        )
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        env = claimed["envelope"]
        self.assertEqual(env["task_id"], "env-t1")
        self.assertEqual(env["worker_id"], f"remote-host:{self.host_id}")
        self.assertIn("payload", env)
        self.assertIn("workflow_digest", env)
