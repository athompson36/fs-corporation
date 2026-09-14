"""Worker gateway invoke_model persists billed_costs (ChatDev-in-worker depth)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from company.core import Company
from company.worker import SubprocessWorkerRuntime
from tests.env_guard import AmbientEnvIsolatedTestCase
from tests.test_core import install, policy


class WorkerChatDevBilledTests(AmbientEnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.registry = {"profiles": {
            "mock-text": {
                "provider": "mock", "enabled": True,
                "capabilities": ["text"], "allowed_data": ["public"],
            },
            "live": {
                "provider": "openai", "enabled": True, "model": "gpt-4o-mini",
                "capabilities": ["text"], "allowed_data": ["public"],
            },
        }}

    def test_gateway_mock_invoke_does_not_write_billed_cost(self):
        before = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        SubprocessWorkerRuntime.handle_request(self.c, {
            "op": "invoke_model",
            "profile_id": "mock-text",
            "prompt": "hello",
            "registry": self.registry,
        })
        after = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        self.assertEqual(after, before)

    @patch("company.model_provider.complete")
    def test_gateway_live_invoke_writes_billed_cost(self, mock_complete):
        mock_complete.return_value = {
            "text": "pilot",
            "profile_id": "live",
            "usage_tokens": 1200,
            "cost_cents": 5,
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        before = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            out = SubprocessWorkerRuntime.handle_request(self.c, {
                "op": "invoke_model",
                "profile_id": "live",
                "prompt": "hello",
                "registry": self.registry,
            })
        self.assertEqual(out["usage_tokens"], 1200)
        self.assertEqual(out["cost_cents"], 5)
        after = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        self.assertEqual(after, before + 1)
        row = self.c.db.execute(
            "SELECT amount_cents, usage_tokens, source, profile_id FROM billed_costs "
            "ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["amount_cents"], 5)
        self.assertEqual(row["usage_tokens"], 1200)
        self.assertEqual(row["source"], "invoke_model")
        self.assertEqual(row["profile_id"], "live")


if __name__ == "__main__":
    unittest.main()
