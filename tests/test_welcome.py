"""Public /welcome landing page."""
import unittest
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
