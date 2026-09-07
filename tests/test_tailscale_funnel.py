import os
import unittest
from unittest.mock import patch

from company.tailscale_funnel import parse_funnel_public_url, probe_funnel_webhooks


class TailscaleFunnelTests(unittest.TestCase):
    def test_parse_web_handlers(self):
        data = {
            "Web": {
                "fs-dev.tail824ab1.ts.net:443": {
                    "Handlers": {
                        "/api/v1/github/webhooks": {"Proxy": "http://127.0.0.1:8000/api/v1/github/webhooks"},
                    }
                }
            }
        }
        url = parse_funnel_public_url(data)
        self.assertEqual(url, "https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks")

    def test_parse_empty(self):
        self.assertIsNone(parse_funnel_public_url({}))
        self.assertIsNone(parse_funnel_public_url(None))

    def test_opt_in_alone_does_not_advertise(self):
        with patch.dict(os.environ, {"FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS": "1"}, clear=False):
            self.assertIsNone(parse_funnel_public_url({}, self_dns_name="fs-dev.tail824ab1.ts.net"))

    def test_probe_fail_closed_without_cli(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("company.tailscale_funnel.shutil.which", return_value=None):
                status = probe_funnel_webhooks()
        self.assertFalse(status["opt_in"])
        self.assertEqual(status["cli"], "live_unavailable")
        self.assertIsNone(status["public_url"])

    def test_probe_uses_env_url(self):
        with patch.dict(os.environ, {
            "FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS": "1",
            "FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL": "https://fs-dev.example.ts.net/api/v1/github/webhooks",
        }, clear=False):
            with patch("company.tailscale_funnel.shutil.which", return_value=None):
                status = probe_funnel_webhooks()
        self.assertTrue(status["opt_in"])
        self.assertEqual(status["public_url"], "https://fs-dev.example.ts.net/api/v1/github/webhooks")


if __name__ == "__main__":
    unittest.main()
