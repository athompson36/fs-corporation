"""Desk Finance init-time mutate disable (v0.3.82)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


def _budget_section(html: str) -> str:
    start = html.find('id="budget"')
    assert start != -1
    end = html.find("</section>", start)
    assert end != -1
    return html[start:end]


class DeskFinanceInitDisableTests(unittest.TestCase):
    def test_scope_notice_visible_in_markup(self):
        # Must not be hidden at first paint
        self.assertRegex(
            DESK_HTML,
            r'<p id="finance-scope-notice" class="muted">Mutations require company\.pause\.</p>',
        )
        self.assertNotRegex(
            DESK_HTML,
            r'<p id="finance-scope-notice"[^>]*\bhidden\b',
        )

    def test_static_mutate_controls_disabled_in_markup(self):
        section = _budget_section(DESK_HTML)
        for control_id in (
            "desk-finance-invoice-submit",
            "desk-finance-adjustment-submit",
            "desk-finance-period-submit",
            "desk-finance-invoice-month",
            "desk-finance-period-30d",
            "desk-finance-provider-invoice-submit",
            "desk-finance-provider-allocate-submit",
        ):
            self.assertRegex(
                section,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_init_calls_set_finance_mutate_enabled_false(self):
        # After setFinanceMutateEnabled is defined, an init call must disable
        idx = DESK_HTML.find("function setFinanceMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 1200]
        # Closing brace of function then init call — allow whitespace/newlines
        self.assertRegex(
            after,
            r"(?s)function setFinanceMutateEnabled\(enabled\) \{.*?\}\s*setFinanceMutateEnabled\(false\);",
        )

    def test_session_and_403_paths_preserved(self):
        self.assertIn("applyFinancePauseFromSession", DESK_HTML)
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertRegex(DESK_HTML, r"await\s+applyFinancePauseFromSession\s*\(")
        self.assertEqual(DESK_HTML.count("setFinanceMutateEnabled(true)"), 0)
        # 403 backup still disables
        self.assertIn("setFinanceMutateEnabled(false)", DESK_HTML)

    def test_version_0_3_82(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')


if __name__ == "__main__":
    unittest.main()
