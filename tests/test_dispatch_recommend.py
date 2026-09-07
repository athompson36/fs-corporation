import unittest
from pathlib import Path
from company.core import Company
from tests.test_core import install, policy


class DispatchOptionsTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "mobile-app", "Mobile companion pilot with API tests")

    def test_options_lists_catalog_and_templates(self):
        opts = self.c.dispatch_options("mobile-app")
        self.assertEqual(opts["project_id"], "mobile-app")
        ids = {d["id"] for d in opts["departments"]}
        self.assertIn("engineering", ids)
        self.assertIn("art", ids)
        art = next(d for d in opts["departments"] if d["id"] == "art")
        self.assertFalse(art["dispatchable"])
        self.assertEqual(art["status"], "dormant")
        fields = opts["fields"]
        self.assertGreaterEqual(len(fields["brief"]["templates"]), 2)
        self.assertEqual(fields["department_budgets"]["presets_cents"], [100, 300, 500, 1000, 5000])
        self.assertGreaterEqual(fields["department_budgets"]["max_cents"], 0)

    def test_mock_recommend_keyword_split(self):
        out = self.c.recommend_dispatch("human-ceo", "mobile-app", use_live=False)
        self.assertEqual(out["source"], "mock")
        ids = {d["id"] for d in out["departments"] if d["recommended"]}
        self.assertIn("engineering", ids)
        self.assertIn("product", ids)
        self.assertIn("quality", ids)  # brief contains "tests"
        max_c = self.c.dispatch_options("mobile-app")["fields"]["department_budgets"]["max_cents"]
        for d in out["departments"]:
            self.assertGreaterEqual(d["budget_cents"], 0)
            self.assertLessEqual(d["budget_cents"], max_c)
