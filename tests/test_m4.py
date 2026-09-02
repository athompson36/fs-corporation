from datetime import timedelta
import unittest
from company.core import Company, now
from tests.test_core import install, policy


class GitHubPilotTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Pilot fork")
        self.c.enroll_github("human-ceo", "app", "111", "222", ["main"], "company/app/", ["push", "open_pr", "prepare_pr"])
        self.addCleanup(self.c.close)

    def test_denials_and_idempotent_effect(self):
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "999", "company/app/t1")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "main")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "random-branch")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "company/app/t1", path=".github/workflows/ci.yml")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "company/app/t1", head_sha="aaa", expected_sha="bbb")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "merge", "222", "company/app/t1")
        self.assertTrue(self.c.authorize_github_effect("app", "push", "222", "company/app/t1"))
        a = self.c.record_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        b = self.c.record_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(self.c.worktree_path("app", "t1"), "workspaces/app/t1")
        self.assertNotEqual(self.c.worktree_path("app", "t1"), "workspaces/human")

    def test_effect_lifecycle_records_then_fail_closed(self):
        first = self.c.apply_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        self.assertEqual(first["status"], "live_unavailable")
        self.assertIsNone(first["remote_id"])
        self.assertEqual(first["repo_id"], "222")
        self.assertEqual(first["operation"], "open_pr")
        retry = self.c.apply_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        self.assertEqual(first["id"], retry["id"])
        self.assertEqual(retry["status"], "live_unavailable")
        count = self.c.db.execute("SELECT COUNT(*) FROM github_effects WHERE task_id='t1'").fetchone()[0]
        self.assertEqual(count, 1)
        kinds = [r[0] for r in self.c.db.execute("SELECT kind FROM events WHERE kind LIKE 'github.%'")]
        self.assertIn("github.effect_recorded", kinds)
        self.assertIn("github.effect_live_unavailable", kinds)

    def test_effect_lifecycle_denies_before_record(self):
        with self.assertRaises(PermissionError):
            self.c.apply_github_effect("app", "t1", "push", "999", "company/app/t1")
        with self.assertRaises(PermissionError):
            self.c.apply_github_effect("app", "t1", "push", "222", "company/app/t1",
                                      head_sha="aaa", expected_sha="bbb")
        with self.assertRaises(PermissionError):
            self.c.apply_github_effect("app", "t1", "merge", "222", "company/app/t1")
        count = self.c.db.execute("SELECT COUNT(*) FROM github_effects").fetchone()[0]
        self.assertEqual(count, 0)

    def test_effect_lifecycle_direct_adapter_still_disabled(self):
        from company.adapters import GitHubAdapter, WorkOrder
        with self.assertRaises(NotImplementedError):
            GitHubAdapter().execute(WorkOrder("t1", "app", 1, "github-effect", 0, {"operation": "open_pr"}))


if __name__ == "__main__":
    unittest.main()
