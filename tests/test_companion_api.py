import unittest
from pathlib import Path
from unittest.mock import patch
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
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "dash", "Dashboard rollout")
        activated = self.client.post(
            "/api/v1/projects/dash/departments/product/activate",
            json={"payload": {}},
            headers={
                "Authorization": "Bearer owner-token",
                "Idempotency-Key": "activate-product",
            },
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "dispatch-1"}
        r = self.client.post("/api/v1/projects/dash/dispatch-brief", json={
            "payload": {
                "brief": "Ship CEO mobile stats",
                "department_budgets": {"engineering": 300, "product": 200},
                "acceptance_criteria": "Dashboard API documented",
            }
        }, headers=headers)
        self.assertEqual(r.status_code, 200)
        dispatches = r.json()["result"]["dispatches"]
        self.assertEqual(len(dispatches), 2)
        detail = self.client.get("/api/v1/projects/dash", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(set(detail.json()["departments"]), {"engineering", "product"})
        events = self.c.db.execute("SELECT kind FROM events WHERE kind='project.dispatched'").fetchall()
        self.assertEqual(len(events), 2)

    def test_companion_dispatch_client_sends_department_budgets(self):
        client_source = (
            Path(__file__).resolve().parents[1] / "companion" / "src" / "api" / "client.ts"
        ).read_text()
        self.assertIn("department_budgets: departmentBudgets", client_source)
        self.assertNotIn("brief, departments, acceptance_criteria, budget_cents", client_source)

    def test_desk_surfaces_org_head_inbox_assignment_and_budget_map(self):
        desk_source = (
            Path(__file__).resolve().parents[1] / "company" / "service.py"
        ).read_text()
        self.assertIn('id="org-list"', desk_source)
        self.assertIn("'/api/v1/org'", desk_source)
        self.assertIn("seat.principal_id || 'vacant'", desk_source)
        self.assertIn('id="head-inbox-list"', desk_source)
        self.assertIn("'/api/v1/inbox/head'", desk_source)
        self.assertIn("department_budgets: departmentBudgets", desk_source)
        self.assertIn("'/api/v1/dispatches/' + encodeURIComponent(dispatch.id) + '/assign'", desk_source)

    def test_companion_wires_org_handoff_and_activation_clients(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client_source = (root / "api" / "client.ts").read_text()
        app_source = (root / "App.tsx").read_text()
        self.assertIn('"/api/v1/org"', client_source)
        self.assertIn('"/api/v1/inbox/head"', client_source)
        self.assertIn("/dispatches/${dispatchId}/assign", client_source)
        self.assertIn("/departments/${departmentId}/activate", client_source)
        self.assertIn('"organization"', app_source)
        self.assertIn("Department budget (¢)", app_source)
        self.assertNotIn("[s.trim(), 500]", app_source)

    def test_dashboard_unauthenticated(self):
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 401)

    def test_health_no_auth(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], __version__)
        self.assertEqual(body["db"], self.c.db_path)

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.ensure_corp_write_repo")
    @patch("company.github_app.repo_by_full_name")
    def test_github_assign_by_address(self, by_name, ensure_corp, _acct, _cfg):
        by_name.return_value = {"id": 11, "name": "demo", "full_name": "acme/demo", "owner": {"login": "acme"}}
        ensure_corp.return_value = ({"id": 22, "name": "demo-corp", "full_name": "acme/demo-corp"}, True)
        r = self.client.post(
            "/api/v1/projects/demo/github-assign",
            json={"payload": {"upstream": "https://github.com/acme/demo"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "gh-assign-1"},
        )
        self.assertEqual(r.status_code, 200)
        result = r.json()["result"]
        self.assertEqual(result["upstream"]["id"], "11")
        self.assertEqual(result["write_repo"]["full_name"], "acme/demo-corp")
        detail = self.client.get("/api/v1/projects/demo", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(detail.json()["github"]["fork_repo_id"], "22")

    def test_consultant_in_decisions_inbox(self):
        ConsultantDesk(self.c).submit("consultant", PROPOSAL)
        headers = {"Authorization": "Bearer owner-token"}
        items = self.client.get("/api/v1/decisions/inbox", headers=headers).json()["items"]
        self.assertTrue(any(i["kind"] == "consultant" for i in items))


if __name__ == "__main__":
    unittest.main()
