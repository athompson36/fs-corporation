"""Org roster, rules, and handoff (grant-backed)."""
from __future__ import annotations
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from company.core import Company, now
from company.schema import COMPANION_SCOPES
from company.service import create_app
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class OrgRosterSeedTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_seed_catalog_creates_vacant_or_dormant_seats(self):
        self.c.seed_catalog(CATALOG)
        seats = list(self.c.db.execute(
            "SELECT department_id, principal_id, status, title FROM department_seats ORDER BY department_id"))
        self.assertGreaterEqual(len(seats), 13)
        eng = next(s for s in seats if s["department_id"] == "engineering")
        self.assertIsNone(eng["principal_id"])
        self.assertEqual(eng["status"], "vacant")
        self.assertEqual(eng["title"], "CTO")
        product = next(s for s in seats if s["department_id"] == "product")
        self.assertEqual(product["status"], "dormant")
        self.assertIsNone(product["principal_id"])


class OrgAppointTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.addCleanup(self.c.close)

    def test_appoint_and_vacate_head(self):
        row = self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["principal_id"], "eng-cto")
        seat = self.c.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?",
            ("engineering",),
        ).fetchone()
        self.assertEqual(seat["principal_id"], "eng-cto")
        vacated = self.c.vacate_head("human-ceo", "engineering")
        self.assertEqual(vacated["status"], "vacant")
        self.assertIsNone(vacated["principal_id"])

    def test_stranger_denied_but_companion_admin_can_manage_roster(self):
        with self.assertRaises(PermissionError):
            self.c.appoint_head("stranger", "engineering", "eng-cto")
        appointed = self.c.appoint_head(
            "companion-admin-phone", "engineering", "eng-cto")
        self.assertEqual(appointed["principal_id"], "eng-cto")
        assignment = self.c.assign_position(
            "companion-admin-phone", "engineering:Developer", "dev-phone")
        self.assertEqual(assignment["status"], "active")
        self.assertEqual(
            self.c.release_position("companion-admin-phone", assignment["id"])["status"],
            "released",
        )
        self.assertEqual(
            self.c.vacate_head("companion-admin-phone", "engineering")["status"],
            "vacant",
        )

    def test_assign_and_release_position(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        aid = self.c.assign_position(
            "human-ceo",
            "engineering:Developer",
            "dev-1",
        )["id"]
        row = self.c.db.execute(
            "SELECT * FROM position_assignments WHERE id=?",
            (aid,),
        ).fetchone()
        self.assertEqual(row["principal_id"], "dev-1")
        self.assertEqual(row["status"], "active")
        self.c.release_position("human-ceo", aid)
        row = self.c.db.execute(
            "SELECT * FROM position_assignments WHERE id=?",
            (aid,),
        ).fetchone()
        self.assertEqual(row["status"], "released")

    def test_list_org_shows_vacant_honestly(self):
        org = self.c.list_org()
        eng = next(d for d in org["departments"] if d["id"] == "engineering")
        self.assertEqual(eng["seat"]["status"], "vacant")
        self.assertIsNone(eng["seat"]["principal_id"])


class OrgApiTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_identity("org-reader", "service", "reader-token", ["organization.read"])
        self.client = TestClient(create_app(self.c))
        self.headers = {"Authorization": "Bearer owner-token"}
        self.addCleanup(self.c.close)

    def test_get_org_requires_read_scope_and_lists_catalog(self):
        response = self.client.get("/api/v1/org", headers={
            "Authorization": "Bearer reader-token",
        })
        self.assertEqual(response.status_code, 200, response.text)
        engineering = next(
            department for department in response.json()["departments"]
            if department["id"] == "engineering"
        )
        self.assertEqual(engineering["seat"]["status"], "vacant")

        self.assertEqual(self.client.get("/api/v1/org").status_code, 401)

    def test_appoint_and_vacate_head_via_api(self):
        appointed = self.client.post(
            "/api/v1/org/heads",
            json={"payload": {
                "department_id": "engineering",
                "principal_id": "eng-cto",
            }},
            headers=self.headers,
        )
        self.assertEqual(appointed.status_code, 200, appointed.text)
        self.assertEqual(appointed.json()["result"]["principal_id"], "eng-cto")

        vacated = self.client.post(
            "/api/v1/org/heads",
            json={"payload": {
                "department_id": "engineering",
                "vacate": True,
            }},
            headers=self.headers,
        )
        self.assertEqual(vacated.status_code, 200, vacated.text)
        self.assertEqual(vacated.json()["result"]["status"], "vacant")
        self.assertIsNone(vacated.json()["result"]["principal_id"])

    def test_assign_and_release_position_via_api(self):
        assigned = self.client.post(
            "/api/v1/org/assignments",
            json={"payload": {
                "position_id": "engineering:Developer",
                "principal_id": "dev-1",
                "reports_to_seat_id": "seat:engineering",
            }},
            headers=self.headers,
        )
        self.assertEqual(assigned.status_code, 200, assigned.text)
        assignment = assigned.json()["result"]
        self.assertEqual(assignment["status"], "active")
        self.assertEqual(assignment["principal_id"], "dev-1")

        released = self.client.post(
            "/api/v1/org/assignments",
            json={"payload": {
                "assignment_id": assignment["id"],
                "release": True,
            }},
            headers=self.headers,
        )
        self.assertEqual(released.status_code, 200, released.text)
        self.assertEqual(released.json()["result"]["status"], "released")

    def test_write_routes_require_organization_write_scope(self):
        denied = self.client.post(
            "/api/v1/org/heads",
            json={"payload": {
                "department_id": "engineering",
                "principal_id": "eng-cto",
            }},
            headers={"Authorization": "Bearer reader-token"},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_companion_admin_scope_catalog_includes_organization_write(self):
        self.assertIn("organization.write", COMPANION_SCOPES)


class OrgActivationDispatchTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Org handoff")
        self.addCleanup(self.c.close)

    def test_dormant_department_dispatch_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.c.dispatch_project_brief(
                "human-ceo",
                "app",
                brief="Need product",
                department_budgets={"product": 1000},
                acceptance_criteria="PRD draft",
            )
        self.assertIn("dormant", str(ctx.exception).lower())

    def test_activate_then_dispatch_dormant(self):
        activated = self.c.activate_department_for_project(
            "companion-admin-phone", "app", "product")
        self.assertEqual(activated["department_id"], "product")
        self.c.appoint_head("human-ceo", "product", "prod-head")
        out = self.c.dispatch_project_brief(
            "human-ceo",
            "app",
            brief="Need product",
            department_budgets={"product": 1000},
            acceptance_criteria="PRD draft",
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["status"], "queued_for_head")
        self.assertEqual(out[0]["head_principal_id"], "prod-head")

    def test_initially_active_vacant_head_blocks_inbox_status(self):
        out = self.c.dispatch_project_brief(
            "human-ceo",
            "app",
            brief="Eng work",
            department_budgets={"engineering": 2000},
            acceptance_criteria="Ship",
        )
        self.assertEqual(out[0]["status"], "blocked_vacant_head")
        self.assertIsNone(out[0]["head_principal_id"])

    def test_department_scoped_grant_fails_closed_without_matching_department(self):
        next_policy = policy(self.c)
        next_policy["grants"]["head"]["departments"] = ["engineering"]
        install(self.c, next_policy)
        self.c._scope("head", "app", "draft", 0, department_id="engineering")
        with self.assertRaises(PermissionError):
            self.c._scope("head", "app", "draft", 0, department_id="marketing")
        with self.assertRaises(PermissionError):
            self.c._scope("head", "app", "draft", 0)

    def test_delegated_grant_inherits_parent_department_scope(self):
        next_policy = policy(self.c)
        next_policy["grants"]["head"]["departments"] = ["engineering"]
        install(self.c, next_policy)
        self.c.create_delegation(
            "head",
            grantee="developer",
            actions=["draft"],
            projects=["app"],
            budget_cents=100,
            per_action_cents=100,
            expires_at=(now() + timedelta(hours=1)).isoformat(),
        )
        grant = self.c._effective_grant("developer")
        self.assertEqual(grant["departments"], ["engineering"])
        self.c._scope(
            "developer", "app", "draft", 0, department_id="engineering")
        with self.assertRaises(PermissionError):
            self.c._scope(
                "developer", "app", "draft", 0, department_id="marketing")


if __name__ == "__main__":
    unittest.main()
