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

    def test_send_push_loads_pem_via_vapid_object_not_raw_string(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from py_vapid import Vapid01
        from company import push_vapid

        vapid = Vapid01()
        vapid.generate_keys()
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "vapid-private.pem"
            vapid.save_key(str(private))
            with patch.dict("os.environ", {
                "VAPID_PRIVATE_KEY_FILE": str(private),
                "VAPID_CONTACT_EMAIL": "mailto:owner@example.com",
            }, clear=False):
                with patch("pywebpush.webpush") as mocked:
                    mocked.return_value = type("R", (), {"status_code": 201})()
                    result = push_vapid.send_push(
                        {"endpoint": "https://push.example/sub/1", "keys": {"p256dh": "k", "auth": "a"}},
                        {"subject": "hello", "kind": "owner_inbox"},
                    )
        self.assertEqual(result["status"], "applied")
        kwargs = mocked.call_args.kwargs
        key_arg = kwargs["vapid_private_key"]
        self.assertFalse(isinstance(key_arg, str) and key_arg.startswith("-----BEGIN"))
        self.assertEqual(type(key_arg).__name__, "Vapid01")

    def test_push_status_endpoint(self):
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        resp = client.get("/api/v1/push/status", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("configured", resp.json())

    def test_companion_can_register_and_list_own_push(self):
        from company.schema import COMPANION_SCOPES
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_identity("companion-admin-x", "service", "companion-token", list(COMPANION_SCOPES))
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        headers = {"Authorization": "Bearer companion-token", "Idempotency-Key": "comp-push-1"}
        ok = client.post("/api/v1/push/subscriptions", json={
            "payload": {"endpoint": "https://push.example/phone/1", "keys": {"p256dh": "k", "auth": "a"}}
        }, headers=headers)
        self.assertEqual(ok.status_code, 200)
        listed = client.get("/api/v1/push/subscriptions", headers={"Authorization": "Bearer companion-token"})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["subscriptions"]), 1)

    def test_concurrent_reads_do_not_corrupt_scopes(self):
        import threading
        from company.schema import COMPANION_SCOPES
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_identity("companion-admin-y", "service", "companion-token", list(COMPANION_SCOPES))
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        errors = []

        def hit():
            for _ in range(20):
                r = client.get("/api/v1/projects", headers={"Authorization": "Bearer companion-token"})
                if r.status_code != 200:
                    errors.append(r.status_code)

        threads = [threading.Thread(target=hit) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(errors, [])

    def test_api_notify_push(self):
        from unittest.mock import patch
        from company.service import create_app
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_push_subscription("human-ceo", "https://push.example/sub/3")
        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        with patch("company.push_vapid.send_push", return_value={"status": "applied", "http_status": 201}):
            resp = client.post(
                "/api/v1/push/notify",
                json={"payload": {"subject": "Test ping", "kind": "owner_inbox"}},
                headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "notify-1"},
            )
        self.assertEqual(resp.status_code, 200)
        deliveries = resp.json()["result"]["deliveries"]
        self.assertEqual(deliveries[0]["status"], "applied")

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
