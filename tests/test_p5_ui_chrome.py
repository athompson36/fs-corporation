"""P5 UI chrome: shared tokens, version strip, HQ keyboard."""
import unittest
from pathlib import Path

from company import __version__
from company.service import DESK_HTML, ASSETS_DIR
from tests.test_api import owner_client

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "assets" / "cosmic-glass-tokens.css"
COMPANION_CSS = ROOT / "companion" / "src" / "styles.css"
COMPANION_APP = ROOT / "companion" / "src" / "App.tsx"


class SharedTokensTests(unittest.TestCase):
    def test_tokens_file(self):
        self.assertTrue(TOKENS.is_file())
        text = TOKENS.read_text()
        self.assertIn("--cosmic:", text)
        self.assertIn("--focus-ring:", text)
        self.assertEqual(ASSETS_DIR, TOKENS.parent)

    def test_static_route(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        r = client.get("/static/cosmic-glass-tokens.css")
        self.assertEqual(r.status_code, 200)
        self.assertIn("--cosmic", r.text)

    def test_desk_and_companion_wire_tokens(self):
        self.assertIn('/static/cosmic-glass-tokens.css', DESK_HTML)
        css = COMPANION_CSS.read_text()
        self.assertIn("cosmic-glass-tokens.css", css)
        self.assertNotIn("--midnight: #070b14", css)


class VersionAndKeyboardTests(unittest.TestCase):
    def test_desk_version_and_keyboard(self):
        self.assertIn('id="desk-version"', DESK_HTML)
        self.assertIn("loadDeskVersion", DESK_HTML)
        self.assertIn("enableTileActivation", DESK_HTML)
        self.assertIn("tabindex", DESK_HTML)
        self.assertIn("Enter", DESK_HTML)
        self.assertIn("role", DESK_HTML)

    def test_companion_version_chrome(self):
        app = COMPANION_APP.read_text()
        self.assertIn("app-version", app)
        self.assertIn("backendVersion", app)
        self.assertIn("api.health()", app)

    def test_version_matches_package(self):
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn(f'"{__version__}"', pkg)


if __name__ == "__main__":
    unittest.main()
