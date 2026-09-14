"""Desk finance open-next + pricing hint (v0.3.86)."""
from __future__ import annotations

import unittest

from company.service import DESK_HTML


class DeskFinanceOpenNextTests(unittest.TestCase):
    def test_open_next_markers(self):
        self.assertIn("openFinanceNextPeriod", DESK_HTML)
        self.assertIn("data-finance-open-next", DESK_HTML)
        self.assertIn("/open-next", DESK_HTML)

    def test_pricing_hint_render(self):
        self.assertIn("finance-pricing-hint", DESK_HTML)
        self.assertIn("model_cents_per_1k_configured", DESK_HTML)

    def test_set_finance_disables_open_next(self):
        idx = DESK_HTML.find("function setFinanceMutateEnabled")
        chunk = DESK_HTML[idx:idx + 1200]
        self.assertIn("data-finance-open-next", chunk)
