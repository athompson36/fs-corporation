"""Desk source contracts for provider invoices."""
import unittest
from company.service import DESK_HTML


class DeskProviderInvoiceTests(unittest.TestCase):
    def test_provider_invoice_surface(self):
        self.assertIn("Provider invoices", DESK_HTML)
        self.assertIn("desk-finance-provider-invoice-submit", DESK_HTML)
        self.assertIn("desk-finance-provider-allocate-submit", DESK_HTML)
        self.assertIn("finance-provider-invoice-list", DESK_HTML)
        self.assertIn("/api/v1/finance/provider-invoices", DESK_HTML)


if __name__ == "__main__":
    unittest.main()
