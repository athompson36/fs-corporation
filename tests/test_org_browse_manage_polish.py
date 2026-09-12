"""Org Browse + Manage title consistency (v0.3.70)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


def _section_head_wraps_h2(text: str, title: str) -> bool:
    pattern = (
        r'<div className="section-head">\s*'
        r"<h2>" + re.escape(title) + r"</h2>\s*"
        r"</div>"
    )
    return re.search(pattern, text) is not None


class OrgBrowseManagePolishTests(unittest.TestCase):
    def test_org_browse_and_manage_section_heads(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        for title in (
            "Departments",
            "Head inbox",
            "Create department",
            "Appoint department head",
            "Vacate department head",
            "Assign position",
            "Release assignment",
            "Create position",
            "Reorder departments",
            "Activate dormant department for project",
            "Worker card",
        ):
            self.assertTrue(
                _section_head_wraps_h2(text, title),
                f"OrgPanel missing section-head for {title!r}",
            )
        self.assertIn("panel-empty", text)
        self.assertIn("ModeSwitch", text)
        self.assertIn("assign-dispatch", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
