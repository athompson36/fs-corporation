"""Projects Browse split + shell polish (v0.3.68)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ProjectsSplitBrowsePolishTests(unittest.TestCase):
    def test_projects_browse_split_markers(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("project-browse-split", text)
        self.assertIn("project-browse-list", text)
        self.assertIn("project-browse-detail", text)
        self.assertIn("Select a project", text)
        self.assertIn("Clear selection", text)
        self.assertNotIn("← Back", text)
        self.assertIn("Local candidates", text)  # Manage preserved
        self.assertIn("Assign GitHub", text)

    def test_styles_have_split_and_empty(self):
        css = (SRC / "styles.css").read_text()
        self.assertIn(".project-browse-split", css)
        self.assertIn(".panel-empty", css)
        self.assertIn(".list-row", css)

    def test_sibling_panels_have_empty_or_section_polish(self):
        for name in ("CorporatePanel.tsx", "WorkersPanel.tsx", "OrgPanel.tsx"):
            text = (SRC / name).read_text()
            self.assertTrue(
                "panel-empty" in text or "section-head" in text,
                f"{name} should use panel-empty or section-head",
            )

    def test_finance_still_has_no_mode_switch(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertNotIn("ModeSwitch", text)
        self.assertNotIn("panel-mode", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.68"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.68"', pkg)
