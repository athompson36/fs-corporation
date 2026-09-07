import tempfile
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from company.core import Company, now
from company.migrate import HEAD_REVISION
from company.service import create_app
from tests.test_core import install, policy


HR = "people:HR Director"
CEO = "human-ceo"


class CareerLadderTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.c.seed_career_ladders()
        self.hired = self.c.hire_employee(
            HR,
            "dev-ada",
            "engineering:Developer",
            "Ada",
            {"seniority": "early-career"},
            "Software developer.",
        )

    def _level(self, index):
        return self.c.db.execute(
            "SELECT * FROM career_levels WHERE department_id='engineering' AND level_index=?",
            (index,),
        ).fetchone()

    def _add_evidence(self, count=2):
        hashes = []
        for index in range(count):
            artifact_hash = f"sha256-artifact-{index}"
            hashes.append(artifact_hash)
            task_id = f"accepted-{index}"
            self.c.db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)",
                (task_id, "dev-ada", f"project-{index}", "draft", 0, 1, "accepted",
                 artifact_hash),
            )
            self.c.db.execute(
                "INSERT INTO qc_inspections VALUES(?,?,?,?,?,?)",
                (f"qc-{index}", task_id, artifact_hash, "quality:Inspector", "pass",
                 now().isoformat()),
            )
        return hashes

    def test_hire_assigns_entry_level_and_standards(self):
        ladder = self.c.employee_ladder("dev-ada")
        self.assertEqual(ladder["current_level"]["level_index"], 1)
        self.assertEqual(ladder["current_level"]["title"], "Developer")
        self.assertEqual(self.c.standards_for("dev-ada")["review_expectation"],
                         "Independent review before acceptance")

    def test_ineligible_without_qc_artifacts_skills_and_reviews(self):
        evaluation = self.c.evaluate_promotion("dev-ada")
        self.assertFalse(evaluation["eligible"])
        self.assertEqual(evaluation["current_level"]["level_index"], 1)
        self.assertEqual(evaluation["next_level"]["level_index"], 2)
        unmet = {item["kind"] for item in evaluation["unmet"]}
        self.assertEqual(
            unmet,
            {"accepted_artifacts", "qc_passes", "required_skills", "review_score"},
        )

    def test_eligible_evidence_includes_exact_artifact_hashes(self):
        hashes = self._add_evidence()
        next_level = self._level(2)
        for skill_id in self.career_skills(next_level):
            self.c.db.execute(
                "INSERT INTO acquired_skills VALUES(?,?,?,?)",
                (skill_id, "dev-ada", f"evidence-{skill_id}", now().isoformat()),
            )
        self.c.record_performance_review(HR, "dev-ada", 82, "Strong delivery.")
        self.c.record_performance_review(HR, "dev-ada", 88, "Continued improvement.")

        evaluation = self.c.evaluate_promotion("dev-ada")

        self.assertTrue(evaluation["eligible"])
        self.assertEqual(evaluation["unmet"], [])
        self.assertEqual(evaluation["evidence"]["artifact_hashes"], hashes)
        self.assertEqual(evaluation["evidence"]["review_trend"], "improving")

    def test_proposal_permissions_and_ceo_approval_update_level_and_training(self):
        with self.assertRaises(PermissionError):
            self.c.propose_promotion("dev-ada", "dev-ada")
        with self.assertRaises(PermissionError):
            self.c.propose_promotion("engineering:Director", "dev-ada")

        target = self._level(2)
        proposal = self.c.propose_promotion(HR, "dev-ada", target["id"])
        self.assertEqual(proposal["status"], "pending")
        self.assertTrue(proposal["evidence"]["unmet"])
        with self.assertRaises(PermissionError):
            self.c.decide_promotion(HR, proposal["id"], "approved")

        decided = self.c.decide_promotion(CEO, proposal["id"], "approved")

        self.assertEqual(decided["status"], "approved")
        self.assertEqual(
            self.c.employee_ladder("dev-ada")["current_level"]["id"], target["id"])
        assigned = {
            row["skill_id"] for row in self.c.db.execute(
                """SELECT * FROM learning_assignments
                   WHERE learner='dev-ada' AND status='assigned'"""
            )
        }
        self.assertTrue(set(self.career_skills(target)).issubset(assigned))

    @staticmethod
    def career_skills(level):
        import json
        return json.loads(level["required_skills"])

    def test_reject_is_terminal(self):
        proposal = self.c.propose_promotion(HR, "dev-ada")
        rejected = self.c.decide_promotion(CEO, proposal["id"], "rejected")
        self.assertEqual(rejected["status"], "rejected")
        with self.assertRaises(ValueError):
            self.c.decide_promotion(CEO, proposal["id"], "approved")


class CareerLadderApiAndMigrationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.c.seed_career_ladders()
        self.c.hire_employee(
            HR, "dev-api", "engineering:Developer", "API Dev", {},
            "API development.",
        )
        self.c.register_identity(CEO, "owner", "owner-token")
        self.c.register_identity(
            HR, "service", "hr-token", ["organization.read", "organization.write"])
        self.c.register_identity(
            "org-reader", "service", "read-token", ["organization.read"])
        self.client = TestClient(create_app(self.c))

    def test_ladder_read_and_promotion_routes_enforce_scope_and_roles(self):
        ladder = self.client.get(
            "/api/v1/employees/dev-api/ladder",
            headers={"Authorization": "Bearer read-token"},
        )
        self.assertEqual(ladder.status_code, 200)
        self.assertEqual(ladder.json()["current_level"]["title"], "Developer")

        denied_scope = self.client.post(
            "/api/v1/employees/dev-api/promotions",
            json={"payload": {}},
            headers={"Authorization": "Bearer read-token"},
        )
        self.assertEqual(denied_scope.status_code, 403)
        proposed = self.client.post(
            "/api/v1/employees/dev-api/promotions",
            json={"payload": {}},
            headers={
                "Authorization": "Bearer hr-token",
                "Idempotency-Key": "promotion-api",
            },
        )
        self.assertEqual(proposed.status_code, 200)
        promotion_id = proposed.json()["result"]["id"]
        denied_decision = self.client.post(
            f"/api/v1/promotions/{promotion_id}/decision",
            json={"payload": {"decision": "approved"}},
            headers={
                "Authorization": "Bearer hr-token",
                "Idempotency-Key": "promotion-denied",
            },
        )
        self.assertEqual(denied_decision.status_code, 403)
        approved = self.client.post(
            f"/api/v1/promotions/{promotion_id}/decision",
            json={"payload": {"decision": "approved"}},
            headers={
                "Authorization": "Bearer owner-token",
                "Idempotency-Key": "promotion-approved",
            },
        )
        self.assertEqual(approved.status_code, 200)

    def test_desk_surfaces_ladder_and_pending_promotions(self):
        desk = self.client.get("/desk").text
        self.assertIn("Pending promotions", desk)
        self.assertIn("/api/v1/employees/' + encodeURIComponent(employeeId) + '/ladder", desk)
        self.assertIn("/api/v1/promotions?status=pending", desk)

    def test_file_database_migrates_through_0020(self):
        self.assertEqual(HEAD_REVISION, "0024_company_settings")
        with tempfile.TemporaryDirectory() as directory:
            company = Company(str(Path(directory) / "career.db"))
            try:
                tables = {
                    row["name"] for row in company.db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")
                }
                self.assertTrue(
                    {"career_levels", "employee_levels", "promotion_records"}
                    .issubset(tables)
                )
            finally:
                company.close()


if __name__ == "__main__":
    unittest.main()
