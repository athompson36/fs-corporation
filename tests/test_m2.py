import json
from pathlib import Path
import unittest
from company.adapters import ChatDevAdapter, MockChatDevAdapter, WorkOrder
from company.chatdev_pin import PINNED_COMMIT, validate_chatdev_lock
from company.core import Company
from company.routing import choose_model


class CatalogAndRoutingTests(unittest.TestCase):
    def test_seed_catalog_and_task_assignment_precedence(self):
        c = Company()
        self.addCleanup(c.close)
        root = Path(__file__).resolve().parents[1]
        c.seed_catalog(root / "config" / "departments.json")
        c.seed_models(root / "config" / "models.example.json")
        self.assertTrue(c.db.execute("SELECT 1 FROM departments WHERE id='engineering'").fetchone())
        c.assign_model("human-ceo", "task", "t-review", "mock-text")
        registry = json.loads((root / "config" / "models.example.json").read_text())
        chosen = choose_model(registry, "engineering", "developer", "text", "public",
                              task_assignment="mock-text", company_default="reasoning-cloud")
        self.assertEqual(chosen["profile_id"], "mock-text")
        narrow = {"profiles": {
            "cloud": {"enabled": True, "capabilities": ["text"], "allowed_data": ["public"]},
            "local": {"enabled": True, "capabilities": ["text"], "allowed_data": ["public", "restricted"]}},
            "departments": {"engineering": ["cloud"]}, "positions": {}, "company_default": ["local"]}
        with self.assertRaises(LookupError):
            choose_model(narrow, "engineering", "developer", "text", "restricted", company_default="local")

    def test_chatdev_pin_and_mock_contract(self):
        lock = json.loads((Path(__file__).resolve().parents[1] / "config" / "upstream.lock.json").read_text())
        self.assertEqual(validate_chatdev_lock(lock, "def run_workflow(yaml_file, *, task_prompt):")["commit"], PINNED_COMMIT)
        with self.assertRaises(ValueError):
            validate_chatdev_lock({**lock, "commit": "deadbeef"})
        order = WorkOrder("t1", "p1", 1, "digest-abc", 10, {"tools": ["none"]})
        result = MockChatDevAdapter().run(order)
        self.assertFalse(result["accepted"])
        self.assertIn("session_name", result["meta_info"])
        self.assertEqual(result["meta_info"]["usage"]["cost_cents"], 0)
        with self.assertRaises(PermissionError):
            MockChatDevAdapter().run(WorkOrder("t1", "p1", 1, "digest-abc", 10, {"tools": ["shell"]}))
        with self.assertRaises(NotImplementedError):
            ChatDevAdapter().run(order)
        c = Company()
        self.addCleanup(c.close)
        c.db.execute("INSERT INTO work_orders VALUES(?,?,?,?,?,?,?)",
                     ("wo1", "t1", 1, "digest-abc", 10, "{}", "stored"))
        self.assertEqual(c.db.execute("SELECT workflow_digest FROM work_orders WHERE id='wo1'").fetchone()[0], "digest-abc")


if __name__ == "__main__":
    unittest.main()
