import os
import unittest
from datetime import timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from company.adapters import TailscaleAdapter
from company.core import Company, now
from company.schema import COMPANION_SCOPES
from company.service import create_app
from tests.test_core import install, policy


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.client = TestClient(create_app(self.c))

    def _issue_and_redeem(self, access_level="admin"):
        created = self.client.post(
            "/api/v1/remote-access/pairing",
            json={"payload": {"access_level": access_level}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": f"pair-{access_level}-{now().isoformat()}"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        body = created.json()["result"]
        self.assertEqual(body["access_level"], access_level)
        redeemed = self.client.post("/api/v1/remote-access/redeem", json={"payload": {"ticket": body["ticket"]}})
        self.assertEqual(redeemed.status_code, 200, redeemed.text)
        return redeemed.json()

    def test_pairing_qr_redeems_companion_token_once(self):
        created = self.client.post(
            "/api/v1/remote-access/pairing",
            json={"payload": {"access_level": "admin"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "pair-1"},
        )
        self.assertEqual(created.status_code, 200)
        body = created.json()["result"]
        self.assertIn("#fs-pair=", body["pair_url"])
        self.assertIn("<svg", body["qr_svg"])
        self.assertFalse(body["contains_owner_token"])
        self.assertNotIn("owner-token", body["qr_svg"])
        self.assertNotIn("owner-token", body["ticket"])
        self.assertEqual(body["access_level"], "admin")
        ticket = body["ticket"]
        redeemed = self.client.post("/api/v1/remote-access/redeem", json={"payload": {"ticket": ticket}})
        self.assertEqual(redeemed.status_code, 200)
        data = redeemed.json()
        self.assertTrue(data["token"])
        self.assertNotEqual(data["token"], "owner-token")
        self.assertTrue(data["principal_id"].startswith("companion-admin-"))
        self.assertIn("company.read", data["scopes"])
        self.assertEqual(data["access_level"], "admin")
        ident = self.c.identity_for_token(data["token"])
        self.assertEqual(ident["kind"], "service")
        again = self.client.post("/api/v1/remote-access/redeem", json={"payload": {"ticket": ticket}})
        self.assertEqual(again.status_code, 422)

    def test_head_cannot_issue_pairing_and_unknown_ticket_fails(self):
        self.c.register_identity("head-svc", "service", "head-token", ["company.read"])
        denied = self.client.post(
            "/api/v1/remote-access/pairing",
            json={"payload": {}},
            headers={"Authorization": "Bearer head-token", "Idempotency-Key": "pair-no"},
        )
        self.assertEqual(denied.status_code, 403)
        missing = self.client.post("/api/v1/remote-access/redeem", json={"payload": {"ticket": "nope"}})
        self.assertEqual(missing.status_code, 422)

    def test_expired_ticket_rejected(self):
        issued = self.c.create_pairing_ticket("human-ceo", "https://192.168.4.100")
        self.c.db.execute(
            "UPDATE pairing_tickets SET expires_at=? WHERE id=?",
            ((now() - timedelta(minutes=1)).isoformat(), issued["id"]),
        )
        with self.assertRaises(ValueError):
            self.c.redeem_pairing_ticket(issued["ticket"])

    def test_tailscale_join_stays_fail_closed_without_auth_key(self):
        os.environ.pop("FS_CORP_TAILSCALE_AUTHKEY", None)
        status = self.c.remote_access_status("https://192.168.4.100")
        self.assertEqual(status["vpn"], "tailscale")
        self.assertFalse(status["auth_key_configured"])
        self.assertEqual(len(status["pairing_levels"]), 3)
        issued = self.c.create_pairing_ticket("human-ceo", "https://192.168.4.100")
        self.assertNotIn("tailscale_auth_key", issued)
        redeemed = self.c.redeem_pairing_ticket(issued["ticket"])
        self.assertNotIn("tailscale_auth_key", redeemed)
        self.assertEqual(redeemed["vpn"]["status"], "live_unavailable")
        with self.assertRaises(NotImplementedError):
            TailscaleAdapter().join({"auth_key": "tskey-not-used"})

    def test_auth_key_is_only_released_on_redeem(self):
        os.environ["FS_CORP_TAILSCALE_AUTHKEY"] = "tskey-auth-test-only"
        self.addCleanup(lambda: os.environ.pop("FS_CORP_TAILSCALE_AUTHKEY", None))
        issued = self.c.create_pairing_ticket("human-ceo", "https://192.168.4.100", access_level="read_only")
        self.assertNotIn("tskey-auth-test-only", issued["qr_svg"])
        self.assertNotIn("tskey-auth-test-only", issued["pair_url"])
        redeemed = self.c.redeem_pairing_ticket(issued["ticket"])
        self.assertEqual(redeemed["tailscale_auth_key"], "tskey-auth-test-only")
        self.assertEqual(redeemed["vpn"]["status"], "configured")
        self.assertEqual(redeemed["access_level"], "read_only")

    def test_unknown_access_level_rejected(self):
        r = self.client.post(
            "/api/v1/remote-access/pairing",
            json={"payload": {"access_level": "superuser"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "pair-bad"},
        )
        self.assertEqual(r.status_code, 422)

    def test_remote_access_lists_pairing_levels(self):
        r = self.client.get("/api/v1/remote-access", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(r.status_code, 200)
        levels = r.json()["pairing_levels"]
        self.assertEqual(len(levels), 3)
        self.assertEqual({l["id"] for l in levels}, {"read_only", "user", "admin"})

    def test_read_only_cannot_approve(self):
        pid = self.c.propose_policy("head", policy(self.c), "read only test")
        data = self._issue_and_redeem("read_only")
        self.assertNotIn("policy.approve", data["scopes"])
        r = self.client.post(
            f"/api/v1/policy-proposals/{pid}/decision",
            json={"payload": {"decision": "approved", "reason": "nope"}},
            headers={"Authorization": f"Bearer {data['token']}", "Idempotency-Key": "ro-approve"},
        )
        self.assertEqual(r.status_code, 403)

    def test_user_can_escalate_cannot_pause(self):
        data = self._issue_and_redeem("user")
        self.assertIn("owner.escalate", data["scopes"])
        self.assertNotIn("company.pause", data["scopes"])
        esc = self.client.post(
            "/api/v1/owner-inbox",
            json={"payload": {
                "department_id": "engineering",
                "kind": "escalation",
                "subject": "Help",
                "body": "Need CEO",
            }},
            headers={"Authorization": f"Bearer {data['token']}", "Idempotency-Key": "user-esc"},
        )
        self.assertEqual(esc.status_code, 200)
        pause = self.client.post(
            "/api/v1/company/pause",
            json={"payload": {}},
            headers={"Authorization": f"Bearer {data['token']}", "Idempotency-Key": "user-pause"},
        )
        self.assertEqual(pause.status_code, 403)

    def test_admin_full_companion_scopes(self):
        data = self._issue_and_redeem("admin")
        self.assertEqual(set(data["scopes"]), set(COMPANION_SCOPES))

    def test_ticket_stores_access_level_redeem_ignores_client_tamper(self):
        issued = self.c.create_pairing_ticket("human-ceo", "https://192.168.4.100", access_level="read_only")
        row = self.c.db.execute("SELECT access_level FROM pairing_tickets WHERE id=?", (issued["id"],)).fetchone()
        self.assertEqual(row["access_level"], "read_only")
        redeemed = self.client.post(
            "/api/v1/remote-access/redeem",
            json={"payload": {"ticket": issued["ticket"], "access_level": "admin"}},
        )
        self.assertEqual(redeemed.status_code, 200)
        self.assertEqual(redeemed.json()["access_level"], "read_only")
        self.assertNotIn("policy.approve", redeemed.json()["scopes"])


if __name__ == "__main__":
    unittest.main()
