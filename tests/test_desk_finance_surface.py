"""Desk Finance surface (v0.3.78)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskFinanceSurfaceTests(unittest.TestCase):
    def test_rail_and_heading_finance_keep_budget_id(self):
        self.assertIn('href="#budget"', DESK_HTML)
        self.assertIn('id="budget"', DESK_HTML)
        self.assertRegex(DESK_HTML, r'href="#budget">\s*Finance\s*<')
        self.assertRegex(DESK_HTML, r'id="budget"[^>]*>\s*<h2>\s*Finance\s*</h2>')
        self.assertNotIn('href="#budget">Budget<', DESK_HTML)
        self.assertNotIn("<h2>Budget</h2>", DESK_HTML)

    def test_no_budget_json_dump(self):
        html = DESK_HTML
        start = html.find('id="budget"')
        self.assertGreater(start, -1)
        # section opens at nearest preceding <section
        sec_start = html.rfind("<section", 0, start)
        self.assertGreater(sec_start, -1)
        sec_end = html.find("</section>", start)
        self.assertGreater(sec_end, -1)
        budget = html[sec_start : sec_end + len("</section>")]
        self.assertNotIn("budget-json", budget)
        self.assertNotIn("simulated_spend_cents", budget)

    def test_finance_markup_ids(self):
        for marker in (
            "finance-overview",
            "finance-invoice-list",
            "finance-adjustment-list",
            "finance-period-list",
            "finance-invoice-form",
            "finance-adjustment-form",
            "finance-period-form",
            "finance-scope-notice",
            "finance-load-error",
            "desk-finance-invoice-start",
            "desk-finance-invoice-end",
            "desk-finance-adjustment-kind",
            "desk-finance-billed-cost",
            "desk-finance-adjustment-amount",
            "desk-finance-adjustment-reason",
            "desk-finance-period-start",
            "desk-finance-period-end",
            "desk-finance-period-limit",
        ):
            self.assertIn(marker, DESK_HTML)

    def test_finance_api_and_helpers(self):
        self.assertIn("/api/v1/finance/summary", DESK_HTML)
        self.assertIn("/api/v1/finance/invoices", DESK_HTML)
        self.assertIn("/api/v1/finance/adjustments", DESK_HTML)
        self.assertIn("/api/v1/finance/budget-periods", DESK_HTML)
        self.assertIn("/api/v1/finance/billed-costs", DESK_HTML)
        self.assertIn("loadFinance", DESK_HTML)
        self.assertIn("formatFinanceUsd", DESK_HTML)
        self.assertIn("setFinanceMutateEnabled", DESK_HTML)
        self.assertIn("desk-finance-", DESK_HTML)
        self.assertIn("Close period", DESK_HTML)

    def test_version_lockstep_soft(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')


if __name__ == "__main__":
    unittest.main()
