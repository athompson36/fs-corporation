import json
import math
import os
import unittest
from unittest.mock import patch

from company.core import Company, canonical
from company.settings_catalog import EDITABLE_KEYS, READONLY_KEYS, validate_value
from company.settings_runtime import effective, list_settings, secrets_status
from tests.test_api import owner_client
from tests.test_core import install, policy


class CatalogTests(unittest.TestCase):
    def test_validate_and_unknown(self):
        self.assertEqual(validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", 14), 14)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", 0)
        with self.assertRaises(ValueError):
            validate_value("NOT_A_KEY", 1)

    def test_rate_limit_window_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_RATE_LIMIT_WINDOW_SEC", 0)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_RATE_LIMIT_WINDOW_SEC", -1.0)
        self.assertEqual(validate_value("FS_CORP_RATE_LIMIT_WINDOW_SEC", 60.0), 60.0)

    def test_validate_rejects_wrong_types(self):
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", True)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", 3.5)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_SSE_IDLE_SEC", True)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_IDEMPOTENCY_RETENTION_DAYS", "3.5")

    def test_string_rejects_non_str(self):
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_PUBLIC_URL", True)
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_PUBLIC_URL", {"url": "x"})
        self.assertEqual(validate_value("FS_CORP_PUBLIC_URL", ""), "")
        self.assertEqual(validate_value("FS_CORP_PUBLIC_URL", "https://x"), "https://x")

    def test_float_rejects_nan_and_inf(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    validate_value("FS_CORP_RATE_LIMIT_WINDOW_SEC", bad)
                with self.assertRaises(ValueError):
                    validate_value("FS_CORP_SSE_IDLE_SEC", bad)
        self.assertTrue(math.isfinite(validate_value("FS_CORP_SSE_IDLE_SEC", 1.0)))

    def test_bool_garbage_env_rejected(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        with patch.dict(os.environ, {"CHATDEV_ALLOW_CONTROL_PLANE": "maybe"}, clear=False):
            with self.assertRaises(ValueError):
                effective(c, "CHATDEV_ALLOW_CONTROL_PLANE")

    def test_malformed_overlay_rejected(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        with c.tx():
            c.db.execute(
                "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                (
                    "FS_CORP_IDEMPOTENCY_RETENTION_DAYS",
                    json.dumps(True),
                    "2026-09-07T00:00:00+00:00",
                    "human-ceo",
                ),
            )
        with self.assertRaises(ValueError):
            effective(c, "FS_CORP_IDEMPOTENCY_RETENTION_DAYS")

    def test_effective_overlay_wins(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        with patch.dict(os.environ, {"FS_CORP_SSE_IDLE_SEC": "9"}, clear=False):
            env_hit = effective(c, "FS_CORP_SSE_IDLE_SEC")
            self.assertEqual(env_hit["source"], "env")
            self.assertEqual(env_hit["value"], 9.0)
            with c.tx():
                c.db.execute(
                    "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                    (
                        "FS_CORP_SSE_IDLE_SEC",
                        canonical(2.5),
                        "2026-09-07T00:00:00+00:00",
                        "human-ceo",
                    ),
                )
            over = effective(c, "FS_CORP_SSE_IDLE_SEC")
            self.assertEqual(over["source"], "overlay")
            self.assertEqual(over["value"], 2.5)
        items = list_settings(c)
        keys = {i["key"] for i in items}
        self.assertIn("FS_CORP_SSE_IDLE_SEC", keys)
        self.assertIn("FS_CORP_LAN_IP", keys)
        self.assertTrue(EDITABLE_KEYS.issubset(keys))
        self.assertTrue(READONLY_KEYS.issubset(keys))
        with patch.dict(os.environ, {"MODEL_PROVIDER_API_KEY": "sekrit"}, clear=False):
            rows = secrets_status()
        names = {r["name"] for r in rows}
        self.assertIn("MODEL_PROVIDER_API_KEY", names)
        hit = next(r for r in rows if r["name"] == "MODEL_PROVIDER_API_KEY")
        self.assertTrue(hit["configured"])
        self.assertEqual(set(hit.keys()), {"name", "configured"})


class SettingsApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.h = {"Authorization": "Bearer owner-token"}

    def _pair(self, access_level):
        issued = self.c.create_pairing_ticket(
            "human-ceo", "https://192.168.4.100", access_level=access_level
        )
        return self.c.redeem_pairing_ticket(issued["ticket"])["token"]

    def test_get_patch_reset(self):
        g = self.client.get("/api/v1/settings", headers=self.h)
        self.assertEqual(g.status_code, 200, g.text)
        keys = {i["key"] for i in g.json()["items"]}
        self.assertIn("FS_CORP_SSE_IDLE_SEC", keys)
        self.assertIn("FS_CORP_LAN_IP", keys)
        p = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"FS_CORP_SSE_IDLE_SEC": 2}}},
            headers={**self.h, "Idempotency-Key": "set-1"},
        )
        self.assertEqual(p.status_code, 200, p.text)
        item = p.json()["result"]["items"][0]
        self.assertEqual(item["value"], 2.0)
        self.assertEqual(item["source"], "overlay")
        r = self.client.post(
            "/api/v1/settings/reset",
            json={"payload": {"keys": ["FS_CORP_SSE_IDLE_SEC"]}},
            headers={**self.h, "Idempotency-Key": "set-reset"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotEqual(r.json()["result"]["items"][0]["source"], "overlay")

    def test_unknown_key_422(self):
        p = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"NOT_A_KEY": 1}}},
            headers={**self.h, "Idempotency-Key": "bad"},
        )
        self.assertEqual(p.status_code, 422)

    def test_write_routes_reject_unknown_fields(self):
        patch_response = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"FS_CORP_SSE_IDLE_SEC": 2}, "extra": True}},
            headers={**self.h, "Idempotency-Key": "patch-extra"},
        )
        self.assertEqual(patch_response.status_code, 422)
        reset_response = self.client.post(
            "/api/v1/settings/reset",
            json={"payload": {"all_overlay": True, "extra": True}},
            headers={**self.h, "Idempotency-Key": "reset-extra"},
        )
        self.assertEqual(reset_response.status_code, 422)

    def test_secrets_status(self):
        s = self.client.get("/api/v1/settings/secrets-status", headers=self.h)
        self.assertEqual(s.status_code, 200)
        for row in s.json()["secrets"]:
            self.assertEqual(set(row.keys()), {"name", "configured"})

    def test_paired_admin_allowed_and_companion_user_denied(self):
        admin_token = self._pair("admin")
        allowed = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"FS_CORP_SSE_IDLE_SEC": 3}}},
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Idempotency-Key": "admin-settings",
            },
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)

        user_token = self._pair("user")
        denied = self.client.patch(
            "/api/v1/settings",
            json={"payload": {"updates": {"FS_CORP_SSE_IDLE_SEC": 4}}},
            headers={
                "Authorization": f"Bearer {user_token}",
                "Idempotency-Key": "user-settings",
            },
        )
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
