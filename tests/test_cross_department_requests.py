"""Cross-department request creation, delivery inbox, acceptance, and API."""
from __future__ import annotations

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class CrossDepartmentRequestTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Cross-department delivery")
        self.c.appoint_head("human-ceo", "engineering", "eng-head")
        self.c.appoint_head("human-ceo", "marketing", "marketing-head")
        self.addCleanup(self.c.close)

    def _create(self, actor="eng-head", **changes):
        args = {
            "project_id": "app",
            "requesting_department_id": "engineering",
            "delivering_department_id": "marketing",
            "budget_owner": "engineering",
            "due_at": "2026-09-30T17:00:00+00:00",
            "acceptance_criteria": "Campaign brief approved by Engineering",
            "escalation_path": "Escalate to human-ceo",
            "budget_cents": 750,
            "subject": "Prepare launch campaign",
            "brief": "Draft positioning and channel plan.",
        }
        args.update(changes)
        return self.c.create_cross_dept_request(actor, **args)

    def test_create_lists_for_delivering_head_then_accepts(self):
        created = self._create()

        self.assertEqual("pending_acceptance", created["status"])
        self.assertEqual(
            [created["id"]],
            [item["id"] for item in self.c.list_cross_dept_requests("marketing-head")["items"]],
        )
        self.assertEqual([], self.c.list_cross_dept_requests("eng-head")["items"])

        accepted = self.c.accept_cross_dept_request("marketing-head", created["id"])

        self.assertEqual("accepted", accepted["status"])
        self.assertEqual("marketing-head", accepted["accepted_by"])
        self.assertIsNotNone(accepted["accepted_at"])
        kinds = {
            row["kind"]
            for row in self.c.db.execute(
                "SELECT kind FROM events WHERE kind LIKE 'cross_department.%'"
            )
        }
        self.assertEqual(
            {"cross_department.request_created", "cross_department.request_accepted"},
            kinds,
        )

    def test_requesting_head_must_match_seated_requesting_department(self):
        with self.assertRaises(PermissionError):
            self._create(actor="marketing-head")

    def test_unknown_departments_fail_closed(self):
        for field in ("requesting_department_id", "delivering_department_id"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self._create(**{field: "unknown"})

    def test_dormant_delivering_department_requires_project_activation(self):
        self.c.appoint_head("human-ceo", "product", "product-head")

        with self.assertRaises(ValueError):
            self._create(delivering_department_id="product")

        self.c.activate_department_for_project("human-ceo", "app", "product")
        created = self._create(delivering_department_id="product")
        self.assertEqual("pending_acceptance", created["status"])

    def test_vacant_delivering_head_cannot_accept_but_ceo_can(self):
        created = self._create()
        self.c.vacate_head("human-ceo", "marketing")

        with self.assertRaises(PermissionError):
            self.c.accept_cross_dept_request("marketing-head", created["id"])

        accepted = self.c.accept_cross_dept_request("human-ceo", created["id"])
        self.assertEqual("human-ceo", accepted["accepted_by"])

    def test_non_delivering_head_cannot_accept(self):
        created = self._create()
        with self.assertRaises(PermissionError):
            self.c.accept_cross_dept_request("eng-head", created["id"])


class CrossDepartmentRequestApiTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Cross-department delivery")
        self.c.appoint_head("human-ceo", "engineering", "eng-head")
        self.c.appoint_head("human-ceo", "marketing", "marketing-head")
        self.c.register_identity(
            "eng-head", "service", "eng-token",
            ["organization.read", "organization.write"],
        )
        self.c.register_identity(
            "marketing-head", "service", "marketing-token",
            ["organization.read", "organization.write"],
        )
        self.client = TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_create_list_and_accept_api(self):
        create_response = self.client.post(
            "/api/v1/cross-department-requests",
            json={"payload": {
                "project_id": "app",
                "requesting_department_id": "engineering",
                "delivering_department_id": "marketing",
                "budget_owner": "engineering",
                "due_at": "2026-09-30T17:00:00+00:00",
                "acceptance_criteria": "Campaign brief approved",
                "escalation_path": "Escalate to human-ceo",
                "budget_cents": 750,
                "subject": "Prepare launch campaign",
                "brief": "Draft positioning and channel plan.",
            }},
            headers={
                "Authorization": "Bearer eng-token",
                "Idempotency-Key": "cross-create-1",
            },
        )
        self.assertEqual(200, create_response.status_code, create_response.text)
        created = create_response.json()["result"]

        inbox = self.client.get(
            "/api/v1/cross-department-requests",
            headers={"Authorization": "Bearer marketing-token"},
        )
        self.assertEqual(200, inbox.status_code, inbox.text)
        self.assertEqual([created["id"]], [item["id"] for item in inbox.json()["items"]])

        accepted = self.client.post(
            f"/api/v1/cross-department-requests/{created['id']}/accept",
            json={"payload": {}},
            headers={
                "Authorization": "Bearer marketing-token",
                "Idempotency-Key": "cross-accept-1",
            },
        )
        self.assertEqual(200, accepted.status_code, accepted.text)
        self.assertEqual("accepted", accepted.json()["result"]["status"])

    def test_create_api_requires_write_scope(self):
        self.c.register_identity(
            "eng-reader", "service", "read-token", ["organization.read"])
        response = self.client.post(
            "/api/v1/cross-department-requests",
            json={"payload": {}},
            headers={"Authorization": "Bearer read-token"},
        )
        self.assertEqual(403, response.status_code, response.text)


if __name__ == "__main__":
    unittest.main()
