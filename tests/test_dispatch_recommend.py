import unittest
from pathlib import Path
from company.core import Company
from company.dispatch_recommend import (
    remaining_budget_cents,
    validate_suggestion,
)
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
        self.assertIn("product", ids)
        product = next(d for d in opts["departments"] if d["id"] == "product")
        self.assertFalse(product["dispatchable"])
        self.assertEqual(product["status"], "dormant")
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

    def test_remaining_budget_decreases_with_ledger_spend(self):
        baseline = remaining_budget_cents(self.c)
        self.assertEqual(baseline, self.c.dispatch_options("mobile-app")["fields"]["department_budgets"]["max_cents"])
        self.c.db.execute(
            "INSERT INTO tasks(id, actor, project, action, cost, version, status, artifact_hash) "
            "VALUES(?,?,?,?,?,?,?,?)",
            ("dispatch-test", "head", "mobile-app", "draft", 120, self.c.policy()["version"], "done", None),
        )
        self.c.db.execute("INSERT INTO ledger VALUES(?,?,?)", ("dispatch-test", "head", 120))
        after = remaining_budget_cents(self.c)
        self.assertEqual(after, baseline - 120)
        self.assertEqual(
            self.c.dispatch_options("mobile-app")["fields"]["department_budgets"]["max_cents"],
            after,
        )


class ValidateSuggestionTests(unittest.TestCase):
    def setUp(self):
        self.catalog_ids = {"engineering", "product", "quality"}
        self.max_cents = 500

    def _raw(self, **overrides):
        payload = {
            "brief": "Ship feature",
            "acceptance_criteria": "Tests pass",
            "departments": [{"id": "engineering", "budget_cents": 100, "recommended": True}],
        }
        payload.update(overrides)
        return payload

    def test_drops_unknown_department_ids(self):
        out = validate_suggestion(
            self._raw(departments=[
                {"id": "engineering", "budget_cents": 100},
                {"id": "unknown-dept", "budget_cents": 200},
            ]),
            self.catalog_ids,
            self.max_cents,
        )
        self.assertEqual([d["id"] for d in out["departments"]], ["engineering"])

    def test_negative_budget_clamps_to_zero(self):
        out = validate_suggestion(
            self._raw(departments=[{"id": "engineering", "budget_cents": -50}]),
            self.catalog_ids,
            self.max_cents,
        )
        self.assertEqual(out["departments"][0]["budget_cents"], 0)

    def test_budget_above_max_clamps_to_max(self):
        out = validate_suggestion(
            self._raw(departments=[{"id": "engineering", "budget_cents": 900}]),
            self.catalog_ids,
            self.max_cents,
        )
        self.assertEqual(out["departments"][0]["budget_cents"], self.max_cents)

    def test_duplicate_department_ids_keep_last(self):
        out = validate_suggestion(
            self._raw(departments=[
                {"id": "engineering", "budget_cents": 100, "recommended": False},
                {"id": "engineering", "budget_cents": 300, "recommended": True},
            ]),
            self.catalog_ids,
            self.max_cents,
        )
        self.assertEqual(len(out["departments"]), 1)
        self.assertEqual(out["departments"][0]["budget_cents"], 300)
        self.assertTrue(out["departments"][0]["recommended"])

    def test_rejects_boolean_budget_cents(self):
        with self.assertRaises(ValueError):
            validate_suggestion(
                self._raw(departments=[{"id": "engineering", "budget_cents": True}]),
                self.catalog_ids,
                self.max_cents,
            )

    def test_rejects_non_whole_number_budget_cents(self):
        with self.assertRaises(ValueError):
            validate_suggestion(
                self._raw(departments=[{"id": "engineering", "budget_cents": 12.5}]),
                self.catalog_ids,
                self.max_cents,
            )
