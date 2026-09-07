"""M10-03: billed cost and revenue stay separate from simulated credits."""
import unittest
from unittest.mock import patch

from company.core import Company
from tests.env_guard import AmbientEnvIsolatedTestCase
from tests.test_core import install, policy


class BilledCostRevenueTests(AmbientEnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.registry = {"profiles": {
            "mock-text": {"provider": "mock", "enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
            "live": {"provider": "openai", "enabled": True, "model": "gpt-4o-mini",
                     "capabilities": ["text"], "allowed_data": ["public"]},
        }}

    def test_mock_invoke_does_not_write_billed_cost(self):
        self.c.invoke_model("mock-text", "hello", self.registry)
        count = self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertEqual(self.c.status()["billed_cost_cents"], 0)

    @patch("company.model_provider.complete")
    def test_live_invoke_persists_unpriced_billed_row(self, mock_complete):
        mock_complete.return_value = {
            "text": "pilot",
            "profile_id": "live",
            "usage_tokens": 1200,
            "cost_cents": 0,
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            out = self.c.invoke_model("live", "hello", self.registry)
        self.assertEqual(out["usage_tokens"], 1200)
        self.assertEqual(out["cost_cents"], 0)
        row = self.c.db.execute("SELECT * FROM billed_costs").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["amount_cents"], 0)
        self.assertEqual(row["usage_tokens"], 1200)
        self.assertEqual(row["source"], "invoke_model")
        self.assertEqual(row["profile_id"], "live")
        status = self.c.status()
        self.assertEqual(status["billed_cost_cents"], 0)
        self.assertEqual(status["simulated_spend_cents"], 0)

    @patch("company.model_provider.complete")
    def test_live_invoke_persists_priced_amount(self, mock_complete):
        mock_complete.return_value = {
            "text": "pilot",
            "profile_id": "live",
            "usage_tokens": 1000,
            "cost_cents": 5,
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            self.c.invoke_model("live", "hello", self.registry)
        row = self.c.db.execute("SELECT amount_cents, usage_tokens FROM billed_costs").fetchone()
        self.assertEqual(row["amount_cents"], 5)
        self.assertEqual(row["usage_tokens"], 1000)
        self.assertEqual(self.c.status()["billed_cost_cents"], 5)
        self.assertEqual(self.c.status()["simulated_spend_cents"], 0)

    def test_record_revenue_ceo_only_and_unmixed(self):
        with self.assertRaises(PermissionError):
            self.c.record_revenue("not-ceo", 250, "manual")
        rid = self.c.record_revenue(self.c.ceo, 250, "manual", note="pilot sale")
        self.assertTrue(rid)
        status = self.c.status()
        self.assertEqual(status["revenue_cents"], 250)
        self.assertEqual(status["simulated_spend_cents"], 0)
        self.assertEqual(status["billed_cost_cents"], 0)
        row = self.c.db.execute("SELECT * FROM revenue WHERE id=?", (rid,)).fetchone()
        self.assertEqual(row["amount_cents"], 250)
        self.assertEqual(row["source"], "manual")
        self.assertEqual(row["note"], "pilot sale")

    def test_money_rejects_negative_revenue(self):
        with self.assertRaises(ValueError):
            self.c.record_revenue(self.c.ceo, -1, "manual")


if __name__ == "__main__":
    unittest.main()
