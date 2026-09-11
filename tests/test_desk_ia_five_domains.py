"""Desk IA aligned to five companion domains (v0.3.67)."""
from __future__ import annotations

import re
import unittest

from company.service import DESK_HTML


def _id_positions(html: str) -> dict[str, int]:
    return {m.group(1): m.start() for m in re.finditer(r'\bid="([^"]+)"', html)}


class DeskIaFiveDomainsTests(unittest.TestCase):
    def test_rail_has_five_domain_groups(self):
        self.assertIn('class="rail-group"', DESK_HTML)
        for label in ("Home", "Work", "People", "Money", "More"):
            self.assertIn(f'class="rail-group-label">{label}</span>', DESK_HTML)

    def test_rail_nested_anchors(self):
        # Home
        for anchor in ("desk", "decisions", "consultant", "hq", "status"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # Work
        for anchor in (
            "scorecard",
            "projects",
            "cross-department",
            "corporate-upgrades",
            "people",
        ):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # People
        for anchor in ("departments", "head-inbox"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)
        # Money / More
        for anchor in ("budget", "intelligence", "diagnostics", "activity", "pairing"):
            self.assertIn(f'href="#{anchor}"', DESK_HTML)

    def test_section_order_matches_domain_map(self):
        pos = _id_positions(DESK_HTML)
        # Home lead (hybrid)
        home = ["desk", "decisions", "consultant", "hq", "status"]
        for earlier, later in zip(home, home[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # Work after Home status
        work = [
            "scorecard",
            "projects",
            "cross-department",
            "corporate-upgrades",
            "people",
        ]
        self.assertLess(pos["status"], pos["scorecard"])
        for earlier, later in zip(work, work[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # People after Work people section
        self.assertLess(pos["people"], pos["departments"])
        self.assertLess(pos["departments"], pos["head-inbox"])
        # Money then More
        self.assertLess(pos["head-inbox"], pos["budget"])
        more = ["intelligence", "diagnostics", "activity", "pairing"]
        self.assertLess(pos["budget"], pos["intelligence"])
        for earlier, later in zip(more, more[1:]):
            self.assertLess(pos[earlier], pos[later], f"{earlier} before {later}")
        # Scorecard is not before Decisions (moved out of old top placement)
        self.assertGreater(pos["scorecard"], pos["decisions"])

    def test_hq_adjacent_detail_panels(self):
        pos = _id_positions(DESK_HTML)
        self.assertLess(pos["hq"], pos["room-detail"])
        self.assertLess(pos["hq"], pos["worker-card"])
        # Details still before Work scorecard
        self.assertLess(pos["room-detail"], pos["scorecard"])
        self.assertLess(pos["worker-card"], pos["scorecard"])

    def test_version_bump_target(self):
        init = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "company"
            / "__init__.py"
        ).read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
