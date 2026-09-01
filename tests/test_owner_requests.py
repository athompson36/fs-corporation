import unittest
from company.service import create_app
from company.core import Company
from tests.test_core import install, policy


class OwnerRequestTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.c.register_identity("engineering:Director", "service", "head-token",
                                 ["owner.escalate", "task.create"])
        self.c.enroll_project("human-ceo", "app", "Main app")
        self.client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_head_escalates_and_ceo_responds(self):
        created = self.client.post("/api/v1/owner-inbox", json={
            "payload": {
                "department_id": "engineering",
                "kind": "feedback",
                "subject": "Need scope decision",
                "body": "Should we prioritize mobile or GitHub pilot?",
                "project_id": "app",
            }
        }, headers={"Authorization": "Bearer head-token", "Idempotency-Key": "esc-1"})
        self.assertEqual(created.status_code, 200)
        req_id = created.json()["result"]["id"]
        inbox = self.client.get("/api/v1/owner-inbox?status=open",
                                headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(len(inbox.json()["items"]), 1)
        dash = self.client.get("/api/v1/dashboard", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(dash.json()["owner_inbox_open"], 1)
        responded = self.client.post(f"/api/v1/owner-inbox/{req_id}/respond", json={
            "payload": {"response": "Prioritize mobile companion first."}
        }, headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "resp-1"})
        self.assertEqual(responded.status_code, 200)
        self.assertEqual(responded.json()["result"]["status"], "closed")
        self.assertEqual(self.client.get("/api/v1/dashboard",
                                         headers={"Authorization": "Bearer owner-token"}).json()["owner_inbox_open"], 0)

    def test_non_escalator_denied(self):
        self.c.register_identity("viewer", "service", "view-token", ["company.read"])
        r = self.client.post("/api/v1/owner-inbox", json={
            "payload": {
                "department_id": "engineering",
                "kind": "escalation",
                "subject": "Blocked",
                "body": "Help",
            }
        }, headers={"Authorization": "Bearer view-token"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
