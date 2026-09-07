"""P0.2 M10 ops: idempotency prune, model/benchmark reads, learning fetch."""
from __future__ import annotations
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from company.core import Company, now
from company.idempotency_prune import DEFAULT_RETENTION_DAYS, retention_days_from_env
from tests.test_api import owner_client
from tests.test_core import install, policy


class IdempotencyPruneTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_default_retention_is_seven_days(self):
        self.assertEqual(DEFAULT_RETENTION_DAYS, 7)
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(retention_days_from_env(), 7)

    def test_prune_deletes_only_old_keys(self):
        old_at = (now() - timedelta(days=10)).isoformat()
        new_at = now().isoformat()
        with self.c.tx():
            self.c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("old-key", "human-ceo", "h1", 200, "{}", old_at),
            )
            self.c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("new-key", "human-ceo", "h2", 200, "{}", new_at),
            )
        out = self.c.prune_idempotency_keys("human-ceo", older_than_days=7)
        self.assertEqual(out["deleted"], 1)
        self.assertEqual(out["older_than_days"], 7)
        keys = {
            r["key"]
            for r in self.c.db.execute("SELECT key FROM command_idempotency")
        }
        self.assertEqual(keys, {"new-key"})

    def test_prune_http(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        old_at = (now() - timedelta(days=30)).isoformat()
        with c.tx():
            c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("stale", "human-ceo", "h", 200, "{}", old_at),
            )
        r = client.post(
            "/api/v1/ops/idempotency/prune",
            json={"payload": {}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "prune-1"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["result"]["deleted"], 1)


if __name__ == "__main__":
    unittest.main()
