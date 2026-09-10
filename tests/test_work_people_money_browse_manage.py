"""Work/People/Money Browse–Manage structure (v0.3.66)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class WorkPeopleMoneyBrowseManageTests(unittest.TestCase):
    def test_mode_switch_module(self):
        text = (SRC / "ModeSwitch.tsx").read_text()
        self.assertIn("browse", text)
        self.assertIn("manage", text)
        self.assertIn("export function ModeSwitch", text)

    def test_projects_panel_browse_manage(self):
        text = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("Browse", text)
        self.assertIn("Manage", text)
        self.assertIn("Local candidates", text)

    def test_corporate_panel_browse_manage(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("CEO scorecard", text)

    def test_org_panel_browse_manage(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("organization", text.lower())  # props or copy

    def test_workers_panel_uses_mode_switch(self):
        text = (SRC / "WorkersPanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)

    def test_finance_has_no_nested_browse_manage(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertNotIn("ModeSwitch", text)
        self.assertIn("Overview", text)
        self.assertIn("Create invoice", text)

    def test_app_wires_extracted_panels(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("ProjectsPanel", text)
        self.assertIn("CorporatePanel", text)
        self.assertIn("OrgPanel", text)
        # Projects JSX must not remain inline as the old section opener alone
        self.assertNotIn('tab === "projects" && (\n        <section>', text)
