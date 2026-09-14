"""Desk Organization session mutate gate (v0.3.83)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]

ORG_SUBMIT_IDS = (
    "desk-org-create-dept-submit",
    "desk-org-appoint-head-submit",
    "desk-org-vacate-head-submit",
    "desk-org-assign-position-submit",
    "desk-org-release-assignment-submit",
    "desk-org-create-position-submit",
    "desk-org-reorder-submit",
)


def _departments_section(html: str) -> str:
    start = html.find('id="departments"')
    assert start != -1
    end = html.find("</section>", start)
    assert end != -1
    return html[start:end]


class DeskOrgSessionGateTests(unittest.TestCase):
    def test_org_scope_notice_visible(self):
        self.assertRegex(
            DESK_HTML,
            r'<p id="org-scope-notice" class="muted"(?:\s+data-org-write-notice)?>Mutations require organization\.write\.</p>',
        )
        self.assertNotRegex(DESK_HTML, r'<p id="org-scope-notice"[^>]*\bhidden\b')

    def test_org_submit_controls_disabled_in_markup(self):
        section = _departments_section(DESK_HTML)
        for control_id in ORG_SUBMIT_IDS:
            self.assertRegex(
                section,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_org_mutate_enabled_and_init(self):
        self.assertRegex(DESK_HTML, r"function setOrgMutateEnabled\s*\(")
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        after = DESK_HTML[idx : idx + 1500]
        self.assertRegex(
            after,
            r"(?s)function setOrgMutateEnabled\s*\(enabled\)\s*\{.*?\}\s*setOrgMutateEnabled\(false\);",
        )
        for control_id in ORG_SUBMIT_IDS:
            self.assertIn(control_id, after)

    def test_shared_session_applies_org_and_finance(self):
        # Single session fetch applies both scopes
        self.assertIn("/api/v1/session", DESK_HTML)
        self.assertIn("organization.write", DESK_HTML)
        self.assertIn("company.pause", DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r"setOrgMutateEnabled\s*\(\s*scopes\.indexOf\(['\"]organization\.write['\"]\)",
        )
        self.assertRegex(
            DESK_HTML,
            r"setFinanceMutateEnabled\s*\(\s*scopes\.indexOf\(['\"]company\.pause['\"]\)",
        )
        # Prefer one await of shared apply (rename OK)
        self.assertRegex(
            DESK_HTML,
            r"await\s+(?:applySessionScopes|applyFinancePauseFromSession)\s*\(",
        )
        # Fail-closed paths for org on session error
        self.assertGreaterEqual(DESK_HTML.count("setOrgMutateEnabled(false)"), 2)

    def test_submit_org_command_403_disables(self):
        idx = DESK_HTML.find("async function submitOrgCommand")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 800]
        self.assertIn("403", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_version_0_3_83(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')


if __name__ == "__main__":
    unittest.main()
