"""HTTP 429 rate-limit contract tests (M10-01)."""
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.register_identity("human-ceo", "owner", "owner-token")
        # Tiny limit so a principal can be driven over the threshold in one test.
        self.app = create_app(
            self.c,
            rate_limit=SimpleNamespace(
                authenticated_limit=3, unauthenticated_limit=2, window_sec=60.0),
        )
        self.client = TestClient(self.app)
        self.addCleanup(self.c.close)

    def test_authenticated_principal_over_limit_returns_429_with_retry_after(self):
        headers = {"Authorization": "Bearer owner-token"}
        for _ in range(3):
            self.assertEqual(self.client.get("/api/v1/company", headers=headers).status_code, 200)
        blocked = self.client.get("/api/v1/company", headers=headers)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)
        self.assertGreaterEqual(int(blocked.headers["Retry-After"]), 1)
        self.assertEqual(blocked.json()["detail"], "rate limit exceeded")

    def test_health_and_desk_are_exempt(self):
        headers = {"Authorization": "Bearer owner-token"}
        # Exhaust the authenticated bucket first.
        for _ in range(3):
            self.client.get("/api/v1/company", headers=headers)
        self.assertEqual(self.client.get("/api/v1/company", headers=headers).status_code, 429)
        self.assertEqual(self.client.get("/api/v1/health").status_code, 200)
        self.assertEqual(self.client.get("/desk").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_webhook_over_limit_returns_429_by_ip(self):
        for _ in range(2):
            r = self.client.post("/api/v1/github/webhooks", content=b"{}", headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": "d1",
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "sha256=dead",
            })
            self.assertIn(r.status_code, {401, 422, 503})
        blocked = self.client.post("/api/v1/github/webhooks", content=b"{}", headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": "d2",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=dead",
        })
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)


if __name__ == "__main__":
    unittest.main()
