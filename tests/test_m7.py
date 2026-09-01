from datetime import timedelta
import unittest
from company.core import Company, now
from tests.test_core import install, policy


class PortfolioTests(unittest.TestCase):
    def test_two_projects_memory_and_period_budget(self):
        c = Company()
        p = policy(c)
        p["grants"]["head"]["projects"] = ["app"]
        p["grants"]["other-head"] = {
            "actions": ["draft"], "projects": ["other"], "budget_cents": 200, "per_action_cents": 200,
            "expires_at": (now() + timedelta(days=1)).isoformat(), "requires_approval": []}
        install(c, p)
        self.addCleanup(c.close)
        c.enroll_project("human-ceo", "app", "First")
        c.enroll_project("human-ceo", "other", "Second")
        c.execute_mock(actor="head", project="app", action="draft", cost=40, task_id="a1")
        c.execute_mock(actor="other-head", project="other", action="draft", cost=40, task_id="b1")
        with self.assertRaises(PermissionError):
            c.execute_mock(actor="head", project="other", action="draft", cost=10, task_id="leak")
        c.put_memory("human-ceo", "m-app", "secret-a", "restricted", project_id="app", approved=True)
        with self.assertRaises(PermissionError):
            c.get_memory("other-head", "m-app", project_id="other")
        self.assertEqual(c.get_memory("head", "m-app", project_id="app")["body"], "secret-a")
        start = now().isoformat()
        end = (now() + timedelta(days=30)).isoformat()
        c.set_budget_period("human-ceo", "company", start, end, 90)
        with self.assertRaises(PermissionError):
            c.execute_mock(actor="head", project="app", action="draft", cost=20, task_id="over-period")
        c.record_benchmark("reviewer", "mock-text", 0.9, 12, 0, 0.0)
        c.consultant_cooldown("manual")
        with self.assertRaises(PermissionError):
            c.consultant_cooldown("manual")


if __name__ == "__main__":
    unittest.main()
