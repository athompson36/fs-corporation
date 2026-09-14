"""Provider invoice headers + allocations (0.3.88)."""
import unittest

from fastapi.testclient import TestClient

from company.core import Company, now
from company.migrate import HEAD_REVISION
from company.service import create_app
from tests.test_core import install, policy


def _insert_billed(c, bid, amount, recorded_at=None, provider="openai"):
    stamp = recorded_at or now().isoformat()
    with c.tx():
        c.db.execute(
            "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
            (bid, stamp, amount, 100, provider, "live", "test", None),
        )


class ProviderInvoiceTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_head_revision(self):
        self.assertEqual(HEAD_REVISION, "0030_provider_invoices")

    def test_create_list_unique_external(self):
        inv = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-1",
            total_cents=500, issued_at=now().isoformat(), note="sept")
        self.assertEqual(inv["status"], "open")
        self.assertEqual(inv["total_cents"], 500)
        self.assertEqual(inv["allocated_cents"], 0)
        self.assertEqual(inv["unallocated_cents"], 500)
        self.assertEqual(inv["variance_cents"], 0)
        self.assertEqual(len(self.c.list_provider_invoices()), 1)
        with self.assertRaises(ValueError):
            self.c.create_provider_invoice(
                "human-ceo", provider="openai", external_id="inv-1",
                total_cents=1, issued_at=now().isoformat())

    def test_allocate_variance_and_guards(self):
        _insert_billed(self.c, "b1", 100)
        _insert_billed(self.c, "b2", 40)
        inv = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-2",
            total_cents=200, issued_at=now().isoformat())
        before_net = self.c.status()["billed_cost_cents"]
        detail = self.c.allocate_provider_invoice(
            "human-ceo", inv["id"], billed_cost_id="b1", allocated_cents=120)
        line = next(a for a in detail["allocations"] if a["billed_cost_id"] == "b1")
        self.assertEqual(line["estimated_cents"], 100)
        self.assertEqual(line["allocated_cents"], 120)
        self.assertEqual(line["variance_cents"], 20)
        self.assertEqual(detail["allocated_cents"], 120)
        self.assertEqual(detail["unallocated_cents"], 80)
        self.assertEqual(detail["variance_cents"], 20)
        self.assertEqual(self.c.status()["billed_cost_cents"], before_net)
        self.assertEqual(
            self.c.finance_summary()["provider_invoice_variance_cents"], 20)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b1", allocated_cents=1)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="missing", allocated_cents=1)
        with self.assertRaises(ValueError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=100)
        other = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-3",
            total_cents=50, issued_at=now().isoformat())
        with self.assertRaises(PermissionError):
            self.c.allocate_provider_invoice(
                "human-ceo", other["id"], billed_cost_id="b1", allocated_cents=10)
        self.c.allocate_provider_invoice(
            "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=40)
        voided = self.c.void_provider_invoice("human-ceo", inv["id"])
        self.assertEqual(voided["status"], "void")
        with self.assertRaises(PermissionError):
            self.c.allocate_provider_invoice(
                "human-ceo", inv["id"], billed_cost_id="b2", allocated_cents=1)
        # void releases lines for re-allocation on a new open invoice
        reopened = self.c.create_provider_invoice(
            "human-ceo", provider="openai", external_id="inv-4",
            total_cents=40, issued_at=now().isoformat())
        self.c.allocate_provider_invoice(
            "human-ceo", reopened["id"], billed_cost_id="b2", allocated_cents=40)
        self.assertEqual(
            self.c.finance_summary()["provider_invoice_variance_cents"], 0)

    def test_api_create_allocate_void_and_scope(self):
        _insert_billed(self.c, "api-b1", 50)
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = TestClient(create_app(self.c))
        auth = {"Authorization": "Bearer owner-token"}
        r = client.post(
            "/api/v1/finance/provider-invoices",
            json={"payload": {"provider": "openai", "external_id": "api-1",
                  "total_cents": 80, "issued_at": now().isoformat()}},
            headers={**auth, "Idempotency-Key": "pi-1"})
        self.assertEqual(r.status_code, 200, r.text)
        iid = r.json()["result"]["id"]
        r2 = client.post(
            f"/api/v1/finance/provider-invoices/{iid}/allocations",
            json={"payload": {"billed_cost_id": "api-b1", "allocated_cents": 55}},
            headers={**auth, "Idempotency-Key": "pi-2"})
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["result"]["variance_cents"], 5)
        r3 = client.get(
            f"/api/v1/finance/provider-invoices/{iid}", headers=auth)
        self.assertEqual(r3.status_code, 200)
        r4 = client.post(
            f"/api/v1/finance/provider-invoices/{iid}/void",
            json={"payload": {}},
            headers={**auth, "Idempotency-Key": "pi-3"})
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["result"]["status"], "void")


if __name__ == "__main__":
    unittest.main()
