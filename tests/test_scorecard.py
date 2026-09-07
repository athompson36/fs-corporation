"""CEO scorecard and objective lifecycle (Corporate HQ Phase 8)."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.migrate import HEAD_REVISION
from company.schema import COMPANION_SCOPES
from company.service import create_app
from tests.test_core import install, policy


CEO = "human-ceo"


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_metrics_use_only_persisted_rows_in_period(self):
        self.c.db.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)",
            ("accepted-in", "worker", "app", "draft", 80, 1, "accepted", "hash-in"),
        )
        self.c.db.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)",
            ("accepted-out", "worker", "old", "draft", 10, 1, "accepted", "hash-out"),
        )
        self.c._event("project.accepted", {"project": "app", "task_id": "accepted-in"})
        self.c._event("project.accepted", {"project": "old", "task_id": "accepted-out"})
        accepted_events = list(self.c.db.execute(
            "SELECT seq FROM events WHERE kind='project.accepted' ORDER BY seq"))
        self.c.db.execute(
            "UPDATE events SET at=? WHERE seq=?", ("2026-08-15T12:00:00+00:00", accepted_events[0]["seq"]))
        self.c.db.execute(
            "UPDATE events SET at=? WHERE seq=?", ("2026-07-31T23:59:59+00:00", accepted_events[1]["seq"]))
        self.c.db.execute(
            "INSERT INTO qc_inspections VALUES(?,?,?,?,?,?)",
            ("qc-pass", "accepted-in", "hash-in", "qc", "pass", "2026-08-16T00:00:00+00:00"),
        )
        self.c.db.execute(
            "INSERT INTO qc_inspections VALUES(?,?,?,?,?,?)",
            ("qc-fail", "accepted-in", "hash-in", "qc", "fail", "2026-08-17T00:00:00+00:00"),
        )
        self.c.db.execute(
            """INSERT INTO project_dispatches(
                 id,project_id,department_id,work_order_id,brief,acceptance_criteria,
                 budget_cents,due_at,created_at,status,head_principal_id,head_inbox_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("late", "app", "engineering", "wo", "brief", "criteria", 100,
             "2020-01-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00",
             "assigned", None, None),
        )
        self.c.db.execute("INSERT INTO ledger VALUES(?,?,?)", ("accepted-in", "worker", 80))
        self.c.db.execute(
            "INSERT INTO reservations VALUES(?,?,?,?,?,?)",
            ("reserve", "reserved-task", "worker", 20, "reserved", "2026-08-10T00:00:00+00:00"),
        )
        self.c.db.execute(
            "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
            ("bill-in", "2026-08-20T00:00:00+00:00", 25, 10, "provider", "profile", "test", None),
        )
        self.c.db.execute(
            "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
            ("bill-out", "2026-09-01T00:00:00+00:00", 1000, 10, "provider", "profile", "test", None),
        )

        scorecard = self.c.compute_scorecard(
            "2026-08-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00")

        self.assertEqual(scorecard["metrics"]["accepted_artifacts"], 1)
        self.assertEqual(scorecard["metrics"]["qc_pass_rate"], 0.5)
        self.assertEqual(scorecard["metrics"]["overdue_dispatches"], 1)
        self.assertEqual(scorecard["metrics"]["budget_adherence"], 0.8)
        self.assertEqual(scorecard["metrics"]["billed_cost_cents"], 25)
        self.assertEqual(scorecard["metrics"]["revenue_cents"], 0)

    def test_explicit_period_is_stable_and_snapshot_is_persisted(self):
        first = self.c.compute_scorecard(
            "2026-08-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00")
        second = self.c.compute_scorecard(
            "2026-08-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00")
        self.assertEqual(first, second)

        snapshot = self.c.record_scorecard_snapshot(
            "2026-08-01T00:00:00+00:00", "2026-09-01T00:00:00+00:00")
        self.assertEqual(snapshot["metrics"], first["metrics"])
        self.assertEqual(
            self.c.db.execute("SELECT COUNT(*) FROM scorecard_snapshots").fetchone()[0], 1)

    def test_objective_lifecycle_requires_ceo_or_admin(self):
        with self.assertRaisesRegex(PermissionError, "CEO authority required"):
            self.c.set_objective("engineering:head", "Ship Phase 8", "2026-09-30T00:00:00+00:00")

        objective = self.c.set_objective(
            CEO, "Ship Phase 8", "2026-09-30T00:00:00+00:00",
            target={"accepted_artifacts": 5})
        self.assertEqual(objective["target"], {"accepted_artifacts": 5})
        self.assertEqual(self.c.list_objectives("open")["items"][0]["id"], objective["id"])

        closed = self.c.close_objective(CEO, objective["id"])
        self.assertEqual(closed["status"], "closed")
        self.assertIsNotNone(closed["closed_at"])
        with self.assertRaisesRegex(ValueError, "already closed"):
            self.c.close_objective(CEO, objective["id"])


class ScorecardApiAndMigrationTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.register_identity(CEO, "owner", "owner-token")
        self.c.register_identity(
            "companion-admin-phone", "service", "admin-token", list(COMPANION_SCOPES))
        self.client = TestClient(create_app(self.c))
        self.addCleanup(self.c.close)

    def test_api_and_desk_expose_scorecard_and_objectives(self):
        headers = {"Authorization": "Bearer admin-token"}
        created = self.client.post(
            "/api/v1/objectives",
            headers=headers,
            json={"payload": {
                "title": "Improve quality",
                "due_at": "2026-10-01T00:00:00+00:00",
                "target": {"qc_pass_rate": 0.95},
            }},
        )
        self.assertEqual(created.status_code, 200, created.text)
        objective_id = created.json()["result"]["id"]

        listed = self.client.get("/api/v1/objectives?status=open", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["items"][0]["id"], objective_id)
        scorecard = self.client.get(
            "/api/v1/scorecard?period_start=2026-08-01T00:00:00%2B00:00"
            "&period_end=2026-09-01T00:00:00%2B00:00",
            headers=headers,
        )
        self.assertEqual(scorecard.status_code, 200, scorecard.text)
        self.assertEqual(scorecard.json()["metrics"]["revenue_cents"], 0)

        closed = self.client.post(
            f"/api/v1/objectives/{objective_id}/close",
            headers=headers,
            json={"payload": {}},
        )
        self.assertEqual(closed.status_code, 200, closed.text)
        desk = self.client.get("/desk").text
        self.assertIn("Measured from persisted operations — not simulated.", desk)
        self.assertIn("/api/v1/scorecard", desk)
        self.assertIn("objective-create-form", desk)

    def test_file_database_migrates_to_0023(self):
        self.assertEqual(HEAD_REVISION, "0024_company_settings")
        with tempfile.TemporaryDirectory() as directory:
            company = Company(str(Path(directory) / "scorecard.db"))
            try:
                tables = {
                    row["name"] for row in company.db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")
                }
                self.assertTrue({"objectives", "scorecard_snapshots"}.issubset(tables))
            finally:
                company.close()


if __name__ == "__main__":
    unittest.main()
