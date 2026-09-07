"""Runtime department and position CRUD (Phase 1)."""
from __future__ import annotations
import unittest
from pathlib import Path

from company.core import Company
from tests.test_core import install, policy

CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class DepartmentEditingTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.addCleanup(self.c.close)

    def test_create_update_retire_department(self):
        row = self.c.create_department(
            "human-ceo",
            department_id="research",
            name="Research",
            head_title="Research Director",
            mission="Explore opportunities",
            measures=["insights"],
            room_type="research-lab",
            initially_active=False,
            default_model_profile="mock-text",
        )
        self.assertEqual(row["id"], "research")
        self.assertEqual(row["origin"], "custom")
        self.assertEqual(row["status"], "dormant")
        seat = self.c.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?", ("research",)
        ).fetchone()
        self.assertEqual(seat["status"], "dormant")
        self.assertIsNone(seat["principal_id"])

        updated = self.c.update_department(
            "human-ceo", "research", name="Applied Research", reason="rebrand"
        )
        self.assertEqual(updated["name"], "Applied Research")
        rev = self.c.db.execute(
            "SELECT COUNT(*) FROM department_revisions WHERE department_id=?",
            ("research",),
        ).fetchone()[0]
        self.assertGreaterEqual(rev, 1)

        retired = self.c.retire_department("human-ceo", "research")
        self.assertEqual(retired["status"], "retired")

    def test_retire_blocked_by_active_seat(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        with self.assertRaises(ValueError) as ctx:
            self.c.retire_department("human-ceo", "engineering")
        self.assertIn("active seat", str(ctx.exception).lower())

    def test_create_update_retire_position(self):
        pos = self.c.create_position(
            "human-ceo", department_id="engineering", title="Platform Engineer"
        )
        self.assertEqual(pos["id"], "engineering:Platform Engineer")
        self.assertEqual(pos["status"], "active")
        updated = self.c.update_position(
            "human-ceo", pos["id"], title="Platform Engineer II"
        )
        self.assertEqual(updated["title"], "Platform Engineer II")
        self.assertEqual(updated["id"], "engineering:Platform Engineer II")
        retired = self.c.retire_position("human-ceo", updated["id"])
        self.assertEqual(retired["status"], "retired")

    def test_reorder_departments(self):
        self.c.reorder_departments(
            "human-ceo",
            [{"id": "engineering", "display_order": 10}, {"id": "art", "display_order": 5}],
        )
        eng = self.c.db.execute(
            "SELECT display_order FROM departments WHERE id=?", ("engineering",)
        ).fetchone()
        art = self.c.db.execute(
            "SELECT display_order FROM departments WHERE id=?", ("art",)
        ).fetchone()
        self.assertEqual(eng["display_order"], 10)
        self.assertEqual(art["display_order"], 5)

    def test_seed_preserves_custom_and_edited_seed(self):
        self.c.create_department(
            "human-ceo",
            department_id="custom-ops",
            name="Custom Ops",
            head_title="Ops Lead",
            mission="Custom",
            measures=["uptime"],
            room_type="operations-center",
            initially_active=True,
            default_model_profile="mock-text",
        )
        self.c.update_department(
            "human-ceo", "engineering", name="Software Engineering", reason="rename"
        )
        self.c.seed_catalog(CATALOG)
        custom = self.c.db.execute(
            "SELECT name, origin FROM departments WHERE id=?", ("custom-ops",)
        ).fetchone()
        self.assertEqual(custom["origin"], "custom")
        self.assertEqual(custom["name"], "Custom Ops")
        eng = self.c.db.execute(
            "SELECT name FROM departments WHERE id=?", ("engineering",)
        ).fetchone()
        self.assertEqual(eng["name"], "Software Engineering")

    def test_non_ceo_denied(self):
        with self.assertRaises(PermissionError):
            self.c.create_department(
                "stranger",
                department_id="x",
                name="X",
                head_title="Head",
                mission="m",
                measures=[],
                room_type="boardroom",
                initially_active=False,
                default_model_profile="mock-text",
            )

    def test_list_org_includes_editing_fields(self):
        org = self.c.list_org()
        eng = next(d for d in org["departments"] if d["id"] == "engineering")
        self.assertIn("origin", eng)
        self.assertIn("status", eng)
        self.assertIn("display_order", eng)
        self.assertEqual(eng["origin"], "seed")


class DepartmentEditingApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from company.service import create_app

        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.client = TestClient(create_app(self.c))
        self.headers = {"Authorization": "Bearer owner-token"}
        self.addCleanup(self.c.close)

    def test_create_department_api(self):
        r = self.client.post(
            "/api/v1/org/departments",
            headers={**self.headers, "Idempotency-Key": "dept-1"},
            json={
                "payload": {
                    "id": "analytics",
                    "name": "Analytics",
                    "head_title": "Analytics Director",
                    "mission": "Measure outcomes",
                    "measures": ["accuracy"],
                    "room_type": "research-lab",
                    "initially_active": False,
                    "default_model_profile": "mock-text",
                }
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json().get("result") or r.json()
        self.assertEqual(body["id"], "analytics")
        org = self.client.get("/api/v1/org", headers=self.headers)
        ids = {d["id"] for d in org.json()["departments"]}
        self.assertIn("analytics", ids)


if __name__ == "__main__":
    unittest.main()
