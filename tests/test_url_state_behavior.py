"""Behavioral urlState parse/serialize via tsx harness (v0.3.79)."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "companion" / "scripts" / "check-url-state.mts"


class UrlStateBehaviorTests(unittest.TestCase):
    def test_check_url_state_harness(self):
        self.assertTrue(HARNESS.is_file(), f"missing harness {HARNESS}")
        npx = shutil.which("npx")
        self.assertIsNotNone(npx, "npx not found — install Node.js to run companion URL harness")
        result = subprocess.run(
            [npx, "--yes", "tsx", str(HARNESS)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            self.fail(
                "urlState harness failed\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
