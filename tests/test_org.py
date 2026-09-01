from pathlib import Path
import json
import unittest
from company.core import Company, now
from tests.test_core import install, policy


QC = "quality:Quality Inspector"
HR = "people:HR Director"


class QualityControlTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_acceptance_requires_qc_pass_from_quality_department(self):
        t = self.c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="qc1")
        with self.assertRaises(PermissionError) as blocked:
            self.c.accept_project("human-ceo", "qc1", t["artifact_hash"])
        self.assertIn("quality", str(blocked.exception).lower())
        with self.assertRaises(PermissionError):
            self.c.inspect_quality("head", "qc1", t["artifact_hash"], "pass")
        with self.assertRaises(PermissionError):
            self.c.inspect_quality("human-ceo", "qc1", t["artifact_hash"], "pass")
        self.c.inspect_quality(QC, "qc1", t["artifact_hash"], "fail")
        with self.assertRaises(PermissionError):
            self.c.accept_project("human-ceo", "qc1", t["artifact_hash"])
        self.c.inspect_quality(QC, "qc1", t["artifact_hash"], "pass")
        self.c.accept_project("human-ceo", "qc1", t["artifact_hash"])
        self.assertEqual(self.c.status()["completions"], 1)

    def test_producer_cannot_qc_own_work(self):
        t = self.c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="qc2")
        with self.assertRaises(PermissionError):
            self.c.inspect_quality("head", "qc2", t["artifact_hash"], "pass")


class HumanResourcesTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_hardware_skills()
        self.addCleanup(self.c.close)

    def test_catalog_names_quality_and_hr(self):
        root = Path(__file__).resolve().parents[1]
        self.c.seed_catalog(root / "config" / "departments.json")
        rows = {r["id"]: dict(r) for r in self.c.db.execute("SELECT * FROM departments")}
        self.assertEqual(rows["quality"]["name"], "Quality Control")
        self.assertEqual(rows["people"]["name"], "Human Resources")
        self.assertTrue(rows["quality"]["initially_active"])
        self.assertTrue(rows["people"]["initially_active"])
        self.assertIn("Quality Inspector", {r["title"] for r in self.c.db.execute(
            "SELECT title FROM positions WHERE department_id='quality'")})
        models = json.loads((root / "config" / "models.example.json").read_text())
        self.assertIn("mock-text", models["departments"]["quality"])
        self.assertIn("mock-text", models["departments"]["people"])

    def test_hr_oversees_training_certification_and_roster(self):
        result = self.c.enroll_hardware_project(
            "human-ceo", "badge", "ESP32 firmware", platform="esp32")
        assignment = result["learning"][0]
        self.c.study_skill(
            assignment["learner"], assignment["id"],
            source="https://docs.espressif.com/projects/esp-idf/en/latest/",
            title="ESP-IDF", published_at=now().isoformat(), observed_at=now().isoformat(),
            summary="Official build steps.")
        with self.assertRaises(PermissionError):
            self.c.certify_skill(assignment["learner"], assignment["id"])
        with self.assertRaises(PermissionError):
            self.c.certify_skill("head", assignment["id"])
        self.c.certify_skill(HR, assignment["id"])
        roster = self.c.development_roster(HR)
        self.assertTrue(any(a["status"] == "acquired" for a in roster["assignments"]))
        self.assertTrue(any(s["holder"] == assignment["learner"] for s in roster["acquired"]))
        with self.assertRaises(PermissionError):
            self.c.development_roster("head")


if __name__ == "__main__":
    unittest.main()
