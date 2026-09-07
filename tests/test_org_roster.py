"""Org roster, rules, and handoff (grant-backed)."""
from __future__ import annotations
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from company.core import Company
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

    def test_non_ceo_cannot_appoint_without_later_grant_hook(self):
        # Milestone 1: CEO-only; milestone 2 may allow org.appoint_head grant.
        with self.assertRaises(PermissionError):
            self.c.appoint_head("stranger", "engineering", "eng-cto")

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


if __name__ == "__main__":
    unittest.main()
