"""Companion finance URL polish (v0.3.79)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class CompanionFinanceUrlPolishTests(unittest.TestCase):
    def test_finance_close_period_no_dead_focus(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        # closePeriod must not focus Manage period input or force group=periods
        close_idx = text.find("async function closePeriod")
        self.assertGreater(close_idx, -1)
        # slice until next top-level async function or export end — use next "async function"
        rest = text[close_idx:]
        next_fn = rest.find("\n  async function ", 10)
        next_fn2 = rest.find("\n  function ", 10)
        ends = [i for i in (next_fn, next_fn2) if i > 0]
        chunk = rest[: min(ends)] if ends else rest[:800]
        self.assertNotIn("periodStartRef.current?.focus", chunk)
        self.assertNotIn('onManageGroupChange("periods")', chunk)
        self.assertIn("period_end", chunk)

    def test_app_cold_load_and_popstate_use_default_group_for(self):
        text = (SRC / "App.tsx").read_text()
        self.assertRegex(
            text,
            r"initialUrl\.group\s*\?\?\s*defaultGroupFor\(\s*initialUrl\.tab\s*,\s*initialUrl\.mode\s*\)",
        )
        self.assertRegex(
            text,
            r"parsed\.group\s*\?\?\s*defaultGroupFor\(\s*parsed\.tab\s*,\s*parsed\.mode\s*\)",
        )
        # Must not keep manage-biased cold-load fallback as the primary path
        self.assertNotRegex(
            text,
            r"initialUrl\.group\s*\?\?\s*defaultManageGroup\(\s*initialUrl\.tab\s*\)",
        )
        self.assertNotRegex(
            text,
            r"parsed\.group\s*\?\?\s*defaultManageGroup\(\s*parsed\.tab\s*\)",
        )

    def test_version_0_3_79(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.79"', init)
        self.assertIn('"version": "0.3.79"', pkg)


if __name__ == "__main__":
    unittest.main()
