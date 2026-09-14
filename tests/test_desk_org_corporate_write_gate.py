"""Desk corporate write forms session gate (v0.3.84)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from company.service import DESK_HTML

ROOT = Path(__file__).resolve().parents[1]

CORP_SUBMIT_IDS = (
    "desk-org-create-objective-submit",
    "desk-org-create-cross-dept-submit",
    "desk-org-propose-division-submit",
)


class DeskOrgCorporateWriteGateTests(unittest.TestCase):
    def test_section_notices_present(self):
        self.assertGreaterEqual(DESK_HTML.count('data-org-write-notice'), 4)
        self.assertIn('id="org-scope-notice"', DESK_HTML)
        self.assertRegex(
            DESK_HTML,
            r'id="org-scope-notice"[^>]*data-org-write-notice|data-org-write-notice[^>]*id="org-scope-notice"',
        )
        for section_id in ("scorecard", "cross-department", "corporate-upgrades"):
            start = DESK_HTML.find(f'id="{section_id}"')
            self.assertGreater(start, -1, section_id)
            end = DESK_HTML.find("</section>", start)
            chunk = DESK_HTML[start:end]
            self.assertIn("data-org-write-notice", chunk)
            self.assertIn("Mutations require organization.write.", chunk)

    def test_corporate_submits_disabled(self):
        for control_id in CORP_SUBMIT_IDS:
            self.assertRegex(
                DESK_HTML,
                rf'id="{control_id}"[^>]*\bdisabled\b|\bdisabled\b[^>]*id="{control_id}"',
            )

    def test_set_org_mutate_extended(self):
        idx = DESK_HTML.find("function setOrgMutateEnabled")
        self.assertGreater(idx, -1)
        after = DESK_HTML[idx : idx + 2000]
        self.assertIn("orgWriteEnabled", after)
        self.assertIn("data-org-write-notice", after)
        self.assertIn("data-org-write", after)
        for control_id in CORP_SUBMIT_IDS:
            self.assertIn(control_id, after)

    def test_dynamic_row_markers(self):
        # Close / Accept use data-org-write
        obj_idx = DESK_HTML.find("function renderObjectives")
        self.assertGreater(obj_idx, -1)
        obj_chunk = DESK_HTML[obj_idx : obj_idx + 1500]
        self.assertIn("data-org-write", obj_chunk)
        self.assertIn("orgWriteEnabled", obj_chunk)
        xd_idx = DESK_HTML.find("function renderCrossDept")
        self.assertGreater(xd_idx, -1)
        xd_chunk = DESK_HTML[xd_idx : xd_idx + 1500]
        self.assertIn("data-org-write", xd_chunk)
        self.assertIn("orgWriteEnabled", xd_chunk)
        # 403 fail-closed on Accept/Close
        self.assertIn("403", obj_chunk)
        self.assertIn("setOrgMutateEnabled(false)", obj_chunk)
        self.assertIn("403", xd_chunk)
        self.assertIn("setOrgMutateEnabled(false)", xd_chunk)

    def test_version_0_3_84(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('__version__ = "0.3.84"', init)
        self.assertIn('"version": "0.3.84"', pkg)


if __name__ == "__main__":
    unittest.main()
