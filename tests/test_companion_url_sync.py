"""Companion URL sync tab+project deep links (v0.3.73+)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "companion" / "src"


class CompanionUrlSyncTests(unittest.TestCase):
    def test_url_state_module_exports(self):
        text = (SRC / "urlState.ts").read_text()
        self.assertIn("export type CompanionTab", text)
        self.assertIn("export function parseCompanionSearch", text)
        self.assertIn("export function serializeCompanionSearch", text)
        self.assertIn('"dashboard"', text)
        self.assertIn('"projects"', text)
        self.assertIn('"finance"', text)
        self.assertIn('"settings"', text)
        # project forces projects tab when present
        self.assertRegex(text, r"project[\s\S]{0,80}projects")

    def test_app_wires_url_sync(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn('from "./urlState"', text)
        self.assertIn("parseCompanionSearch", text)
        self.assertIn("serializeCompanionSearch", text)
        self.assertIn("history.replaceState", text)
        self.assertIn("popstate", text)
        self.assertIn("pairingTicketFromHash", text)
        self.assertIn("clearPairingHash", text)

    def test_app_unknown_project_clear_gated_on_projects_loaded(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("projectsLoaded", text)
        self.assertIn("setProjectsLoaded", text)
        self.assertIn("setProjectsLoaded(true)", text)
        # Gate clear on loaded flag — not empty-list early return alone
        self.assertRegex(
            text,
            r"if\s*\(\s*!projectsLoaded\s*\|\|\s*!selectedProject\s*\)\s*return",
        )
        self.assertNotRegex(
            text,
            r"if\s*\(\s*!selectedProject\s*\|\|\s*!projects\.length\s*\)\s*return",
        )

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')

    def test_version_bump_target_exact(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
