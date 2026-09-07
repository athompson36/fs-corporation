"""Approval-gated HR staffing proposals (Corporate HQ Phase 6)."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.migrate import HEAD_REVISION
from company.service import create_app
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"
HR = "people:HR Director"
CEO = "human-ceo"


class StaffingProposalTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.addCleanup(self.c.close)

    def _blocked_dispatch(self):
        self.c.enroll_project(CEO, "staffing-project", "Staffing test project.")
        return self.c.dispatch_project_brief(
            CEO, "staffing-project", "Build the feature", {"engineering": 10},
            "Acceptance evidence exists.",
        )[0]

    def _hire_proposal(self):
        return self.c.create_staffing_proposal(
            HR,
            kind="hire",
            department_id="engineering",
            position_id="engineering:Developer",
            rationale="Approved capacity is needed for queued work.",
            evidence={
                "employee_id": "dev-phase6",
                "display_name": "Phase Six Developer",
                "background": "Software delivery and independent review.",
                "attributes": {"seniority": "mid-level"},
                "source": "manual-capacity-review",
            },
            cost_estimate_cents=2500,
        )

    def test_scan_creates_evidence_backed_proposals_without_hiring(self):
        dispatch = self._blocked_dispatch()

        result = self.c.scan_staffing_gaps(HR)

        proposal = next(
            item for item in result["items"]
            if item["department_id"] == "engineering"
            and item["evidence"].get("source") == "blocked_vacant_head"
        )
        self.assertEqual(proposal["kind"], "hire")
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(proposal["evidence"]["dispatch_ids"], [dispatch["id"]])
        self.assertGreater(len(proposal["rationale"]), 0)
        self.assertEqual(
            self.c.db.execute("SELECT COUNT(*) FROM employees").fetchone()[0], 0)

    def test_scan_deduplicates_pending_kind_department_position(self):
        self._blocked_dispatch()
        first = self.c.scan_staffing_gaps(HR)
        self.c.db.execute(
            """UPDATE staffing_scan_cooldown
               SET cooldown_until='2000-01-01T00:00:00+00:00' WHERE id='default'""")

        second = self.c.scan_staffing_gaps(HR)

        self.assertGreater(len(first["items"]), 0)
        self.assertEqual(second["created"], 0)
        rows = self.c.db.execute(
            """SELECT COUNT(*) FROM staffing_proposals
               WHERE kind='hire' AND department_id='engineering'
                 AND position_id='engineering:CTO' AND status='pending'"""
        ).fetchone()[0]
        self.assertEqual(rows, 1)

    def test_scan_is_rate_limited(self):
        self.c.scan_staffing_gaps(HR)

        with self.assertRaisesRegex(ValueError, "cooldown active"):
            self.c.scan_staffing_gaps(HR)

    def test_approval_hires_atomically(self):
        proposal = self._hire_proposal()

        approved = self.c.decide_staffing_proposal(CEO, proposal["id"], "approved")

        self.assertEqual(approved["status"], "approved")
        employee = self.c.db.execute(
            "SELECT * FROM employees WHERE id='dev-phase6'").fetchone()
        self.assertIsNotNone(employee)
        self.assertEqual(employee["position_id"], "engineering:Developer")
        self.assertEqual(approved["evidence"]["employee_id"], "dev-phase6")

    def test_hire_approval_rolls_back_decision_when_hire_fails(self):
        proposal = self._hire_proposal()
        self.c.hire_employee(
            HR, "dev-phase6", "engineering:Developer", "Existing Developer", {},
            "Already employed.",
        )

        with self.assertRaisesRegex(ValueError, "already hired"):
            self.c.decide_staffing_proposal(CEO, proposal["id"], "approved")

        stored = self.c.list_staffing_proposals()["items"][0]
        self.assertEqual(stored["status"], "pending")
        self.assertIsNone(stored["approver"])

    def test_rejection_has_no_hiring_side_effect(self):
        proposal = self._hire_proposal()

        rejected = self.c.decide_staffing_proposal(CEO, proposal["id"], "rejected")

        self.assertEqual(rejected["status"], "rejected")
        self.assertIsNone(self.c.db.execute(
            "SELECT 1 FROM employees WHERE id='dev-phase6'").fetchone())

    def test_unauthorized_actors_are_denied(self):
        fields = {
            "kind": "hire",
            "department_id": "engineering",
            "position_id": "engineering:Developer",
            "rationale": "Capacity review.",
            "evidence": {"source": "manual"},
            "cost_estimate_cents": 0,
        }
        with self.assertRaises(PermissionError):
            self.c.scan_staffing_gaps("stranger")
        with self.assertRaises(PermissionError):
            self.c.create_staffing_proposal("stranger", **fields)
        proposal = self.c.create_staffing_proposal(HR, **fields)
        with self.assertRaises(PermissionError):
            self.c.decide_staffing_proposal(HR, proposal["id"], "rejected")


class StaffingProposalApiAndMigrationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.register_identity(CEO, "owner", "owner-token")
        self.c.register_identity(
            HR, "service", "hr-token", ["organization.read", "organization.write"])
        self.c.register_identity(
            "org-reader", "service", "read-token", ["organization.read"])
        self.client = TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_routes_and_desk_support_proposal_decisions(self):
        created = self.client.post(
            "/api/v1/staffing-proposals",
            headers={"Authorization": "Bearer hr-token", "Idempotency-Key": "staff-1"},
            json={"payload": {
                "kind": "hire",
                "department_id": "engineering",
                "position_id": "engineering:Developer",
                "rationale": "Queue capacity.",
                "evidence": {
                    "employee_id": "api-phase6",
                    "display_name": "API Phase Six",
                    "background": "API engineering.",
                },
                "cost_estimate_cents": 500,
            }},
        )
        self.assertEqual(created.status_code, 200, created.text)
        proposal_id = created.json()["result"]["id"]
        denied = self.client.post(
            f"/api/v1/staffing-proposals/{proposal_id}/decision",
            headers={"Authorization": "Bearer hr-token"},
            json={"payload": {"decision": "approved"}},
        )
        self.assertEqual(denied.status_code, 403)
        approved = self.client.post(
            f"/api/v1/staffing-proposals/{proposal_id}/decision",
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "staff-2"},
            json={"payload": {"decision": "approved"}},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        listed = self.client.get(
            "/api/v1/staffing-proposals?status=approved",
            headers={"Authorization": "Bearer read-token"},
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["items"][0]["id"], proposal_id)
        desk = self.client.get("/desk").text
        self.assertIn("Pending staffing proposals", desk)
        self.assertIn("/api/v1/staffing-proposals?status=pending", desk)
        self.assertIn("staffing-proposals/' + proposal.id + '/decision", desk)

    def test_file_database_preserves_staffing_tables_at_current_head(self):
        self.assertEqual(HEAD_REVISION, "0024_company_settings")
        with tempfile.TemporaryDirectory() as directory:
            company = Company(str(Path(directory) / "staffing.db"))
            try:
                tables = {
                    row["name"] for row in company.db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")
                }
                self.assertTrue(
                    {"staffing_proposals", "staffing_scan_cooldown"}.issubset(tables))
            finally:
                company.close()


if __name__ == "__main__":
    unittest.main()
