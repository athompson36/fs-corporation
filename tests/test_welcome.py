"""Public /welcome landing page."""
import unittest
from pathlib import Path

from tests.test_api import owner_client


class WelcomeTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_welcome_is_public_html(self):
        # no Authorization header
        r = self.client.get("/welcome")
        self.assertEqual(r.status_code, 200)
        text = r.text
        self.assertIn("FS-Corporation", text)
        self.assertIn('href="/"', text)
        self.assertIn('href="/desk"', text)
        self.assertIn("/static/cosmic-glass-tokens.css", text)
        self.assertIn("offline", text.lower())  # support line mentions offline starter

    def test_welcome_exempt_from_auth(self):
        from company.rate_limit import EXEMPT_PATHS
        self.assertIn("/welcome", EXEMPT_PATHS)

    def test_welcome_deeper_craft(self):
        r = self.client.get("/welcome")
        text = r.text
        self.assertIn("/static/welcome.css", text)
        self.assertIn("/static/fonts/", text)
        self.assertIn("constellation", text.lower())
        self.assertIn("FS-Corporation", text)
        self.assertIn('href="/"', text)
        self.assertIn('href="/desk"', text)

        css = self.client.get("/static/welcome.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn("prefers-reduced-motion", css.text)

    def test_welcome_font_files_exist(self):
        root = Path(__file__).resolve().parents[1] / "assets" / "fonts"
        woffs = list(root.glob("*.woff2"))
        self.assertGreaterEqual(len(woffs), 2, "need display + text woff2")


class WelcomeCaddyTests(unittest.TestCase):
    def test_caddyfile_proxies_welcome(self):
        text = (Path(__file__).resolve().parents[1] / "deploy/fs-dev/Caddyfile").read_text()
        self.assertIn("handle /welcome", text)
        self.assertIn("reverse_proxy 127.0.0.1:8000", text)
