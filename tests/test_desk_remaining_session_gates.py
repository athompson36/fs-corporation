"""Desk remaining session gates + docs ship (v0.3.85)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]


class DeskRemainingSessionGatesTests(unittest.TestCase):
    def test_people_notice_and_staffing_scan_disabled(self):
        start = DESK_HTML.find('id="people"')
        self.assertGreater(start, -1)
        end = DESK_HTML.find("</section>", start)
        chunk = DESK_HTML[start:end]
        self.assertIn("data-org-write-notice", chunk)
        self.assertIn("Mutations require organization.write.", chunk)
        self.assertRegex(
            DESK_HTML,
            r'id="staffing-scan-btn"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="staffing-scan-btn"',
        )

    def test_set_org_includes_staffing_scan(self):
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 2500]
        self.assertIn("staffing-scan-btn", after)

    def test_dynamic_org_write_markers(self):
        for fn_name in (
            "function renderPromotions",
            "function renderStaffingProposals",
            "function renderDivisions",
        ):
            idx = DESK_HTML.find(fn_name)
            self.assertGreater(idx, -1, fn_name)
            chunk = DESK_HTML[idx : idx + 2200]
            self.assertIn("data-org-write", chunk, fn_name)
            self.assertIn("orgWriteEnabled", chunk, fn_name)
            self.assertIn("403", chunk, fn_name)
            self.assertIn("setOrgMutateEnabled(false)", chunk, fn_name)

    def test_staffing_scan_403_and_guard(self):
        idx = DESK_HTML.find("staffing-scan-btn').addEventListener")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 900]
        self.assertIn("orgWriteEnabled", chunk)
        self.assertIn("403", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_dispatch_enroll_markup(self):
        self.assertIn('id="dispatch-scope-notice"', DESK_HTML)
        self.assertIn("Mutations require project.enroll.", DESK_HTML)
        for control_id in ("dispatch-submit-btn", "dispatch-recommend-btn"):
            self.assertRegex(
                DESK_HTML,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_dispatch_enroll_helper(self):
        self.assertIn("function setDispatchEnrollEnabled", DESK_HTML)
        self.assertIn("dispatchEnrollEnabled", DESK_HTML)
        self.assertIn("setDispatchEnrollEnabled(false)", DESK_HTML)
        idx = DESK_HTML.find("function updateDispatchSubmitGate")
        self.assertGreater(idx, -1)
        chunk = DESK_HTML[idx : idx + 800]
        self.assertIn("dispatchEnrollEnabled", chunk)

    def test_session_applies_project_enroll(self):
        # Shared session apply (name may still be applyFinancePauseFromSession)
        self.assertIn("project.enroll", DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r"setDispatchEnrollEnabled\(scopes\.indexOf\('project\.enroll'\)",
        )
        fail_idx = DESK_HTML.find("async function applyFinancePauseFromSession")
        if fail_idx < 0:
            fail_idx = DESK_HTML.find("async function applySessionScopes")
        self.assertGreater(fail_idx, -1)
        chunk = DESK_HTML[fail_idx : fail_idx + 900]
        self.assertIn("setDispatchEnrollEnabled(false)", chunk)
        self.assertIn("setOrgMutateEnabled(false)", chunk)

    def test_dispatch_403_fail_closed(self):
        for marker in (
            "dispatch-form').addEventListener('submit'",
            "dispatch-recommend-btn').addEventListener",
        ):
            idx = DESK_HTML.find(marker)
            self.assertGreater(idx, -1, marker)
            span = 1300 if "dispatch-form" in marker else 1200
            chunk = DESK_HTML[idx : idx + span]
            self.assertIn("403", chunk, marker)
            self.assertIn("setDispatchEnrollEnabled(false)", chunk, marker)

    def test_version_lockstep(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertRegex(init, r'__version__ = "0\.3\.\d+"')
        self.assertRegex(pkg, r'"version": "0\.3\.\d+"')


if __name__ == "__main__":
    unittest.main()
