"""P3 durable finance: invoices, adjustments, period close."""
import unittest
from datetime import timedelta

from company.core import Company, now
from tests.test_api import owner_client
from tests.test_core import install, policy


def _insert_billed(c, bid, amount, recorded_at, provider="openai", profile="live"):
    with c.tx():
        c.db.execute(
            "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
            (bid, recorded_at, amount, 100, provider, profile, "test", None),
        )


class InvoiceTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_empty_window_rejected(self):
        start = now().isoformat()
        end = (now() + timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            self.c.create_invoice("human-ceo", start, end)

    def test_create_list_get(self):
        t0 = (now() - timedelta(hours=2)).isoformat()
        t1 = (now() - timedelta(hours=1)).isoformat()
        t2 = now().isoformat()
        _insert_billed(self.c, "b1", 100, t0)
        _insert_billed(self.c, "b2", 50, t1)
        _insert_billed(self.c, "b3", 999, (now() + timedelta(days=1)).isoformat())
        inv = self.c.create_invoice("human-ceo", t0, t2)
        self.assertEqual(inv["total_cents"], 150)
        self.assertEqual(inv["line_count"], 2)
        self.assertEqual(len(inv["body"]["lines"]), 2)
        listed = self.c.list_invoices()
        self.assertEqual(len(listed), 1)
        got = self.c.get_invoice(inv["id"])
        self.assertEqual(got["id"], inv["id"])


class AdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        _insert_billed(self.c, "b10", 100, now().isoformat())

    def test_void_and_net(self):
        self.assertEqual(self.c.status()["billed_cost_cents"], 100)
        self.c.post_finance_adjustment(
            "human-ceo", kind="void", billed_cost_id="b10", reason="duplicate")
        st = self.c.status()
        self.assertEqual(st["billed_cost_gross_cents"], 100)
        self.assertEqual(st["billed_adjustment_cents"], 100)
        self.assertEqual(st["billed_cost_cents"], 0)
        with self.assertRaises(PermissionError):
            self.c.post_finance_adjustment(
                "human-ceo", kind="void", billed_cost_id="b10", reason="again")

    def test_partial_then_void_remaining(self):
        self.c.post_finance_adjustment(
            "human-ceo", kind="partial_credit", billed_cost_id="b10",
            amount_cents=40, reason="goodwill")
        self.assertEqual(self.c.status()["billed_cost_cents"], 60)
        self.c.post_finance_adjustment(
            "human-ceo", kind="void", billed_cost_id="b10", reason="rest")
        self.assertEqual(self.c.status()["billed_cost_cents"], 0)


class PeriodCloseTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_close_once(self):
        start = (now() - timedelta(days=1)).isoformat()
        end = (now() + timedelta(days=30)).isoformat()
        pid = self.c.set_budget_period("human-ceo", "company", start, end, 5000)
        closed = self.c.close_budget_period("human-ceo", pid)
        self.assertTrue(closed["closed"])
        self.assertIn("limit_cents", closed["closure"]["snapshot"])
        with self.assertRaises(PermissionError):
            self.c.close_budget_period("human-ceo", pid)


class FinanceApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.h = {"Authorization": "Bearer owner-token"}

    def test_invoice_and_adjustment_http(self):
        t0 = (now() - timedelta(hours=1)).isoformat()
        t1 = (now() + timedelta(hours=1)).isoformat()
        _insert_billed(self.c, "http-b1", 75, t0)
        created = self.client.post(
            "/api/v1/finance/invoices",
            json={"payload": {"period_start": t0, "period_end": t1}},
            headers={**self.h, "Idempotency-Key": "inv-1"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["result"]["total_cents"], 75)
        adj = self.client.post(
            "/api/v1/finance/adjustments",
            json={"payload": {
                "kind": "partial_credit", "billed_cost_id": "http-b1",
                "amount_cents": 25, "reason": "credit",
            }},
            headers={**self.h, "Idempotency-Key": "adj-1"},
        )
        self.assertEqual(adj.status_code, 200, adj.text)
        summary = self.client.get("/api/v1/finance/summary", headers=self.h)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["billed_cost_cents"], 50)


if __name__ == "__main__":
    unittest.main()
