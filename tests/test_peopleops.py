from datetime import timedelta
import unittest
from company.core import Company, now
from tests.test_core import install, policy

HR = "people:HR Director"


class EmployeeDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def hire_ada(self, **changes):
        args = dict(
            actor=HR, employee_id="dev-ada", position_id="engineering:Developer",
            display_name="Ada Developer",
            attributes={"seniority": "mid", "specialties": ["firmware"], "languages": ["en"]},
            background="Former ESP32 hobbyist; joined to expand board-support skills.")
        args.update(changes)
        return self.c.hire_employee(**args)

    def test_hire_stores_configurable_attributes_and_background(self):
        with self.assertRaises(PermissionError):
            self.hire_ada(actor="head")
        with self.assertRaises(ValueError):
            self.hire_ada(background="")
        hired = self.hire_ada()
        self.assertEqual(hired["id"], "dev-ada")
        self.assertEqual(hired["position_id"], "engineering:Developer")
        self.assertEqual(hired["attributes"]["seniority"], "mid")
        self.assertIn("ESP32", hired["background"])
        row = self.c.employee("dev-ada")
        self.assertEqual(row["display_name"], "Ada Developer")
        with self.assertRaises(ValueError):
            self.hire_ada(display_name="Duplicate")

    def test_hire_assigns_regular_pertinent_training_and_blocks_overdue_work(self):
        hired = self.hire_ada()
        self.assertTrue(hired["training"])
        skills = {a["skill_id"] for a in hired["training"]}
        self.assertIn("company-conduct", skills)
        due = self.c.training_due("dev-ada")
        self.assertTrue(due)
        p = policy(self.c)
        p["grants"]["dev-ada"] = p["grants"]["head"]
        install(self.c, p)
        with self.assertRaises(PermissionError) as blocked:
            self.c.execute_mock(actor="dev-ada", project="app", action="draft", cost=10, task_id="train1")
        self.assertIn("training", str(blocked.exception).lower())
        for item in hired["training"]:
            self.c.study_skill(
                "dev-ada", item["id"],
                source="https://example.com/training/"+item["skill_id"],
                title=item["skill_id"], published_at=now().isoformat(), observed_at=now().isoformat(),
                summary="Documented study for review.")
            self.c.certify_skill(HR, item["id"])
        self.assertEqual(self.c.training_due("dev-ada"), [])
        self.c.execute_mock(actor="dev-ada", project="app", action="draft", cost=10, task_id="train1")
        file = self.c.training_file(HR, "dev-ada")
        self.assertTrue(file["records"])
        self.assertTrue(all(r.get("summary") for r in file["records"]))
        with self.assertRaises(PermissionError):
            self.c.training_file("head", "dev-ada")
        stale = (now() - timedelta(days=120)).isoformat()
        self.c.db.execute("UPDATE acquired_skills SET acquired_at=? WHERE holder=?", (stale, "dev-ada"))
        refreshed = self.c.schedule_company_training(HR)
        self.assertTrue(any(a["learner"] == "dev-ada" and a["status"] == "assigned" for a in refreshed))
        self.assertTrue(self.c.training_due("dev-ada"))

    def test_performance_goals_reviews_and_trend(self):
        self.hire_ada()
        with self.assertRaises(PermissionError):
            self.c.set_performance_goal("dev-ada", "dev-ada", "Ship firmware", 80, "2026-Q3")
        goal = self.c.set_performance_goal(HR, "dev-ada", "Ship firmware", 80, "2026-Q3")
        self.assertEqual(goal["target"], 80)
        with self.assertRaises(PermissionError):
            self.c.record_performance_review("dev-ada", "dev-ada", 70, "self")
        first = self.c.record_performance_review(HR, "dev-ada", 70, "Met most goals; training in progress.")
        second = self.c.record_performance_review(HR, "dev-ada", 85, "Improved after certification.")
        trend = self.c.performance_trend(HR, "dev-ada")
        self.assertEqual([p["score"] for p in trend["points"]], [70, 85])
        self.assertEqual(trend["direction"], "improving")
        self.assertTrue(any(g["title"] == "Ship firmware" for g in trend["goals"]))
        self.assertEqual(first["employee_id"], "dev-ada")
        self.assertIn("training", second["notes"].lower() + first["notes"].lower())


if __name__ == "__main__":
    unittest.main()
