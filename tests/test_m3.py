import tempfile
from pathlib import Path
import unittest
from company.core import Company, now
from datetime import timedelta
from tests.test_core import install, policy, qc_pass


class WorkerGatewayTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_reservation_queue_lease_and_gateway(self):
        reserved = self.c.reserve_budget("head", "app", "draft", 100, "r1")
        self.assertEqual(reserved["status"], "reserved")
        with self.assertRaises(PermissionError):
            self.c.reserve_budget("head", "app", "draft", 450, "r2")
        self.c.release_reservation("r1")
        self.c.reserve_budget("head", "app", "draft", 100, "r3")
        self.c.capture_reservation("r3")
        queued = self.c.queue_task("head", "app", "draft", 50, "q1")
        self.assertEqual(queued["status"], "queued")
        until = self.c.claim_lease("worker-1", "q1")
        self.assertTrue(until)
        result = self.c.dispatch_queued("q1")
        self.assertEqual(result["status"], "produced")
        with tempfile.TemporaryDirectory() as worker_scratch:
            self.c.queue_task("head", "app", "draft", 50, "q2")
            self.c.claim_lease("worker-2", "q2")
            isolated = self.c.dispatch_queued_isolated("worker-2", "q2", worker_scratch)
            self.assertEqual(isolated["status"], "produced")
            run = self.c.db.execute("SELECT runtime FROM worker_runs WHERE task_id='q2'").fetchone()
            self.assertEqual(run["runtime"], "subprocess")
        check = self.c.gateway_check("head", "app", "draft", 10, "g1")
        self.assertTrue(check["allow"])
        oid = self.c.outbox_add("task.produced", {"task_id": "q1"})
        self.assertEqual(len(self.c.outbox_pending()), 1)
        self.c.outbox_mark(oid, "sent")
        self.assertEqual(self.c.outbox_pending(), [])

    def test_artifact_store_and_mock_model_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            digest_hex = self.c.store_artifact("head", "t-art", "app", b"hello", d)
            self.assertEqual(len(digest_hex), 64)
            self.c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="t-art")
            artifact = self.c.db.execute("SELECT artifact_hash FROM tasks WHERE id='t-art'").fetchone()[0]
            qc_pass(self.c, {"id": "t-art", "artifact_hash": artifact})
            self.c.accept_artifact("human-ceo", "t-art", artifact)
        registry = {"profiles": {
            "mock-text": {"provider": "mock", "enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
            "live": {"provider": "openai", "enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
        }}
        self.assertEqual(self.c.invoke_model("mock-text", "hello", registry)["provider"], "mock")
        with self.assertRaises(NotImplementedError):
            self.c.invoke_model("live", "hello", registry)

    def test_consultant_work_order_no_execute(self):
        from company.consultant import ConsultantDesk
        from tests.test_m1 import PROPOSAL
        desk = ConsultantDesk(self.c)
        pid = desk.submit("master-consultant", PROPOSAL)
        desk.decide("human-ceo", pid, "approved", "authorize separately")
        oid = desk.to_work_order("human-ceo", pid)
        self.assertTrue(oid)
        self.assertEqual(self.c.db.execute("SELECT status FROM work_orders WHERE id=?", (oid,)).fetchone()[0], "authorized")
        self.assertEqual(self.c.status()["tasks"], 0)


if __name__ == "__main__":
    unittest.main()
