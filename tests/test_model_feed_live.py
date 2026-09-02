import unittest
from unittest.mock import patch

from company.core import Company
from company.feed_fetch import parse_feed
from company.model_provider import complete
from tests.test_core import install, policy


SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
<item><title>Vendor advisory</title>
<link>https://example.com/advisory/1</link>
<pubDate>Mon, 01 Sep 2025 12:00:00 GMT</pubDate>
<description>Test feed item for FS-Corporation pilot.</description>
</item></channel></rss>"""


class ModelLiveTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.registry = {"profiles": {
            "mock-text": {"provider": "mock", "enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
            "live": {"provider": "openai", "enabled": True, "model": "gpt-4o-mini",
                     "capabilities": ["text"], "allowed_data": ["public"]},
        }}

    def test_invoke_model_fail_closed_without_key(self):
        with patch("company.model_provider.model_configured", return_value=False):
            with self.assertRaises(NotImplementedError):
                self.c.invoke_model("live", "hello", self.registry)

    @patch("company.model_provider.model_configured", return_value=True)
    @patch("company.model_provider.complete")
    def test_invoke_model_live(self, mock_complete, _configured):
        mock_complete.return_value = {"text": "pilot", "profile_id": "live", "cost_cents": 1, "provider": "openai"}
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            out = self.c.invoke_model("live", "hello", self.registry)
        self.assertEqual(out["text"], "pilot")
        mock_complete.assert_called_once()

    @patch("company.model_provider.httpx.Client")
    def test_complete_openai_shape(self, client_cls):
        response = client_cls.return_value.__enter__.return_value.post.return_value
        response.raise_for_status = lambda: None
        response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"total_tokens": 12},
        }
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            out = complete("live", {"provider": "openai", "model": "gpt-4o-mini"}, "hi")
        self.assertEqual(out["text"], "ok")
        self.assertEqual(out["cost_cents"], 12)

    @patch("company.model_provider.httpx.Client")
    def test_complete_anthropic_shape(self, client_cls):
        response = client_cls.return_value.__enter__.return_value.post.return_value
        response.raise_for_status = lambda: None
        response.json.return_value = {
            "content": [{"type": "text", "text": "claude ok"}],
            "usage": {"input_tokens": 5, "output_tokens": 7},
        }
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False):
            out = complete("claude", {"provider": "anthropic", "model": "claude-3-5-haiku-latest"}, "hi")
        self.assertEqual(out["text"], "claude ok")
        self.assertEqual(out["cost_cents"], 12)

    def test_invoke_model_anthropic_fail_closed_without_key(self):
        registry = {"profiles": {
            "claude": {"provider": "anthropic", "enabled": True, "model": "claude-3-5-haiku-latest",
                       "capabilities": ["text"], "allowed_data": ["public"],
                       "credential_ref": "ANTHROPIC_API_KEY"},
        }}
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(NotImplementedError):
                self.c.invoke_model("claude", "hello", registry)

    @patch("company.model_provider.status_summary")
    def test_status_endpoint(self, mock_status):
        from fastapi.testclient import TestClient
        from company.service import create_app
        mock_status.return_value = {"configured": True, "live": True}
        app = create_app(self.c)
        client = TestClient(app)
        self.c.register_identity("human-ceo", "owner", "owner-token")
        r = client.get("/api/v1/model/status", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["live"])


class FeedLiveTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_parse_rss_sample(self):
        items = parse_feed(SAMPLE_RSS, observed_at="2025-09-01T12:00:00+00:00")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Vendor advisory")
        self.assertTrue(items[0]["source"].startswith("https://"))

    @patch("company.adapters.MarketFeedAdapter.poll")
    def test_poll_market_feed_applied(self, mock_poll):
        mock_poll.return_value = parse_feed(SAMPLE_RSS, observed_at="2025-09-01T12:00:00+00:00")
        self.c.approve_feed_source("human-ceo", "platform-changes", "https://example.com/approved-feed")
        first = self.c.poll_market_feed("platform-changes")
        self.assertEqual(first["status"], "applied")
        self.assertEqual(first["ingested"], 1)
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 1)
        retry = self.c.poll_market_feed("platform-changes")
        self.assertEqual(first["id"], retry["id"])
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM feed_polls").fetchone()[0], 1)

    @patch("company.adapters.MarketFeedAdapter.poll")
    def test_feed_api_approve_and_poll(self, mock_poll):
        from fastapi.testclient import TestClient
        from company.service import create_app
        mock_poll.return_value = parse_feed(SAMPLE_RSS, observed_at="2025-09-01T12:00:00+00:00")
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = TestClient(create_app(self.c))
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "feed-approve-1"}
        approved = client.post("/api/v1/feeds", json={"payload": {
            "id": "gh-releases", "url": "https://github.com/athompson36/fs-corporation/releases.atom"}},
            headers=headers)
        self.assertEqual(approved.status_code, 200)
        listed = client.get("/api/v1/feeds", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(len(listed.json()["feeds"]), 1)
        polled = client.post("/api/v1/feeds/gh-releases/poll", json={"payload": {}},
                             headers={**headers, "Idempotency-Key": "feed-poll-1"})
        self.assertEqual(polled.status_code, 200)
        self.assertEqual(polled.json()["result"]["status"], "applied")


if __name__ == "__main__":
    unittest.main()
