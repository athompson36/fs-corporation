from datetime import timedelta
import tempfile
from pathlib import Path
import unittest
from company.core import Company, now
from tests.test_core import install, policy, qc_pass


class HeadquartersTests(unittest.TestCase):
    def test_projection_and_inspection(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "hq.db")
            c = Company(path)
            p = policy(c)
            p["grants"]["inspector"] = {
                "actions": ["inspect_room"], "projects": ["app"], "budget_cents": 0, "per_action_cents": 0,
                "expires_at": (now() + timedelta(days=1)).isoformat(), "requires_approval": []}
            install(c, p)
            t = c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="hq1")
            qc_pass(c, t)
            c.accept_project("human-ceo", "hq1", t["artifact_hash"])
            c.cost_expansion("human-ceo", "expansion-app", 0)
            c.approve_expansion("human-ceo", "expansion-app")
            self.assertTrue(c.inspect_expansion("inspector", "expansion-app", True))
            c.build_mock("builder", "expansion-app")
            before = c.headquarters()
            self.assertEqual(before["room_count"], 2)
            self.assertEqual(before["source"], "persisted_events")
            c.close()
            replay = Company(path)
            self.addCleanup(replay.close)
            self.assertEqual(replay.headquarters()["room_count"], 2)
            self.assertEqual([r["id"] for r in replay.headquarters()["rooms"]],
                             [r["id"] for r in before["rooms"]])
            replay.accept_project("human-ceo", "hq1", t["artifact_hash"])
            self.assertEqual(replay.status()["completions"], 1)

    def test_room_detail_from_persisted_work_only(self):
        c = Company()
        self.addCleanup(c.close)
        install(c, policy(c))
        with self.assertRaises(LookupError):
            c.room_detail("missing-room")
        empty = c.headquarters()
        self.assertEqual(empty["rooms"], [])
        t = c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="hq-room")
        qc_pass(c, t)
        c.accept_project("human-ceo", "hq-room", t["artifact_hash"])
        c.approve_expansion("human-ceo", "expansion-app")
        c.build_mock("builder", "expansion-app")
        detail = c.room_detail("expansion-app")
        self.assertEqual(detail["room"]["id"], "expansion-app")
        self.assertEqual(detail["room"]["source_project"], "app")
        self.assertEqual(detail["source"], "persisted_events")
        self.assertEqual([task["id"] for task in detail["tasks"]], ["hq-room"])
        self.assertEqual(detail["staff"], [])
        self.assertEqual(detail["deliverables"], [])
        self.assertEqual(detail["costs"]["simulated_spend_cents"], 10)
        self.assertNotIn("occupancy", detail)
        self.assertIn("occupancy_note", detail)

    def test_room_detail_includes_staff_and_artifact(self):
        root = Path(__file__).resolve().parents[1]
        c = Company()
        self.addCleanup(c.close)
        install(c, policy(c))
        c.seed_catalog(root / "config" / "departments.json")
        c.enroll_project("human-ceo", "app", "Persisted app brief")
        c.hire_employee("human-ceo", "dev-ada", "engineering:Developer", "Ada",
                        {"seniority": "mid"}, "Firmware background.")
        c.dispatch_project_brief(
            "human-ceo", "app", "Follow-up brief", ["engineering"], "Ship the accepted draft", 0)
        with tempfile.TemporaryDirectory() as d:
            digest_hex = c.store_artifact("head", "hq-art", "app", b"artifact-bytes", d)
        t = c.execute_mock(actor="head", project="app", action="draft", cost=25, task_id="hq-art")
        qc_pass(c, t)
        c.accept_project("human-ceo", "hq-art", t["artifact_hash"])
        c.approve_expansion("human-ceo", "expansion-app")
        c.build_mock("builder", "expansion-app")
        detail = c.room_detail("expansion-app")
        self.assertEqual([s["id"] for s in detail["staff"]], ["dev-ada"])
        self.assertEqual([item["hash"] for item in detail["deliverables"]], [digest_hex])
        self.assertEqual(detail["departments"][0]["id"], "engineering")
        kinds = {item["kind"] for item in detail["decisions"]}
        self.assertTrue({"project.accepted", "expansion.approved", "room.built"} & kinds)


if __name__ == "__main__":
    unittest.main()
