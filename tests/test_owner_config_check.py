import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_owner_config", ROOT / "scripts" / "check_owner_config.py")
coc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(coc)


class OwnerConfigCheckTests(unittest.TestCase):
    def test_missing_required_reports_github_not_ready(self):
        env = {k: "" for _, k, _, _ in coc.CHECKS}
        self.assertFalse(all(coc.file_configured(env, k) for k in (
            "GITHUB_APP_ID", "GITHUB_INSTALLATION_ID", "GITHUB_PRIVATE_KEY_FILE")))

    def test_env_file_load_and_key_file_detection(self):
        with tempfile.TemporaryDirectory() as d:
            key_path = Path(d) / "github.pem"
            key_path.write_text("fake-key")
            env_file = Path(d) / "secrets.env"
            env_file.write_text(
                "GITHUB_APP_ID=123\n"
                "GITHUB_INSTALLATION_ID=456\n"
                f"GITHUB_PRIVATE_KEY_FILE={key_path}\n"
                "MODEL_PROVIDER_API_KEY=sk-test\n"
            )
            env = coc.load_env_file(env_file)
            self.assertEqual(env["GITHUB_APP_ID"], "123")
            self.assertTrue(coc.file_configured(env, "GITHUB_PRIVATE_KEY_FILE"))
            self.assertTrue(coc.file_configured(env, "MODEL_PROVIDER_API_KEY"))

    def test_main_exits_zero(self):
        old = sys.argv
        sys.argv = ["check_owner_config.py"]
        try:
            self.assertEqual(coc.main(), 0)
        finally:
            sys.argv = old


if __name__ == "__main__":
    unittest.main()
