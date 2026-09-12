"""Mode/cluster/group companion URL sync (v0.3.76)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class ModeClusterGroupUrlSyncTests(unittest.TestCase):
    def test_url_state_exports_mode_cluster_group(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn("mode", text)
        self.assertIn("cluster", text)
        self.assertIn("group", text)
        self.assertIn("PanelMode", text)
        self.assertIn('"browse"', text)
        self.assertIn('"manage"', text)
        self.assertIn('"strategy"', text)
        self.assertIn('"catalog"', text)
        self.assertIn('"goals"', text)
        self.assertIn('"enroll"', text)
        self.assertIn('"hosts"', text)
        self.assertIn("MODE_CAPABLE_TABS", text)
        self.assertIn("defaultManageGroup", text)
        self.assertIn("serializeCompanionSearch", text)
        self.assertIn("parseCompanionSearch", text)

    def test_manage_clusters_supports_controlled_active(self):
        text = (SRC / "ManageClusters.tsx").read_text()
        self.assertIn("activeGroupId", text)
        self.assertIn("onActiveGroupIdChange", text)

    def test_panels_accept_controlled_mode_props(self):
        for name, extras in (
            ("OrgPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
            ("CorporatePanel.tsx", ("mode", "onModeChange", "cluster", "onClusterChange", "manageGroup", "onManageGroupChange")),
            ("ProjectsPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
            ("WorkersPanel.tsx", ("mode", "onModeChange", "manageGroup", "onManageGroupChange")),
        ):
            text = (SRC / name).read_text()
            for marker in extras:
                self.assertIn(marker, text, f"{name} missing {marker}")

    def test_app_wires_mode_cluster_group(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("panelMode", text)
        self.assertIn("corporateCluster", text)
        self.assertIn("manageGroup", text)
        self.assertIn("onModeChange", text)
        self.assertIn("onClusterChange", text)
        self.assertIn("onManageGroupChange", text)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.76"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.76"', pkg)
