"""Corporate Browse clusters + Manage title polish (v0.3.71)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _cluster_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="cluster-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


def _section_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class CorporateBrowseClustersTests(unittest.TestCase):
    def test_browse_cluster_heads_and_narrow_tablist(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in ("Strategy", "Structure", "People", "Coordination"):
            self.assertTrue(
                _cluster_head_wraps_h2(text, title),
                f"CorporatePanel missing cluster-head for {title!r}",
            )
        self.assertIn('aria-label="Corporate clusters"', text)
        self.assertIn('from "./useWideViewport"', text)
        hook = (SRC / "useWideViewport.ts").read_text()
        self.assertIn('matchMedia("(min-width: 720px)")', hook)
        self.assertIn("panel-empty", text)
        self.assertIn("ModeSwitch", text)
        # Existing list titles remain section-heads
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
                f"CorporatePanel missing section-head for {title!r}",
            )

    def test_manage_section_heads(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        for title in (
            "Corporate operations",
            "Create objective",
            "Propose division",
            "Create cross-department request",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"CorporatePanel Manage missing section-head for {title!r}",
            )

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')

    def test_cluster_head_css_present(self):
        css = (SRC / "styles.css").read_text()
        self.assertIn(".cluster-head", css)
