import json
import os
import unittest
from unittest.mock import patch

from company.core import Company, canonical
from company.settings_catalog import EDITABLE_KEYS, READONLY_KEYS, validate_value
from company.settings_runtime import effective, list_settings, secrets_status
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


if __name__ == "__main__":
    unittest.main()
