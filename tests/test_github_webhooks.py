"""GitHub webhook signature and ingest tests (fail-closed)."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class GitHubWebhookTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.addCleanup(self.c.close)
        self.client = TestClient(create_app(self.c))
        self.secret = "test-webhook-secret"
        os.environ["GITHUB_WEBHOOK_SECRET"] = self.secret
        self.addCleanup(lambda: os.environ.pop("GITHUB_WEBHOOK_SECRET", None))

    def _post(self, event: str, payload: dict, *, delivery: str = "deliv-1", secret: str | None = None, raw: bytes | None = None):
        body = raw if raw is not None else json.dumps(payload).encode()
        headers = {
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery,
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _sign(secret or self.secret, body),
        }
        return self.client.post("/api/v1/github/webhooks", content=body, headers=headers)

    def test_fail_closed_without_secret(self):
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        r = self._post("ping", {"zen": "x"})
        self.assertEqual(r.status_code, 503)

    def test_reject_bad_signature(self):
        r = self._post("ping", {"zen": "x"}, secret="wrong")
        self.assertEqual(r.status_code, 401)

    def test_reject_oversize_body(self):
        huge = b"{" + b'"a":"' + (b"x" * (1024 * 1024)) + b'"}'
        r = self._post("ping", {}, delivery="big", raw=huge)
        self.assertEqual(r.status_code, 413)

    def test_ignore_unknown_event(self):
        r = self._post("marketplace_purchase", {"action": "purchased"}, delivery="unk-1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ignored")
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM github_webhook_deliveries").fetchone()[0], 0)

    def test_accept_ping_and_idempotent_replay(self):
        r1 = self._post("ping", {"zen": "keyboard cat"}, delivery="ping-1")
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r1.json()["status"], "accepted")
        r2 = self._post("ping", {"zen": "keyboard cat"}, delivery="ping-1")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["status"], "duplicate")
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM github_webhook_deliveries").fetchone()[0], 1)

    def test_normalize_pull_request_without_privilege(self):
        payload = {
            "action": "opened",
            "number": 1,
            "pull_request": {"html_url": "https://github.com/acme/pilot/pull/1", "head": {"sha": "abc"}},
            "repository": {"id": 1355366113, "full_name": "athompson36/fs-corp-comp"},
        }
        r = self._post("pull_request", payload, delivery="pr-1")
        self.assertEqual(r.status_code, 200)
        row = self.c.db.execute("SELECT * FROM github_webhook_deliveries WHERE delivery_id=?", ("pr-1",)).fetchone()
        self.assertEqual(row["event"], "pull_request")
        self.assertEqual(row["repo_id"], "1355366113")
        self.assertIn("opened", row["summary"])
        # Must not treat payload as an identity grant
        self.assertIsNone(self.c.identity_for_token("abc"))

    def test_status_reports_webhook_secret(self):
        r = self.client.get("/api/v1/github/status", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["webhook_secret_configured"])


if __name__ == "__main__":
    unittest.main()
