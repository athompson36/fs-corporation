"""Desk furnished HQ SVG is driven by persisted room_type only."""
import unittest
from pathlib import Path

from company.service import DESK_HTML


class DeskFurnitureTests(unittest.TestCase):
    def test_furniture_helpers_in_desk(self):
        self.assertIn("iso-furniture", DESK_HTML)
        self.assertIn("function furnitureKind", DESK_HTML)
        self.assertIn("function drawFurniture", DESK_HTML)
        self.assertIn("workstation", DESK_HTML)
        self.assertIn("conference", DESK_HTML)
        self.assertIn("campaign", DESK_HTML)
        self.assertIn("market", DESK_HTML)  # match in furnitureKind
        self.assertIn("data-furniture", DESK_HTML)
        self.assertIn("campaign-podium", DESK_HTML)
        self.assertIn("campaign-banner", DESK_HTML)
        # Must bind to room fields, not invent workers
        self.assertIn("room.room_type", DESK_HTML)
        self.assertNotIn("inventedOccupancy", DESK_HTML)


class DeskHtmlExportTests(unittest.TestCase):
    def test_desk_html_constant_exists(self):
        path = Path(__file__).resolve().parents[1] / "company" / "service.py"
        text = path.read_text()
        self.assertIn("iso-furniture", text)


if __name__ == "__main__":
    unittest.main()
