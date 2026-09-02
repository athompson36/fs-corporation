import unittest
from company.adapters import PushNotificationAdapter
from company.core import Company
from tests.test_core import install, policy


class PushNotificationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_register_requires_https_and_ceo(self):
        with self.assertRaises(ValueError):
            self.c.register_push_subscription("human-ceo", "http://insecure.example/push")
        with self.assertRaises(PermissionError):
            self.c.register_push_subscription("engineering-head", "https://push.example/sub/1")
        row = self.c.register_push_subscription("human-ceo", "https://push.example/sub/1")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["endpoint"], "https://push.example/sub/1")

    def test_notify_fail_closes_and_is_idempotent(self):
        self.c.register_push_subscription("human-ceo", "https://push.example/sub/1")
        first = self.c.notify_push("owner_inbox", "Need scope decision", {"request_id": "r1"})
        self.assertEqual(len(first["deliveries"]), 1)
        self.assertEqual(first["deliveries"][0]["status"], "live_unavailable")
        retry = self.c.notify_push("owner_inbox", "Need scope decision", {"request_id": "r1"})
        self.assertEqual(first["deliveries"][0]["id"], retry["deliveries"][0]["id"])
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM push_deliveries").fetchone()[0], 1)
        kinds = [r[0] for r in self.c.db.execute("SELECT kind FROM events WHERE kind LIKE 'push.%'")]
        self.assertIn("push.subscription_registered", kinds)
        self.assertIn("push.delivery_live_unavailable", kinds)

    def test_revoked_subscription_is_skipped(self):
        sub = self.c.register_push_subscription("human-ceo", "https://push.example/sub/1")
        self.c.revoke_push_subscription("human-ceo", sub["id"])
        result = self.c.notify_push("owner_inbox", "Closed", {})
        self.assertEqual(result["deliveries"], [])
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM push_deliveries").fetchone()[0], 0)

    def test_owner_request_attempts_push(self):
        from pathlib import Path
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.register_identity("engineering:Director", "service", "head-token", ["owner.escalate"])
        self.c.register_push_subscription("human-ceo", "https://push.example/sub/1")
        self.c.create_owner_request(
            "engineering:Director", "engineering", "feedback", "Need scope", "Details")
        row = self.c.db.execute("SELECT * FROM push_deliveries").fetchone()
        self.assertEqual(row["status"], "live_unavailable")
        self.assertEqual(row["kind"], "owner_inbox")

    def test_api_register_requires_owner(self):
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        denied = client.post("/api/v1/push/subscriptions", json={
            "payload": {"endpoint": "https://push.example/sub/1"}
        })
        self.assertEqual(denied.status_code, 401)
        ok = client.post("/api/v1/push/subscriptions", json={
            "payload": {"endpoint": "https://push.example/sub/1"}
        }, headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "push-1"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["result"]["status"], "active")

    def test_adapter_still_disabled(self):
        with self.assertRaises(NotImplementedError):
            PushNotificationAdapter().send(
                {"endpoint": "https://push.example/sub/1", "keys": {}}, {"title": "x"})

    def test_notify_applied_when_send_succeeds(self):
        from unittest.mock import patch
        self.c.register_push_subscription(
            "human-ceo", "https://push.example/sub/1", {"p256dh": "k", "auth": "a"})
        with patch("company.push_vapid.send_push", return_value={"status": "applied", "http_status": 201}):
            result = self.c.notify_push("owner_inbox", "Approved", {"request_id": "r2"})
        self.assertEqual(result["deliveries"][0]["status"], "applied")
        kinds = [r[0] for r in self.c.db.execute("SELECT kind FROM events WHERE kind LIKE 'push.%'")]
        self.assertIn("push.delivery_applied", kinds)

    def test_push_status_endpoint(self):
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        resp = client.get("/api/v1/push/status", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("configured", resp.json())

    def test_list_push_subscriptions(self):
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_push_subscription("human-ceo", "https://push.example/sub/2")
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        resp = client.get("/api/v1/push/subscriptions", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(resp.status_code, 200)
        subs = resp.json()["subscriptions"]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["endpoint"], "https://push.example/sub/2")
        self.assertNotIn("keys", subs[0])

    def test_application_server_key_when_vapid_pem_set(self):
        from unittest.mock import patch
        from company.push_vapid import application_server_key, status_summary
        pem = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAERttVz4X43Iium1+kPMmbYQ1TvcFO
cUkkvN9F9kBLrxZcmXQSpnCH4P75HX6FIqwq0Uu4fHMd3hIEN5OrD57j6w==
-----END PUBLIC KEY-----"""
        with patch.dict("os.environ", {
            "VAPID_PRIVATE_KEY": "x",
            "VAPID_PUBLIC_KEY": pem,
        }, clear=False):
            key = application_server_key()
            summary = status_summary()
        self.assertTrue(key)
        self.assertEqual(summary.get("application_server_key"), key)


if __name__ == "__main__":
    unittest.main()
