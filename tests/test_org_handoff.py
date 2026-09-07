"""Department-head inbox and dispatch assignment handoff."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from company.core import Company, now
from company.service import create_app
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class OrgHandoffTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Handoff")
        self.addCleanup(self.c.close)

    @staticmethod
    def _grant(actions, *, departments=None):
        grant = {
            "actions": actions,
            "projects": ["app"],
            "budget_cents": 500,
            "per_action_cents": 500,
            "expires_at": (now() + timedelta(days=1)).isoformat(),
            "requires_approval": [],
        }
        if departments is not None:
            grant["departments"] = departments
        return grant

    def _install_handoff_grants(
            self, *, head_departments=None, include_developer=True):
        next_policy = self.c.policy()
        next_policy["version"] += 1
        next_policy["company_budget_cents"] = 2_000
        next_policy["grants"]["eng-cto"] = self._grant(
            ["work.assign"], departments=head_departments)
        if include_developer:
            next_policy["grants"]["dev-1"] = self._grant(["draft"])
        proposal_id = self.c.propose_policy(
            "eng-cto", next_policy, "Grant department handoff authority")
        self.c.approve_policy("human-ceo", proposal_id)

    def _dispatch(self):
        return self.c.dispatch_project_brief(
            "human-ceo", "app", "Build it", {"engineering": 500}, "Reviewed draft")[0]

    def test_vacant_cannot_assign(self):
        dispatch = self._dispatch()
        with self.assertRaises(ValueError):
            self.c.assign_dispatch(
                "human-ceo", dispatch["id"], "dev-1",
                action="draft", cost_cents=10)

    def test_head_inbox_is_scoped_and_ceo_sees_all_open_dispatches(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        queued = self._dispatch()
        self.c.activate_department_for_project("human-ceo", "app", "product")
        blocked = self.c.dispatch_project_brief(
            "human-ceo", "app", "Plan it", {"product": 200}, "Approved plan")[0]

        self.assertEqual(
            [queued["id"]],
            [item["id"] for item in self.c.list_head_inbox("eng-cto")["items"]],
        )
        self.assertEqual(
            {queued["id"], blocked["id"]},
            {item["id"] for item in self.c.list_head_inbox("human-ceo")["items"]},
        )
        self.assertEqual([], self.c.list_head_inbox("other-head")["items"])

    def test_head_assigns_rostered_specialist(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.c.assign_position("human-ceo", "engineering:Developer", "dev-1")
        self._install_handoff_grants(head_departments=["engineering"])
        dispatch = self._dispatch()

        result = self.c.assign_dispatch(
            "eng-cto", dispatch["id"], "dev-1",
            action="draft", cost_cents=25)

        self.assertEqual("assigned", result["status"])
        queued = self.c.db.execute(
            "SELECT * FROM queue WHERE task_id=?", (result["queue_task_id"],)).fetchone()
        self.assertEqual("dev-1", queued["actor"])
        self.assertEqual("queued", queued["status"])

    def test_head_grant_must_cover_department(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.c.assign_position("human-ceo", "engineering:Developer", "dev-1")
        self._install_handoff_grants(head_departments=["marketing"])
        dispatch = self._dispatch()

        with self.assertRaises(PermissionError):
            self.c.assign_dispatch(
                "eng-cto", dispatch["id"], "dev-1",
                action="draft", cost_cents=10)

    def test_roster_miss_fails(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self._install_handoff_grants(include_developer=False)
        dispatch = self._dispatch()

        with self.assertRaises(PermissionError):
            self.c.assign_dispatch(
                "eng-cto", dispatch["id"], "not-on-roster",
                action="draft", cost_cents=10)

    def test_vacate_cancels_assigned_queue_and_blocks_open_dispatches(self):
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.c.assign_position("human-ceo", "engineering:Developer", "dev-1")
        self._install_handoff_grants()
        assigned = self.c.assign_dispatch(
            "eng-cto", self._dispatch()["id"], "dev-1",
            action="draft", cost_cents=25)
        still_open = self._dispatch()

        self.c.vacate_head("human-ceo", "engineering")

        queued = self.c.db.execute(
            "SELECT status FROM queue WHERE task_id=?",
            (assigned["queue_task_id"],),
        ).fetchone()
        open_dispatch = self.c.db.execute(
            "SELECT status, head_principal_id FROM project_dispatches WHERE id=?",
            (still_open["id"],),
        ).fetchone()
        self.assertEqual("cancelled", queued["status"])
        self.assertEqual("blocked_vacant_head", open_dispatch["status"])
        self.assertIsNone(open_dispatch["head_principal_id"])


class OrgHandoffApiTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Handoff")
        self.c.appoint_head("human-ceo", "engineering", "eng-cto")
        self.c.assign_position("human-ceo", "engineering:Developer", "dev-1")
        grants = self.c.policy()
        grants["version"] += 1
        grants["company_budget_cents"] = 2_000
        grants["grants"]["eng-cto"] = OrgHandoffTests._grant(
            ["work.assign"], departments=["engineering"])
        grants["grants"]["dev-1"] = OrgHandoffTests._grant(["draft"])
        proposal_id = self.c.propose_policy(
            "eng-cto", grants, "Grant API handoff authority")
        self.c.approve_policy("human-ceo", proposal_id)
        self.c.register_identity(
            "eng-cto", "service", "head-token",
            ["organization.read", "organization.write"])
        self.c.register_identity(
            "read-only-head", "service", "read-token", ["organization.read"])
        self.client = TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_head_reads_inbox_and_assigns_dispatch(self):
        dispatch = self.c.dispatch_project_brief(
            "human-ceo", "app", "Build it", {"engineering": 500}, "Reviewed draft")[0]
        headers = {"Authorization": "Bearer head-token"}

        inbox = self.client.get("/api/v1/inbox/head", headers=headers)
        assigned = self.client.post(
            f"/api/v1/dispatches/{dispatch['id']}/assign",
            json={"payload": {
                "assignee": "dev-1", "action": "draft", "cost_cents": 25,
            }},
            headers=headers,
        )

        self.assertEqual(200, inbox.status_code, inbox.text)
        self.assertEqual(dispatch["id"], inbox.json()["items"][0]["id"])
        self.assertEqual(200, assigned.status_code, assigned.text)
        self.assertEqual("assigned", assigned.json()["result"]["status"])

    def test_assign_api_requires_write_scope(self):
        dispatch = self.c.dispatch_project_brief(
            "human-ceo", "app", "Build it", {"engineering": 500}, "Reviewed draft")[0]
        response = self.client.post(
            f"/api/v1/dispatches/{dispatch['id']}/assign",
            json={"payload": {
                "assignee": "dev-1", "action": "draft", "cost_cents": 25,
            }},
            headers={"Authorization": "Bearer read-token"},
        )
        self.assertEqual(403, response.status_code, response.text)


if __name__ == "__main__":
    unittest.main()
