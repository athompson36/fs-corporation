"""Approval-gated divisions and industry packs (Corporate HQ Phase 7)."""
from pathlib import Path
import json
import tempfile
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.migrate import HEAD_REVISION
from company.service import create_app
from tests.test_core import install, policy


CEO = "human-ceo"


class DivisionTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_industry_packs()
        self.addCleanup(self.c.close)

    def test_consultant_can_propose_but_cannot_self_activate(self):
        division = self.c.propose_division(
            "consultant", "finance-operations", "Finance Operations")

        self.assertEqual(division["status"], "proposed")
        with self.assertRaisesRegex(PermissionError, "CEO authority required"):
            self.c.activate_division("consultant", division["id"])

        stored = self.c.list_divisions()["divisions"][0]
        self.assertEqual(stored["status"], "proposed")

    def test_minimal_and_full_create_different_department_sets(self):
        minimal = self.c.propose_division(
            CEO, "finance-operations", "Finance Minimal", mode="minimal")
        full = self.c.propose_division(
            CEO, "finance-operations", "Finance Full", mode="full")

        self.c.activate_division(CEO, minimal["id"])
        self.c.activate_division(CEO, full["id"])

        counts = {
            row["division_id"]: row["count"]
            for row in self.c.db.execute(
                """SELECT division_id,COUNT(*) AS count
                   FROM division_departments GROUP BY division_id""")
        }
        self.assertEqual(counts[minimal["id"]], 1)
        self.assertEqual(counts[full["id"]], 3)

    def test_pack_skills_create_company_learning_assignments(self):
        division = self.c.propose_division(
            CEO, "finance-operations", "Finance Skills", mode="full")

        activated = self.c.activate_division(CEO, division["id"])

        self.assertEqual(activated["status"], "active")
        skills = self.c.db.execute(
            """SELECT s.id,la.project_id,la.department_id
               FROM skills s JOIN learning_assignments la ON la.skill_id=s.id
               WHERE s.id LIKE 'finance-%' ORDER BY s.id""").fetchall()
        self.assertTrue(skills)
        self.assertTrue(all(row["project_id"] == "company" for row in skills))

    def test_activation_is_atomic(self):
        division = self.c.propose_division(
            CEO, "finance-operations", "Broken Finance", mode="full")
        row = self.c.db.execute(
            "SELECT body FROM industry_packs WHERE id='finance-operations'").fetchone()
        body = json.loads(row["body"])
        body["full_departments"][1]["positions"].append("")
        self.c.db.execute(
            "UPDATE industry_packs SET body=? WHERE id='finance-operations'",
            (json.dumps(body),))

        with self.assertRaisesRegex(ValueError, "title required"):
            self.c.activate_division(CEO, division["id"])

        self.assertEqual(
            self.c.db.execute(
                "SELECT COUNT(*) FROM departments WHERE id IN ('fin-ops','treasury','controllership')"
            ).fetchone()[0],
            0,
        )
        self.assertEqual(
            self.c.list_divisions()["divisions"][0]["status"], "proposed")

    def test_deactivate_is_blocked_by_open_department_work(self):
        division = self.c.propose_division(
            CEO, "finance-operations", "Finance Work")
        self.c.activate_division(CEO, division["id"])
        self.c.db.execute(
            """INSERT INTO project_dispatches(
                 id,project_id,department_id,work_order_id,brief,acceptance_criteria,
                 budget_cents,due_at,created_at,status,head_principal_id,head_inbox_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("open-finance", "project", "fin-ops", "work", "brief", "criteria",
             0, None, "2026-09-07T00:00:00+00:00", "assigned", None, None),
        )

        with self.assertRaisesRegex(ValueError, "open dispatches"):
            self.c.deactivate_division(CEO, division["id"])

        self.assertEqual(
            self.c.list_divisions()["divisions"][0]["status"], "active")


class DivisionApiAndMigrationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_industry_packs()
        self.c.register_identity(CEO, "owner", "owner-token")
        self.c.register_identity(
            "consultant", "service", "consultant-token",
            ["organization.read", "organization.write", "consultant.propose"])
        self.client = TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_routes_and_desk_support_division_lifecycle(self):
        packs = self.client.get(
            "/api/v1/industry-packs",
            headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(packs.status_code, 200, packs.text)
        self.assertEqual(len(packs.json()["industry_packs"]), 4)

        proposed = self.client.post(
            "/api/v1/divisions/proposals",
            headers={"Authorization": "Bearer consultant-token"},
            json={"payload": {
                "pack_id": "corporate-consulting",
                "name": "Consulting",
                "mode": "minimal",
            }},
        )
        self.assertEqual(proposed.status_code, 200, proposed.text)
        division_id = proposed.json()["result"]["id"]
        denied = self.client.post(
            f"/api/v1/divisions/{division_id}/activate",
            headers={"Authorization": "Bearer consultant-token"},
            json={"payload": {}},
        )
        self.assertEqual(denied.status_code, 403)
        activated = self.client.post(
            f"/api/v1/divisions/{division_id}/activate",
            headers={"Authorization": "Bearer owner-token"},
            json={"payload": {}},
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        listed = self.client.get(
            "/api/v1/divisions",
            headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(listed.json()["divisions"][0]["status"], "active")

        desk = self.client.get("/desk").text
        self.assertIn("Corporate upgrades", desk)
        self.assertIn("/api/v1/industry-packs", desk)
        self.assertIn("/api/v1/divisions/", desk)

    def test_file_database_migrates_to_0022(self):
        self.assertEqual(HEAD_REVISION, "0027_worker_hosts")
        with tempfile.TemporaryDirectory() as directory:
            company = Company(str(Path(directory) / "divisions.db"))
            try:
                tables = {
                    row["name"] for row in company.db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")
                }
                self.assertTrue({
                    "industry_packs", "divisions", "division_departments",
                    "division_activations",
                }.issubset(tables))
            finally:
                company.close()


if __name__ == "__main__":
    unittest.main()
