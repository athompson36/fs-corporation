"""Suggested first production slice: Engineering draft → QC → CEO accept → Art/Marketing."""
from __future__ import annotations
import unittest
from datetime import timedelta
from pathlib import Path

from company.core import Company, now
from tests.test_core import install, policy, qc_pass


class ProductionSliceTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.addCleanup(self.c.close)

    def _extend_grants_for_art_marketing(self):
        p = self.c.policy()
        body = {
            "version": p["version"] + 1,
            "company_budget_cents": p["company_budget_cents"],
            "grants": {
                **p["grants"],
                "art": {
                    "actions": ["draft"],
                    "projects": ["app"],
                    "budget_cents": 50_000,
                    "per_action_cents": 10_000,
                    "expires_at": (now() + timedelta(days=30)).isoformat(),
                    "requires_approval": [],
                },
                "marketing": {
                    "actions": ["draft"],
                    "projects": ["app"],
                    "budget_cents": 50_000,
                    "per_action_cents": 10_000,
                    "expires_at": (now() + timedelta(days=30)).isoformat(),
                    "requires_approval": [],
                },
            },
        }
        pid = self.c.propose_policy("human-ceo", body, "Art/Marketing production slice grants")
        self.c.approve_policy("human-ceo", pid)

    def test_engineering_qc_accept_then_art_marketing(self):
        self.c.enroll_project("human-ceo", "app", "Production slice pilot")
        task = self.c.execute_mock(
            actor="head", project="app", action="draft", cost=25, task_id="slice-eng-1")
        self.assertEqual(task["status"], "produced")

        with self.assertRaises(PermissionError):
            self.c.accept_project("human-ceo", "slice-eng-1", task["artifact_hash"])

        qc_pass(self.c, {"id": "slice-eng-1", "artifact_hash": task["artifact_hash"]})
        self.c.accept_project("human-ceo", "slice-eng-1", task["artifact_hash"])
        accepted = self.c.db.execute("SELECT * FROM tasks WHERE id=?", ("slice-eng-1",)).fetchone()
        self.assertEqual(accepted["status"], "accepted")
        self.assertTrue(self.c.db.execute("SELECT 1 FROM completions WHERE project=?", ("app",)).fetchone())

        self._extend_grants_for_art_marketing()
        self.c.activate_department_for_project("human-ceo", "app", "art")
        self.c.activate_department_for_project("human-ceo", "app", "marketing")
        dispatches = self.c.dispatch_project_brief(
            "human-ceo", "app",
            brief="Add launch visuals and positioning for the accepted pilot deliverable",
            department_budgets={"art": 2_500, "marketing": 2_500},
            acceptance_criteria="Art asset + marketing brief recorded as mock drafts",
        )
        self.assertEqual({d["department_id"] for d in dispatches}, {"art", "marketing"})

        art = self.c.execute_mock(
            actor="art", project="app", action="draft", cost=10, task_id="slice-art-1")
        mkt = self.c.execute_mock(
            actor="marketing", project="app", action="draft", cost=10, task_id="slice-mkt-1")
        self.assertEqual(art["status"], "produced")
        self.assertEqual(mkt["status"], "produced")
        qc_pass(self.c, {"id": "slice-art-1", "artifact_hash": art["artifact_hash"]})
        with self.assertRaises(ValueError):
            self.c.accept_project("human-ceo", "slice-art-1", art["artifact_hash"])


if __name__ == "__main__":
    unittest.main()
