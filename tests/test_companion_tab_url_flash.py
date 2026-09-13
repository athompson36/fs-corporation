"""Companion tab/mode URL flash fix (v0.3.81)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"
APP = SRC / "App.tsx"
URL = SRC / "urlState.ts"
HARNESS = ROOT / "companion" / "scripts" / "check-url-state.mts"


class CompanionTabUrlFlashTests(unittest.TestCase):
    def test_url_state_exports_transition_helpers(self):
        text = URL.read_text()
        self.assertRegex(text, r"export function stateAfterTabChange\(")
        self.assertRegex(text, r"export function stateAfterModeChange\(")

    def test_app_select_tab_batches_resets(self):
        text = APP.read_text()
        self.assertRegex(text, r"function selectTab|const selectTab")
        self.assertRegex(
            text,
            r"const selectTab = useCallback\(\(next: Tab\) => \{\s*if \(next === tab\) return;",
            re.S,
        )
        self.assertIn("stateAfterTabChange", text)
        self.assertIn("stateAfterModeChange", text)
        # User tab clicks must not use raw setTab(
        for needle in (
            'onClick={() => setTab("dashboard")}',
            "onClick={() => setTab(t)}",
            "onClick={() => setTab(lastWorkTab)}",
            "onClick={() => setTab(lastMoreTab)}",
            'onClick={() => setTab("organization")}',
            'onClick={() => setTab("finance")}',
            'onOpenDecisions={() => setTab("decisions")}',
            'onOpenInbox={() => setTab("inbox")}',
        ):
            self.assertNotIn(needle, text, f"raw setTab still used: {needle}")

    def test_all_panels_use_batched_mode_handler(self):
        text = APP.read_text()
        self.assertNotIn(
            "onModeChange={setPanelMode}",
            text,
            "mode toggles must use handlePanelModeChange for batched URL state",
        )

    def test_no_tab_or_mode_reset_effects(self):
        text = APP.read_text()
        # Former tab-change effect pattern: tabRef.current === tab early return then setPanelMode("browse")
        self.assertNotRegex(
            text,
            r"if \(tabRef\.current === tab\) return;\s*tabRef\.current = tab;\s*setPanelMode\(\"browse\"\)",
            re.S,
        )
        self.assertNotRegex(
            text,
            r"if \(modeRef\.current === panelMode\) return;\s*modeRef\.current = panelMode;",
            re.S,
        )

    def test_harness_covers_tab_mode_transitions(self):
        text = HARNESS.read_text()
        self.assertIn("stateAfterTabChange", text)
        self.assertIn("stateAfterModeChange", text)
        self.assertIn("org-manage-to-finance", text)
        self.assertIn("finance-manage-to-dashboard", text)
        self.assertIn("corporate-people-to-org", text)
        self.assertIn("finance-periods-to-manage", text)
        self.assertIn("finance-adjustment-to-browse", text)

    def test_version_0_3_81(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.81"', init)
        self.assertIn('"version": "0.3.81"', pkg)


if __name__ == "__main__":
    unittest.main()
