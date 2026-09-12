"""Projects list-row span fix + Clear on loading (v0.3.72)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ProjectsListRowClearLoadingTests(unittest.TestCase):
    def test_list_row_uses_span_muted_not_div(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        # Extract the list map button body roughly between list-row and project-browse-detail
        list_part = text.split("project-browse-list", 1)[1].split("project-browse-detail", 1)[0]
        self.assertIn('className="muted"', list_part)
        self.assertIn("<span className=\"muted\">", list_part)
        self.assertNotIn("<div className=\"muted\">", list_part)
        self.assertIn("list-row", list_part)

    def test_loading_card_has_clear_selection_toolbar(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        # Loading branch sits between empty pane and loaded detail
        loading = text.split("selectedProject && !projectDetail", 1)[1].split(
            "selectedProject && projectDetail", 1
        )[0]
        self.assertIn("detail-toolbar", loading)
        self.assertIn("Clear selection", loading)
        self.assertIn("Loading…", loading)
        self.assertIn("setSelectedProject(null)", loading)
        # Empty pane must not gain Clear
        empty = text.split("!selectedProject", 1)[1].split("selectedProject && !projectDetail", 1)[0]
        self.assertIn("Select a project", empty)
        self.assertNotIn("Clear selection", empty)

    def test_list_row_muted_display_block(self):
        css = (SRC / "styles.css").read_text()
        self.assertRegex(
            css,
            r"\.list-row\s+\.muted\s*\{[^}]*display:\s*block",
        )

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
