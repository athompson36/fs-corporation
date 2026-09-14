"""Work-order baseline/after ops measurements (v0.3.87)."""
import unittest

from company.consultant import ConsultantDesk
from company.core import Company
from company.measurements import METRIC_KEYS, capture_ops_metrics
from tests.test_core import install, policy
from tests.test_m1 import PROPOSAL


class CaptureOpsMetricsTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_keys_and_ints(self):
        m = capture_ops_metrics(self.c)
        self.assertEqual(set(m), set(METRIC_KEYS))
        for k in METRIC_KEYS:
            self.assertIsInstance(m[k], int)


class MeasurementLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.desk = ConsultantDesk(self.c)

    def _authorize(self):
        pid = self.desk.submit("consultant", PROPOSAL)
        self.desk.decide("human-ceo", pid, "approved", "ok")
        return self.desk.to_work_order("human-ceo", pid)

    def test_baseline_on_to_work_order(self):
        oid = self._authorize()
        got = self.c.get_work_order_measurements(oid)
        self.assertIsNotNone(got["baseline"])
        self.assertIsNone(got["after"])
        self.assertIsNone(got["deltas"])
        self.assertEqual(set(got["baseline"]["metrics"]), set(METRIC_KEYS))

    def test_baseline_idempotent(self):
        oid = self._authorize()
        first = self.c.get_work_order_measurements(oid)["baseline"]["created_at"]
        self.c.record_work_order_authorized(
            "human-ceo", oid,
            dict(self.c.db.execute("SELECT workflow_digest FROM work_orders WHERE id=?", (oid,)).fetchone())["workflow_digest"],
            outcome={"status": "authorized"},
        )
        second = self.c.get_work_order_measurements(oid)["baseline"]["created_at"]
        self.assertEqual(first, second)

    def test_after_and_deltas(self):
        oid = self._authorize()
        before = self.c.get_work_order_measurements(oid)["baseline"]["metrics"]
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done", "artifact": "patch"})
        got = self.c.get_work_order_measurements(oid)
        self.assertIsNotNone(got["after"])
        self.assertIsNotNone(got["deltas"])
        for k in METRIC_KEYS:
            self.assertEqual(
                got["deltas"][k],
                got["after"]["metrics"][k] - before[k],
            )

    def test_after_idempotent(self):
        oid = self._authorize()
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done"})
        a1 = self.c.get_work_order_measurements(oid)["after"]["created_at"]
        self.c.complete_work_order_outcome(
            "human-ceo", oid, {"status": "done", "again": True})
        a2 = self.c.get_work_order_measurements(oid)["after"]["created_at"]
        self.assertEqual(a1, a2)
