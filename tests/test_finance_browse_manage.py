"""Finance Browse/Manage + URL sync (v0.3.77)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class FinanceBrowseManageTests(unittest.TestCase):
    def test_url_state_finance_mode_capable_and_groups(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn('"finance"', text)
        self.assertIn("MODE_CAPABLE_TABS", text)
        self.assertIn("defaultGroupFor", text)
        self.assertIn('"overview"', text)
        self.assertIn('"invoices"', text)
        self.assertIn('"adjustments"', text)
        self.assertIn('"periods"', text)
        self.assertIn('"invoice"', text)
        self.assertIn('"adjustment"', text)
        self.assertIn('"period"', text)
        # finance writes group in browse — look for finance-specific serialize path
        self.assertRegex(text, r"tab\s*===\s*[\"']finance[\"']")

    def test_finance_panel_mode_switch_and_clusters(self):
        text = (SRC / "FinancePanel.tsx").read_text()
        self.assertIn("ModeSwitch", text)
        self.assertIn("ManageClusters", text)
        self.assertIn('label="Finance mode"', text)
        self.assertIn('ariaLabel="Finance browse groups"', text)
        self.assertIn('ariaLabel="Finance manage groups"', text)
        for title in ("Overview", "Invoices", "Adjustments", "Periods"):
            self.assertIn(f'label: "{title}"', text)
        for title in ("Invoice", "Adjustment", "Period"):
            # Manage cluster-head labels — use Create invoice style section heads inside
            pass
        self.assertIn('label: "Invoice"', text)
        self.assertIn('label: "Adjustment"', text)
        self.assertIn('label: "Period"', text)
        self.assertNotIn("not a second Browse/Manage layer", text)
        self.assertIn("manageGroup", text)
        self.assertIn("onManageGroupChange", text)
        self.assertIn("onModeChange", text)

    def test_app_wires_finance_controlled_props(self):
        text = (SRC / "App.tsx").read_text()
        # FinancePanel call site must pass mode/group handlers
        idx = text.find("<FinancePanel")
        self.assertGreaterEqual(idx, 0)
        snippet = text[idx : idx + 800]
        self.assertIn("mode={panelMode}", snippet)
        self.assertIn("onModeChange=", snippet)
        self.assertIn("manageGroup={manageGroup}", snippet)
        self.assertIn("onManageGroupChange=", snippet)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.77"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.77"', pkg)
