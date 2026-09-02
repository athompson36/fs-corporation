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

    def test_slos_unmeasured_until_sourced_observation(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        listed = c.list_slos()["items"]
        self.assertGreaterEqual(len(listed), 3)
        self.assertTrue(all(item["status"] == "unmeasured" for item in listed))
        self.assertTrue(all(item.get("value") is None for item in listed))
        with self.assertRaises(ValueError):
            c.record_slo_observation("human-ceo", "api.health_availability", 1.0, "", "2026-09-01T00:00:00+00:00", "2026-09-01T01:00:00+00:00")
        with self.assertRaises(LookupError):
            c.record_slo_observation("human-ceo", "invented.capacity", 99, "lab", "2026-09-01T00:00:00+00:00", "2026-09-01T01:00:00+00:00")
        with self.assertRaises(PermissionError):
            c.record_slo_observation("engineering-head", "api.health_availability", 1.0, "loopback curl", "2026-09-01T00:00:00+00:00", "2026-09-01T01:00:00+00:00")
        row = c.record_slo_observation(
            "human-ceo", "api.health_availability", 1.0, "loopback GET /api/v1/health",
            "2026-09-01T00:00:00+00:00", "2026-09-01T01:00:00+00:00")
        self.assertEqual(row["status"], "observed")
        self.assertEqual(row["source"], "loopback GET /api/v1/health")
        after = {item["id"]: item for item in c.list_slos()["items"]}
        self.assertEqual(after["api.health_availability"]["status"], "observed")
        self.assertEqual(after["api.request_latency_ms"]["status"], "unmeasured")


if __name__ == "__main__":
    unittest.main()
