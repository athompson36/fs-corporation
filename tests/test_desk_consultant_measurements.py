"""Desk consultant work-order measurements surface (v0.3.87)."""
from __future__ import annotations

import unittest

from company.consultant import ConsultantDesk
from company.service import DESK_HTML, create_app
from fastapi.testclient import TestClient
from tests.test_api import owner_client
from tests.test_m1 import PROPOSAL


class DeskConsultantMeasurementsTests(unittest.TestCase):
    def test_desk_contracts(self):
        self.assertIn('id="consultant-measures-list"', DESK_HTML)
        self.assertIn("renderConsultantMeasures", DESK_HTML)
        self.assertIn("/work-orders/measurements", DESK_HTML)
        self.assertIn("complete-outcome", DESK_HTML)


class WorkOrderMeasurementsApiTests(unittest.TestCase):
    def test_list_measurements(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        desk = ConsultantDesk(c)
        pid = desk.submit("consultant", PROPOSAL)
        desk.decide("human-ceo", pid, "approved", "ok")
        oid = desk.to_work_order("human-ceo", pid)

        r = client.get(
            "/api/v1/work-orders/measurements",
            headers={"Authorization": "Bearer owner-token"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        items = r.json()["items"]
        self.assertTrue(any(row["work_order_id"] == oid for row in items))
        row = next(row for row in items if row["work_order_id"] == oid)
        self.assertIsNotNone(row["baseline"])
        self.assertIsNone(row["after"])

        detail = client.get(
            f"/api/v1/work-orders/{oid}/measurements",
            headers={"Authorization": "Bearer owner-token"},
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["work_order_id"], oid)

    def test_consultant_read_scope(self):
        c = owner_client()[0]
        self.addCleanup(c.close)
        client = TestClient(create_app(c))
        r = client.get(
            "/api/v1/work-orders/measurements",
            headers={"Authorization": "Bearer c-token"},
        )
        self.assertEqual(r.status_code, 200, r.text)

    def test_measurements_denied_without_read_scopes(self):
        c, _ = owner_client()
        self.addCleanup(c.close)
        c.register_identity("noscope", "service", "noscope-token", ["audit.read"])
        client = TestClient(create_app(c))
        r = client.get(
            "/api/v1/work-orders/measurements",
            headers={"Authorization": "Bearer noscope-token"},
        )
        self.assertEqual(r.status_code, 403, r.text)


if __name__ == "__main__":
    unittest.main()
