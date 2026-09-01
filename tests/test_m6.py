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


if __name__ == "__main__":
    unittest.main()
