"""Manage visual groups hybrid chrome (v0.3.74)."""
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


class ManageVisualGroupsTests(unittest.TestCase):
    def test_shared_modules_exist(self):
        hook = (SRC / "useWideViewport.ts").read_text()
        self.assertIn('matchMedia("(min-width: 720px)")', hook)
        self.assertIn("export function useWideViewport", hook)
        chrome = (SRC / "ManageClusters.tsx").read_text()
        self.assertIn("export function ManageClusters", chrome)
        self.assertIn("manage-cluster-tabs", chrome)
        self.assertIn('role="tablist"', chrome)
        self.assertIn("useWideViewport", chrome)
        self.assertRegex(
            chrome,
            r'className="cluster-head"[\s\S]{0,80}<h2>\{group\.label\}</h2>',
        )

    def test_org_manage_group_labels(self):
        text = (SRC / "OrgPanel.tsx").read_text()
        self.assertIn("ManageClusters", text)
        self.assertIn('ariaLabel="Organization manage groups"', text)
        for title in ("Catalog", "Seats", "Positions", "Lookup"):
            self.assertIn(f'label: "{title}"', text)

    def test_corporate_manage_group_labels(self):
        text = (SRC / "CorporatePanel.tsx").read_text()
        self.assertIn("ManageClusters", text)
        self.assertIn('ariaLabel="Corporate manage groups"', text)
        for title in ("Goals", "Structure", "Coordination", "Ops"):
            self.assertIn(f'label: "{title}"', text)
        self.assertIn('from "./useWideViewport"', text)
        self.assertNotRegex(text, r"function useWideViewport\s*\(")

    def test_projects_and_workers_manage_groups(self):
        projects = (SRC / "ProjectsPanel.tsx").read_text()
        self.assertIn("ManageClusters", projects)
        self.assertIn('ariaLabel="Projects manage groups"', projects)
        for title in ("Enroll", "GitHub"):
            self.assertIn(f'label: "{title}"', projects)
        workers = (SRC / "WorkersPanel.tsx").read_text()
        self.assertIn("ManageClusters", workers)
        self.assertIn('ariaLabel="Workers manage groups"', workers)
        for title in ("Hosts", "Token"):
            self.assertIn(f'label: "{title}"', workers)
        self.assertTrue(_section_head_wraps_h2(workers, "Create worker host"))
        self.assertTrue(_section_head_wraps_h2(workers, "Worker host token"))
        self.assertIn("No token issued yet.", workers)
        self.assertIn('key={issuedToken ? "token" : "hosts"}', workers)
        self.assertIn('defaultGroupId={issuedToken ? "token" : "hosts"}', workers)

    def test_version_bump_target(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')
