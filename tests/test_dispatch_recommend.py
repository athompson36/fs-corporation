import json
import unittest
from pathlib import Path
from unittest.mock import patch

from company.core import Company, canonical
from company.dispatch_recommend import (
    _coerce_budget_cents,
    remaining_budget_cents,
    validate_suggestion,
)
from tests.test_api import owner_client
from tests.test_core import install, policy

# One past JavaScript Number.MAX_SAFE_INTEGER; must not round via float().
HUGE_CENTS_STRING = "9007199254740993"
HUGE_CENTS = int(HUGE_CENTS_STRING)


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

    def test_rejects_decimal_string_budget_cents(self):
        with self.assertRaises(ValueError):
            validate_suggestion(
                self._raw(departments=[{"id": "engineering", "budget_cents": "12.5"}]),
                self.catalog_ids,
                self.max_cents,
            )

    def test_huge_integer_string_budget_preserved_exactly(self):
        self.assertEqual(_coerce_budget_cents(HUGE_CENTS_STRING), HUGE_CENTS)
        out = validate_suggestion(
            self._raw(departments=[{"id": "engineering", "budget_cents": HUGE_CENTS_STRING}]),
            self.catalog_ids,
            HUGE_CENTS,
        )
        self.assertEqual(out["departments"][0]["budget_cents"], HUGE_CENTS)

    def test_accepts_leading_plus_budget_string(self):
        self.assertEqual(_coerce_budget_cents("+100"), 100)


class DispatchDeskWiringTests(unittest.TestCase):
    def test_desk_wires_dispatch_recommend_controls(self):
        desk = (Path(__file__).resolve().parents[1] / "company" / "service.py").read_text()
        for needle in (
            'id="dispatch-recommend-btn"',
            "/dispatch-options",
            "/dispatch-recommend",
            'id="dispatch-brief-template"',
            'id="dispatch-valid-values"',
            "presets_cents",
        ):
            self.assertIn(needle, desk)


class DispatchRecommendLiveTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "dash", "Dashboard API")
        with self.c.tx():
            self.c.db.execute(
                "INSERT OR REPLACE INTO model_profiles VALUES(?,?,?)",
                (
                    "live-dispatch",
                    canonical({
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "enabled": True,
                        "capabilities": ["text"],
                        "allowed_data": ["public", "internal"],
                    }),
                    1,
                ),
            )

    def test_options_and_recommend_http(self):
        h = {"Authorization": "Bearer owner-token"}
        opts = self.client.get("/api/v1/projects/dash/dispatch-options", headers=h)
        self.assertEqual(opts.status_code, 200, opts.text)
        self.assertEqual(opts.json()["project_id"], "dash")
        rec = self.client.post(
            "/api/v1/projects/dash/dispatch-recommend",
            json={"payload": {"use_live": False}},
            headers={**h, "Idempotency-Key": "rec-1"},
        )
        self.assertEqual(rec.status_code, 200, rec.text)
        body = rec.json()["result"]
        self.assertEqual(body["source"], "mock")
        self.assertFalse(body["live_attempted"])

    def test_live_bad_json_falls_back_to_mock(self):
        with patch.object(self.c, "invoke_model", return_value={"text": "not-json", "provider": "openai"}):
            with patch(
                "company.model_provider.status_summary",
                return_value={"live": True, "configured": True},
            ):
                out = self.c.recommend_dispatch("human-ceo", "dash", use_live=True)
        self.assertEqual(out["source"], "mock")
        self.assertTrue(out["live_attempted"])
        self.assertIn("live_unusable", out["notes"])

    def test_live_success_returns_validated_payload(self):
        payload = {
            "brief": "Live brief for dash",
            "acceptance_criteria": "Live criteria",
            "departments": [{"id": "engineering", "budget_cents": 300}],
        }
        with patch.object(
            self.c,
            "invoke_model",
            return_value={"text": json.dumps(payload), "provider": "openai"},
        ):
            with patch(
                "company.model_provider.status_summary",
                return_value={"live": True, "configured": True},
            ):
                out = self.c.recommend_dispatch("human-ceo", "dash", use_live=True)
        self.assertEqual(out["source"], "live")
        self.assertTrue(out["live_attempted"])
        self.assertEqual(out["brief"], "Live brief for dash")
        self.assertEqual(out["departments"][0]["id"], "engineering")
        self.assertEqual(out["departments"][0]["budget_cents"], 300)
