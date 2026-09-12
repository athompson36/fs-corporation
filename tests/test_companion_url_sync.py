"""Companion URL sync tab+project deep links (v0.3.73)."""
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

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.73"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.73"', pkg)
