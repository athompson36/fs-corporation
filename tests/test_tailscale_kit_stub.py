"""Source assertions for TailscaleKit stub honesty."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "companion-native" / "tailscale_kit.ts"
README = ROOT / "companion-native" / "README.md"


class TailscaleKitStubTests(unittest.TestCase):
    def test_stub_exports_not_implemented(self):
        text = KIT.read_text()
        self.assertIn("isTailscaleKitAvailable", text)
        self.assertIn("return false", text)
        self.assertIn("joinWithAuthKey", text)
        self.assertIn("not_implemented", text)

    def test_readme_documents_future_path(self):
        text = README.read_text()
        self.assertIn("TailscaleKit", text)
        self.assertIn("tailscale_kit.ts", text)
        self.assertIn("clipboard", text.lower())


if __name__ == "__main__":
    unittest.main()
