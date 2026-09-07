"""Impact brief HTTP API — list/create/correct; no auto-publish."""
from __future__ import annotations
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


class ImpactBriefApiTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Brief pilot")
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.addCleanup(self.c.close)
        self.client = TestClient(create_app(self.c))
        self.sid = self.c.ingest_signal(
            source="https://example.com/feed",
            title="Vendor announces breaking API change",
            published_at="2026-09-07T00:00:00+00:00",
            observed_at="2026-09-07T00:01:00+00:00",
            summary="Vendor announces breaking API change",
        )

    def test_list_empty_then_create_and_list(self):
        listed = self.client.get("/api/v1/impact-briefs", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["briefs"], [])

        created = self.client.post(
            "/api/v1/impact-briefs",
            json={"payload": {
                "signal_id": self.sid,
                "project_id": "app",
                "affected_summary": "API clients may need updates",
                "recommended_action": "Open engineering review task; do not publish",
                "cost_cents": 0,
                "authority": "human-ceo",
            }},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "brief-1"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        body = created.json()["result"]
        self.assertEqual(body["status"], "proposed")
        self.assertEqual(body["signal_id"], self.sid)
        brief_body = __import__("json").loads(body["body"])
        self.assertFalse(brief_body["auto_publish"])
        self.assertFalse(brief_body["trusted_instruction"])

        listed2 = self.client.get("/api/v1/impact-briefs", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(len(listed2.json()["briefs"]), 1)

        # Idempotent recreate
        again = self.client.post(
            "/api/v1/impact-briefs",
            json={"payload": {
                "signal_id": self.sid,
                "project_id": "app",
                "affected_summary": "other",
                "recommended_action": "other",
                "cost_cents": 0,
                "authority": "human-ceo",
            }},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "brief-2"},
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["result"]["id"], body["id"])

    def test_correct_marks_brief(self):
        self.c.create_impact_brief(
            self.sid, "app", "x", "y", 0, "human-ceo")
        r = self.client.post(
            f"/api/v1/signals/{self.sid}/correct",
            json={"payload": {"note": "Retracted by source"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "corr-1"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        status = self.c.db.execute(
            "SELECT status FROM impact_briefs WHERE signal_id=?", (self.sid,)
        ).fetchone()[0]
        self.assertEqual(status, "corrected")


if __name__ == "__main__":
    unittest.main()
