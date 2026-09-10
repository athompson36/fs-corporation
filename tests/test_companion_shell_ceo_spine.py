"""Companion shell + CEO spine (v0.3.65) — source and static contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompanionShellCeoSpineTests(unittest.TestCase):
    def test_brand_fonts_css_exists_and_faces(self):
        css = (ROOT / "assets" / "brand-fonts.css").read_text()
        self.assertIn('font-family: "Syne"', css)
        self.assertIn('font-family: "Manrope"', css)
        self.assertIn("/static/fonts/syne-latin-700-normal.woff2", css)
        self.assertIn("/static/fonts/manrope-latin-400-normal.woff2", css)
        self.assertIn("/static/fonts/manrope-latin-600-normal.woff2", css)

    def test_tokens_declare_font_vars(self):
        tokens = (ROOT / "assets" / "cosmic-glass-tokens.css").read_text()
        self.assertIn("--font-display", tokens)
        self.assertIn("--font-body", tokens)

    def test_companion_imports_brand_fonts(self):
        css = (ROOT / "companion" / "src" / "styles.css").read_text()
        self.assertIn("brand-fonts.css", css)
        self.assertIn("var(--font-display)", css)
        self.assertIn("var(--font-body)", css)

    def test_desk_and_welcome_link_brand_fonts(self):
        from company.service import DESK_HTML, WELCOME_HTML

        self.assertIn("/static/brand-fonts.css", DESK_HTML)
        self.assertIn("/static/brand-fonts.css", WELCOME_HTML)
        self.assertIn("var(--font-display)", DESK_HTML)
        # welcome may use Manrope via CSS file; brand link is required

    def test_static_brand_fonts_route(self):
        from tests.test_api import owner_client

        c, client = owner_client()
        self.addCleanup(c.close)
        r = client.get("/static/brand-fonts.css")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Syne", r.text)

    def test_home_panel_module_exists(self):
        path = ROOT / "companion" / "src" / "HomePanel.tsx"
        self.assertTrue(path.is_file())
        text = path.read_text()
        self.assertIn("Needs you", text)
        self.assertIn("View all", text)


if __name__ == "__main__":
    unittest.main()
