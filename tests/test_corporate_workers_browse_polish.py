"""Corporate + Workers Browse consistency (v0.3.69)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _section_head_wraps_h2(text: str, title: str) -> bool:
    """True if an h2 with this title appears inside a section-head div."""
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class CorporateWorkersBrowsePolishTests(unittest.TestCase):
    def test_corporate_browse_section_heads(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in (
            "Objectives",
            "Industry packs",
            "Divisions",
            "Pending promotions",
            "Staffing proposals",
            "Cross-department requests",
            "Open activity",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"Corporate Browse missing section-head for {title!r}",
            )
        self.assertIn("panel-empty", text)
        self.assertIn("CEO scorecard", text)

    def test_workers_section_head_outside_card(self):
        text = (SRC / "WorkersPanel.tsx").read_text()
        self.assertTrue(_section_head_wraps_h2(text, "Worker hosts"))
        # section-head must appear before the Browse list card that contains hosts.map
        head_at = text.find('className="section-head"')
        hosts_card_at = text.find("{hosts.map")
        self.assertGreaterEqual(head_at, 0)
        self.assertGreaterEqual(hosts_card_at, 0)
        self.assertLess(
            head_at,
            hosts_card_at,
            "Worker hosts section-head must precede hosts.map",
        )
        # Title should not be nested inside the first card of browse in the old way:
        # after ModeSwitch browse block, section-head comes before `<div className="card">`
        browse = text.split('mode === "browse"')[1].split('mode === "manage"')[0]
        self.assertRegex(
            browse,
            r'section-head[\s\S]*?<div className="card">',
            "section-head should appear before the Browse card",
        )
        self.assertIn("panel-empty", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.69"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.69"', pkg)
