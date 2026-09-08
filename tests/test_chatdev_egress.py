"""ChatDev worker egress allowlist."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company.chatdev_egress import (
    allowlist_status,
    container_network_args,
    load_https_hosts,
    url_allowed,
)
from company.core import Company
from company.settings_catalog import validate_value
from tests.test_core import install, policy


class ChatDevEgressTests(unittest.TestCase):
    def test_catalog_enum(self):
        self.assertEqual(validate_value("FS_CORP_CHATDEV_WORKER_EGRESS", "allowlist"), "allowlist")
        with self.assertRaises(ValueError):
            validate_value("FS_CORP_CHATDEV_WORKER_EGRESS", "bridge")

    def test_load_and_url_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "allow.json"
            path.write_text(json.dumps({"https_hosts": ["api.anthropic.com", "Example.COM"]}))
            hosts = load_https_hosts(path)
            self.assertEqual(hosts, ["api.anthropic.com", "example.com"])
            self.assertTrue(url_allowed("https://api.anthropic.com/v1", hosts))
            self.assertTrue(url_allowed("https://example.com/x", hosts))
            self.assertFalse(url_allowed("http://api.anthropic.com/v1", hosts))
            self.assertFalse(url_allowed("https://evil.example/x", hosts))

    def test_rejects_url_shaped_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"https_hosts": ["https://api.anthropic.com"]}))
            with self.assertRaises(ValueError):
                load_https_hosts(path)

    def test_status_not_ready_by_default(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE", None)
            os.environ.pop("FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK", None)
            os.environ.pop("FS_CORP_CHATDEV_WORKER_EGRESS", None)
            st = allowlist_status(c)
        self.assertEqual(st["worker_egress_mode"], "none")
        self.assertFalse(st["allowlist_configured"])
        self.assertFalse(st["worker_egress_ready"])
        self.assertEqual(container_network_args(c), ["--network", "none"])

    def test_ready_requires_mode_file_and_docker_network(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "allow.json"
            path.write_text(json.dumps({"https_hosts": ["api.anthropic.com"]}))
            c.patch_company_settings("human-ceo", {"FS_CORP_CHATDEV_WORKER_EGRESS": "allowlist"})
            with patch.dict(
                os.environ,
                {
                    "FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE": str(path),
                    "FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK": "fs-corp-chatdev-egress",
                },
                clear=False,
            ):
                st = allowlist_status(c)
                self.assertTrue(st["worker_egress_ready"])
                self.assertEqual(st["allowlist_count"], 1)
                self.assertEqual(
                    container_network_args(c),
                    ["--network", "fs-corp-chatdev-egress"],
                )


if __name__ == "__main__":
    unittest.main()
