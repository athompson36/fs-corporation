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


if __name__ == "__main__":
    unittest.main()
