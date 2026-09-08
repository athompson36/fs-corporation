"""Feed source approve / pause / revoke / poll lifecycle."""
import unittest
from unittest.mock import patch

from company.core import Company
from tests.test_api import owner_client
from tests.test_core import install, policy


class FeedLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_pause_blocks_poll_reapprove_restores(self):
        self.c.approve_feed_source("human-ceo", "f1", "https://example.com/feed")
        paused = self.c.pause_feed_source("human-ceo", "f1")
        self.assertEqual(paused["status"], "paused")
        with self.assertRaises(PermissionError):
            self.c.poll_market_feed("f1", actor="human-ceo")
        self.c.approve_feed_source("human-ceo", "f1", "https://example.com/feed")
        with patch("company.adapters.MarketFeedAdapter.poll", return_value=[]):
            row = self.c.poll_market_feed("f1", actor="human-ceo")
        self.assertEqual(row["status"], "applied")
        kinds = [r[0] for r in self.c.db.execute("SELECT kind FROM events WHERE kind LIKE 'feed.%'")]
        self.assertIn("feed.source_paused", kinds)

    def test_revoke_blocks_poll(self):
        self.c.approve_feed_source("human-ceo", "f2", "https://example.com/feed2")
        rev = self.c.revoke_feed_source("human-ceo", "f2")
        self.assertEqual(rev["status"], "revoked")
        with self.assertRaises(PermissionError):
            self.c.poll_market_feed("f2", actor="human-ceo")
        kinds = [r[0] for r in self.c.db.execute("SELECT kind FROM events WHERE kind LIKE 'feed.%'")]
        self.assertIn("feed.source_revoked", kinds)

    def test_head_cannot_pause_or_revoke(self):
        self.c.approve_feed_source("human-ceo", "f3", "https://example.com/feed3")
        with self.assertRaises(PermissionError):
            self.c.pause_feed_source("engineering-head", "f3")
        with self.assertRaises(PermissionError):
            self.c.revoke_feed_source("engineering-head", "f3")

    def test_pause_missing_and_revoked(self):
        with self.assertRaises(ValueError):
            self.c.pause_feed_source("human-ceo", "missing")
        self.c.approve_feed_source("human-ceo", "f4", "https://example.com/feed4")
        self.c.revoke_feed_source("human-ceo", "f4")
        with self.assertRaises(ValueError):
            self.c.pause_feed_source("human-ceo", "f4")


class FeedApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.h = {"Authorization": "Bearer owner-token"}

    def test_pause_revoke_via_http(self):
        approve = self.client.post(
            "/api/v1/feeds",
            json={"payload": {"id": "http-f1", "url": "https://example.com/http-feed"}},
            headers={**self.h, "Idempotency-Key": "feed-approve-1"},
        )
        self.assertEqual(approve.status_code, 200, approve.text)
        paused = self.client.post(
            "/api/v1/feeds/http-f1/pause",
            json={"payload": {}},
            headers={**self.h, "Idempotency-Key": "feed-pause-1"},
        )
        self.assertEqual(paused.status_code, 200, paused.text)
        self.assertEqual(paused.json()["result"]["status"], "paused")
        listed = self.client.get("/api/v1/feeds", headers=self.h)
        self.assertEqual(listed.status_code, 200)
        row = next(f for f in listed.json()["feeds"] if f["id"] == "http-f1")
        self.assertEqual(row["status"], "paused")
        poll = self.client.post(
            "/api/v1/feeds/http-f1/poll",
            json={"payload": {}},
            headers={**self.h, "Idempotency-Key": "feed-poll-paused"},
        )
        self.assertIn(poll.status_code, {400, 403, 409}, poll.text)
        revoked = self.client.post(
            "/api/v1/feeds/http-f1/revoke",
            json={"payload": {}},
            headers={**self.h, "Idempotency-Key": "feed-revoke-1"},
        )
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()["result"]["status"], "revoked")


if __name__ == "__main__":
    unittest.main()
