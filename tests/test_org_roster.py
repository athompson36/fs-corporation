"""Org roster, rules, and handoff (grant-backed)."""
from __future__ import annotations
import unittest
from pathlib import Path

from company.core import Company
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


if __name__ == "__main__":
    unittest.main()
