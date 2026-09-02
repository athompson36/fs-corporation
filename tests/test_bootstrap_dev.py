import unittest
from datetime import timedelta

from company.core import Company, now
from scripts.bootstrap_dev_company import bootstrap_dev


class BootstrapDevTests(unittest.TestCase):
    def test_bootstrap_adds_head_grant_and_app_project(self):
        c = Company()
        self.addCleanup(c.close)
        self.assertNotIn("head", c.policy().get("grants", {}))
        bootstrap_dev(c)
        self.assertIn("head", c.policy()["grants"])
        self.assertTrue(c.db.execute("SELECT 1 FROM projects WHERE id='app'").fetchone())
        c.queue_task("head", "app", "draft", 10, "bootstrap-test")
        bootstrap_dev(c)
        self.assertEqual(c.policy()["version"], c.policy()["version"])


if __name__ == "__main__":
    unittest.main()
