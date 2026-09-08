"""Work-order replay ledger."""
import unittest

from company.consultant import ConsultantDesk
from company.core import Company
from tests.test_core import install, policy
from tests.test_m1 import PROPOSAL


class WorkOrderReplayTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.desk = ConsultantDesk(self.c)

    def test_authorize_complete_replay(self):
        pid = self.desk.submit("consultant", PROPOSAL)
        self.desk.decide("human-ceo", pid, "approved", "ok")
        oid = self.desk.to_work_order("human-ceo", pid)
        wo = dict(self.c.db.execute("SELECT * FROM work_orders WHERE id=?", (oid,)).fetchone())
        replays = self.c.list_work_order_replays(oid)
        self.assertEqual(len(replays), 1)
        self.assertEqual(replays[0]["status"], "authorized")
        completed = self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done", "artifact": "patch"})
        self.assertEqual(completed["status"], "completed")
        again = self.c.replay_work_order("human-ceo", oid, wo["workflow_digest"])
        self.assertTrue(again["replay"])
        self.assertEqual(again["outcome"]["artifact"], "patch")
        self.assertEqual(len(self.c.list_work_order_replays(oid)), 3)
        with self.assertRaises(PermissionError):
            self.c.replay_work_order("human-ceo", oid, "wrong-digest")


if __name__ == "__main__":
    unittest.main()
