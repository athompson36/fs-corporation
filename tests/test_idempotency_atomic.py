"""Atomic idempotency: effect and remember_command share one transaction (M10-01)."""
import json
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


class AtomicIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.addCleanup(self.c.close)

    def test_nested_tx_joins_outer_and_rolls_back_together(self):
        with self.assertRaises(RuntimeError):
            with self.c.tx():
                self.c.pause("human-ceo", True)
                self.c.remember_command("k1", "human-ceo", "hash", 200, "{}")
                raise RuntimeError("boom")
        self.assertEqual(
            self.c.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0],
            "false",
        )
        self.assertIsNone(self.c.lookup_command("k1"))

    def test_run_idempotent_commits_effect_and_record_together(self):
        def work():
            self.c.pause("human-ceo", True)
            body = json.dumps({"paused": True})
            return {"paused": True}, 200, body

        out = self.c.run_idempotent("pause-atomic", "human-ceo", "h-pause", work)
        self.assertFalse(out["replay"])
        self.assertEqual(
            self.c.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0],
            "true",
        )
        self.assertIsNotNone(self.c.lookup_command("pause-atomic"))

        again = self.c.run_idempotent("pause-atomic", "human-ceo", "h-pause", work)
        self.assertTrue(again["replay"])
        paused_events = self.c.db.execute(
            "SELECT COUNT(*) AS n FROM events WHERE kind='company.paused'"
        ).fetchone()["n"]
        self.assertEqual(paused_events, 1)

    def test_api_pause_idempotency_still_replays(self):
        client = TestClient(create_app(self.c))
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "pause-1"}
        a = client.post("/api/v1/company/pause", json={"payload": {}}, headers=headers)
        b = client.post("/api/v1/company/pause", json={"payload": {}}, headers=headers)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.json(), b.json())
        self.assertEqual(
            self.c.db.execute(
                "SELECT COUNT(*) AS n FROM events WHERE kind='company.paused'"
            ).fetchone()["n"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
