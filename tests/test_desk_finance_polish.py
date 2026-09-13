"""Desk Finance polish — pause gate + openRoom (v0.3.80)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskFinancePolishTests(unittest.TestCase):
    def test_session_pause_gate_markers(self):
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertIn("applyFinancePauseFromSession", DESK_HTML)
        self.assertIn("company.pause", DESK_HTML)
        self.assertRegex(DESK_HTML, r"await\s+applyFinancePauseFromSession\s*\(")
        self.assertEqual(DESK_HTML.count("setFinanceMutateEnabled(true)"), 0)

    def test_open_room_restores_simulated_spend(self):
        self.assertIn("async function openRoom", DESK_HTML)
        idx = DESK_HTML.find("async function openRoom")
        chunk = DESK_HTML[idx : idx + 1200]
        self.assertIn("simulated_spend_cents", chunk)
        self.assertIn("reserved_cents", chunk)

    def test_version_0_3_80(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')


if __name__ == "__main__":
    unittest.main()
