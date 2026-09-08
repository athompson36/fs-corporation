"""Feed source approve / pause / revoke / poll lifecycle."""
import unittest
from unittest.mock import patch

from company.core import Company
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


if __name__ == "__main__":
    unittest.main()
