import unittest
from company import __version__
from company.core import Company, now
from company.service import create_app
from tests.test_api import owner_client
from tests.test_core import install, policy
from tests.test_m1 import PROPOSAL
from company.consultant import ConsultantDesk


class CompanionApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_dashboard_projects_and_decisions(self):
        self.c.enroll_project("human-ceo", "mobile-app", "Mobile companion pilot")
        pid = self.c.propose_policy("head", policy(self.c), "mobile test")
        headers = {"Authorization": "Bearer owner-token"}
        dash = self.client.get("/api/v1/dashboard", headers=headers)
        self.assertEqual(dash.status_code, 200)
        body = dash.json()
        self.assertIn("company", body)
        self.assertEqual(body["company"]["paused"], False)
        self.assertTrue(any(p["id"] == "mobile-app" for p in body["projects"]))
        self.assertTrue(any(d["kind"] == "policy" for d in body["pending_decisions"]))
        projects = self.client.get("/api/v1/projects", headers=headers)
        self.assertEqual(projects.status_code, 200)
        self.assertEqual(projects.json()["projects"][0]["id"], "mobile-app")
        detail = self.client.get("/api/v1/projects/mobile-app", headers=headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["brief"], "Mobile companion pilot")
        inbox = self.client.get("/api/v1/decisions/inbox", headers=headers)
        self.assertEqual(inbox.status_code, 200)
        self.assertTrue(inbox.json()["items"])
        self.c.approve_policy("human-ceo", pid)

    def test_dispatch_brief_creates_work_orders(self):
        from pathlib import Path
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "dash", "Dashboard rollout")
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "dispatch-1"}
        r = self.client.post("/api/v1/projects/dash/dispatch-brief", json={
            "payload": {
                "brief": "Ship CEO mobile stats",
                "departments": ["engineering", "product"],
                "acceptance_criteria": "Dashboard API documented",
                "budget_cents": 500,
            }
        }, headers=headers)
        self.assertEqual(r.status_code, 200)
        dispatches = r.json()["result"]["dispatches"]
        self.assertEqual(len(dispatches), 2)
        detail = self.client.get("/api/v1/projects/dash", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(set(detail.json()["departments"]), {"engineering", "product"})
        events = self.c.db.execute("SELECT kind FROM events WHERE kind='project.dispatched'").fetchall()
        self.assertEqual(len(events), 2)

    def test_dashboard_unauthenticated(self):
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 401)

    def test_health_no_auth(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], __version__)
        self.assertEqual(body["db"], self.c.db_path)

    def test_consultant_in_decisions_inbox(self):
        ConsultantDesk(self.c).submit("consultant", PROPOSAL)
        headers = {"Authorization": "Bearer owner-token"}
        items = self.client.get("/api/v1/decisions/inbox", headers=headers).json()["items"]
        self.assertTrue(any(i["kind"] == "consultant" for i in items))


if __name__ == "__main__":
    unittest.main()
